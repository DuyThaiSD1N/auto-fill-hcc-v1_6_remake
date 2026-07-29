"""Đính kèm bước 3 cho "Thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc".

Bảng thành phần hồ sơ:
  STT1 - Mẫu hộ tịch điện tử (Tờ khai): eform tự đính, KHÔNG xử lý.
  STT2 - Giấy tờ liên quan đến việc thay đổi/cải chính...: gắn giấy tờ hộ tịch chứng minh
         (giấy khai sinh / giấy đăng ký kết hôn hoặc trích lục kết hôn / giấy khai tử hoặc trích lục khai tử).
  STT3 - Văn bản ủy quyền (nếu có).
Các giấy tờ khác (CCCD, ...) → thêm thành phần hồ sơ MỚI.
"""
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

_HO_TICH_DOC_LABEL = "Giấy tờ hộ tịch chứng minh"
_AUTHORIZATION_LABEL = "Văn bản ủy quyền"
_IDENTITY_LABEL = "Căn cước công dân"
_OTHER_LABEL = "Tài liệu kèm theo"

# componentName để khớp đúng dòng có sẵn (substring đặc trưng + componentIndex theo STT).
_ROW_2_COMPONENT = "Giấy tờ liên quan đến việc thay đổi, cải chính, bổ sung thông tin hộ tịch"
_ROW_3_COMPONENT = "Văn bản ủy quyền"


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _canonical_type(value: str) -> str:
    text = re.sub(r"[\s_-]+", " ", str(value or "").strip().lower())
    if text in {"ho tich doc", "hotich", "civil status", "birth", "marriage", "death",
                "giay khai sinh", "trich luc ket hon", "trich luc khai tu"}:
        return "ho_tich_doc"
    if text in {"authorization", "uy quyen", "power of attorney"}:
        return "authorization"
    if text in {"identity", "cccd", "cmnd", "passport", "requester identity"}:
        return "identity"
    return "other"


def _route_for_type(doc_type: str) -> tuple[str, int | None, str]:
    if doc_type == "ho_tich_doc":
        return "existing", 2, _ROW_2_COMPONENT
    if doc_type == "authorization":
        return "existing", 3, _ROW_3_COMPONENT
    return "new", None, ""


def _label_for_type(doc_type: str) -> str:
    return {
        "ho_tich_doc": _HO_TICH_DOC_LABEL,
        "authorization": _AUTHORIZATION_LABEL,
        "identity": _IDENTITY_LABEL,
    }.get(doc_type, _OTHER_LABEL)


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
        {"index": item["index"], "fileName": item["fileName"], "text": _truncate_text(item.get("text", ""))}
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
            "documentName": str(item.get("documentName") or "").strip(),
        }

    out: dict[int, dict[str, str]] = {}
    # Bền vững: LLM trả đúng số lượng → map theo THỨ TỰ (tránh lệch 0/1-based index).
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


def _resolve_document_name(file: dict, doc_type: str, detected: dict, used: set[str]) -> str:
    fallback = _label_for_type(doc_type)
    base = detected.get("documentName") or fallback or file.get("name") or ""
    return _unique_document_name(base, used, fallback)


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


async def plan_thay_doi_ho_tich_attachments(
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
    for idx, file in enumerate(raw_files):
        detected = llm_types.get(idx) or {"type": "other", "documentName": ""}
        doc_type = detected["type"]
        document_name = _resolve_document_name(file, doc_type, detected, used_names)
        attachments.append(_build_item(file, idx, doc_type, document_name))
        classified.append({"fileName": file.get("name"), "type": doc_type, "documentName": document_name})

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


plan = plan_thay_doi_ho_tich_attachments
