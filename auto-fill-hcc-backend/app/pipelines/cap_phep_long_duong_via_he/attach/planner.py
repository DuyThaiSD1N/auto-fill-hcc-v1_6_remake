"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Cấp phép sử dụng tạm thời lòng đường, vỉa hè" (cổng DVC
Bộ Xây dựng dvc.moc.gov.vn — Angular mat-table, engine FE `attp-row`, CÙNG cổng #63/#76/#78).

Bảng CÓ 2 DÒNG (cả 2 mặc định "Bản chính"):
  [1] "Phương án sử dụng tạm thời lòng đường vỉa hè vào mục đích khác, phương án tổ chức giao thông" —
      nhận Phương án / Sơ đồ vị trí / Giấy phép vỉa hè cũ.
  [2] "Văn bản đề nghị cấp phép sử dụng tạm thời lòng đường, vỉa hè" — nhận Đơn/Văn bản đề nghị.

componentName lấy đoạn text ĐẶC TRƯNG (2 dòng có leading khác nhau "Phương án"/"Văn bản đề nghị" nên không
lồng nhau) + componentIndex để chắc chắn. CCCD/GCN ĐKDN/cam kết/hợp đồng → other → bỏ qua (không có dòng).

Phân loại **LLM-primary**: LLM đọc OCR quyết định loại; rule keyword chỉ DỰ PHÒNG.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_phep_long_duong_via_he.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_PHUONG_AN = "phuong_an"
_VAN_BAN = "van_ban_de_nghi"
_OTHER = "other"

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold); componentIndex = STT dòng (1-based).
_ROWS: dict[str, dict[str, Any]] = {
    _PHUONG_AN: {
        "componentName": "Phương án sử dụng tạm thời lòng đường vỉa hè vào mục đích khác, phương án tổ chức giao thông",
        "componentIndex": 1,
        "loaiBan": "Bản chính",
        "documentName": "Phương án sử dụng tạm thời lòng đường, vỉa hè / phương án tổ chức giao thông",
    },
    _VAN_BAN: {
        "componentName": "Văn bản đề nghị cấp phép sử dụng tạm thời lòng đường, vỉa hè",
        "componentIndex": 2,
        "loaiBan": "Bản chính",
        "documentName": "Văn bản đề nghị cấp phép sử dụng tạm thời lòng đường, vỉa hè",
    },
}
_ALLOWED_DOC_TYPES = set(_ROWS) | {_OTHER}


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM)."""
    h = _fold(text)
    if not h:
        return ""
    if "phuong an" in h and ("giao thong" in h or "long duong" in h or "via he" in h):
        return _PHUONG_AN
    if "so do vi tri" in h or ("giay phep" in h and "via he" in h):
        return _PHUONG_AN
    if ("don de nghi" in h or "van ban de nghi" in h) and ("via he" in h or "long duong" in h or "cap phep" in h):
        return _VAN_BAN
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "phuong an" in text or "so do" in text or "giao thong" in text:
        return _PHUONG_AN
    if "van ban" in text or "don de nghi" in text or "de nghi" in text:
        return _VAN_BAN
    return value if value in _ALLOWED_DOC_TYPES else _OTHER


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
        "componentIndex": row["componentIndex"],
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
        # other = giấy tờ chỉ trích thông tin (CCCD/GCN ĐKDN/cam kết/hợp đồng) → bỏ qua, KHÔNG cảnh báo.
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
