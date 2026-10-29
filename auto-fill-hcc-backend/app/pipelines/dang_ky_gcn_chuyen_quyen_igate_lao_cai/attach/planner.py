"""Đính kèm cho [Lào Cai - cổng iGate mới] đăng ký, cấp GCN khi đã chuyển quyền trước 01/8/2024 (1.115666).

Phân loại giữ NGUYÊN của pipeline cổng cũ (dang_ky_gcn_chuyen_quyen_truoc_2024_lao_cai/attach: OCR → LLM từng tệp →
docType) và quy tắc chọn trường hợp: có văn bản chuyển quyền → a), chỉ có GCN của bên chuyển quyền → b).

Bước 2 "Thành phần hồ sơ hệ thống" (crawl 29/10/2026, Sở NN&MT Lào Cai): MỘT bảng 5 dòng, cổng TÍCH SẴN cả 5, KHÔNG
còn dòng tiêu đề trường hợp, KHÔNG có dòng "giấy tờ khác" (dưới bảng có nút "Thêm giấy tờ" — chưa crawl danh mục nên
chưa dùng). Hai trường hợp nối liền nhau, mỗi trường hợp mở đầu bằng dòng Đơn Mẫu số 24:
   1 Đơn Mẫu 24 · 2 Hợp đồng, văn bản về chuyển quyền                            → a)
   3 Đơn Mẫu 24 · 4 Bản gốc GCN đã cấp · 5 Giấy tờ chuyển quyền đủ chữ ký 2 bên → b)
Dòng 1 và 3 TRÙNG tên nguyên văn → gửi componentIndex để FE chọn đúng dòng. GCN chỉ có MỘT dòng (4) nên dùng cho cả
hai trường hợp như cổng cũ. Giấy tờ ngoài danh mục (cổng cũ thêm dòng "Giấy tờ khác" kèm tên) → dòng Đơn của trường hợp,
giữ tên theo tệp + cảnh báo. Không bỏ tệp nào.

Engine FE "attp-row" + untickUnplannedRows dùng chung với cho_thue_dat_thue_rung_igate_lao_cai: FE bỏ chọn tất cả rồi
chỉ tích dòng có tệp, nên dòng của trường hợp còn lại tự được bỏ tick.
"""

import time

from app.pipelines._shared import fold
from app.pipelines.cap_gcn_nhan_chuyen_nhuong_igate_lao_cai.attach.planner import _branch_rows
from app.pipelines.cho_thue_dat_thue_rung.attach import planner as _size
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.pipelines.dang_ky_gcn_chuyen_quyen_truoc_2024_lao_cai.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = (
    "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 ban hành kèm theo Quyết định số "
    "47/2026/QĐ-UBND ngày 28 tháng 6 năm 2026 của UBND tỉnh Lào Cai"
)
# Bảng 5 dòng NGUYÊN VĂN (crawl 29/10/2026).
_DEFAULT_ROWS = [
    _DON,
    "Hợp đồng, văn bản về chuyển quyền sử dụng đất đã lập theo quy định",
    _DON,
    "Bản gốc Giấy chứng nhận đã cấp",
    "Giấy tờ về việc chuyển quyền sử dụng đất có đủ chữ ký của bên chuyển quyền và bên nhận chuyển quyền",
]

_DON_KEYS = ["mau so 24"]
# docType → từ khoá dòng; dò TRONG nhóm dòng của trường hợp nên "chuyen quyen su dung dat" chỉ khớp một dòng.
_ROW_KEYS: dict[str, list[str]] = {
    "don_mau_24": _DON_KEYS,
    "van_ban_chuyen_quyen": ["chuyen quyen su dung dat"],
    "gcn_ban_goc": ["ban goc giay chung nhan"],
}

Row = _igate.Row


def _default_rows() -> list[Row]:
    return [(i + 1, name, fold(name)) for i, name in enumerate(_DEFAULT_ROWS)]


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, str] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    all_rows = _igate._portal_rows(components) or _default_rows()
    resolved = [
        (index, str(file.get("name") or f"file-{index + 1}"),
         llm_types.get(index) if llm_types.get(index) in _goc._ALLOWED else "other")
        for index, file in enumerate(files)
    ]
    nhanh = _goc._chon_nhanh([doc_type for _, _, doc_type in resolved])
    rows = _branch_rows(all_rows)[nhanh]

    warnings: list[str] = []
    don = _igate._find(_DON_KEYS, rows)
    if don is None:
        don = rows[0]
        warnings.append(
            f"Bảng thành phần hồ sơ không có dòng 'Đơn Mẫu số 24' — tệp chưa rõ loại tạm đính vào dòng '{don[1]}'; "
            "cán bộ kiểm tra lại."
        )

    attachments: list[dict] = []
    classified: list[dict] = []
    unknown: list[str] = []
    missing: list[str] = []
    bytes_per_row: dict[int, int] = {}
    for index, file_name, doc_type in resolved:
        if doc_type == "other":
            row, document_name = don, _goc._other_component_name(file_name)
            unknown.append(file_name)
        else:
            document_name = _goc._DISPLAY[doc_type]
            # GCN chỉ có một dòng (thuộc trường hợp b) → dò cả bảng.
            row = _igate._find(_ROW_KEYS[doc_type], all_rows if doc_type == "gcn_ban_goc" else rows)
            if row is None:
                row = don
                missing.append(f"{file_name} ({document_name})")
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + _size._data_url_size(files[index].get("dataUrl"))
        attachments.append(_igate._item(index, file_name, document_name, row, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "nhanh": nhanh,
                           "source": "llm" if index in llm_types else "default", "componentIndex": row[0]})

    if attachments:
        warnings.append(
            f"Hồ sơ được xếp theo TRƯỜNG HỢP {nhanh.upper()}) "
            + ("(có văn bản/hợp đồng chuyển quyền)." if nhanh == _goc._NHANH_A
               else "(chỉ có Giấy chứng nhận của bên chuyển quyền, không có văn bản chuyển quyền).")
            + " Trợ lý chỉ tích các dòng có tệp — cán bộ kiểm tra lại trường hợp trước khi nộp."
        )
    if unknown:
        warnings.append(
            "Giấy tờ ngoài danh mục (CCCD, ủy quyền…) đã tạm đính vào dòng \"Đơn Mẫu số 24\" vì cổng mới không có dòng "
            f"\"giấy tờ khác\" — nếu cần tách riêng, cán bộ dùng nút \"Thêm giấy tờ\" của cổng: {', '.join(unknown)}."
        )
    if missing:
        warnings.append(
            "Bảng thành phần hồ sơ trên trang không có dòng cho các giấy tờ sau, đã đính vào dòng Đơn — cán bộ kiểm "
            f"tra lại: {', '.join(missing)}."
        )
    for row_index, total in sorted(bytes_per_row.items()):
        if total > _size._MAX_SLOT_BYTES:
            warnings.append(
                f"Tổng dung lượng các tệp đính vào dòng thứ {row_index} là {_size._mb(total)}, vượt giới hạn 6 MB "
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
    llm_types: dict[int, str] = {}
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
