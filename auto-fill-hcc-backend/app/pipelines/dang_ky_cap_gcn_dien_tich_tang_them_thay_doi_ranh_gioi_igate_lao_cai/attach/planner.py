"""Đính kèm cho [Lào Cai - cổng iGate mới] diện tích tăng thêm do thay đổi ranh giới (1.115693).

Phân loại giữ NGUYÊN của pipeline cổng cũ (dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi/attach: OCR → LLM
từng tệp, thuần LLM; không bỏ sót tệp nào; tệp quá 6 MB bị loại vì cổng không nhận; nhắc thiếu thành phần chính và
giấy cam kết chữ ký thiếu giấy ủy quyền).

Cổng cũ không có bảng "Thành phần hồ sơ" → mọi tệp xuống "Giấy tờ khác". Bước 2 "Thành phần hồ sơ hệ thống" của cổng
mới (crawl 02/11/2026, UBND Phường Yên Bái) là bảng 5 dòng, cổng TÍCH SẴN cả 5:
   1  Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 (QĐ 47/2026/QĐ-UBND)
   2  Giấy chứng nhận đã cấp
   3  Giấy tờ chứng minh phần diện tích tăng thêm (nếu có)
   4  Mảnh trích đo bản đồ địa chính thửa đất
   5  Văn bản về việc đại diện … thông qua người đại diện
Giấy tờ không có dòng riêng (giấy cam kết chữ ký, tờ khai thuế, CCCD, chưa rõ loại) → dòng Đơn, giữ tên mô tả + cảnh báo
dùng nút "Thêm giấy tờ". Không còn "Giấy tờ khác".

Engine FE "attp-row" dùng chung với cho_thue_dat_thue_rung_igate_lao_cai.
"""

import time

from app.pipelines._shared import fold
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.pipelines.dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Cổng Lào Cai: "Dung lượng tối đa là 6 Mb" cho mỗi tệp.
_MAX_FILE_BYTES = 6 * 1024 * 1024

_DEFAULT_ROWS = [
    "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 ban hành kèm theo Quyết định số "
    "47/2026/QĐ-UBND",
    "Giấy chứng nhận đã cấp",
    "Giấy tờ chứng minh phần diện tích tăng thêm (nếu có)",
    "Mảnh trích đo bản đồ địa chính thửa đất",
    "Văn bản về việc đại diện theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ tục đăng ký đất "
    "đai, tài sản gắn liền với đất thông qua người đại diện",
]
_DON_KEYS = ["don dang ky bien dong"]
# docType cổng cũ → cụm (fold) tìm dòng cổng mới.
_ROW_KEYS: dict[str, list[str]] = {
    "don_bien_dong": _DON_KEYS,
    "gcn": ["giay chung nhan da cap"],
    "bien_ban_ranh_gioi": ["dien tich tang them"],
    "giay_to_chuyen_quyen": ["dien tich tang them"],
    "phieu_do_dac": ["manh trich do"],
    "van_ban_dai_dien": ["viec dai dien"],
}

Row = _igate.Row


