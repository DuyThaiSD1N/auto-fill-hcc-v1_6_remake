"""Đính kèm "Thành phần hồ sơ" cho "Xóa đăng ký biện pháp bảo đảm..." (cổng DVC Đà Nẵng — engine `attp-row`).

Bảng thành phần hồ sơ có 9 dòng (nhiều dòng điều kiện hiếm gặp). Ta route những loại nhận diện được:
  (3) Phiếu yêu cầu theo Mẫu số 03a                                    → Bản chính  (BẮT BUỘC)
  (1) Giấy chứng nhận (bản gốc) của tài sản bảo đảm                    → Bản chính
  (2) Văn bản đồng ý xóa/xác nhận giải chấp của bên nhận bảo đảm       → Bản chính
  (4) (i) Văn bản có nội dung về đại diện (Giấy ủy quyền)              → Bản sao
FE khớp dòng bằng componentName (substring fold), tick + chọn loaiBan + set file. Phân loại **LLM-primary**;
rule keyword chỉ DỰ PHÒNG. CCCD không có dòng riêng → bỏ qua (chỉ đối chiếu).
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines.xoa_dang_ky_bien_phap_bao_dam_da_nang.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_PHIEU_03A = "phieu_yeu_cau_03a"
_BAN_GOC_GCN = "ban_goc_gcn"
_VB_DONG_Y_XOA = "van_ban_dong_y_xoa"
_VB_DAI_DIEN = "van_ban_dai_dien"
_CCCD = "cccd"
_OTHER = "other"

# componentName = ĐOẠN TEXT ĐẶC TRƯNG của dòng (FE khớp substring fold vào nhãn dòng lấy từ DOM).
_ROWS: dict[str, dict[str, str]] = {
    _PHIEU_03A: {"componentName": "Phiếu yêu cầu theo Mẫu số 03a", "loaiBan": "Bản chính",
                 "documentName": "Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm (Mẫu số 03a)"},
    _BAN_GOC_GCN: {"componentName": "Giấy chứng nhận (bản gốc)", "loaiBan": "Bản chính",
                 "documentName": "Giấy chứng nhận (bản gốc) của tài sản bảo đảm"},
    _VB_DONG_Y_XOA: {"componentName": "không phải là bên nhận bảo đảm", "loaiBan": "Bản chính",
                 "documentName": "Văn bản đồng ý xóa đăng ký / xác nhận giải chấp của bên nhận bảo đảm"},
    _VB_DAI_DIEN: {"componentName": "thông qua người đại diện", "loaiBan": "Bản sao",
                 "documentName": "Văn bản về đại diện (Giấy ủy quyền)"},
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
    if "phieu yeu cau" in h and ("xoa dang ky" in h or "mau so 03a" in h or "03a" in h):
        return _PHIEU_03A
    if "giay uy quyen" in h or ("uy quyen" in h and "duoc uy quyen" in h):
        return _VB_DAI_DIEN
    if ("dong y" in h or "xac nhan" in h or "giai chap" in h) and ("xoa" in h or "the chap" in h) and "ngan hang" in h:
        return _VB_DONG_Y_XOA
    if "giay chung nhan quyen su dung dat" in h or ("giay chung nhan" in h and "quyen su dung dat" in h):
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
    if "03a" in text or ("phieu" in text and "yeu cau" in text):
        return _PHIEU_03A
    if "uy quyen" in text or "dai dien" in text:
        return _VB_DAI_DIEN
    if "dong y" in text or "giai chap" in text or "chap thuan" in text:
        return _VB_DONG_Y_XOA
    if "gcn" in text or "chung nhan" in text or "so do" in text:
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
