"""Đính kèm cho [Lào Cai - cổng iGate mới] cấp GCN cho người nhận chuyển nhượng trong dự án BĐS (1.115667).

Phân loại giữ NGUYÊN của pipeline cổng cũ (cap_GCN_nhan_chuyen_nhuong/attach: OCR → LLM → nhãn catalog + nhánh a/b cho
cả bộ). Chỉ cách đặt tệp vào bảng là khác.

Bước 2 "Thành phần hồ sơ hệ thống" (crawl 29/10/2026, Sở NN&MT Lào Cai): MỘT bảng 16 dòng, cổng TÍCH SẴN cả 16, KHÔNG
còn dòng tiêu đề nhánh, KHÔNG có radio chọn trường hợp, KHÔNG có dòng "giấy tờ khác". Hai nhánh của cổng cũ nối liền nhau,
mỗi nhánh mở đầu bằng dòng Đơn Mẫu số 24:
   1–8  a) chủ đầu tư nộp       : Đơn · nghiệm thu · đủ điều kiện · Hợp đồng · bàn giao · GCN chủ đầu tư · chứng từ · Sơ đồ
   9–16 b) người nhận tự nộp    : Đơn · Hợp đồng · bàn giao · nghiệm thu · đủ điều kiện · GCN chủ đầu tư · chứng từ · Sơ đồ
Dòng 4/10 và 5/11 TRÙNG tên nguyên văn → khoanh nhóm theo dòng Đơn rồi mới dò từ khoá, và gửi componentIndex để FE chọn
đúng dòng của nhánh. GCN chủ đầu tư có trang Sơ đồ mà hồ sơ không có sơ đồ riêng → đính lại chính tệp GCN vào dòng Sơ đồ
(như cổng cũ). CCCD và tài liệu không rõ loại không có dòng → bỏ qua kèm cảnh báo (như cổng cũ).

Engine FE "attp-row" + untickUnplannedRows dùng chung với cho_thue_dat_thue_rung_igate_lao_cai.
"""

import time

from app.pipelines._shared import fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cap_GCN_nhan_chuyen_nhuong.attach import catalog
from app.pipelines.cap_GCN_nhan_chuyen_nhuong.attach import planner as _goc
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_HOP_DONG = (
    "Hợp đồng chuyển nhượng quyền sử dụng đất, quyền sở hữu nhà ở, công trình xây dựng, hạng mục công trình xây dựng "
    "theo quy định của pháp luật"
)
_BAN_GIAO = "Biên bản bàn giao nhà, đất, công trình xây dựng, hạng mục công trình xây dựng"
_NGHIEM_THU = (
    "Văn bản về việc nhà ở, công trình xây dựng đã được nghiệm thu đưa vào khai thác, sử dụng theo quy định của pháp "
    "luật về xây dựng đối với trường hợp có nhận chuyển nhượng nhà ở, công trình xây dựng"
)
_DU_DIEU_KIEN = (
    "Văn bản về việc đủ điều kiện được chuyển nhượng cho cá nhân tự xây dựng nhà ở đối với trường hợp chuyển nhượng "
    "quyền sử dụng đất đã có hạ tầng kỹ thuật theo quy định của pháp luật về kinh doanh bất động sản"
)
_GCN = "Giấy chứng nhận đã cấp cho chủ đầu tư dự án"
_CHUNG_TU = (
    "Chứng từ chứng minh việc hoàn thành nghĩa vụ tài chính đối với trường hợp Văn phòng Đăng ký đất đai nhận được văn "
    "bản của cơ quan có thẩm quyền về việc dự án được điều chỉnh quy hoạch xây dựng chi tiết mà làm phát sinh nghĩa vụ "
    "tài chính theo quy định của pháp luật"
)
_SO_DO = "Sơ đồ tài sản gắn liền với đất"
_DON = "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND"

# Bảng 16 dòng NGUYÊN VĂN (crawl 29/10/2026).
_DEFAULT_ROWS = [
    _DON + " do người nhận chuyển nhượng quyền sử dụng đất, quyền sở hữu nhà ở, công trình xây dựng, hạng mục công "
    "trình xây dựng kê khai",
    _NGHIEM_THU, _DU_DIEU_KIEN, _HOP_DONG, _BAN_GIAO, _GCN, _CHUNG_TU, _SO_DO,
    _DON, _HOP_DONG, _BAN_GIAO,
    _NGHIEM_THU + " (nếu có)", _DU_DIEU_KIEN + " (nếu có)", _GCN + " (nếu có)", _CHUNG_TU + " (nếu có)", _SO_DO,
]

_DON_KEY = "mau so 24"
# Nhãn catalog cổng cũ → từ khoá dòng; trong CÙNG một nhánh mỗi từ khoá chỉ khớp đúng một dòng.
_ROW_KEYS = {label: keywords for label, _a, _b, keywords, _name, _desc in catalog.CATALOG}

Row = _igate.Row


def _default_rows() -> list[Row]:
    return [(i + 1, name, fold(name)) for i, name in enumerate(_DEFAULT_ROWS)]


