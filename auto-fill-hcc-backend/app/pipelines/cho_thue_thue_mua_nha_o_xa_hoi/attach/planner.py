"""Đính kèm bước "Thành phần hồ sơ" cho "Cho thuê, cho thuê mua nhà ở xã hội…" (cổng DVC Bộ Xây dựng
dvc.moc.gov.vn — Angular mat-table, engine FE `attp-row`, CÙNG cổng #63/#76/#78/#113).

Bảng có 8 dòng (hồ sơ THUÊ chỉ dùng 3 dòng liên quan, đều "Bản chính"):
  [5] "Đơn đăng ký thuê nhà ở xã hội theo mẫu"                         ← Tờ đơn (to_don)
  [1] "Giấy tờ chứng minh điều kiện được hưởng chính sách…nhà ở xã hội" ← giấy CM đối tượng/điều kiện
  [7] "Trường hợp thuê nhà ở xã hội"                                    ← CCCD/giấy tờ tùy thân
(componentIndex theo thứ tự DOM trang đính kèm mẫu; FE khớp CHÍNH bằng componentName substring fold, index
chỉ là chốt phụ. Các dòng "thuê MUA" không dùng vì hồ sơ chọn THUÊ.)

componentName lấy đoạn text ĐẶC TRƯNG, KHÔNG lồng nhau: "thuê nhà ở xã hội theo mẫu" ≠ "thuê MUA nhà…";
"Trường hợp thuê nhà ở xã hội" ≠ "Trường hợp thuê mua…". GCN ĐKDN/sổ hộ khẩu → other → bỏ qua.

Phân loại **LLM-primary**: LLM đọc OCR quyết định loại; rule keyword chỉ DỰ PHÒNG.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_TO_DON = "to_don"
_DOI_TUONG = "doi_tuong"
_CCCD = "cccd"
_OTHER = "other"

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold); componentIndex = STT dòng (1-based).
_ROWS: dict[str, dict[str, Any]] = {
    _TO_DON: {
        "componentName": "Đơn đăng ký thuê nhà ở xã hội theo mẫu",
        "componentIndex": 5,
        "loaiBan": "Bản chính",
        "documentName": "Đơn đăng ký thuê nhà ở xã hội theo mẫu",
    },
    _DOI_TUONG: {
        "componentName": "Giấy tờ chứng minh điều kiện được hưởng chính sách hỗ trợ về nhà ở xã hội",
        "componentIndex": 1,
        "loaiBan": "Bản chính",
        "documentName": "Giấy tờ chứng minh điều kiện được hưởng chính sách hỗ trợ về nhà ở xã hội",
    },
    _CCCD: {
        "componentName": "Trường hợp thuê nhà ở xã hội",
        "componentIndex": 7,
        "loaiBan": "Bản chính",
        "documentName": "Giấy tờ chứng minh đối tượng - trường hợp thuê nhà ở xã hội (CCCD/tùy thân)",
    },
}
_ALLOWED_DOC_TYPES = set(_ROWS) | {_OTHER}


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM)."""
    h = _fold(text)
    if not h:
        return ""
    if "don dang ky thue" in h and "nha o xa hoi" in h:
        return _TO_DON
    if "can cuoc" in h or "cccd" in h or "chung minh nhan dan" in h:
        return _CCCD
    if "thuong binh" in h or "liet si" in h or "nguoi co cong" in h or "ho ngheo" in h or "thu nhap" in h:
        return _DOI_TUONG
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if "don" in text and "thue" in text:
        return _TO_DON
    if "cccd" in text or "can cuoc" in text or "chung minh" in text:
        return _CCCD
    if "doi tuong" in text or "dieu kien" in text or "chinh sach" in text:
        return _DOI_TUONG
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
        # other = giấy tờ chỉ trích thông tin (GCN ĐKDN, sổ hộ khẩu…) → bỏ qua, KHÔNG cảnh báo.
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
