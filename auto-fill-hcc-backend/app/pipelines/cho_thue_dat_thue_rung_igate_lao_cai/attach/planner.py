"""Đính kèm cho [Lào Cai - cổng iGate mới] giao đất/cho thuê đất, giao rừng/cho thuê rừng (1.115678).

Phân loại giữ NGUYÊN của pipeline cổng cũ (cho_thue_dat_thue_rung/attach: OCR → LLM từng tệp → docType). Chỉ cách đặt
tệp vào bảng là khác.

Bước 2 "Thành phần hồ sơ hệ thống" (crawl 29/10/2026 ở dichvucongtest.laocai.gov.vn, UBND Phường Yên Bái): MỘT bảng
10 dòng, KHÔNG có radio chọn trường hợp, KHÔNG có dòng "giấy tờ khác", cổng TÍCH SẴN cả 10 dòng. Mười dòng đúng thứ
tự 10 dòng của cổng cũ (slot 0..9):
   1 Đơn Mẫu số 01 · 2 VB phê duyệt dự án/chủ trương đầu tư · 3 KQ đấu giá KHÔNG THÀNH · 4 điểm i khoản 1 Điều 133
   5 PA SDĐ Điều 180 · 6 PA SDĐ công ty nông, lâm nghiệp tại địa phương · 7 PA SDĐ diện tích đất thu hồi
   8 Giấy phép khai thác khoáng sản · 9 giao rừng, cho thuê rừng · 10 miễn, giảm tiền sử dụng đất
Bộ giấy tờ trúng đấu giá (quyết định công nhận, biên bản, thông báo thuế, chứng từ nộp tiền, hợp đồng ủy quyền, CCCD)
không có dòng riêng → gộp vào dòng Đơn như cổng cũ. Tài liệu chưa rõ loại: cổng cũ đẩy xuống "giấy tờ khác", cổng
mới không có dòng đó → cũng vào dòng Đơn + cảnh báo. Không bỏ tệp nào.

Engine FE "attp-row": gửi index + tên NGUYÊN VĂN của dòng (dò trong attachmentContext theo từ khoá; extension không gửi
thì dùng bảng 10 dòng dưới đây) và cờ untickUnplannedRows để FE bỏ chọn tất cả rồi chỉ tích dòng có tệp.
"""

import time

from app.pipelines._shared import fold
from app.pipelines.cho_thue_dat_thue_rung.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

# Bảng 10 dòng NGUYÊN VĂN (crawl 29/10/2026; dòng 2 bị cắt ở 600 ký tự — FE so chuỗi con nên vẫn khớp).
_DEFAULT_ROWS = [
    "Đơn theo Mẫu số 01 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND",
    "Bản sao Văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu tư, quyết định chấp thuận chủ "
    "trương đầu tư đồng thời chấp thuận nhà đầu tư, văn bản phê duyệt kết quả lựa chọn nhà đầu tư theo quy định "
    "của pháp luật về đầu tư, pháp luật về đầu tư công, pháp luật về đầu tư theo phương thức đối tác công tư hoặc "
    "các văn bản, giấy tờ có giá trị pháp lý tương đương theo quy định của pháp luật",
    "Bản sao văn bản của đơn vị được giao tổ chức thực hiện việc đấu giá quyền sử dụng đất về kết quả đấu giá quyền "
    "sử dụng đất không thành quy định tại điểm b khoản 6 Điều 125 Luật Đất đai",
    "Bản sao các văn bản theo quy định của pháp luật đối với trường hợp quy định tại điểm i khoản 1 Điều 133 Luật "
    "Đất đai mà phải thu hồi đất để giao đất, cho thuê đất cho tổ chức, cá nhân sau chia tách, sáp nhập, chuyển đổi "
    "mô hình tổ chức",
    "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với tổ chức kinh tế, đơn vị "
    "sự nghiệp công lập đã được Nhà nước giao đất, cho thuê đất trước ngày Luật Đất đai có hiệu lực thi hành đối với "
    "trường hợp quy định tại Điều 180 Luật Đất đai (nếu có)",
    "Bản sao Phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương đã được cơ quan, tổ chức có thẩm quyền "
    "phê duyệt đối với trường hợp quy định tại Điều 181 Luật Đất đai (nếu có)",
    "Bản sao Phương án sử dụng đất đã được cơ quan, tổ chức có thẩm quyền phê duyệt đối với diện tích đất thu hồi của "
    "công ty nông, lâm nghiệp quản lý, sử dụng để giao đất, cho thuê đất quy định tại các điểm c, d và đ khoản 2 "
    "Điều 181 Luật Đất đai (nếu có)",
    "Bản sao Giấy phép khai thác khoáng sản trong trường hợp dự án sử dụng cho hoạt động khoáng sản",
    "Đối với trường hợp giao rừng, cho thuê rừng thì phải có thêm các tài liệu sau: Báo cáo điều tra, đánh giá hiện "
    "trạng rừng và bản đồ hiện trạng rừng theo quy định của pháp luật về lâm nghiệp đối với trường hợp giao đất và "
    "giao rừng",
    "Bản sao Giấy tờ chứng minh thuộc đối tượng miễn, giảm tiền sử dụng đất theo quy định của pháp luật",
]

