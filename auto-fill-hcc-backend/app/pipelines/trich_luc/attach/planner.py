import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_LLM_TYPES = {
    "civil_status_birth",
    "civil_status_marriage",
    "civil_status_death",
    "identity",
    "authorization",
    "residence_proof",
    "paper_declaration",
    "other",
}

_BIRTH_LABEL = "Giấy khai sinh"
_MARRIAGE_LABEL = "Giấy đăng ký kết hôn"
_DEATH_LABEL = "Trích lục khai tử"
_IDENTITY_LABEL = "Căn cước công dân"
_AUTHORIZATION_LABEL = "Văn bản ủy quyền"
_RESIDENCE_LABEL = "Giấy tờ chứng minh cư trú"
_PAPER_DECLARATION_LABEL = "Tờ khai bản giấy"
_OTHER_LABEL = "Tài liệu trích lục hộ tịch"

_ROW_2_COMPONENT = "Văn bản ủy quyền theo quy định của pháp luật trong trường hợp ủy quyền"
_ROW_3_COMPONENT = "Hộ chiếu/Chứng minh nhân dân/Thẻ căn cước công dân/Thẻ căn cước/Căn cước điện tử"
_ROW_4_COMPONENT = "Giấy tờ có giá trị chứng minh thông tin về cư trú"


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _canonical_type(value: str) -> str:
    doc_type = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    return doc_type if doc_type in _ALLOWED_LLM_TYPES else "other"


def _label_for_type(doc_type: str, title: str = "") -> str:
    title = str(title or "").strip()
    if doc_type == "civil_status_birth":
        return _BIRTH_LABEL
    if doc_type == "civil_status_marriage":
        return _MARRIAGE_LABEL
    if doc_type == "civil_status_death":
        return _DEATH_LABEL
    if doc_type == "identity":
        return title or _IDENTITY_LABEL
    if doc_type == "authorization":
        return title or _AUTHORIZATION_LABEL
    if doc_type == "residence_proof":
        return title or _RESIDENCE_LABEL
    if doc_type == "paper_declaration":
        return _PAPER_DECLARATION_LABEL
    return title or _OTHER_LABEL


