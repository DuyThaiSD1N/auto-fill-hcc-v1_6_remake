"""Đính kèm "Thành phần hồ sơ" cho "Cấp điều chỉnh giấy phép xây dựng" (cổng Bộ Xây dựng dvc.moc.gov.vn —
Angular mat-table, engine FE `attp-row`, CÙNG cổng #114 tham_dinh_bcnckt).

Bảng có 5 dòng thành phần hồ sơ; FE khớp dòng bằng componentName substring fold, tick + chọn loaiBan +
set file. Phân loại **LLM-primary**; rule keyword chỉ DỰ PHÒNG. CCCD/ủy quyền → other (bỏ qua).
"""

import re
import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.dieu_chinh_giay_phep_xay_dung.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}


def _truncate(text: str, limit: int = 2500) -> str:
    """Loại giấy tờ nhận ra từ TRANG ĐẦU (tiêu đề); cắt ngắn để 3 file 9–11 trang không vượt context LLM."""
    value = re.sub(r"\s+", " ", text or "").strip()
    return value if len(value) <= limit else value[:limit] + "..."

_GPXD = "gpxd_da_cap"
_HSTK = "hstk_dieu_chinh"
_THAM_DINH = "bao_cao_tham_dinh"
_DAT_DAI = "giay_to_dat_dai"
_DON = "don_dieu_chinh"
_OTHER = "other"

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold). loaiBan tất cả "Bản chính".
_ROWS: dict[str, dict[str, str]] = {
    _GPXD: {
        "componentName": "Giấy phép xây dựng kèm theo hồ sơ bản vẽ đã được cấp",
        "loaiBan": "Bản chính",
        "documentName": "Giấy phép xây dựng đã cấp kèm bản vẽ",
    },
    _HSTK: {
        "componentName": "Bộ bản vẽ thiết kế xây dựng điều chỉnh",
        "loaiBan": "Bản chính",
        "documentName": "Bộ bản vẽ thiết kế xây dựng điều chỉnh",
    },
    _THAM_DINH: {
        "componentName": "Báo cáo kết quả thẩm định và văn bản phê duyệt thiết kế xây dựng điều chỉnh",
        "loaiBan": "Bản chính",
        "documentName": "Báo cáo thẩm định + văn bản phê duyệt thiết kế điều chỉnh",
    },
    _DAT_DAI: {
        "componentName": "Giấy tờ hợp pháp về đất đai",
        "loaiBan": "Bản chính",
        "documentName": "Giấy tờ hợp pháp về đất đai (GCN QSDĐ)",
    },
    _DON: {
        "componentName": "Đơn đề nghị điều chỉnh, gia hạn, cấp lại giấy phép xây dựng",
        "loaiBan": "Bản chính",
        "documentName": "Đơn đề nghị điều chỉnh GPXD (Mẫu số 02)",
    },
}
_ALLOWED_DOC_TYPES = set(_ROWS) | {_OTHER}


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM). Dấu hiệu đặc trưng trước, GCN/GPXD sau."""
    h = _fold(text)
    if not h:
        return ""
    if "don de nghi" in h and ("dieu chinh" in h or "gia han" in h or "cap lai" in h) and "giay phep xay dung" in h:
        return _DON
    if "giay phep moi truong" not in h and "giay phep xay dung" in h and ("cap cho" in h or "so" in h) \
            and "don de nghi" not in h:
        return _GPXD
    if ("ban ve" in h or "thiet ke" in h) and "dieu chinh" in h:
        return _HSTK
    if "ket qua tham dinh" in h and ("phe duyet" in h or "thiet ke" in h):
        return _THAM_DINH
    if "giay chung nhan quyen su dung dat" in h or ("giay chung nhan" in h and "quyen su dung dat" in h):
        return _DAT_DAI
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if text in _ALLOWED_DOC_TYPES:
        return text
    if "don" in text and ("dieu chinh" in text or "gia han" in text or "cap lai" in text):
        return _DON
    if "tham dinh" in text or "phe duyet" in text:
        return _THAM_DINH
    if "thiet ke" in text or ("ban ve" in text and "dieu chinh" in text):
        return _HSTK
    if "dat dai" in text or "qsdd" in text or "chung nhan" in text or "so do" in text:
        return _DAT_DAI
    if "gpxd" in text or "giay phep xay dung" in text:
        return _GPXD
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
        if llm_type in _ROWS:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown"

        if doc_type in _ROWS:
            items.append(_build_row_item(file, idx, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "source": source})
            continue
        warnings.append(f"Không xác định được loại giấy tờ cho file '{file_name}' — vui lòng đính kèm thủ công.")
        classified.append({"fileName": file_name, "docType": _OTHER, "source": source, "skipped": True})

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
            llm_docs.append({"index": idx, "text": _truncate(text)})

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
