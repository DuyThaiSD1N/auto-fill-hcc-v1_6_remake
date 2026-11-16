"""Đính kèm NGUYÊN TỆP cho [Lào Cai - cổng iGate mới] đăng ký biến động quyền sử dụng đất (1.115668).

Phân loại giữ NGUYÊN của pipeline cổng cũ (dang_ky_quyen_su_dung_dat_lao_cai/attach: OCR → LLM từng tệp → nhãn catalog;
nhánh b) chỉ khi có biên bản tặng cho QSDĐ cho Nhà nước/cộng đồng). Chỉ cách đặt tệp vào bảng là khác.

Bước 2 "Thành phần hồ sơ hệ thống" của cổng mới (crawl 16/11/2026, cổng test, Chi nhánh VPĐKĐĐ khu vực Yên Bái): MỘT
bảng 14 dòng có ô chọn tệp, cổng TÍCH SẴN cả 14, KHÔNG có dòng "giấy tờ khác". 14 dòng = 12 dòng nhánh a) + 2 dòng nhánh
b) của cổng cũ nối liền (bỏ hai dòng tiêu đề nhánh) — SUY theo số dòng, bản crawl chưa đọc được tên dòng. Vì vậy dòng
được dò theo TỪ KHOÁ catalog cổng cũ trên tên dòng extension gửi lên (attachmentContext); nhánh b) bắt đầu từ dòng đầu
tiên chứa từ khoá biên bản tặng cho. Không có danh sách dòng của trang → dựng theo vị trí a1…a12, b1, b2.

Tệp không có dòng riêng (CCCD, hóa đơn, tờ khai thuế, tài liệu chưa rõ loại, giấy nhánh a) khi hồ sơ đi nhánh b)) →
đính chung dòng Đơn của nhánh (vẫn là tệp riêng, giữ tên) kèm cảnh báo; không bỏ tệp nào.

Engine FE "attp-row" + untickUnplannedRows dùng chung với cho_thue_dat_thue_rung_igate_lao_cai.
"""

import time

from app.pipelines._shared import fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.attach import catalog
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

Row = _igate.Row

# Thứ tự dòng của bảng cổng mới (SUY): a1…a12 rồi b1, b2.
_ORDER = sorted(catalog.ROWS, key=lambda row: (row[0], row[1]))
_B_KEYS = [key for (branch, _), (keys, _name) in catalog.ROWS.items() if branch == catalog.BRANCH_B for key in keys]


def _default_rows() -> list[Row]:
    """Dòng dựng theo vị trí; tên rút gọn + từ khoá để _igate._find dò được như tên dòng thật."""
    rows = []
    for index, row in enumerate(_ORDER, start=1):
        keys, name = catalog.ROWS[row]
        rows.append((index, name, fold(" ".join([*keys, name]))))
    return rows


def _branch_rows(rows: list[Row]) -> dict[str, list[Row]]:
    """Cắt bảng phẳng: nhánh b) mở từ dòng đầu tiên mang từ khoá biên bản tặng cho; không thấy thì cả bảng là a)."""
    start = next((i for i, row in enumerate(rows) if any(key in row[2] for key in _B_KEYS)), None)
    if start is None:
        return {catalog.BRANCH_A: rows, catalog.BRANCH_B: []}
    return {catalog.BRANCH_A: rows[:start], catalog.BRANCH_B: rows[start:]}


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict], str]:
    llm_types = llm_types or {}
    entries: list[dict] = []
    used_names: set[str] = set()
    for position, file in enumerate(files):
        index = int(file.get("_index", position))
        detected = llm_types.get(index) or {}
        label = detected.get("label") or "khac"
        fallback = catalog.display_name(label)
        entries.append({
            "index": index,
            "file": file,
            "fileName": str(file.get("name") or f"file-{index + 1}"),
            "label": label,
            "documentName": _goc._unique_document_name(detected.get("documentName") or fallback, used_names, fallback),
        })

    b_rows = sorted(
        row for row in (catalog.row_of(e["label"]) for e in entries) if row and row[0] == catalog.BRANCH_B
    )
    branch = catalog.BRANCH_B if b_rows else catalog.BRANCH_A
    all_rows = _igate._portal_rows(components) or _default_rows()
    rows = _branch_rows(all_rows)[branch] or all_rows
    if branch == catalog.BRANCH_A:
        don_row = _igate._find(catalog.ROWS[(catalog.BRANCH_A, 1)][0], rows) or rows[0]
    else:
        don_row = rows[0]

    attachments: list[dict] = []
    warnings: list[str] = []
    classified: list[dict] = []
    extra_files: list[str] = []
    bytes_per_row: dict[int, int] = {}
    for entry in entries:
        label, file_name, document_name = entry["label"], entry["fileName"], entry["documentName"]
        slot = catalog.row_of(label)
        if branch == catalog.BRANCH_B and label == "gcn":
            # Dòng nhánh b) ghi "… và bản gốc Giấy chứng nhận đã cấp" → GCN đi cùng dòng biên bản đầu tiên.
            slot = b_rows[0]
        row = _igate._find(catalog.ROWS[slot][0], rows) if slot and slot[0] == branch else None
        routed = row is None
        if routed:
            row = don_row
            extra_files.append(f"{file_name} ({document_name})")
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + _goc._data_url_size(entry["file"].get("dataUrl"))
        attachments.append(_igate._item(entry["index"], file_name, document_name, row, label))
        classified.append({"fileName": file_name, "label": label, "documentName": document_name, "target": "attp-row",
                           "source": "llm" if (llm_types.get(entry["index"]) or {}).get("label") else "default",
                           "componentIndex": row[0], **({"routedTo": "don_dang_ky"} if routed else {})})

    if extra_files:
        warnings.append(
            f"Giấy tờ không có dòng riêng hoặc chưa rõ loại đã đính chung dòng \"{don_row[1]}\" — cán bộ kiểm tra "
            f"lại: {', '.join(extra_files)}."
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
    llm_types: dict[int, dict[str, str]] = {}
    if any(doc["text"].strip() for doc in llm_docs):
        try:
            llm_types = await _goc._classify_with_llm(llm_docs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified, branch = build_plan_items(valid_files, llm_types, components)
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
        "llm_output": {str(idx): value for idx, value in llm_types.items()},
        "errors": errors,
    }
