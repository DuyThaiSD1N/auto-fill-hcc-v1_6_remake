import re
import time
from typing import Any

from app.config import settings
from app.pipelines.xac_nhan_tthn.attach import prompt
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines._shared.identity_merge import merge_identity_attachments
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_IDENTITY_LABEL = "Căn cước công dân"
_DIVORCE_OR_DEATH_LABEL = "Giấy tờ chứng minh đã ly hôn hoặc vợ chồng đã chết"
_FOREIGN_DIVORCE_NOTE_LABEL = "Trích lục ghi chú ly hôn"
_PREVIOUS_CERT_OR_AUTH_LABEL = "Giấy xác nhận tình trạng hôn nhân đã cấp hoặc văn bản ủy quyền"
_OTHER_LABEL = "Tài liệu chứng thực"

_ROW_2_COMPONENT = (
    "Trường hợp người yêu cầu cấp Giấy xác nhận tình trạng hôn nhân đã có vợ hoặc chồng "
    "nhưng đã ly hôn hoặc người vợ/chồng đã chết"
)
_ROW_3_COMPONENT = "Công dân Việt Nam đã ly hôn, hủy việc kết hôn ở nước ngoài"
_ROW_4_COMPONENT = "Trường hợp cá nhân yêu cầu cấp lại Giấy xác nhận tình trạng hôn nhân"


def _canonical_type(value: str) -> str:
    text = re.sub(r"[\s_-]+", " ", str(value or "").strip().lower())
    if text in {"identity", "id", "cccd", "cmnd", "passport"}:
        return "identity"
    if text in {"divorce or death proof", "divorce proof", "death proof"}:
        return "divorce_or_death_proof"
    if text in {"foreign divorce note", "divorce note"}:
        return "foreign_divorce_note"
    if text in {
        "previous marital status certificate or authorization",
        "previous certificate",
        "authorization",
    }:
        return "previous_marital_status_certificate_or_authorization"
    return "other"


def _label_for_type(doc_type: str, title: str = "") -> str:
    if doc_type == "identity":
        return _IDENTITY_LABEL
    if doc_type == "divorce_or_death_proof":
        return _DIVORCE_OR_DEATH_LABEL
    if doc_type == "foreign_divorce_note":
        return _FOREIGN_DIVORCE_NOTE_LABEL
    if doc_type == "previous_marital_status_certificate_or_authorization":
        return _PREVIOUS_CERT_OR_AUTH_LABEL
    return str(title or "").strip() or _OTHER_LABEL


def _route_for_type(doc_type: str) -> tuple[str, int | None, str]:
    if doc_type == "divorce_or_death_proof":
        return "existing", 2, _ROW_2_COMPONENT
    if doc_type == "foreign_divorce_note":
        return "existing", 3, _ROW_3_COMPONENT
    if doc_type == "previous_marital_status_certificate_or_authorization":
        return "existing", 4, _ROW_4_COMPONENT
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


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}

    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=700, enable_thinking=settings.agent_reasoning)
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


async def plan_xac_nhan_tthn_attachments(
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

    attachments: list[dict] = []
    classified: list[dict] = []
    used_names: set[str] = set()
    ocr_text_by_index: dict[int, str] = {}
    identity_indexes: set[int] = set()
    for idx, file in enumerate(raw_files):
        detected = llm_types.get(idx) or {"type": "other", "title": "", "documentName": ""}
        doc_type = detected["type"]
        ocr_text_by_index[idx] = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        if doc_type == "identity":
            identity_indexes.add(idx)
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
        # Cho trace hiện lại OCR (như các planner khác). AttachmentPlanResp tự lược khỏi HTTP response.
        "ocr_text": join_ocr_documents(ocr_results),
        "errors": errors,
    }


# Entrypoint thống nhất cho registry app.pipelines.<procedure>.attach.
plan = plan_xac_nhan_tthn_attachments
