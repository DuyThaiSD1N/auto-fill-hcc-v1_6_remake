"""Đính kèm cho thủ tục Cấp bản sao từ sổ gốc.

Thủ tục có đúng 2 thành phần hồ sơ (đều là ô CÓ SẴN trên form):
- STT 1: giấy tờ chứng minh quan hệ với người được cấp bản chính
  (Giấy khai sinh, Giấy chứng nhận kết hôn, Giấy báo tử, Trích lục khai tử...).
- STT 2 (bắt buộc): giấy tờ tùy thân của người yêu cầu (CCCD/Hộ chiếu...).

OCR + LLM chỉ để phân loại identity (→ STT 2) vs còn lại (→ STT 1); route là tất định.
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
_ALLOWED_LLM_TYPES = {"identity", "relationship_proof"}

_IDENTITY_LABEL = "Căn cước công dân"
_RELATIONSHIP_LABEL = "Giấy tờ chứng minh quan hệ"

# Nhãn nhận dạng ô hồ sơ trên form (frontend khớp theo substring đã fold).
_ROW_1_COMPONENT = (
    "Bản chính hoặc bản sao có chứng thực giấy tờ chứng minh quan hệ với người được cấp bản chính"
)
_ROW_2_COMPONENT = (
    "Một trong các giấy tờ sau: Căn cước điện tử; bản chính hoặc bản sao của Thẻ căn cước công dân"
)


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _canonical_type(value: str) -> str:
    doc_type = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
    return doc_type if doc_type in _ALLOWED_LLM_TYPES else "relationship_proof"


def _looks_like_identity(text: str) -> bool:
    """Fallback khi LLM lỗi/thiếu: nhận CCCD/Hộ chiếu qua các cụm đặc trưng của chính thẻ."""
    haystack = _fold(text or "")
    if (
        "can cuoc cong dan" in haystack
        or "the can cuoc" in haystack
        or "cccd" in haystack
        or "chung minh nhan dan" in haystack
        or "ho chieu" in haystack
        or "passport" in haystack
    ):
        return True
    if "so dinh danh ca nhan" not in haystack:
        return False
    markers = [
        "co gia tri den",
        "date of expiry",
        "noi thuong tru",
        "place of residence",
        "que quan",
        "place of origin",
        "dac diem nhan dang",
    ]
    return sum(1 for m in markers if m in haystack) >= 2


# Giấy tờ hộ tịch/chứng minh quan hệ (→ STT 1). Ưu tiên hơn identity vì các giấy này
# đời mới cũng in "số định danh cá nhân" nên dễ bị nhầm là giấy tùy thân.
_CIVIL_STATUS_MARKERS = (
    "giay khai sinh",
    "trich luc khai sinh",
    "giay chung nhan ket hon",
    "dang ky ket hon",
    "trich luc ket hon",
    "giay bao tu",
    "trich luc khai tu",
    "giay chung tu",
    "so ho khau",
)


def _detect_route_type(ocr_text: str) -> str | None:
    """Route TẤT ĐỊNH theo nội dung OCR. None = không rõ (để LLM/mặc định quyết)."""
    haystack = _fold(ocr_text or "")
    if not haystack.strip():
        return None
    if any(m in haystack for m in _CIVIL_STATUS_MARKERS):
        return "relationship_proof"
    if "ket hon" in haystack and any(k in haystack for k in ("vo", "chong", "ben nam", "ben nu")):
        return "relationship_proof"
    if _looks_like_identity(ocr_text):
        return "identity"
    return None


def _label_for_type(doc_type: str, document_name: str = "") -> str:
    document_name = str(document_name or "").strip()
    if document_name:
        return document_name
    return _IDENTITY_LABEL if doc_type == "identity" else _RELATIONSHIP_LABEL


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    key = _fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized

    stem = normalized[:45].strip() or fallback[:45].strip() or _RELATIONSHIP_LABEL
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

    docs = [{"index": item["index"], "text": _truncate_text(item.get("text", ""))} for item in documents]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(docs)},
    ]
    raw = await client.chat(messages, max_tokens=600, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []

    def _coerce(item: dict) -> dict[str, str]:
        return {
            "type": _canonical_type(str(item.get("type") or "")),
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
    if doc_type == "identity":
        component_index = 2
        component_name = _ROW_2_COMPONENT
    else:
        component_index = 1
        component_name = _ROW_1_COMPONENT
    return {
        "fileIndex": idx,
        "fileName": str(file.get("name") or f"file-{idx + 1}"),
        "documentName": document_name,
        "componentName": component_name,
        "target": "existing",
        "componentIndex": component_index,
        "needsAddComponent": False,
        "detectedType": document_name,
    }


async def plan(
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
        {"index": idx, "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or "")}
        for idx, file in enumerate(raw_files)
    ]

    t1 = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if any(d["text"].strip() for d in llm_docs):
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as e:  # noqa: BLE001
            errors.append(f"attachment_agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments: list[dict] = []
    classified: list[dict] = []
    used_names: set[str] = set()
    for idx, file in enumerate(raw_files):
        detected = llm_types.get(idx) or {"type": "", "documentName": ""}
        ocr_text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        # Route TẤT ĐỊNH theo nội dung OCR (không tin type LLM — hay nhầm GKS/kết hôn thành
        # identity vì có "số định danh"). LLM chỉ dùng cho documentName.
        doc_type = _detect_route_type(ocr_text)
        if doc_type is None:
            llm_type = detected.get("type") or ""
            doc_type = llm_type if llm_type in _ALLOWED_LLM_TYPES else "relationship_proof"

        base_name = detected.get("documentName") or _label_for_type(doc_type)
        fallback = _IDENTITY_LABEL if doc_type == "identity" else _RELATIONSHIP_LABEL
        document_name = _unique_document_name(base_name, used_names, fallback)

        item = _build_item(file, idx, doc_type, document_name)
        attachments.append(item)
        classified.append({
            "fileName": file.get("name"),
            "type": doc_type,
            "documentName": document_name,
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
