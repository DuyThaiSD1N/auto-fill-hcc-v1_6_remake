"""Đính kèm cho [Lào Cai - cổng iGate mới] giao đất, cho thuê đất (1.115650).

Phân loại giữ NGUYÊN của pipeline cổng cũ (giao_thue_dat_lao_cai/attach: OCR → LLM từng tệp → docType + tên giấy tờ).

Bước 2 "Thành phần hồ sơ hệ thống" (crawl 29/10/2026, Sở NN&MT Lào Cai): MỘT bảng 10 dòng, không radio trường hợp,
không dòng "giấy tờ khác", cổng TÍCH SẴN cả 10 dòng — trùng NGUYÊN VĂN thứ tự và tên dòng với 1.115678 (bảng của cổng
cũ thì khác: Điều 133 nằm cuối) → dùng lại bảng 10 dòng + từ khoá dò dòng của pipeline
cho_thue_dat_thue_rung_igate_lao_cai. Tài liệu chưa rõ loại (cổng cũ: thêm dòng "giấy tờ khác" kèm tên) → dòng Đơn,
giữ tên LLM đọc được làm documentName + cảnh báo. Không bỏ tệp nào.
"""

import time

from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.pipelines.giao_thue_dat_lao_cai.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# docType (catalog cổng cũ 1.115650) → từ khoá dòng. "van_ban_dau_gia" của cổng cũ là dòng kết quả đấu giá KHÔNG THÀNH.
_ROW_KEYS: dict[str, list[str]] = {
    **{k: v for k, v in _igate._ROW_KEYS.items() if k in _goc._ROUTES},
    "van_ban_dau_gia": _igate._ROW_KEYS["van_ban_dau_gia_khong_thanh"],
}


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, tuple[str, str] | str] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    rows = _igate._portal_rows(components) or _igate._default_rows()
    warnings: list[str] = []
    don = _igate._find(_igate._DON_KEYS, rows)
    if don is None:
        don = rows[0]
        warnings.append(
            f"Bảng thành phần hồ sơ không có dòng 'Đơn theo Mẫu số 01' — tệp chưa rõ loại tạm đính vào dòng '{don[1]}'; "
            "cán bộ kiểm tra lại."
        )

    attachments: list[dict] = []
    classified: list[dict] = []
    unknown: list[str] = []
    missing: list[str] = []
    bytes_per_row: dict[int, int] = {}
    used_names: set[str] = set()
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        raw = llm_types.get(index)
        llm_type, llm_name = raw if isinstance(raw, tuple) else (raw or "", "")
        doc_type = llm_type if llm_type in _goc._ALLOWED else "other"
        if doc_type == "other":
            row = don
            document_name = _goc._unique_document_name(llm_name, used_names)
            unknown.append(f"{file_name} → \"{document_name}\"")
        else:
            document_name = _goc._ROUTES[doc_type]["display"]
            row = _igate._find(_ROW_KEYS[doc_type], rows) if doc_type in _ROW_KEYS else don
            if row is None:
                row = don
                missing.append(f"{file_name} ({document_name})")
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + (_goc._file_bytes(file) or 0)
        attachments.append(_igate._item(index, file_name, document_name, row, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "documentName": document_name,
                           "source": "llm" if llm_type else "default", "componentIndex": row[0]})

    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, cổng mới không có dòng \"giấy tờ khác\" nên đã tạm đính vào dòng \"Đơn theo "
            f"Mẫu số 01\" để không bỏ sót — cán bộ kiểm tra lại: {', '.join(unknown)}."
        )
    if missing:
        warnings.append(
            "Bảng thành phần hồ sơ trên trang không có dòng cho các giấy tờ sau, đã đính vào dòng Đơn — cán bộ kiểm "
            f"tra lại: {', '.join(missing)}."
        )
    for row_index, total in sorted(bytes_per_row.items()):
        if total > _goc._MAX_FILE_BYTES:
            ten = don[1] if row_index == don[0] else f"thứ {row_index}"
            warnings.append(
                f"Tổng dung lượng các tệp đính vào dòng \"{ten}\" là {total / 1024 / 1024:.1f} MB, vượt giới hạn 6 MB "
                "của cổng — cần nén PDF hoặc tách thành nhiều tệp trước khi nộp."
            )
    _igate._dedupe_document_names(attachments)
    if not attachments:
        warnings.append("Không có tài liệu nào để đính kèm.")
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    components = ((options or {}).get("attachmentContext") or {}).get("components")
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    ocr_files = [f for f in raw_files if f.get("type") in _OCR_TYPES]
    errors: list[str] = []

    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
        for index, file in enumerate(raw_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, tuple[str, str]] = {}
    if llm_documents:
        try:
            llm_types = await _goc._classify_with_llm(llm_documents, errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, llm_types, components)
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [raw_files[d["index"]]["name"] for d in llm_documents],
            "portalRows": len(_igate._portal_rows(components)),
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
