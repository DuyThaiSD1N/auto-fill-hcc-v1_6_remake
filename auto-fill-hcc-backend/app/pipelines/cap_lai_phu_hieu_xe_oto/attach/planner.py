"""Đính kèm "Thành phần hồ sơ" cho "Cấp, cấp lại Phù hiệu cho xe ô tô … kinh doanh vận tải" (cổng DVC Bộ Xây
dựng — Angular Reactive Form, engine FE `attp-row`).

Bảng 2 dòng:
  (1) Chứng nhận đăng ký xe ô tô … (kèm hợp đồng thuê / hợp đồng dịch vụ giữa thành viên và HTX nếu xe không
      thuộc sở hữu đơn vị KDVT) ← "1 Bản sao" — Chứng nhận đăng ký + hợp đồng (thường gộp 1 file).
  (2) Giấy đề nghị cấp (cấp lại) phù hiệu theo mẫu ← "1 Bản chính".
GPKDVT / GCN đăng ký doanh nghiệp không có dòng ở bước 2 (GPKDVT đính trong tờ khai) → bỏ, kèm cảnh báo. CCCD
chỉ để trích, KHÔNG đính. Phân loại **LLM-primary**; rule keyword chỉ DỰ PHÒNG. File chưa rõ → dòng (1) kèm
cảnh báo.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines.cap_lai_phu_hieu_xe_oto.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DE_NGHI = "de_nghi"
_XE = "ho_so_xe"
_GPKD = "giay_phep_kdvt"
_DKDN = "dang_ky_doanh_nghiep"
_CCCD = "cccd"
_OTHER = "other"

# componentName = đoạn text ĐẶC TRƯNG của dòng (FE khớp substring đã fold dấu vào tên dòng).
_ROWS: dict[str, dict[str, str]] = {
    _XE: {
        "componentName": "Chứng nhận đăng ký xe ô tô",
        "loaiBan": "Bản sao",
        "documentName": "Chứng nhận đăng ký xe ô tô và hợp đồng thuê/hợp đồng dịch vụ",
    },
    _DE_NGHI: {
        "componentName": "Giấy đề nghị cấp (cấp lại) phù hiệu",
        "loaiBan": "Bản chính",
        "documentName": "Giấy đề nghị cấp (cấp lại) phù hiệu",
    },
}
_ROW_OF: dict[str, str] = {_XE: _XE, _DE_NGHI: _DE_NGHI}
_SKIP_DOCS: dict[str, str] = {
    _CCCD: "",
    _GPKD: "là Giấy phép kinh doanh vận tải — bước 2 không có dòng riêng, vui lòng đính kèm tại ô 'Đính kèm "
           "GPKDVT' trong tờ khai.",
    _DKDN: "là GCN đăng ký doanh nghiệp/HTX — bước 2 không có dòng riêng, chỉ dùng để trích thông tin.",
}
_ALLOWED_DOC_TYPES = set(_ROW_OF) | set(_SKIP_DOCS) | {_OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM)."""
    h = _fold(text)
    if not h:
        return ""
    if "phu hieu" in h and ("giay de nghi cap" in h or "so luong phu hieu nop lai" in h):
        return _DE_NGHI
    if (
        "chung nhan dang ky xe" in h
        or "car registration" in h
        or "hop dong dich vu giua xa vien" in h
        or "hop dong thue" in h
        or "hop dong hop tac kinh doanh" in h
        or ("so khung" in h and ("so may" in h or "so dong co" in h))
    ):
        return _XE
    if "giay phep kinh doanh van tai" in h:
        return _GPKD
    if "chung nhan dang ky doanh nghiep" in h or "chung nhan dang ky hop tac xa" in h or (
        "chung nhan dang ky ho kinh doanh" in h
    ):
        return _DKDN
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if text in _ALLOWED_DOC_TYPES:
        return text
    if "giay phep" in text or "gpkd" in text:
        return _GPKD
    if "doanh nghiep" in text or "hop tac xa" in text:
        return _DKDN
    if "de nghi" in text:
        return _DE_NGHI
    if any(k in text for k in ("ho so xe", "ho_so_xe", "hop dong", "dang ky xe")):
        return _XE
    if any(k in text for k in ("cccd", "can cuoc", "cmnd", "ho chieu")):
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


def _build_row_item(file: dict, file_index: int, row_id: str, doc_type: str) -> dict:
    row = _ROWS[row_id]
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
        # LLM-primary: ưu tiên phán đoán LLM; rule dự phòng khi LLM trả other/không hợp lệ.
        if llm_type in _ROW_OF or llm_type in _SKIP_DOCS:
            doc_type, source = llm_type, "llm"
        elif rule_type:
            doc_type, source = rule_type, "rule"
        else:
            doc_type, source = _OTHER, "unknown"

        if doc_type in _SKIP_DOCS:
            classified.append({"fileName": file_name, "docType": doc_type, "source": source, "skipped": True})
            if _SKIP_DOCS[doc_type]:
                warnings.append(f"'{file_name}' {_SKIP_DOCS[doc_type]}")
            continue

        if doc_type in _ROW_OF:
            row_id = _ROW_OF[doc_type]
            items.append(_build_row_item(file, idx, row_id, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "rowId": row_id, "source": source})
            continue

        # Mặc định: file chưa rõ gần như luôn là giấy tờ xe → dòng (1), kèm cảnh báo để kiểm tra.
        items.append(_build_row_item(file, idx, _XE, _OTHER))
        classified.append({"fileName": file_name, "docType": _OTHER, "rowId": _XE, "source": f"{source}-default"})
        warnings.append(
            f"Không phân loại chắc chắn '{file_name}' — tạm đính dòng 'Chứng nhận đăng ký xe ô tô', vui lòng "
            "kiểm tra."
        )

    if items and not any(it["componentName"] == _ROWS[_XE]["componentName"] for it in items):
        warnings.append("Chưa có Chứng nhận đăng ký xe ô tô (thành phần bắt buộc).")
    if items and not any(it["componentName"] == _ROWS[_DE_NGHI]["componentName"] for it in items):
        warnings.append("Chưa có Giấy đề nghị cấp (cấp lại) phù hiệu (thành phần bắt buộc).")
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
    ocr_results.extend(_extract_docx_text(f) for f in raw_files if _is_docx(f))
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
    skipped_ocr = [f["name"] for f in raw_files if f.get("type") not in _OCR_TYPES and not _is_docx(f)]

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
