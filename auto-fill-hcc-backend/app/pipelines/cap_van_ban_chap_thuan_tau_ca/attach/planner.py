"""Đính kèm bước "Thành phần hồ sơ" cho thủ tục "Cấp văn bản chấp thuận đóng mới, cải hoán, thuê, mua
tàu cá Việt Nam" (cổng Nông nghiệp & Môi trường — Angular mat-table, engine FE `attp-row`).

Bảng thành phần hồ sơ có 1 dòng cố định: "Tờ khai theo Mẫu số 12.TC ...". FE khớp dòng bằng componentName
(substring fold), tick checkbox + chọn loaiBan + set file. Ta upload bản SCAN → loaiBan = "Scan tệp tin".

Phân loại **LLM-primary**: LLM đọc OCR quyết định loại; rule keyword chỉ DỰ PHÒNG. CCCD KHÔNG có dòng
riêng (chỉ đối chiếu) → bỏ qua.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_van_ban_chap_thuan_tau_ca.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_LOAI_BAN = "Scan tệp tin"

_TO_KHAI = "to_khai"
_CCCD = "cccd"
_OTHER = "other"

_ROWS: dict[str, dict[str, str]] = {
    _TO_KHAI: {
        "componentName": "Tờ khai theo Mẫu số 12",
        "loaiBan": _LOAI_BAN,
        "documentName": "Tờ khai chấp thuận đóng mới/cải hoán/thuê/mua tàu cá (Mẫu số 12.TC)",
    },
}
# CCCD chỉ đối chiếu, KHÔNG có dòng riêng trên bảng → bỏ qua.
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM)."""
    h = _fold(text)
    if not h:
        return ""
    # Tờ khai Mẫu 12.
    if "mau so 12" in h or ("to khai" in h and "tau ca" in h) \
            or ("chap thuan" in h and ("dong moi" in h or "cai hoan" in h)) \
            or "chu co so/ca nhan de nghi" in h:
        return _TO_KHAI
    # CCCD/CMND (bỏ qua).
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "to khai" in text or "12" in text or "tau ca" in text:
        return _TO_KHAI
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


def _build_row_item(file: dict, file_index: int, doc_type: str, document_name: str | None = None) -> dict:
    # Form CHỈ có 1 dòng "Tờ khai Mẫu 12" → mọi file đều đính vào dòng này (ô upload nhận NHIỀU file,
    # FE gom theo componentName). Tờ khai dùng tên chuẩn Mẫu 12; giấy tờ khác giữ TÊN GỐC (khỏi trùng tên).
    row = _ROWS[_TO_KHAI]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name or row["documentName"],
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

        # Form chỉ có 1 dòng "Tờ khai Mẫu 12" (ô upload nhận NHIỀU file) → ĐÍNH MỌI file vào dòng này.
        # Tờ khai → tên chuẩn Mẫu 12; CCCD/CNĐK tàu/thẩm định thiết kế/giấy tờ khác → giữ TÊN GỐC.
        document_name = _ROWS[_TO_KHAI]["documentName"] if doc_type == _TO_KHAI else file_name
        items.append(_build_row_item(file, idx, doc_type, document_name))
        classified.append({"fileName": file_name, "docType": doc_type, "source": source})

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
