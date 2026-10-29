"""Đính kèm cho [Lào Cai - cổng iGate mới] sử dụng đất kết hợp đa mục đích, cấp phường/xã (1.115682).

Phân loại giữ NGUYÊN của pipeline cổng cũ (su_dung_dat_ket_hop_da_muc_dich_cap_xa/attach: OCR → LLM từng tệp → docType)
và tên giấy tờ theo danh mục thành phần hồ sơ.

Cổng cũ KHÔNG có bảng thành phần (mọi tệp xuống "Giấy tờ khác"). Bước 2 "Thành phần hồ sơ hệ thống" của cổng mới (crawl
29/10/2026, UBND phường) có MỘT bảng 3 dòng, cổng TÍCH SẴN cả 3, KHÔNG có dòng "giấy tờ khác":
   1 Văn bản đề nghị sử dụng đất kết hợp đa mục đích theo Mẫu số 20 (QĐ 47/2026/QĐ-UBND)
   2 Phương án sử dụng đất kết hợp
   3 Giấy chứng nhận đã cấp hoặc giấy tờ về quyền sử dụng đất (nếu có)
⚠ Bản crawl ghi componentName dòng 2 là "scannerScan tệp tin…" (đọc nhầm ô nút); dò tên không ra thì lấy theo VỊ TRÍ
dòng khi bảng đúng 3 dòng. Giấy tờ còn lại (CCCD chủ hộ, giấy uỷ quyền, tờ khai thuế, tài liệu lạ) → dòng Đơn, giữ tên +
cảnh báo; cổng cũ cũng đính TẤT CẢ tệp. Không bỏ tệp nào.

Engine FE "attp-row" + untickUnplannedRows dùng chung với cho_thue_dat_thue_rung_igate_lao_cai.
"""

import time

from app.pipelines._shared import fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_cap_xa.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Bảng 3 dòng NGUYÊN VĂN (crawl 29/10/2026; tên dòng 2 lấy từ ô "Tên giấy tờ").
_DEFAULT_ROWS = [
    "Văn bản đề nghị sử dụng đất kết hợp đa mục đích theo Mẫu số 20 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND",
    "Phương án sử dụng đất kết hợp",
    "Giấy chứng nhận đã cấp hoặc một trong các loại giấy tờ về quyền sử dụng đất theo quy định của pháp luật (nếu có).",
]
# docType → (từ khoá dò dòng, vị trí dòng mặc định 0-based)
_ROW_KEYS: dict[str, tuple[list[str], int]] = {
    "don_de_nghi": (["mau so 20", "van ban de nghi su dung dat ket hop"], 0),
    "phuong_an": (["phuong an su dung dat ket hop"], 1),
    "gcn": (["giay chung nhan da cap"], 2),
}
# Tên tài liệu: cổng mới dùng Mẫu số 20 nên bỏ số mẫu của cổng cũ khỏi tên Đơn.
_TEN_DON = "Văn bản đề nghị sử dụng đất kết hợp đa mục đích"

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
    don = _row("don_de_nghi", rows) or rows[0]

    attachments: list[dict] = []
    classified: list[dict] = []
    ngoai: list[str] = []
    unknown: list[str] = []
    seen_types: set[str] = set()
    used_names: set[str] = set()
    bytes_per_row: dict[int, int] = {}
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _goc._ALLOWED else _goc._OTHER
        seen_types.add(doc_type)
        if doc_type == _goc._OTHER:
            base = _goc._other_display(file_name)
        else:
            base = _TEN_DON if doc_type == "don_de_nghi" else _goc._DOC_NAMES[doc_type]
        document_name = _goc._unique_document_name(base, used_names)
        row = _row(doc_type, rows) if doc_type in _ROW_KEYS else None
        if row is None:
            row = don
            (unknown if doc_type == _goc._OTHER else ngoai).append(f"{file_name} → \"{document_name}\"")
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + _goc._data_url_size(file.get("dataUrl"))
        attachments.append(_igate._item(index, file_name, document_name, row, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "source": "llm" if llm_type else "default",
                           "documentName": document_name, "componentIndex": row[0]})

    if ngoai or unknown:
        warnings.append(
            "Giấy tờ ngoài 3 dòng của bảng đã tạm đính vào dòng văn bản đề nghị (vẫn là tệp riêng, giữ tên) vì cổng "
            "mới không có dòng \"giấy tờ khác\" — nếu cần tách riêng, cán bộ dùng nút \"Thêm giấy tờ\" của cổng: "
            f"{', '.join(ngoai + unknown)}."
        )
    thieu = [ten for loai, ten in _goc._GIAY_TO_COT_LOI.items() if loai not in seen_types and loai != "gcn"]
    if attachments and thieu:
        warnings.append(
            "Chưa có tệp cho thành phần hồ sơ: " + "; ".join(thieu).replace(" theo Mẫu số 13", "")
            + ". Nơi tiếp nhận sẽ trả hồ sơ thiếu — cán bộ đề nghị người dân bổ sung bản scan."
        )
    for row_index, total in sorted(bytes_per_row.items()):
        if total > _goc._MAX_FILE_BYTES:
            warnings.append(
                f"Tổng dung lượng các tệp đính vào dòng thứ {row_index} là {total / 1024 / 1024:.1f} MB, vượt giới hạn "
                "6 MB của cổng — Phương án kèm bản đồ/bản vẽ hay vướng chỗ này: nén PDF hoặc tách tệp trước khi nộp."
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
