"""Đính kèm cho thủ tục đăng ký kết hôn có yếu tố nước ngoài.

Form có các ô CỐ ĐỊNH (STT 1 = tờ khai tự sinh, KHÔNG đính):
  STT2 y tế | STT3 TTHN người nước ngoài | STT4 hộ chiếu/giấy tờ thay thế người nước ngoài
  STT5 văn bản cơ quan ngành | STT6 TTHN do ĐSQ/lãnh sự VN cấp
Các loại KHÔNG có ô sẵn (TTHN công dân VN trong nước, trích lục ghi chú ly hôn, CCCD VN...) → thành phần MỚI.
Mỗi ô cố định chỉ chứa 1 file; file dư cùng loại → thành phần mới.
"""
import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared import normalize_document_name
from app.pipelines._shared.identity_merge import merge_identity_attachments
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
_ALLOWED_LLM_TYPES = {
    "medical",
    "marital_foreign",
    "passport_foreign",
    "agency_confirm",
    "marital_diplomatic",
    "marital_vn",
    "divorce_note",
    "identity_vn",
    "other",
}

# Nhãn mặc định cho từng loại (documentName khi LLM không trả cụ thể).
_LABELS = {
    "medical": "Giấy xác nhận sức khỏe",
    "marital_foreign": "Giấy chứng minh tình trạng hôn nhân (nước ngoài)",
    "passport_foreign": "Hộ chiếu/giấy tờ tùy thân nước ngoài",
    "agency_confirm": "Văn bản xác nhận của cơ quan",
    "marital_diplomatic": "Giấy xác nhận tình trạng hôn nhân (cơ quan đại diện VN)",
    "marital_vn": "Giấy xác nhận tình trạng hôn nhân",
    "divorce_note": "Trích lục ghi chú ly hôn",
    "identity_vn": "Căn cước công dân",
    "other": "Tài liệu kèm theo hồ sơ kết hôn",
}

# Ô cố định: type → (componentIndex, đoạn text CÓ trong dòng để extension khớp).
_FIXED_SLOT = {
    "medical": (2, "Giấy xác nhận của tổ chức y tế"),
    "marital_foreign": (3, "Giấy tờ chứng minh tình trạng hôn nhân của người nước ngoài"),
    "passport_foreign": (4, "bản sao hộ chiếu"),
    "agency_confirm": (5, "công chức, viên chức"),
    "marital_diplomatic": (6, "Cơ quan đại diện ngoại giao"),
}


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _canonical_type(value: str) -> str:
    doc_type = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    return doc_type if doc_type in _ALLOWED_LLM_TYPES else "other"


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    key = _fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized
    stem = normalized[:45].strip() or fallback[:45].strip() or _LABELS["other"]
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
    docs = [{"index": d["index"], "text": _truncate_text(d.get("text", ""))} for d in documents]
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
    # Bền vững: LLM trả đúng số lượng → map theo THỨ TỰ (tránh lệch 0/1-based).
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


def _build_item(file: dict, idx: int, document_name: str,
                target: str, component_index: int | None, component_name: str) -> dict:
    return {
        "fileIndex": idx,
        "fileName": str(file.get("name") or f"file-{idx + 1}"),
        "documentName": document_name,
        "componentName": component_name if target == "existing" else document_name,
        "target": target,
        "componentIndex": component_index,
        "needsAddComponent": target == "new",
        "detectedType": document_name,
    }


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    _ = options or {}
    _ = session
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
        {"index": idx, "text": str(ocr_by_name.get(f.get("name"), {}).get("text") or "")}
        for idx, f in enumerate(raw_files)
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
    used_slots: set[int] = set()  # ô cố định đã bị chiếm
    # Người dân hay chụp CCCD 2 mặt thành 2 file rời → gom CÙNG NGƯỜI thành 1 PDF (helper hậu xử lý).
    ocr_text_by_index: dict[int, str] = {}
    identity_indexes: set[int] = set()
    for idx, file in enumerate(raw_files):
        detected = llm_types.get(idx) or {"type": "other", "documentName": ""}
        doc_type = detected["type"]
        ocr_text_by_index[idx] = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        if doc_type == "identity_vn":  # CCCD/CMND công dân VN → ứng viên gộp 2 mặt
            identity_indexes.add(idx)
        base_name = detected.get("documentName") or _LABELS.get(doc_type, _LABELS["other"]) or file.get("name")
        document_name = _unique_document_name(base_name, used_names, _LABELS.get(doc_type, _LABELS["other"]))

        slot = _FIXED_SLOT.get(doc_type)
        if slot and slot[0] not in used_slots:  # ô cố định còn trống → chiếm
            used_slots.add(slot[0])
            target, component_index, component_name = "existing", slot[0], slot[1]
        else:  # không có ô sẵn / ô đã bị chiếm → thành phần mới
            target, component_index, component_name = "new", None, ""

        item = _build_item(file, idx, document_name, target, component_index, component_name)
        attachments.append(item)
        classified.append({
            "fileName": file.get("name"), "type": doc_type, "documentName": document_name,
            "target": item["target"], "componentIndex": item["componentIndex"],
        })

    # Gộp CCCD 2 mặt cùng người → 1 item mang sourceFileIndexes (FE ghép pdf-lib); 2 người khác KHÔNG gộp.
    attachments = merge_identity_attachments(attachments, ocr_text_by_index, identity_indexes)

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [f["name"] for f in raw_files],
            "sessionId": (session or {}).get("request_id"),
            "classified": classified,
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
