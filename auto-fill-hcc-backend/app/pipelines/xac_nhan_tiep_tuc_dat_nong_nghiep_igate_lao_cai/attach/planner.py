"""Đính kèm cho [Lào Cai - cổng iGate mới] xác nhận tiếp tục sử dụng đất nông nghiệp (1.115677).

Phân loại giữ NGUYÊN của pipeline cổng cũ (xac_nhan_tiep_tuc_dat_nong_nghiep/attach: OCR → LLM từng tệp → docType).

Bước 2 "Thành phần hồ sơ hệ thống" (crawl 29/10/2026, Sở NN&MT Lào Cai): MỘT bảng 2 dòng như cổng cũ, cổng TÍCH SẴN
cả 2, KHÔNG có dòng "giấy tờ khác" (dưới bảng có nút "Thêm giấy tờ" — chưa crawl danh mục nên chưa dùng):
   1 Văn bản đề nghị xác nhận lại thời hạn sử dụng đất Mẫu số 39 · 2 Giấy chứng nhận đã cấp
Mảnh trích đo nộp riêng, giấy ủy quyền, CCCD, tài liệu chưa rõ loại (cổng cũ xuống "Giấy tờ khác" kèm tên) → dòng Đơn,
giữ tên tài liệu + cảnh báo. Không bỏ tệp nào. Giữ các cảnh báo nghiệp vụ của cổng cũ: thiếu dòng bắt buộc, mảnh trích
đo hay quét gộp trong file GCN, CCCD không thuộc thành phần hồ sơ.

Engine FE "attp-row" + untickUnplannedRows dùng chung với cho_thue_dat_thue_rung_igate_lao_cai.
"""

import time

from app.pipelines._shared import fold
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Bảng 2 dòng NGUYÊN VĂN (crawl 29/10/2026).
_DEFAULT_ROWS = [
    "Văn bản đề nghị xác nhận lại thời hạn sử dụng đất theo Mẫu số 39 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND",
    "Giấy chứng nhận đã cấp",
]
_DON_KEYS = ["mau so 39"]
_ROW_KEYS: dict[str, list[str]] = {
    "don_mau_39": _DON_KEYS,
    "gcn": ["giay chung nhan da cap"],
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
    rows = _igate._portal_rows(components) or _default_rows()
    warnings: list[str] = []
    don = _igate._find(_DON_KEYS, rows)
    if don is None:
        don = rows[0]
        warnings.append(
            f"Bảng thành phần hồ sơ không có dòng 'Mẫu số 39' — tệp chưa rõ loại tạm đính vào dòng '{don[1]}'; cán bộ "
            "kiểm tra lại."
        )

    attachments: list[dict] = []
    classified: list[dict] = []
    ngoai_danh_muc: list[str] = []
    unknown: list[str] = []
    missing: list[str] = []
    filled: set[str] = set()
    used_names: set[str] = set()
    bytes_per_row: dict[int, int] = {}
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _goc._ALLOWED else _goc._OTHER
        if doc_type in _goc._ROUTES:
            document_name = _goc._ROUTES[doc_type][1]
            row = _igate._find(_ROW_KEYS[doc_type], rows)
            if row is None:
                row = don
                missing.append(f"{file_name} ({document_name})")
            else:
                filled.add(doc_type)
        else:
            row = don
            base = _goc._other_display(file_name) if doc_type == _goc._OTHER else _goc._OTHER_ROUTES[doc_type]
            document_name = _goc._unique_document_name(base, used_names)
            (unknown if doc_type == _goc._OTHER else ngoai_danh_muc).append(f"{file_name} → \"{document_name}\"")
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + _goc._data_url_size(file.get("dataUrl"))
        attachments.append(_igate._item(index, file_name, document_name, row, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "source": "llm" if llm_type else "default",
                           "componentIndex": row[0]})

    if ngoai_danh_muc or unknown:
        warnings.append(
            "Giấy tờ ngoài 2 dòng của bảng đã tạm đính vào dòng \"Mẫu số 39\" (vẫn là tệp riêng, giữ tên) vì cổng mới "
            "không có dòng \"giấy tờ khác\" — nếu cần tách riêng, cán bộ dùng nút \"Thêm giấy tờ\" của cổng: "
            f"{', '.join(ngoai_danh_muc + unknown)}."
        )
    if missing:
        warnings.append(
            "Bảng thành phần hồ sơ trên trang không có dòng cho các giấy tờ sau, đã đính vào dòng Đơn — cán bộ kiểm "
            f"tra lại: {', '.join(missing)}."
        )
    thieu = [_goc._ROWS_CAN_NHAC[_goc._ROUTES[t][0]] for t in ("don_mau_39", "gcn") if t not in filled]
    if thieu:
        warnings.append(
            "Chưa có tệp nào cho dòng: " + "; ".join(thieu) + ". Đây là thành phần hồ sơ bắt buộc của thủ tục — cán "
            "bộ đề nghị người dân bổ sung."
        )
    have_types = {item["detectedType"] for item in attachments}
    if "gcn" in have_types and "manh_trich_do" not in have_types:
        warnings.append(
            "Không thấy tệp riêng cho mảnh trích đo bản đồ địa chính thửa đất — hồ sơ dạng này thường quét gộp nó vào "
            "trang cuối file Giấy chứng nhận nên nó đi kèm dòng GCN; nơi tiếp nhận yêu cầu tách riêng thì cán bộ đề "
            "nghị người dân tách tệp."
        )
    if "giay_to_nhan_than" in have_types:
        warnings.append(
            "CCCD/giấy tờ hộ tịch KHÔNG thuộc thành phần hồ sơ của thủ tục này; trợ lý vẫn đính để không bỏ sót tệp — "
            "nơi tiếp nhận không yêu cầu thì cán bộ xoá tệp đó đi."
        )
    for row_index, total in sorted(bytes_per_row.items()):
        if total > _goc._MAX_FILE_BYTES:
            warnings.append(
                f"Tổng dung lượng các tệp đính vào dòng thứ {row_index} là {total / 1024 / 1024:.1f} MB, vượt giới hạn "
                "6 MB của cổng — cần nén PDF hoặc tách thành nhiều tệp trước khi nộp."
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