def _branch_rows(rows: list[Row]) -> dict[str, list[Row]]:
    """Cắt bảng thành nhóm, mỗi nhóm mở đầu bằng dòng Đơn Mẫu số 24: nhóm 1 = nhánh a), nhóm 2 = nhánh b)."""
    groups: list[list[Row]] = []
    for row in rows:
        if _DON_KEY in row[2] or not groups:
            groups.append([])
        groups[-1].append(row)
    if len(groups) < 2:
        return {catalog.BRANCH_A: rows, catalog.BRANCH_B: rows}
    return {catalog.BRANCH_A: groups[0], catalog.BRANCH_B: groups[1]}


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
    llm_branch: str = "",
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict], str]:
    llm_types = llm_types or {}
    branch = llm_branch if llm_branch in catalog.SECTION_HEADERS else catalog.BRANCH_B
    rows = _branch_rows(_igate._portal_rows(components) or _default_rows())[branch]
    ocr_by_name = {item.get("name"): item for item in ocr_results}

    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    skipped: list[str] = []
    missing: list[str] = []
    bytes_per_row: dict[int, int] = {}
    used_names: set[str] = set()

    def place(index: int, file: dict, file_name: str, document_name: str, row: Row, label: str) -> None:
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + _goc._data_url_size(file.get("dataUrl"))
        attachments.append(_igate._item(index, file_name, document_name, row, label))

    gcn_entries: list[tuple[int, dict, str, str]] = []
    has_so_do = False
    for position, file in enumerate(files):
        index = int(file.get("_index", position))
        file_name = str(file.get("name") or f"file-{index + 1}")
        detected = llm_types.get(index) or {}
        label = detected.get("label") or "khac"
        fallback = catalog.display_name(label)
        document_name = _goc._unique_document_name(detected.get("documentName") or fallback, used_names, fallback)
        row = _igate._find(_ROW_KEYS[label], rows) if catalog.has_slot(label) else None
        if row is None:
            target = "skip"
            if catalog.has_slot(label):
                missing.append(f"{file_name} ({document_name})")
            else:
                skipped.append(f"{file_name} ({document_name})")
        else:
            target = "attp-row"
            place(index, file, file_name, document_name, row, label)
            has_so_do = has_so_do or label == "so_do"
            if label == "gcn_chu_dau_tu":
                gcn_entries.append((index, file, file_name, document_name))
        classified.append({"fileName": file_name, "label": label, "documentName": document_name, "target": target,
                           "source": "llm" if detected.get("label") else "default",
                           "componentIndex": row[0] if row else None})

    # Sơ đồ nằm ở trang 2 GCN của chủ đầu tư → đính lại chính tệp GCN vào dòng Sơ đồ khi không có sơ đồ riêng.
    so_do_row = _igate._find(_ROW_KEYS["so_do"], rows)
    if not has_so_do and so_do_row:
        for index, file, file_name, document_name in gcn_entries:
            text = fold(str(ocr_by_name.get(file_name, {}).get("text") or ""))
            if any(marker in text for marker in _goc._SO_DO_MARKERS):
                place(index, file, file_name, document_name, so_do_row, "gcn_chu_dau_tu")
                classified.append({"fileName": file_name, "label": "gcn_chu_dau_tu", "documentName": document_name,
                                   "target": "attp-row", "componentIndex": so_do_row[0], "reason": "so_do_in_gcn"})
                break

    if skipped:
        warnings.append(
            "Bảng thành phần hồ sơ không có dòng cho CCCD và giấy tờ không rõ loại — đã bỏ qua (cổng mới không có dòng "
            f"\"giấy tờ khác\"): {', '.join(skipped)}."
        )
    if missing:
        warnings.append(
            "Bảng thành phần hồ sơ trên trang không có dòng cho các giấy tờ sau — đã bỏ qua, cán bộ đính tay: "
            f"{', '.join(missing)}."
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
    return attachments, warnings, classified, branch


async def plan(files: list[FileItem], options: dict | None = None, session: dict | None = None) -> dict:
    components = ((options or {}).get("attachmentContext") or {}).get("components")
    errors: list[str] = []
    raw_files = [
        {"name": file.name, "type": file.type, "dataUrl": file.dataUrl, "_index": idx}
        for idx, file in enumerate(files)
    ]
    valid_files: list[dict] = []
    for file in raw_files:
        size = _goc._data_url_size(file.get("dataUrl", ""))
        if size > _goc._MAX_FILE_BYTES:
            errors.append(f"File '{file['name']}' vượt quá 6 MB ({size / 1024 / 1024:.2f} MB) — đã bỏ qua.")
        else:
            valid_files.append(file)

    ocr_files = [file for file in valid_files if file.get("type") in _OCR_TYPES]
    started = time.monotonic()
    ocr_results = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    ocr_ms = int((time.monotonic() - started) * 1000)
    for result in ocr_results:
        if result.get("error"):
            errors.append(f"OCR {result.get('name')}: {result['error']}")

    ocr_by_name = {result.get("name"): result for result in ocr_results}
    llm_docs = [
        {"index": file["_index"], "text": str(ocr_by_name.get(file.get("name"), {}).get("text") or "")}
        for file in valid_files
    ]
    started = time.monotonic()
    llm_branch, llm_types = "", {}
    if any(doc["text"].strip() for doc in llm_docs):
        try:
            llm_branch, llm_types = await _goc._classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified, branch = build_plan_items(
        valid_files, ocr_results, llm_types, llm_branch, components
    )
    errors.extend(warnings)
    return {
        "attachments": attachments,
        "extracted": {
            "documents": [file["name"] for file in raw_files],
            "ocrDocuments": [result.get("name") for result in ocr_results if result.get("text")],
            "llmDocuments": [file["name"] for file in valid_files],
            "portalRows": len(_igate._portal_rows(components)),
            "sessionId": (session or {}).get("request_id"),
            "branch": branch,
            "classified": classified,
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {"branch": llm_branch, **{str(idx): value for idx, value in llm_types.items()}},
        "errors": errors,
    }
