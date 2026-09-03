"""Đính kèm "Thành phần hồ sơ" cho "Cấp đổi Giấy chứng nhận QSDĐ..." (cổng DVC Đà Nẵng — engine `attp-row`).

Bảng thành phần hồ sơ có 3 dòng:
  (1) Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18)   → Bản chính
  (2) Bản gốc Giấy chứng nhận đã cấp                                         → Bản gốc
  (3) Mảnh trích đo bản đồ địa chính thửa đất                                → Bản sao
FE khớp dòng bằng componentName (substring fold), tick + chọn loaiBan + set file. Phân loại **LLM-primary**;
rule keyword chỉ DỰ PHÒNG. CCCD / Giấy ủy quyền / GCN ĐKDN không có dòng riêng → bỏ qua (chỉ đối chiếu).
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cap_doi_gcn_da_nang.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON_M18 = "don_m18"
_BAN_GOC_GCN = "ban_goc_gcn"
_MANH_TRICH_DO = "manh_trich_do"
_CCCD = "cccd"
_OTHER = "other"

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold vào nhãn dòng lấy từ DOM).
# loaiBan theo radio thật của từng dòng (đọc từ HTML đính kèm).
_ROWS: dict[str, dict[str, str]] = {
    _DON_M18: {"componentName": "Đơn đăng ký biến động đất đai", "loaiBan": "Bản chính",
               "documentName": "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18)"},
    _BAN_GOC_GCN: {"componentName": "Bản gốc Giấy chứng nhận đã cấp", "loaiBan": "Bản gốc",
               "documentName": "Bản gốc Giấy chứng nhận đã cấp (kèm Trang bổ sung nếu có)"},
    _MANH_TRICH_DO: {"componentName": "Mảnh trích đo bản đồ địa chính", "loaiBan": "Bản sao",
               "documentName": "Mảnh trích đo bản đồ địa chính thửa đất"},
}

# CCCD chỉ đối chiếu → bỏ qua.
_SKIP_DOCS = {_CCCD}
_ALLOWED_DOC_TYPES = set(_ROWS) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM). Dấu hiệu đặc trưng trước."""
    h = _fold(text)
    if not h:
        return ""
    if "don dang ky bien dong" in h or "mau so 18" in h:
        return _DON_M18
    if "manh trich do" in h or "trich do ban do dia chinh" in h or "phieu do dac" in h or ("do dac" in h and "thua dat" in h):
        return _MANH_TRICH_DO
    if "giay chung nhan quyen su dung dat" in h or ("giay chung nhan" in h and "quyen su dung dat" in h) or "trang bo sung" in h:
        return _BAN_GOC_GCN
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if text in _ALLOWED_DOC_TYPES:
        return text
    if "18" in text or ("don" in text and "bien dong" in text):
        return _DON_M18
    if "trich do" in text or "do dac" in text or "phieu" in text:
        return _MANH_TRICH_DO
    if "gcn" in text or "chung nhan" in text or "so do" in text or "bo sung" in text:
        return _BAN_GOC_GCN
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


def _build_row_item(file: dict, file_index: int, doc_type: str, *, fallback: bool = False) -> dict:
    row = _ROWS[doc_type]
    file_name = str(file.get("name") or f"file-{file_index + 1}")
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        # ⚠ GIỮ NGUYÊN TÊN FILE GỐC: FE (attp-row) đặt tên File tải lên = documentName (nếu có), rỗng thì
        # dùng tên gốc. Để RỖNG → không đổi tên file. Đồng thời FE dedup theo (documentName || fileName):
        # rỗng → dedup theo fileName (unique) nên NHIỀU file dồn vào cùng 1 dòng không bị coi trùng.
        "documentName": "",
        # Tên thành phần hồ sơ (để tham chiếu/hiển thị; KHÔNG dùng đặt tên file).
        "rowDocumentName": row["documentName"],
        "componentName": row["componentName"],
        "loaiBan": row["loaiBan"],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
        "fallback": fallback,
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

        # KHÔNG khớp dòng cụ thể (CCCD / giấy tờ khác / không xác định) → MẶC ĐỊNH đưa vào dòng "Đơn đăng ký
        # biến động" (thành phần chính) để KHÔNG bỏ sót file nào (user yêu cầu). Giữ tên file gốc; dòng đơn
        # nhận nhiều file. Cán bộ tự sắp xếp lại nếu cần.
        items.append(_build_row_item(file, idx, _DON_M18, fallback=True))
        classified.append({"fileName": file_name, "docType": doc_type, "source": source, "fallbackTo": _DON_M18})

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
