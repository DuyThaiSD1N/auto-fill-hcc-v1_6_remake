"""Đính kèm "Thành phần hồ sơ" cho "Tách thửa đất hoặc hợp thửa đất" (cổng DVC Đà Nẵng — engine `attp-row`).

Bảng thành phần hồ sơ của form tách/hợp thửa có 4 dòng (KHÁC bảng 13 dòng của biến động QSDĐ):
  (1) Đơn đề nghị tách thửa đất, hợp thửa đất (Mẫu số 21)      → Bản chính
  (3) Giấy chứng nhận đã cấp (hoặc bản sao)                     → Bản sao
  (4) Văn bản của cơ quan có thẩm quyền (nếu có)                → Bản sao
  (5) Bản vẽ tách thửa đất, hợp thửa đất (Mẫu số 22)            → Bản sao
Giấy phép hoạt động đo đạc của đơn vị lập bản vẽ đính kèm CHUNG dòng (5).

FE khớp dòng bằng componentName (substring fold vào nhãn dòng), tick checkbox → chọn loaiBan (Bản chính/
Bản sao) → set file. Phân loại **LLM-primary**; rule keyword chỉ DỰ PHÒNG. CCCD / Hợp đồng ủy quyền không
có dòng riêng → bỏ qua.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.tach_hop_thua_dat_da_nang.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "don_m21"
_GCN = "gcn"
_VB_CQCTQ = "van_ban_cqctq"
_BAN_VE = "ban_ve_m22"
_GIAY_PHEP_DO_DAC = "giay_phep_do_dac"
_CCCD = "cccd"
_OTHER = "other"

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold vào nhãn dòng lấy từ DOM).
# loaiBan theo yêu cầu từng dòng của form (đọc từ HTML đính kèm thật).
_ROWS: dict[str, dict[str, str]] = {
    _DON: {"componentName": "Đơn đề nghị tách thửa đất, hợp thửa đất", "loaiBan": "Bản chính",
           "documentName": "Đơn đề nghị tách thửa đất, hợp thửa đất (Mẫu số 21)"},
    _GCN: {"componentName": "Giấy chứng nhận đã cấp", "loaiBan": "Bản sao",
           "documentName": "Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất"},
    _VB_CQCTQ: {"componentName": "văn bản của cơ quan có thẩm quyền", "loaiBan": "Bản sao",
           "documentName": "Văn bản của cơ quan có thẩm quyền về nội dung tách/hợp thửa"},
    _BAN_VE: {"componentName": "Bản vẽ tách thửa đất, hợp thửa đất", "loaiBan": "Bản sao",
           "documentName": "Bản vẽ tách thửa đất, hợp thửa đất (Mẫu số 22)"},
    # Giấy phép đo đạc đính kèm CHUNG dòng (5) Bản vẽ Mẫu 22 (cùng componentName + loaiBan).
    _GIAY_PHEP_DO_DAC: {"componentName": "Bản vẽ tách thửa đất, hợp thửa đất", "loaiBan": "Bản sao",
           "documentName": "Giấy phép hoạt động đo đạc và bản đồ (đơn vị lập bản vẽ)"},
}

# CCCD chỉ đối chiếu → bỏ qua.
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM). Dấu hiệu đặc trưng trước, GCN sau."""
    h = _fold(text)
    if not h:
        return ""
    if "don de nghi tach thua" in h or "don de nghi tach thua dat" in h or "mau so 21" in h:
        return _DON
    if "ban ve tach thua" in h or "ban ve tach thua dat" in h or "mau so 22" in h:
        return _BAN_VE
    if "giay phep hoat dong do dac" in h or ("giay phep" in h and "do dac va ban do" in h):
        return _GIAY_PHEP_DO_DAC
    if "co quan co tham quyen" in h and ("tach thua" in h or "hop thua" in h):
        return _VB_CQCTQ
    if "giay chung nhan quyen su dung dat" in h or ("giay chung nhan" in h and "quyen su dung dat" in h):
        return _GCN
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if text in _ALLOWED_DOC_TYPES:
        return text
    if "21" in text or ("don" in text and "tach" in text):
        return _DON
    if "do dac" in text or "giay phep" in text:
        return _GIAY_PHEP_DO_DAC
    if "22" in text or "ban ve" in text:
        return _BAN_VE
    if "co quan" in text or "tham quyen" in text or "cqctq" in text:
        return _VB_CQCTQ
    if "gcn" in text or "chung nhan" in text or "so do" in text:
        return _GCN
    if "cccd" in text or "can cuoc" in text or "cmnd" in text or "ho chieu" in text:
        return _CCCD
    return _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=500, enable_thinking=settings.agent_reasoning)
    parsed = client.extract_json_block(raw)
    out: dict[int, str] = {}
    for item in parsed.get("documents", []) or []:
        try:
            idx = int(item.get("index"))
        except Exception:  # noqa: BLE001
            continue
        out[idx] = _normalize_doc_type(str(item.get("docType") or item.get("type") or ""))
    return out


def _build_row_item(file: dict, file_index: int, doc_type: str) -> dict:
    row = _ROWS[doc_type]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": row["documentName"],
        "componentName": row["componentName"],
        "loaiBan": row["loaiBan"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
    }


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    by_name = {item.get("name"): item for item in ocr_results}
    items: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []

    for idx, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{idx + 1}")
        text = str(by_name.get(file_name, {}).get("text") or "")
        llm_type = llm_types.get(idx, "")
        rule_type = _rule_doc_type(text)
        # LLM-PRIMARY: ưu tiên LLM; rule chỉ dùng khi LLM rỗng/không hợp lệ (lỗi 502...).
        if llm_type in _ROWS or llm_type in _SKIP_DOCS:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown"

        if doc_type in _ROWS:
            items.append(_build_row_item(file, idx, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
            continue
        if doc_type in _SKIP_DOCS:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            continue

        warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — vui lòng đính kèm thủ công.")
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source})

    return items, warnings, classified


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
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    ocr_by_name = {item.get("name"): item for item in ocr_results}
    llm_docs: list[dict[str, Any]] = []
    for idx, file in enumerate(raw_files):
        text = str(ocr_by_name.get(file.get("name"), {}).get("text") or "")
        if text.strip():
            llm_docs.append({"index": idx, "text": text})

    t1 = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_docs:
        try:
            llm_types = await _classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - t1) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types)
    errors.extend(warnings)
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES]

    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[doc["index"]]["name"] for doc in llm_docs],
            "classified": classified,
            "skippedOcr": skipped_ocr,
            "rows": [{"docType": k, **v} for k, v in _ROWS.items()],
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