def _rows(components: list[dict] | None) -> list[Row]:
    return _igate._portal_rows(components) or [(i + 1, name, fold(name)) for i, name in enumerate(_DEFAULT_ROWS)]


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, str] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    rows = _rows(components)
    don = _igate._find(_DON_KEYS, rows) or rows[0]
    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    unknown: list[str] = []
    ngoai_bang: list[str] = []

    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _goc._ALLOWED else _goc._OTHER
        if doc_type == _goc._OTHER:
            unknown.append(file_name)
            document_name = _goc._other_display(file_name)
        else:
            document_name = _goc._ROUTES[doc_type]
        row = _igate._find(_ROW_KEYS[doc_type], rows) if doc_type in _ROW_KEYS else None
        if row is None:
            row = don
            ngoai_bang.append(f"{file_name} → \"{document_name}\"")
        attachments.append(_igate._item(index, file_name, document_name, row, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "source": "llm" if llm_type else "default",
                           "componentIndex": row[0]})

    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, đã đính kèm với tên lấy theo tên tệp để không bỏ sót — cán bộ kiểm tra lại: "
            f"{', '.join(unknown)}."
        )
    have_types = {item["detectedType"] for item in attachments}
    thieu = [mo_ta for doc_type, mo_ta in _goc._THANH_PHAN_CHINH.items() if doc_type not in have_types]
    if thieu:
        warnings.append(
            "Chưa có tệp cho thành phần hồ sơ chính: " + "; ".join(thieu) + ". Cổng không chặn nhưng nơi tiếp nhận sẽ "
            "trả hồ sơ — cán bộ đề nghị người dân bổ sung bản scan. KHÔNG tự tạo tệp thay thế."
        )
    if _goc._CAM_KET in have_types and _goc._UY_QUYEN not in have_types:
        warnings.append(
            "Hồ sơ có Giấy cam kết xác nhận chữ ký của người được ủy quyền nhưng KHÔNG có bản scan của chính Giấy ủy "
            "quyền. Giấy cam kết chỉ là giấy bổ trợ, không thay được văn bản về việc đại diện — cán bộ yêu cầu bổ sung "
            "bản ủy quyền công chứng trước khi nộp."
        )
    if ngoai_bang:
        warnings.append(
            "Giấy tờ không có dòng riêng trong bảng thành phần hồ sơ đã tạm đính vào dòng Đơn đăng ký biến động (vẫn "
            "là tệp riêng, giữ tên) vì cổng mới không còn danh sách \"Giấy tờ khác\" — nếu cần tách riêng, cán bộ "
            f"dùng nút \"Thêm giấy tờ\" của cổng: {', '.join(ngoai_bang)}."
        )
    _igate._dedupe_document_names(attachments)
    if not attachments:
        warnings.append("Không có tài liệu nào để đính kèm.")
    return attachments, warnings, classified


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    components = ((options or {}).get("attachmentContext") or {}).get("components")
    raw_files = [{"name": f.name, "type": f.type, "dataUrl": f.dataUrl} for f in files]
    errors: list[str] = []

    valid_files: list[dict] = []
    original_indexes: list[int] = []
    for raw_index, file in enumerate(raw_files):
        size = _goc._data_url_size(file.get("dataUrl"))
        if size > _MAX_FILE_BYTES:
            errors.append(
                f"File '{file['name']}' vượt quá 6 MB ({size / 1024 / 1024:.2f} MB) — cổng không nhận, đã bỏ qua. Nén "
                "PDF (giảm ảnh quét về 300 dpi) hoặc tách thành nhiều tệp rồi đính lại."
            )
        else:
            valid_files.append(file)
            original_indexes.append(raw_index)

    ocr_files = [f for f in valid_files if f.get("type") in _OCR_TYPES]
    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for item in ocr_results:
        if item.get("error"):
            errors.append(f"OCR {item.get('name')}: {item['error']}")

    by_name = {item.get("name"): item for item in ocr_results}
    llm_documents = [
        {"index": index, "text": str(by_name.get(file.get("name"), {}).get("text") or "")}
        for index, file in enumerate(valid_files)
        if str(by_name.get(file.get("name"), {}).get("text") or "").strip()
    ]
    started = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_documents:
        try:
            llm_types = await _goc._classify_with_llm(llm_documents, errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(valid_files, llm_types, components)
    # fileIndex đánh theo valid_files; extension lấy tệp theo vị trí trong danh sách GỐC → đổi lại.
    for item in attachments:
        item["fileIndex"] = original_indexes[item["fileIndex"]]
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [f["name"] for f in raw_files],
            "ocrDocuments": [r.get("name") for r in ocr_results if r.get("text")],
            "llmDocuments": [valid_files[d["index"]]["name"] for d in llm_documents],
            "portalRows": len(_igate._portal_rows(components)),
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
