"""Đính kèm cho [Lào Cai - cổng iGate mới] điều chỉnh quyết định giao đất, cho thuê đất (1.115652).

Phân loại giữ NGUYÊN của pipeline cổng cũ (dieu_chinh_giao_dat_lao_cai/attach: OCR → LLM từng tệp → docType + tên).

Bước 2 "Thành phần hồ sơ hệ thống" (crawl 29/10/2026, Sở NN&MT Lào Cai): MỘT bảng 3 dòng, cổng TÍCH SẴN cả 3, dưới bảng
có nút "Thêm giấy tờ" (modal chọn giấy tờ theo danh mục — chưa crawl danh mục đó nên CHƯA dùng):
   1 Đơn theo Mẫu số 04 · 2 GCN / giấy tờ Điều 137 / quyết định giao đất (quyết định BỊ điều chỉnh)
   3 Văn bản làm thay đổi căn cứ quyết định giao đất
Tài liệu khác (ĐKKD, ủy quyền, CCCD…; cổng cũ thêm dòng "giấy tờ khác" kèm tên) → dòng Đơn, giữ tên LLM đọc được làm
documentName + cảnh báo. Engine attp-row + untickUnplannedRows dùng chung với cho_thue_dat_thue_rung_igate_lao_cai.
"""

import time

from app.pipelines._shared import fold
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.pipelines.dieu_chinh_giao_dat_lao_cai.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DEFAULT_ROWS = [
    "Đơn theo Mẫu số 04 kèm theo Quyết định số 47/2026/QĐ-UBND",
    "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất đai hoặc một trong các "
    "loại giấy tờ quy định tại Điều 137 Luật Đất đai hoặc quyết định giao đất, cho thuê đất, cho phép chuyển mục đích "
    "sử dụng đất của cơ quan nhà nước có thẩm quyền theo quy định của pháp luật về đất đai qua các thời kỳ",
    "Văn bản của cơ quan nhà nước có thẩm quyền có nội dung làm thay đổi căn cứ quyết định giao đất, cho thuê đất, cho "
    "phép chuyển mục đích sử dụng đất (đối với trường hợp thay đổi căn cứ quyết định giao đất, cho thuê đất, cho phép "
    "chuyển mục đích sử dụng đất)",
]

_DON_KEYS = ["mau so 04"]
# Dòng 3 cũng chứa "quyết định giao đất" (căn cứ quyết định giao đất) → dòng 2 dò bằng "khoản 21 Điều 3" TRƯỚC.
_ROW_KEYS: dict[str, list[str]] = {
    "don_mau_04": _DON_KEYS,
    "quyet_dinh_bi_dieu_chinh": ["khoan 21 dieu 3", "dieu 137 luat dat dai"],
    "van_ban_thay_doi_can_cu": ["thay doi can cu"],
}


def _default_rows() -> list[tuple[int, str, str]]:
    return [(i + 1, name, fold(name)) for i, name in enumerate(_DEFAULT_ROWS)]


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, tuple[str, str] | str] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    rows = _igate._portal_rows(components) or _default_rows()
    warnings: list[str] = []
    don = _igate._find(_DON_KEYS, rows)
    if don is None:
        don = rows[0]
        warnings.append(
            f"Bảng thành phần hồ sơ không có dòng 'Đơn theo Mẫu số 04' — tệp chưa rõ loại tạm đính vào dòng '{don[1]}'; "
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
            row = _igate._find(_ROW_KEYS[doc_type], rows)
            if row is None:
                row = don
                missing.append(f"{file_name} ({document_name})")
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + (_goc._file_bytes(file) or 0)
        attachments.append(_igate._item(index, file_name, document_name, row, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "documentName": document_name,
                           "source": "llm" if llm_type else "default", "componentIndex": row[0]})

    if unknown:
        warnings.append(
            "Giấy tờ ngoài danh mục (ĐKKD, ủy quyền, CCCD…) đã tạm đính vào dòng \"Đơn theo Mẫu số 04\" — nếu cần "
            f"tách riêng, cán bộ dùng nút \"Thêm giấy tờ\" của cổng: {', '.join(unknown)}."
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
