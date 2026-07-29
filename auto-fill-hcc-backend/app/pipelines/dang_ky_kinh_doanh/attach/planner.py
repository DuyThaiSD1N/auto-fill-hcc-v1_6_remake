"""Đính kèm cho thủ tục Đăng ký thành lập hộ kinh doanh (cổng HkdOnline, ASP.NET).

Nghiệp vụ hiện tại chỉ dùng 2 loại đính kèm của cổng:
- BUSREGFRM: "Giấy đề nghị đăng ký hộ kinh doanh".
- OTHERS ("Khác"): mọi giấy tờ còn lại (CCCD, biên bản, ủy quyền...).

OCR + LLM chỉ để phân loại business_form vs other; route category là TẤT ĐỊNH.
FE (content/procedures/business-registration.js) tự suy ra attId (ô modal) + droptypleValue
(ô "Loại đính kèm") từ category, và tự tính danh sách loại cần khai báo trong modal.
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

# category cổng dùng: BUSREGFRM (Giấy đề nghị) | CPID (giấy tờ pháp lý cá nhân) | OTHERS (Khác).
_CAT_BUSREG = "BUSREGFRM"
_CAT_CPID = "CPID"
_CAT_OTHERS = "OTHERS"

_LABEL_BY_CAT = {
    _CAT_BUSREG: "Giấy đề nghị đăng ký hộ kinh doanh",
    _CAT_CPID: "Bản sao giấy tờ pháp lý của cá nhân",
    _CAT_OTHERS: "Khác",
}

# LLM type → category cổng.
_LLM_TO_CAT = {
    "business_form": _CAT_BUSREG,
    "personal_legal": _CAT_CPID,
    "other": _CAT_OTHERS,
}


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


# Marker tiêu đề/nội dung đặc trưng của GIẤY ĐỀ NGHỊ ĐĂNG KÝ HỘ KINH DOANH.
_BUSREG_MARKERS = (
    "giay de nghi dang ky ho kinh doanh",
    "de nghi dang ky ho kinh doanh",
    "giay de nghi dang ky thanh lap ho kinh doanh",
)

# Marker giấy tờ pháp lý CÁ NHÂN (CCCD/Căn cước/CMND/Hộ chiếu) → CPID.
_CPID_MARKERS = (
    "can cuoc cong dan",
    "the can cuoc",
    "chung minh nhan dan",
    "chung minh thu",
    "ho chieu",
    "passport",
)


def _detect_category(ocr_text: str) -> str | None:
    """Route TẤT ĐỊNH theo nội dung OCR. None = không rõ (để LLM/mặc định quyết)."""
    haystack = _fold(ocr_text or "")
    if not haystack.strip():
        return None
    # BUSREGFRM ưu tiên: giấy đề nghị cũng có "số định danh cá nhân" của chủ hộ, không được coi là CPID.
    if any(m in haystack for m in _BUSREG_MARKERS):
        return _CAT_BUSREG
    # "de nghi dang ky" + "ho kinh doanh" rời nhau (OCR ngắt dòng) vẫn là giấy đề nghị.
    if "ho kinh doanh" in haystack and "de nghi dang ky" in haystack:
        return _CAT_BUSREG
    if any(m in haystack for m in _CPID_MARKERS):
        return _CAT_CPID
    return None


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    normalized = normalize_document_name(base, fallback)
    key = _fold(normalized)
    if key and key not in used:
        used.add(key)
        return normalized

    stem = normalized[:45].strip() or fallback[:45].strip() or fallback
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
        t = str(item.get("type") or "").strip().lower()
        return {
            "type": t if t in _LLM_TO_CAT else "other",
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


def _build_item(file: dict, idx: int, category: str, document_name: str) -> dict:
    return {
        "fileIndex": idx,
        "fileName": str(file.get("name") or f"file-{idx + 1}"),
        "documentName": document_name,
        "componentName": _LABEL_BY_CAT[category],
        "target": "new",
        "needsAddComponent": False,
        "detectedType": _LABEL_BY_CAT[category],
        "category": category,
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
        # Route TẤT ĐỊNH theo nội dung OCR; LLM chỉ để fallback + documentName.
        category = _detect_category(ocr_text)
        if category is None:
            category = _LLM_TO_CAT.get(detected.get("type") or "", _CAT_OTHERS)

        base_name = detected.get("documentName") or _LABEL_BY_CAT[category]
        document_name = _unique_document_name(base_name, used_names, _LABEL_BY_CAT[category])

        item = _build_item(file, idx, category, document_name)
        attachments.append(item)
        classified.append({
            "fileName": file.get("name"),
            "category": category,
            "documentName": document_name,
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
