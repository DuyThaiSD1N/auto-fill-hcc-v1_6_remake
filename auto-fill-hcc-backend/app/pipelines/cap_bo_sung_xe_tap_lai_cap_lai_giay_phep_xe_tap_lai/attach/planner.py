"""Đính kèm "Thành phần hồ sơ" cho "Cấp bổ sung xe tập lái, cấp lại Giấy phép xe tập lái" (cổng DVC Bộ Xây
dựng — Angular Reactive Form, engine FE `attp-row`).

Bảng 2 dòng (đều "1 Bản chính"):
  (1) Danh sách đề nghị cấp giấy phép xe tập lái theo mẫu quy định_NĐ94.2026 ← DS đề nghị.
  (2) Đối với xe tập lái không thuộc quyền sở hữu của cơ sở đào tạo … Giấy tờ chứng minh quyền sử dụng hợp
      pháp ← HĐ thuê xe + GCN đăng ký xe + GCN kiểm định (thường gộp 1 file nhiều trang).
Biên bản kiểm tra xe (DS nhắc "gửi kèm") không có dòng riêng → gộp dòng (1). CCCD chỉ để trích, KHÔNG đính.
Phân loại **LLM-primary**; rule keyword chỉ DỰ PHÒNG. File chưa rõ → dòng (2) kèm cảnh báo.
"""

import time
from typing import Any

from app.config import settings
from app.pipelines._shared import fold as _fold
from app.pipelines._shared.compact_agent.runner import _extract_docx_text, _is_docx
from app.pipelines.cap_bo_sung_xe_tap_lai_cap_lai_giay_phep_xe_tap_lai.attach import prompt
from app.process.schemas import FileItem
from app.services.llm import client

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DS = "danh_sach_de_nghi"
_XE = "ho_so_xe"
_BIEN_BAN = "bien_ban_kiem_tra"
_CCCD = "cccd"
_OTHER = "other"

# componentName = đoạn text ĐẶC TRƯNG của dòng (FE khớp substring đã fold dấu vào tên dòng).
_ROWS: dict[str, dict[str, str]] = {
    _DS: {
        "componentName": "Danh sách đề nghị cấp giấy phép xe tập lái",
        "loaiBan": "Bản chính",
        "documentName": "Danh sách đề nghị cấp giấy phép xe tập lái theo mẫu quy định",
    },
    _XE: {
        "componentName": "không thuộc quyền sở hữu của cơ sở đào tạo",
        "loaiBan": "Bản chính",
        "documentName": "Giấy tờ chứng minh quyền sử dụng hợp pháp xe tập lái (HĐ thuê xe, GCN đăng ký, "
                        "GCN kiểm định)",
    },
}
# Loại giấy tờ không có dòng riêng → đính vào dòng khác (giữ tên tài liệu riêng: FE đặt tên file theo
# documentName và chống trùng theo tên đó).
_ROW_OF: dict[str, str] = {_DS: _DS, _XE: _XE, _BIEN_BAN: _DS}
_DOC_NAME_OVERRIDE: dict[str, str] = {_BIEN_BAN: "Biên bản kiểm tra xe tập lái"}
_SKIP_DOCS: set[str] = {_CCCD}
_ALLOWED_DOC_TYPES = set(_ROW_OF) | _SKIP_DOCS | {_OTHER}


def _is_identity_text(text: str) -> bool:
    h = _fold(text)
    return any(m in h for m in ("can cuoc cong dan", "chung minh nhan dan", "the can cuoc", "ho chieu", "passport"))


def _rule_doc_type(text: str) -> str:
    """Route TẤT ĐỊNH theo OCR (dự phòng cho LLM)."""
    h = _fold(text)
    if not h:
        return ""
    if "danh sach xe de nghi cap giay phep xe tap lai" in h or (
        "de nghi" in h and "cap giay phep xe tap lai" in h and "kinh gui" in h and "hop dong thue" not in h
    ):
        return _DS
    if "bien ban kiem tra" in h and "xe tap lai" in h:
        return _BIEN_BAN
    if (
        "hop dong thue xe" in h
        or "chung nhan dang ky xe" in h
        or "kiem dinh an toan ky thuat" in h
        or ("so khung" in h and ("so may" in h or "so dong co" in h))
    ):
        return _XE
    if _is_identity_text(h):
        return _CCCD
    return ""


def _normalize_doc_type(value: str) -> str:
    text = _fold(value or "")
    if not text or text == "other":
        return _OTHER
    if text in _ALLOWED_DOC_TYPES:
        return text
    if "danh sach" in text or "de nghi" in text:
        return _DS
    if "bien ban" in text:
        return _BIEN_BAN
    if any(k in text for k in ("ho so xe", "ho_so_xe", "hop dong", "dang ky xe", "kiem dinh")):
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
        "documentName": _DOC_NAME_OVERRIDE.get(doc_type, row["documentName"]),
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
            continue

        if doc_type in _ROW_OF:
            row_id = _ROW_OF[doc_type]
            items.append(_build_row_item(file, idx, row_id, doc_type))
            classified.append({"fileName": file_name, "docType": doc_type, "rowId": row_id, "source": source})
            if doc_type == _BIEN_BAN:
                warnings.append(
                    f"'{file_name}' là biên bản kiểm tra xe — form không có dòng riêng, đã đính cùng dòng "
                    "'Danh sách đề nghị'."
                )
            continue

        # Mặc định: file chưa rõ gần như luôn là giấy tờ xe → dòng (2), kèm cảnh báo để kiểm tra.
        items.append(_build_row_item(file, idx, _XE, _OTHER))
        classified.append({"fileName": file_name, "docType": _OTHER, "rowId": _XE, "source": f"{source}-default"})
        warnings.append(
            f"Không phân loại chắc chắn '{file_name}' — tạm đính dòng 'Giấy tờ chứng minh quyền sử dụng hợp "
            "pháp', vui lòng kiểm tra."
        )

    if items and not any(it["componentName"] == _ROWS[_DS]["componentName"] for it in items):
        warnings.append("Chưa có file Danh sách đề nghị cấp giấy phép xe tập lái (thành phần bắt buộc).")
    if items and not any(it["componentName"] == _ROWS[_XE]["componentName"] for it in items):
        warnings.append("Chưa có giấy tờ chứng minh quyền sử dụng hợp pháp xe (HĐ thuê xe/GCN đăng ký/kiểm định).")
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