def _route_for_type(doc_type: str) -> tuple[str, int | None, str]:
    if doc_type == "authorization":
        return "existing", 2, _ROW_2_COMPONENT
    if doc_type == "identity":
        return "existing", 3, _ROW_3_COMPONENT
    if doc_type == "residence_proof":
        return "existing", 4, _ROW_4_COMPONENT
    return "new", None, ""


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    """Đảm bảo tên tài liệu KHÔNG trùng nhau (form coi trùng tên là 'đã có'). Trùng → thêm hậu tố ' 2', ' 3'..."""
    normalized = normalize_document_name(base, fallback)
    key = _fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized

    stem = normalized[:45].strip() or fallback[:45].strip() or _OTHER_LABEL
    n = 2
    while True:
        candidate = f"{stem} {n}"[:50].strip()
        key = _fold(candidate)
        if key not in used:
            used.add(key)
            return candidate
        n += 1


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}

    docs = [
        {
            "index": item["index"],
            "text": _truncate_text(item.get("text", "")),
        }
        for item in documents
    ]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(docs)},
    ]
    raw = await client.chat(messages, max_tokens=800, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []

    def _coerce(item: dict) -> dict[str, str]:
        return {
            "type": _canonical_type(str(item.get("type") or "")),
            "title": str(item.get("title") or "").strip(),
            "documentName": str(item.get("documentName") or "").strip(),
        }

    out: dict[int, dict[str, str]] = {}

    # Bền vững: LLM trả đúng số lượng → map theo THỨ TỰ (tránh lệch 0/1-based index gán nhầm file).
    if len(parsed_docs) == len(documents):
        for pos, item in enumerate(parsed_docs):
            out[documents[pos]["index"]] = _coerce(item)
        return out

    raw_items: list[tuple[int, dict]] = []
    for item in parsed_docs:
        try:
            raw_items.append((int(item.get("index")), item))
        except Exception:  # noqa: BLE001
            continue
    offset = 0 if any(r == 0 for r, _ in raw_items) else 1
    valid = {d["index"] for d in documents}
    for r, item in raw_items:
        idx = r - offset
        if idx in valid:
            out[idx] = _coerce(item)
    return out


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _pick_requester_identity(
    identity_indices: list[int], ocr_by_name: dict, raw_files: list[dict], options: dict | None
) -> int | None:
    """Chọn CCCD của NGƯỜI YÊU CẦU cho ô giấy tờ tùy thân (STT3).

    Ưu tiên khớp mỏ neo formContext (số định danh rồi tên); không có mỏ neo → lấy identity đầu tiên.
    """
    if not identity_indices:
        return None
    ctx = (options or {}).get("formContext") or {}
    want_id = _digits(ctx.get("applicantIdentityNumber"))
    want_name = _fold(ctx.get("applicantFullname"))
    if want_id or want_name:
        for idx in identity_indices:
            text = str(ocr_by_name.get(raw_files[idx].get("name"), {}).get("text") or "")
            if want_id and len(want_id) >= 9 and want_id in _digits(text):
                return idx
            if want_name and want_name in _fold(text):
                return idx
    return identity_indices[0]


def _build_item(
    file: dict, idx: int, doc_type: str, document_name: str,
    target: str, component_index: int | None, existing_component: str,
) -> dict:
    component_name = existing_component if target == "existing" else document_name
    return {
        "fileIndex": idx,
        "fileName": str(file.get("name") or f"file-{idx + 1}"),
        "documentName": document_name,
        "componentName": component_name,
        "target": target,
        "componentIndex": component_index,
        "needsAddComponent": target == "new",
        "detectedType": document_name,
    }


async def plan_trich_luc_attachments(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]

    from app.services import ocr


    t0 = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - t0) * 1000)
    for r in ocr_results:
        if r.get("error"):
            errors.append(f"OCR {r.get('name')}: {r['error']}")

    ocr_by_name = {r.get("name"): r for r in ocr_results}
    llm_docs = [
        {
            "index": idx,
            "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or ""),
        }
        for idx, file in enumerate(raw_files)
    ]

    t1 = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    # Mỗi ô cố định (STT 2/3/4) chỉ chứa 1 file. Riêng ô giấy tờ tùy thân (STT3) ưu tiên CCCD
    # của người yêu cầu; các CCCD khác (vd của con/chủ thể) → thành phần hồ sơ MỚI, không dồn 1 ô.
    identity_indices = [
        i for i in range(len(raw_files)) if (llm_types.get(i) or {}).get("type") == "identity"
    ]
    requester_identity = _pick_requester_identity(identity_indices, ocr_by_name, raw_files, options)

    attachments: list[dict] = []
    classified: list[dict] = []
    used_names: set[str] = set()
    used_slots: set[int] = set()  # componentIndex ô cố định đã bị chiếm
    for idx, file in enumerate(raw_files):
        detected = llm_types.get(idx) or {"type": "other", "title": "", "documentName": ""}
        doc_type = detected["type"]
        # Tên cơ sở: ưu tiên documentName CỤ THỂ từ LLM.
        # - "other": thiếu documentName → dùng tên file (OCR lỗi); chỉ về nhãn chung khi tên file vô nghĩa.
        # - loại đã biết: dùng nhãn loại; vẫn ưu tiên documentName nếu LLM cung cấp tên cụ thể hơn.
        if doc_type == "other":
            fallback = _OTHER_LABEL
            base_name = detected.get("documentName") or file.get("name") or ""
        else:
            fallback = _label_for_type(doc_type)
            base_name = (
                detected.get("documentName")
                or _label_for_type(doc_type, detected.get("title", ""))
                or file.get("name")
                or ""
            )
        document_name = _unique_document_name(base_name, used_names, fallback)

        target, component_index, existing_component = _route_for_type(doc_type)
        if target == "existing":
            # identity: chỉ CCCD người yêu cầu giữ ô STT3. Ô khác: file đầu tiên giữ ô, dư → mới.
            keeps_slot = (
                (idx == requester_identity) if doc_type == "identity"
                else (component_index not in used_slots)
            )
            if keeps_slot and component_index not in used_slots:
                used_slots.add(component_index)
            else:
                target, component_index, existing_component = "new", None, ""

        item = _build_item(file, idx, doc_type, document_name, target, component_index, existing_component)
        attachments.append(item)
        classified.append({
            "fileName": file.get("name"),
            "type": doc_type,
            "documentName": document_name,
            "target": item["target"],
            "componentIndex": item["componentIndex"],
        })

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [f["name"] for f in raw_files],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
        },
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
        "errors": errors,
    }


plan = plan_trich_luc_attachments
