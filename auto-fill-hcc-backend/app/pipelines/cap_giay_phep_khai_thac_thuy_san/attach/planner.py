"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Cấp, cấp lại Giấy phép khai thác thủy sản" (cổng Nông
nghiệp & Môi trường — Angular mat-table, engine FE `attp-row`).

Bảng có 2 dòng cố định (hồ sơ nộp 1 trong 2):
  1) "Đơn đề nghị theo Mẫu số 04.KT ..."      ← cấp MỚI.
  2) "Đơn đề nghị cấp lại theo Mẫu số 05.KT ..." ← cấp LẠI.
FE khớp dòng bằng componentName (substring fold), tick checkbox + chọn loaiBan + set file. loaiBan =
"Scan tệp tin".

Phân loại **LLM-primary**: LLM đọc OCR quyết định loại; rule keyword chỉ DỰ PHÒNG. CCCD KHÔNG có dòng
riêng → bỏ qua.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_giay_phep_khai_thac_thuy_san.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_LOAI_BAN = "Scan tệp tin"

_CAP_MOI = "don_cap_moi"
_CAP_LAI = "don_cap_lai"
_CCCD = "cccd"
_GIAY_PHEP_CU = "giay_phep_cu"
_OTHER = "other"

_ROWS: dict[str, dict[str, str]] = {
    _CAP_MOI: {
        "componentName": "Đơn đề nghị theo Mẫu số 04",
        "loaiBan": _LOAI_BAN,
        "documentName": "Đơn đề nghị cấp Giấy phép khai thác thủy sản (Mẫu số 04.KT)",
    },
    _CAP_LAI: {
        "componentName": "Đơn đề nghị cấp lại theo Mẫu số 05",
        "loaiBan": _LOAI_BAN,
        "documentName": "Đơn đề nghị cấp lại Giấy phép khai thác thủy sản (Mẫu số 05.KT)",
    },
}
# CCCD + tờ GIẤY PHÉP cũ chỉ đối chiếu (nguồn số/ngày cấp cho pipeline điền),
# KHÔNG có dòng riêng trên bảng → bỏ qua, không sinh cảnh báo "đính thủ công".
_SKIP_DOCS = {_CCCD, _GIAY_PHEP_CU}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM). Cấp lại nhận TRƯỚC (đơn cấp lại cũng có 'khai thác')."""
    h = _fold(text)
    if not h:
        return ""
    # Đơn cấp lại (Mẫu 05) — có 'cấp lại' / 'lý do cấp lại' / 'mẫu số 05'.
    if "mau so 05" in h or "cap lai" in h or "ly do cap lai" in h:
        return _CAP_LAI
    # Đơn cấp mới (Mẫu 04).
    if "mau so 04" in h or ("de nghi cap" in h and "giay phep khai thac thuy san" in h):
        return _CAP_MOI
    # Tờ GIẤY PHÉP đã cấp (không phải đơn) — sau 2 nhánh đơn nên "de nghi" đã bị loại.
    if "giay phep khai thac thuy san" in h and "de nghi" not in h:
        return _GIAY_PHEP_CU
    # CCCD/CMND (bỏ qua).
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    # Token của LLM ("giay_phep_cu") phải nhận TRƯỚC nhánh "cap lai" (giấy phép cũ hay bị
    # LLM mô tả kèm chữ "cấp lại").
    if "giay_phep" in text or "giay phep cu" in text:
        return _GIAY_PHEP_CU
    if "cap lai" in text or "05" in text:
        return _CAP_LAI
    if "cap moi" in text or "04" in text:
        return _CAP_MOI
    if "cccd" in text or "can cuoc" in text or "cmnd" in text or "ho chieu" in text:
        return _CCCD
    return value if value in _ALLOWED_DOC_TYPES else _OTHER


async def _classify_with_llm(documents: list[dict[str, Any]]) -> dict[int, str]:
    if not documents:
        return {}
    messages = [
        {"role": "system", "content": prompt.SYSTEM_PROMPT},
        {"role": "user", "content": prompt.build_user_prompt(documents)},
    ]
    raw = await client.chat(messages, max_tokens=400, enable_thinking=settings.agent_reasoning)
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
        # LLM-primary: ưu tiên phán đoán LLM; rule keyword chỉ dự phòng khi LLM trả other/không hợp lệ.
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
