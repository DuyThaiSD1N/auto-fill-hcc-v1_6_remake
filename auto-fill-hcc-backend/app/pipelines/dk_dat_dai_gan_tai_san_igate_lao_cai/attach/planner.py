"""Đính kèm cho [Lào Cai - cổng iGate mới] Đăng ký đất đai, cấp Giấy chứng nhận lần đầu (1.115688).

Phân loại giữ NGUYÊN của pipeline cổng cũ (dk_dat_dai_gan_tai_san_lao_cai/attach: OCR → LLM gán nhãn catalog +
documentName) cùng các cảnh báo thiếu Đơn / giấy tờ quét gộp vào tệp Đơn (MERGED_HINTS).

Bước 2 "Thành phần hồ sơ hệ thống" của cổng mới (crawl 02/11/2026, UBND phường) là bảng 8 dòng, cổng TÍCH SẴN cả 8, KHÔNG
còn danh sách "Giấy tờ khác". Thứ tự khác cổng cũ (dòng quốc phòng lên thứ 6):
   1 Đơn đăng ký Mẫu số 21 · 2 Giấy tờ Điều 137/148/149 · 3 Nhận thừa kế · 4 Trích lục/trích đo bản đồ địa chính
   5 Báo cáo rà soát Mẫu 21d · 6 Quyết định vị trí đóng quân · 7 Hồ sơ thiết kế xây dựng · 8 Chứng từ nghĩa vụ tài chính
Dò dòng theo TỪ KHOÁ của catalog cổng cũ; không ra thì lấy theo VỊ TRÍ khi bảng đúng 8 dòng. Giấy tờ không có dòng riêng
(quyết định thành lập, phương án sử dụng đất, Giấy ủy quyền, đơn đề nghị xác nhận, CCCD, tài liệu khác) → dòng Đơn, giữ
tên + cảnh báo dùng nút "Thêm giấy tờ". Không bỏ tệp nào.

Engine FE "attp-row" + untickUnplannedRows dùng chung với cho_thue_dat_thue_rung_igate_lao_cai.
"""

import time

from app.pipelines._shared import fold
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.pipelines.dk_dat_dai_gan_tai_san_lao_cai.attach import catalog
from app.pipelines.dk_dat_dai_gan_tai_san_lao_cai.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
# Cổng Lào Cai: "Dung lượng tối đa là 6 Mb".
_GIOI_HAN_BYTE = 6 * 1024 * 1024

# Bảng 8 dòng (crawl 02/11/2026), tên rút gọn — chỉ dùng khi extension không gửi danh sách dòng.
_DEFAULT_ROWS = [
    "Đơn đăng ký đất đai, tài sản gắn liền với đất theo Mẫu số 21 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND",
    "Một trong các loại giấy tờ quy định tại Điều 137, khoản 4, khoản 5 Điều 148, khoản 4, khoản 5 Điều 149 Luật Đất đai",
    "Giấy tờ về việc nhận thừa kế quyền sử dụng đất theo quy định của pháp luật về dân sự đối với người gốc Việt Nam "
    "định cư ở nước ngoài",
    "Sơ đồ hoặc bản trích lục bản đồ địa chính hoặc mảnh trích đo bản đồ địa chính thửa đất (nếu có)",
    "Báo cáo kết quả rà soát hiện trạng sử dụng đất theo Mẫu số 21d ban hành kèm theo Quyết định số 47/2026/QĐ-UBND",
    "Quyết định vị trí đóng quân hoặc văn bản giao cơ sở nhà đất hoặc địa điểm công trình quốc phòng, an ninh",
    "Hồ sơ thiết kế xây dựng công trình đã được cơ quan chuyên môn về xây dựng thẩm định",
    "Chứng từ thực hiện nghĩa vụ tài chính, giấy tờ liên quan đến việc miễn, giảm nghĩa vụ tài chính về đất đai, tài sản "
    "gắn liền với đất (nếu có)",
]
# vị trí dòng trong catalog cổng cũ → vị trí (1-based) trên bảng cổng mới.
_VI_TRI_MOI = {
    catalog.ROW_DON: 1,
    catalog.ROW_GIAY_TO_QSDD: 2,
    catalog.ROW_THUA_KE: 3,
    catalog.ROW_TRICH_LUC: 4,
    catalog.ROW_BAO_CAO_RA_SOAT: 5,
    catalog.ROW_QUOC_PHONG: 6,
    catalog.ROW_THIET_KE: 7,
    catalog.ROW_NGHIA_VU_TAI_CHINH: 8,
}

