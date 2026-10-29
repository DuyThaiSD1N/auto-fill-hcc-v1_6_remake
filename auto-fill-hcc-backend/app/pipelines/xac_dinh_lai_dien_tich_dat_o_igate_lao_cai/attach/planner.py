"""Đính kèm cho [Lào Cai - cổng iGate mới] xác định lại diện tích đất ở, cấp phường/xã (1.115685).

Phân loại giữ NGUYÊN của pipeline cổng cũ (xac_dinh_lai_dien_tich_dat_o/attach: OCR → LLM từng tệp → docType) và tên
giấy tờ của cổng cũ.

Bước 2 "Thành phần hồ sơ hệ thống" của cổng mới (crawl 29/10/2026, UBND phường) là CÙNG bảng 3 dòng như cổng cũ, cổng
TÍCH SẴN cả 3, KHÔNG có dòng "giấy tờ khác":
   1 Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 (QĐ 47/2026/QĐ-UBND)
   2 Giấy chứng nhận đã cấp
   3 Văn bản về việc đại diện … thông qua người đại diện
⚠ Bản crawl ghi componentName dòng 2 là "scannerScan tệp tin…" (đọc nhầm ô nút); dò tên không ra thì lấy theo VỊ TRÍ
dòng khi bảng đúng 3 dòng. Giấy tờ cổng cũ xuống "Giấy tờ khác" (bản án, tờ khai thuế, CCCD, tài liệu lạ) → dòng Đơn,
giữ tên + cảnh báo. Dòng Đơn nhận NHIỀU TỆP (bản ký số + bản chưa ký). Không bỏ tệp nào.

Engine FE "attp-row" + untickUnplannedRows dùng chung với cho_thue_dat_thue_rung_igate_lao_cai.
"""

import time

from app.pipelines._shared import fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.pipelines.xac_dinh_lai_dien_tich_dat_o.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Bảng 3 dòng = bảng cổng cũ (_goc._ROWS, đúng chữ bản crawl 29/10/2026).
_DEFAULT_ROWS = [_goc._ROWS[i] for i in sorted(_goc._ROWS)]
# docType → (từ khoá dò dòng, vị trí dòng mặc định 0-based)
_ROW_KEYS: dict[str, tuple[list[str], int]] = {
    "don_bien_dong": (["mau so 24", "don dang ky bien dong"], 0),
    "gcn": (["giay chung nhan da cap"], 1),
    "van_ban_dai_dien": (["thong qua nguoi dai dien"], 2),
}

Row = _igate.Row


def _default_rows() -> list[Row]:
    return [(i + 1, name, fold(name)) for i, name in enumerate(_DEFAULT_ROWS)]


def _row(doc_type: str, rows: list[Row]) -> Row | None:
    keys, position = _ROW_KEYS[doc_type]
    found = _igate._find(keys, rows)
    if found is None and len(rows) == len(_DEFAULT_ROWS):
        found = rows[position]
    return found


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, str] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    rows = _igate._portal_rows(components) or _default_rows()
    warnings: list[str] = []
    don = _row("don_bien_dong", rows) or rows[0]

    attachments: list[dict] = []
    classified: list[dict] = []
    ngoai: list[str] = []
    seen_types: set[str] = set()
    used_names: set[str] = set()
    bytes_per_row: dict[int, int] = {}
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _goc._ALLOWED else _goc._OTHER
        seen_types.add(doc_type)
        if doc_type in _goc._ROUTES:
            base = _goc._ROUTES[doc_type][1]
        else:
            base = _goc._other_display(file_name) if doc_type == _goc._OTHER else _goc._OTHER_ROUTES[doc_type]
        document_name = _goc._unique_document_name(base, used_names)
        row = _row(doc_type, rows) if doc_type in _ROW_KEYS else None
        if row is None:
            row = don
            ngoai.append(f"{file_name} → \"{document_name}\"")
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + _goc._data_url_size(file.get("dataUrl"))
        attachments.append(_igate._item(index, file_name, document_name, row, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "source": "llm" if llm_type else "default",
                           "documentName": document_name, "componentIndex": row[0]})

    if ngoai:
        warnings.append(
            "Giấy tờ ngoài 3 dòng của bảng đã tạm đính vào dòng Đơn (vẫn là tệp riêng, giữ tên) vì cổng mới không có "
            "dòng \"giấy tờ khác\" — nếu cần tách riêng, cán bộ dùng nút \"Thêm giấy tờ\" của cổng: "
            f"{', '.join(ngoai)}."
        )
    thieu = [ten for slot, ten in _goc._ROWS_BAT_BUOC.items()
             if not any(_goc._ROUTES[t][0] == slot for t in seen_types if t in _goc._ROUTES)]
    if attachments and thieu:
        warnings.append(
            "Thiếu thành phần hồ sơ bắt buộc, chưa có tệp cho dòng: " + "; ".join(thieu) + ". Nơi tiếp nhận sẽ trả "
            "hồ sơ — cán bộ đề nghị người dân bổ sung bản scan."
        )
    if "van_ban_dai_dien" in seen_types:
        warnings.append(
            "Hồ sơ có Văn bản về việc đại diện → đây là trường hợp NỘP THAY. Tài khoản đang đăng nhập phải là của "
            "chính người được ủy quyền (cổng mới khoá Họ tên/Số CCCD người nộp theo tài khoản)."
        )
    for row_index, total in sorted(bytes_per_row.items()):
        if total > _goc._MAX_FILE_BYTES:
            warnings.append(
                f"Tổng dung lượng các tệp đính vào dòng thứ {row_index} là {total / 1024 / 1024:.1f} MB, vượt giới hạn "
                "6 MB của cổng — cần nén PDF, bỏ bản trùng (bản ký số + bản chưa ký) hoặc tách tệp trước khi nộp."
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
        "ocr_text": join_ocr_documents(ocr_results),
        "errors": errors,
    }