# Từ khoá (đã fold) của dòng Đơn — nơi gộp bộ hồ sơ trúng đấu giá và tài liệu chưa rõ loại.
_DON_KEYS = ["mau so 01"]

# docType (catalog cổng cũ) → từ khoá dòng; mỗi từ khoá chỉ khớp ĐÚNG MỘT dòng trong 10 dòng.
_ROW_KEYS: dict[str, list[str]] = {
    "van_ban_chu_truong_dau_tu": ["phe duyet du an dau tu", "chap thuan chu truong dau tu"],
    "van_ban_dau_gia_khong_thanh": ["dau gia quyen su dung dat khong thanh"],
    "van_ban_dieu_133": ["diem i khoan 1 dieu 133"],
    "phuong_an_sdd_dieu_180": ["dieu 180"],
    "phuong_an_sdd_nong_lam_181": ["cong ty nong, lam nghiep tai dia phuong"],
    "phuong_an_sdd_dat_thu_hoi": ["dien tich dat thu hoi"],
    "giay_phep_khoang_san": ["khai thac khoang san"],
    "ho_so_rung": ["giao rung, cho thue rung"],
    "giay_to_mien_giam": ["mien, giam tien su dung dat"],
}

Row = tuple[int, str, str]  # (index 1-based, tên nguyên văn, tên fold)


def _portal_rows(components: list[dict] | None) -> list[Row]:
    rows: list[Row] = []
    for component in components or []:
        if not isinstance(component, dict):
            continue
        try:
            index = int(component.get("index"))
        except (TypeError, ValueError):
            continue
        name = str(component.get("componentName") or "").strip()
        if index > 0 and name:
            rows.append((index, name, fold(name)))
    return rows


def _default_rows() -> list[Row]:
    return [(i + 1, name, fold(name)) for i, name in enumerate(_DEFAULT_ROWS)]


def _find(keys: list[str], rows: list[Row]) -> Row | None:
    for key in keys:
        hits = [row for row in rows if key in row[2]]
        if hits:
            return min(hits, key=lambda row: (len(row[2]), row[0]))
    return None


def _item(file_index: int, file_name: str, document_name: str, row: Row, doc_type: str) -> dict:
    return {
        "fileIndex": file_index,
        "fileName": file_name,
        "documentName": document_name,
        "componentName": row[1],
        "componentIndex": row[0],
        "target": "attp-row",
        "needsAddComponent": False,
        "detectedType": doc_type,
        # Cổng tích sẵn mọi dòng → FE bỏ chọn tất cả rồi chỉ tích dòng được đính.
        "untickUnplannedRows": True,
    }