Row = _igate.Row


def _default_rows() -> list[Row]:
    return [(i + 1, name, fold(name)) for i, name in enumerate(_DEFAULT_ROWS)]


def _row(position: int, rows: list[Row]) -> Row | None:
    found = _igate._find(catalog.ROWS[position][0], rows)
    if found is None and len(rows) == len(_DEFAULT_ROWS):
        found = rows[_VI_TRI_MOI[position] - 1]
    return found


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, dict[str, str]] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    rows = _igate._portal_rows(components) or _default_rows()
    warnings: list[str] = []
    don = _row(catalog.ROW_DON, rows) or rows[0]

    attachments: list[dict] = []
    classified: list[dict] = []
    ngoai_bang: list[str] = []
    used_names: set[str] = set()
    labels: set[str] = set()
    bytes_per_row: dict[int, int] = {}
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        detected = llm_types.get(index) or {}
        label = detected.get("label") or "khac"
        if not catalog.is_valid(label):
            label = "khac"
        labels.add(label)
        fallback = catalog.display_name(label)
        document_name = _goc._unique_document_name(detected.get("documentName") or fallback, used_names, fallback)
        position = catalog.row_for(label)
        row = (_row(position, rows) if position else None) or don
        if not position:
            ngoai_bang.append(f"{file_name} → \"{document_name}\"")
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + _goc._data_url_size(file.get("dataUrl", ""))
        attachments.append(_igate._item(index, file_name, document_name, row, label))
        classified.append({"fileName": file_name, "label": label, "documentName": document_name,
                           "source": "llm" if index in llm_types else "default", "target": "attp-row",
                           "componentIndex": row[0], **({} if position else {"routedTo": "don"})})

    if "don_dang_ky" not in labels:
        warnings.append(
            "Không thấy Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 21) — đây là thành phần bắt buộc, dòng "
            "Đơn đăng ký sẽ để trống. Cán bộ kiểm tra lại hồ sơ."
        )
    for label, (host_label, mo_ta) in catalog.MERGED_HINTS.items():
        if label not in labels and host_label in labels:
            warnings.append(
                f"Không thấy tệp riêng cho {mo_ta}. Hồ sơ thủ tục này thường quét gộp chúng vào cùng tệp với "
                f"\"{catalog.display_name(host_label)}\". Mỗi tệp chỉ xếp được vào MỘT dòng nên chúng đi kèm ở dòng "
                "Đơn và dòng riêng để trống; nếu nơi tiếp nhận yêu cầu tách riêng thì cán bộ đề nghị người dân tách "
                "tệp rồi đính bổ sung."
            )
    if ngoai_bang:
        warnings.append(
            "Giấy tờ không có dòng riêng hoặc chưa rõ loại đã tạm đính vào dòng Đơn đăng ký (vẫn là tệp riêng, giữ "
            "tên) vì cổng mới không còn danh sách \"Giấy tờ khác\" — nếu cần tách riêng, cán bộ dùng nút \"Thêm giấy "
            f"tờ\" của cổng: {', '.join(ngoai_bang)}."
        )
    for row_index, total in sorted(bytes_per_row.items()):
        if total > _GIOI_HAN_BYTE:
            warnings.append(
                f"Tổng dung lượng các tệp đính vào dòng thứ {row_index} là {total / 1024 / 1024:.1f} MB, vượt giới hạn "
                "6 MB của cổng — cần nén PDF hoặc giảm DPI trước khi nộp."
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
    ]
    started = time.monotonic()
    llm_types: dict[int, dict[str, str]] = {}
    if any(doc["text"].strip() for doc in llm_documents):
        try:
            llm_types = await _goc._classify_with_llm(llm_documents)
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
            "llmDocuments": [f["name"] for f in raw_files],
            "portalRows": len(_igate._portal_rows(components)),
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "ocr_text": join_ocr_documents(ocr_results),
        "llm_output": {str(idx): value for idx, value in llm_types.items()},
        "errors": errors,
    }
