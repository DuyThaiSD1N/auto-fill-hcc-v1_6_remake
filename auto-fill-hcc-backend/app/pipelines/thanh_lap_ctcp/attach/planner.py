"""Đính kèm cho thủ tục Đăng ký thành lập công ty cổ phần (cổng dangkyquamang.dkkd.gov.vn).

Cùng khuôn với app/pipelines/dang_ky_kinh_doanh/attach: OCR + LLM CHỈ để phân loại tài liệu và đặt
tên hiển thị; việc route sang category của cổng là TẤT ĐỊNH (đọc marker trong OCR trước, LLM chỉ là
lưới đỡ). Extension nhận `attachments` rồi tự khai loại + tải file lên cổng.

`category` ở đây là hợp đồng NGHIỆP VỤ (nhãn tiếng Việt đúng như cổng hiển thị), KHÔNG phải mã option
của cổng: mã option (`attId`/`droptyple` bên HkdOnline) là thứ chỉ đọc được từ DOM thật, chưa có nên
KHÔNG bịa — extension sẽ khớp theo NHÃN.
"""

import re
import time

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.process.schemas import FileItem
from app.services.llm import client

from .prompt import SYSTEM_PROMPT, build_user_prompt

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_CAT_BUSREG = "ENTREGFRM"        # Giấy đề nghị đăng ký doanh nghiệp
_CAT_CHARTER = "CHARTER"         # Điều lệ công ty
_CAT_FOUNDERS = "FOUNDERLIST"    # Danh sách cổ đông sáng lập / cổ đông là nhà đầu tư nước ngoài
_CAT_CPID = "CPID"               # Giấy tờ pháp lý của cá nhân
_CAT_AUTH = "AUTHORIZATION"      # Văn bản ủy quyền cho người nộp hồ sơ
_CAT_OTHERS = "OTHERS"           # Khác

# Nhãn phải trùng CHỮ hiển thị trên cổng — đây là thứ extension dùng để khớp option.
_LABEL_BY_CAT = {
    _CAT_BUSREG: "Giấy đề nghị đăng ký doanh nghiệp",
    _CAT_CHARTER: "Điều lệ công ty",
    _CAT_FOUNDERS: "Danh sách cổ đông sáng lập",
    _CAT_CPID: "Bản sao giấy tờ pháp lý của cá nhân",
    _CAT_AUTH: "Văn bản ủy quyền cho người đi nộp hồ sơ",
    _CAT_OTHERS: "Khác",
}

_LLM_TO_CAT = {
    "business_form": _CAT_BUSREG,
    "charter": _CAT_CHARTER,
    "founder_list": _CAT_FOUNDERS,
    "personal_legal": _CAT_CPID,
    "authorization": _CAT_AUTH,
    "other": _CAT_OTHERS,
}

_BUSREG_MARKERS = (
    "giay de nghi dang ky doanh nghiep",
    "de nghi dang ky doanh nghiep",
)
_CHARTER_MARKERS = ("dieu le cong ty", "dieu le")
_FOUNDER_MARKERS = (
    "danh sach co dong sang lap",
    "danh sach co dong la nha dau tu nuoc ngoai",
    "danh sach co dong",
)
_CPID_MARKERS = (
    "can cuoc cong dan",
    "the can cuoc",
    "chung minh nhan dan",
    "ho chieu",
    "passport",
)
_AUTH_MARKERS = ("giay uy quyen", "van ban uy quyen")


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _detect_category(ocr_text: str) -> str | None:
    """Route TẤT ĐỊNH theo nội dung OCR. None = không rõ (để LLM/mặc định quyết)."""
    haystack = _fold(ocr_text or "")
    if not haystack.strip():
        return None
    # Giấy đề nghị xét TRƯỚC: nó cũng chứa bảng cổ phần và số định danh cá nhân, dễ bị bắt nhầm
    # sang danh sách cổ đông hoặc giấy tờ cá nhân.
    if any(m in haystack for m in _BUSREG_MARKERS):
        return _CAT_BUSREG
    # Điều lệ cũng liệt kê cổ đông -> phải xét trước danh sách cổ đông; dấu hiệu chắc là "chương"/"điều".
    if "dieu le" in haystack and ("chuong" in haystack or "dieu 1" in haystack):
        return _CAT_CHARTER
    if any(m in haystack for m in _FOUNDER_MARKERS):
        return _CAT_FOUNDERS
    if any(m in haystack for m in _AUTH_MARKERS):
        return _CAT_AUTH
    if any(m in haystack for m in _CPID_MARKERS):
        return _CAT_CPID
    if any(m in haystack for m in _CHARTER_MARKERS):
        return _CAT_CHARTER
    return None


def _unique_document_name(base: str, used: set[str], fallback: str) -> str:
    name = re.sub(r"\s+", " ", str(base or "")).strip() or fallback
    name = name[:50].strip()
    if name not in used:
        used.add(name)
        return name
    for i in range(2, 50):
        candidate = f"{name} {i}"[:50].strip()
        if candidate not in used:
            used.add(candidate)
            return candidate
    used.add(name)
    return name


async def _classify_with_llm(documents: list[dict]) -> dict[int, dict[str, str]]:
    if not documents:
        return {}
    docs = [{"index": item["index"], "text": _truncate_text(item.get("text", ""))} for item in documents]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(docs)},
    ]
    raw = await client.chat(messages, max_tokens=800, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    parsed_docs = parsed.get("documents", []) or []

    def _coerce(item: dict) -> dict[str, str]:
        kind = str(item.get("type") or "").strip().lower()
        return {
            "type": kind if kind in _LLM_TO_CAT else "other",
            "documentName": str(item.get("documentName") or "").strip(),
        }

    out: dict[int, dict[str, str]] = {}
    # LLM trả đúng số lượng -> map theo THỨ TỰ, tránh lệch index 0/1-based gán nhầm file.
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
        "detectedType": _LABEL_BY_CAT[category],
        "category": category,
        "target": "new",
        "needsAddComponent": False,
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
    for result in ocr_results:
        if result.get("error"):
            errors.append(f"OCR {result.get('name')}: {result['error']}")

    ocr_by_name = {r.get("name"): r for r in ocr_results}
    llm_docs = [
        {"index": idx, "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or "")}
        for idx, file in enumerate(raw_files)
    ]

    t1 = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if any(doc["text"].strip() for doc in llm_docs):
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
        category = _detect_category(ocr_text)
        if category is None:
            category = _LLM_TO_CAT.get(detected.get("type") or "", _CAT_OTHERS)

        base_name = detected.get("documentName") or _LABEL_BY_CAT[category]
        document_name = _unique_document_name(base_name, used_names, _LABEL_BY_CAT[category])

        attachments.append(_build_item(file, idx, category, document_name))
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