def _dedupe_document_names(attachments: list[dict]) -> None:
    """documentName thành TÊN TỆP khi FE dựng file → hai tệp cùng tên trong một ô sẽ bị bộ chống trùng bỏ qua."""
    counts: dict[tuple, int] = {}
    for item in attachments:
        key = (item["componentIndex"], item["documentName"])
        counts[key] = counts.get(key, 0) + 1
    used: dict[tuple, int] = {}
    for item in attachments:
        key = (item["componentIndex"], item["documentName"])
        if counts[key] < 2:
            continue
        used[key] = used.get(key, 0) + 1
        item["documentName"] = f"{item['documentName']} ({used[key]})"


def build_plan_items(
    files: list[dict],
    llm_types: dict[int, str] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    rows = _portal_rows(components) or _default_rows()
    warnings: list[str] = []
    don = _find(_DON_KEYS, rows)
    if don is None:
        don = rows[0]
        warnings.append(
            f"Bảng thành phần hồ sơ không có dòng 'Đơn theo Mẫu số 01' — bộ hồ sơ tạm đính vào dòng '{don[1]}'; "
            "cán bộ kiểm tra lại."
        )

    attachments: list[dict] = []
    classified: list[dict] = []
    bundled: list[str] = []
    unknown: list[str] = []
    missing: list[str] = []
    bytes_per_row: dict[int, int] = {}
    for index, file in enumerate(files):
        file_name = str(file.get("name") or f"file-{index + 1}")
        llm_type = llm_types.get(index, "")
        doc_type = llm_type if llm_type in _goc._ALLOWED else "other"
        if doc_type == "other":
            row, document_name = don, _goc._other_display(file_name)
            unknown.append(file_name)
        else:
            document_name = _goc._ROUTES[doc_type]["display"]
            row = _find(_ROW_KEYS[doc_type], rows) if doc_type in _ROW_KEYS else don
            if row is None:
                row = don
                missing.append(f"{file_name} ({document_name})")
            elif doc_type in _goc._BUNDLE_TYPES:
                bundled.append(f"{file_name} ({document_name})")
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + _goc._data_url_size(file.get("dataUrl"))
        attachments.append(_item(index, file_name, document_name, row, doc_type))
        classified.append({"fileName": file_name, "docType": doc_type, "source": "llm" if llm_type else "default",
                           "componentIndex": row[0]})

    if bundled:
        warnings.append(
            "Danh mục thành phần hồ sơ KHÔNG có dòng riêng cho giấy tờ trúng đấu giá, nộp tiền, thông báo thuế, ủy "
            f"quyền, CCCD — đã gộp chung vào dòng \"Đơn theo Mẫu số 01\": {', '.join(bundled)}."
        )
    if unknown:
        warnings.append(
            "Chưa nhận ra loại giấy tờ, cổng mới không có dòng \"giấy tờ khác\" nên đã tạm đính vào dòng \"Đơn theo "
            f"Mẫu số 01\" để không bỏ sót — cán bộ kiểm tra lại: {', '.join(unknown)}."
        )
    if missing:
        warnings.append(
            "Bảng thành phần hồ sơ trên trang không có dòng cho các giấy tờ sau, đã đính vào dòng Đơn — cán bộ kiểm "
            f"tra lại: {', '.join(missing)}."
        )
    # Trần 6 MB tính cho TỪNG DÒNG: cả bộ trúng đấu giá dồn vào dòng Đơn nên dòng đó vượt trần trước tiên.
    for row_index, total in sorted(bytes_per_row.items()):
        if total > _goc._MAX_SLOT_BYTES:
            ten = don[1] if row_index == don[0] else f"thứ {row_index}"
            warnings.append(
                f"Tổng dung lượng các tệp đính vào dòng \"{ten}\" là {_goc._mb(total)}, vượt giới hạn 6 MB của "
                "cổng — cần nén PDF hoặc tách thành nhiều tệp trước khi nộp."
            )
    _dedupe_document_names(attachments)
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
            "portalRows": len(_portal_rows(components)),
            "classified": classified,
            "sessionId": (session or {}).get("request_id"),
        },
        "stats": {"ocr_latency_ms": ocr_ms, "llm_latency_ms": llm_ms, "total_latency_ms": ocr_ms + llm_ms},
        "errors": errors,
    }
