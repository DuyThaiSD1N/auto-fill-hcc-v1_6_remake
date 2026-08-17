import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.identity_merge import merge_identity_attachments
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_REQUESTER_IDENTITY_LABEL = "Căn cước công dân người yêu cầu"
_PAPER_DECLARATION_LABEL = "Tờ khai đăng ký khai tử bản giấy"
_DEATH_NOTICE_LABEL = "Giấy báo tử"
_DEATH_EVENT_PROOF_LABEL = "Giấy tờ chứng minh sự kiện chết"
_DEATH_PLACE_PROOF_LABEL = "Giấy tờ chứng minh nơi chết hoặc nơi phát hiện thi thể"
_OTHER_LABEL = "Tài liệu khai tử"

_ROW_2_COMPONENT = "- Giấy báo tử hoặc giấy tờ thay Giấy báo tử do cơ quan có thẩm quyền cấp."
_ROW_3_COMPONENT = (
    "- Giấy tờ, tài liệu, chứng cứ do cơ quan, tổ chức có thẩm quyền cấp hoặc xác nhận hợp lệ "
    "chứng minh sự kiện chết đối với trường hợp đăng ký khai tử cho người chết đã lâu"
)
_ROW_5_COMPONENT = (
    "- Trường hợp không xác định được nơi cư trú cuối cùng của người chết thì xuất trình giấy tờ "
    "chứng minh nơi người đó chết hoặc nơi phát hiện thi thể của người chết."
)


def _digits(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _fields_by_name(session: dict | None) -> dict[str, Any]:
    fields = (session or {}).get("fields") or []
    return {
        str(item.get("name")): item.get("value")
        for item in fields
        if isinstance(item, dict) and item.get("value") not in (None, "", {}, [])
    }


def _requester_identity_number_from_session(session: dict | None) -> str:
    values = _fields_by_name(session)
    return _digits(values.get("SoDinhDanhC") or values.get("SoGiayToDinhDanhC"))


def _canonical_type(value: str) -> str:
    text = re.sub(r"[\s_-]+", " ", str(value or "").strip().lower())
    if text in {"requester identity", "identity", "id", "cccd", "cmnd", "passport"}:
        return "requester_identity"
    if text in {"paper declaration", "declaration", "death declaration", "paper form"}:
        return "paper_declaration"
    if text in {"death notice", "death certificate", "death report", "death substitute document"}:
        return "death_notice"
    if text in {"death event proof", "old death proof", "authorization", "death proof"}:
        return "death_event_proof"
    if text in {"death place proof", "body found place proof", "place of death proof"}:
        return "death_place_proof"
    return "other"


def _label_for_type(doc_type: str, title: str = "") -> str:
    if doc_type == "requester_identity":
        return _REQUESTER_IDENTITY_LABEL
    if doc_type == "paper_declaration":
        return _PAPER_DECLARATION_LABEL
    if doc_type == "death_notice":
        return str(title or "").strip() or _DEATH_NOTICE_LABEL
    if doc_type == "death_event_proof":
        return str(title or "").strip() or _DEATH_EVENT_PROOF_LABEL
    if doc_type == "death_place_proof":
        return str(title or "").strip() or _DEATH_PLACE_PROOF_LABEL
    return str(title or "").strip() or _OTHER_LABEL


def _route_for_type(doc_type: str) -> tuple[str, int | None, str]:
    if doc_type == "death_notice":
        return "existing", 2, _ROW_2_COMPONENT
    if doc_type == "death_event_proof":
        return "existing", 3, _ROW_3_COMPONENT
    if doc_type == "death_place_proof":
        return "existing", 5, _ROW_5_COMPONENT
    return "new", None, ""


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    """Tên tài liệu KHÔNG được trùng (form coi trùng tên là 'đã có'). Trùng → thêm hậu tố ' 2', ' 3'..."""
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
            "fileName": item["fileName"],
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


def _identity_mismatch_warning(doc_type: str, text: str, requester_id: str, file_name: str) -> str | None:
    if doc_type != "requester_identity" or not requester_id:
        return None
    digits = _digits(text)
    if requester_id in digits:
        return None
    found_ids = re.findall(r"\d{9,12}", digits)
    if found_ids:
        return f"CCCD trong file {file_name} không khớp số định danh người yêu cầu từ bước 2."
    return None


def _build_item(file: dict, idx: int, doc_type: str, document_name: str) -> dict:
    target, component_index, existing_component = _route_for_type(doc_type)
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

def _resolve_document_name(file: dict, doc_type: str, detected: dict, used: set[str]) -> str:
    """Tên thành phần hồ sơ: ưu tiên documentName cụ thể từ LLM; 'other' thiếu thì theo tên file; dedup."""
    if doc_type == "other":
        fallback = _OTHER_LABEL
        base = detected.get("documentName") or file.get("name") or ""
    else:
        fallback = _label_for_type(doc_type)
        base = (
            detected.get("documentName")
            or _label_for_type(doc_type, detected.get("title", ""))
            or file.get("name")
            or ""
        )
    return _unique_document_name(base, used, fallback)


async def plan_khai_tu_attachments(
    files: list[FileItem],
    options: dict | None = None,
    session: dict | None = None,
) -> dict:
    _ = options or {}
    errors: list[str] = []
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    # import ocr đặt MODULE-LEVEL (không import trong hàm) — test monkeypatch được.
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]


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
            "fileName": file.get("name"),
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

    requester_id = _requester_identity_number_from_session(session)
    attachments: list[dict] = []
    classified: list[dict] = []
    used_names: set[str] = set()
    ocr_text_by_index: dict[int, str] = {}
    identity_indexes: set[int] = set()
    for idx, file in enumerate(raw_files):
        detected = llm_types.get(idx) or {"type": "other", "title": "", "documentName": ""}
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        ocr_text_by_index[idx] = text
        doc_type = detected["type"]
        if doc_type == "requester_identity":
            identity_indexes.add(idx)
        warning = _identity_mismatch_warning(doc_type, text, requester_id, str(file.get("name") or ""))
        if warning:
            errors.append(warning)
        document_name = _resolve_document_name(file, doc_type, detected, used_names)
        attachments.append(_build_item(file, idx, doc_type, document_name))
        classified.append({
            "fileName": file.get("name"),
            "type": doc_type,
            "documentName": document_name,
        })

    # Gộp CCCD 2 mặt CÙNG người thành 1 PDF (mặt trước→sau) vào ô giấy tùy thân.
    attachments = merge_identity_attachments(attachments, ocr_text_by_index, identity_indexes)

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [doc["fileName"] for doc in llm_docs],
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


plan = plan_khai_tu_attachments
