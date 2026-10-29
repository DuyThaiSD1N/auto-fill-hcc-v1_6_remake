"""Đính kèm cho [Lào Cai - cổng iGate mới] tổ chức kinh tế nhận chuyển nhượng QSDĐ thực hiện dự án (1.115681).

Phân loại giữ NGUYÊN của pipeline cổng cũ (to_chuc_kinh_te_nhan_chuyen_nhung_sqdd_du_an/attach: OCR → LLM từng tệp →
docType) và tên mô tả của từng loại giấy tờ.

Cổng cũ KHÔNG có bảng thành phần (mọi tệp xuống "Giấy tờ khác"). Bước 2 "Thành phần hồ sơ hệ thống" của cổng mới (crawl
29/10/2026, UBND phường) có MỘT bảng 3 dòng, cổng TÍCH SẴN cả 3, KHÔNG có dòng "giấy tờ khác":
   1 Văn bản đề nghị Mẫu số 16 (dự án thu hồi đất theo Điều 79 không dùng vốn NSNN, nhà đầu tư chọn thoả thuận)
   2 Văn bản đề nghị Mẫu số 37 (điểm a, b khoản 1 Điều 127 — trường hợp chính của thủ tục)
   3 Trích lục vị trí khu đất mà nhà đầu tư đề xuất thực hiện dự án
Văn bản đề nghị vào dòng Mẫu 37, trừ khi OCR của chính văn bản đó ghi "Mẫu số 16" mà không ghi "Mẫu số 37". Sơ đồ/trích
lục khu đất → dòng 3. Giấy tờ còn lại (QĐ chấp thuận chủ trương, GCN ĐKDN, giấy uỷ quyền, QĐ cho thuê đất, sơ hoạ mặt
bằng, GCN QSDĐ, giấy tờ tuỳ thân, tài liệu lạ) → dòng văn bản đề nghị đã chọn, giữ tên + cảnh báo (cổng cũ cũng đính
TẤT CẢ tệp, kể cả giấy tờ tuỳ thân). Không bỏ tệp nào.

Engine FE "attp-row" + untickUnplannedRows dùng chung với cho_thue_dat_thue_rung_igate_lao_cai.
"""

import time

from app.pipelines._shared import fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhung_sqdd_du_an.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Bảng 3 dòng NGUYÊN VĂN (crawl 29/10/2026).
_DEFAULT_ROWS = [
    "Văn bản đề nghị theo Mẫu số 16 kèm theo Quyết định số 47/2026/QĐ-UBND đối với dự án thuộc trường hợp nhà nước "
    "thu hồi đất theo điều 79 Luật Đất đai năm 2024 không sử dụng vốn ngân sách nhà nước mà nhà đầu tư lựa chọn "
    "phương án thỏa thuận về quyền sử dụng đất, không đề xuất thu hồi đất",
    "Văn bản đề nghị theo Mẫu số 37 kèm theo Quyết định số 47/2026/QĐ-UBND đối với trường hợp quy định tại điểm a, b "
    "Khoản 1 Điều 127 Luật Đất đai",
    "Trích lục vị trí khu đất mà nhà đầu tư đề xuất thực hiện dự án",
]
_MAU_16 = ["mau so 16"]
_MAU_37 = ["mau so 37"]
_TRICH_LUC = ["trich luc vi tri khu dat"]

Row = _igate.Row


def _default_rows() -> list[Row]:
    return [(i + 1, name, fold(name)) for i, name in enumerate(_DEFAULT_ROWS)]


def _la_mau_16(text: str) -> bool:
    folded = fold(text or "")
    return "mau so 16" in folded and "mau so 37" not in folded


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, str] | None = None,
    components: list[dict] | None = None,
    ocr_texts: dict[int, str] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    ocr_texts = ocr_texts or {}
    rows = _igate._portal_rows(components) or _default_rows()
    warnings: list[str] = []

    mau_16 = any(
        llm_types.get(i) == "don_de_nghi" and _la_mau_16(ocr_texts.get(i, "")) for i in range(len(files))
    )
    don = _igate._find(_MAU_16 if mau_16 else _MAU_37, rows) or _igate._find(_MAU_37 + _MAU_16, rows) or rows[0]
    trich_luc = _igate._find(_TRICH_LUC, rows)

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
        doc_type = llm_type if llm_type in _goc._ALLOWED else "other"
        seen_types.add(doc_type)
        if doc_type == "other":
            document_name = _goc._unique_name(_goc._other_display(file_name), used_names)
        else:
            document_name = _goc._unique_name(_goc._DISPLAY[doc_type], used_names)
        if doc_type == "don_de_nghi":
            row = don
        elif doc_type == "so_do_khu_dat" and trich_luc:
            row = trich_luc
        else:
            row = don
            (unknown if doc_type == "other" else ngoai).append(f"{file_name} → \"{document_name}\"")
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + _goc._data_url_size(file.get("dataUrl"))
        attachments.append(_igate._item(index, file_name, document_name, row, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "source": "llm" if llm_type else "default",
                           "documentName": document_name, "componentIndex": row[0]})

    if mau_16:
        warnings.append(
            "Văn bản đề nghị ghi Mẫu số 16 (dự án thu hồi đất theo Điều 79, nhà đầu tư chọn thoả thuận) nên được đính "
            "vào dòng Mẫu số 16 — cán bộ kiểm tra lại đúng trường hợp."
        )
    if ngoai or unknown:
        warnings.append(
            "Giấy tờ ngoài 3 dòng của bảng đã tạm đính vào dòng văn bản đề nghị (vẫn là tệp riêng, giữ tên) vì cổng "
            "mới không có dòng \"giấy tờ khác\" — nếu cần tách riêng, cán bộ dùng nút \"Thêm giấy tờ\" của cổng: "
            f"{', '.join(ngoai + unknown)}."
        )
    thieu = [nhan for doc_type, nhan in _goc._CORE_TYPES if doc_type not in seen_types]
    if thieu and attachments:
        warnings.append(
            "Chưa thấy trong bộ tệp đã tải lên: " + "; ".join(thieu) + ". Đây là các giấy tờ chính của hồ sơ tổ chức "
            "kinh tế nhận chuyển nhượng quyền sử dụng đất — cán bộ kiểm tra lại, nếu thiếu thật thì bổ sung trước khi "
            "nộp."
        )
    if "giay_to_tuy_than" in seen_types:
        warnings.append(
            "Có tệp là giấy tờ tùy thân (CCCD/CMND) — trợ lý vẫn đính như cổng cũ để không bỏ sót tệp; nơi tiếp nhận "
            "không yêu cầu thì cán bộ xoá tệp đó đi."
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
    ocr_texts = {
        index: str(by_name.get(file.get("name"), {}).get("text") or "") for index, file in enumerate(raw_files)
    }
    llm_documents = [{"index": index, "text": text} for index, text in ocr_texts.items() if text.strip()]
    started = time.monotonic()
    llm_types: dict[int, str] = {}
    if llm_documents:
        try:
            llm_types = await _goc._classify_with_llm(llm_documents, errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, llm_types, components, ocr_texts)
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
