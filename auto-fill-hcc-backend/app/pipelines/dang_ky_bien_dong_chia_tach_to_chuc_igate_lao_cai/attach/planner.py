"""Đính kèm cho [Lào Cai - cổng iGate mới] đăng ký biến động do chia, tách, hợp nhất, sáp nhập tổ chức (1.115670).

Phân loại giữ NGUYÊN của pipeline cổng cũ (dang_ky_bien_dong_chia_tach_to_chuc_lao_cai/attach: OCR → LLM từng tệp →
docType + alsoTypes cho bản scan gộp) và quy tắc MỖI TỆP MỘT DÒNG theo thứ tự ưu tiên phủ dòng của cổng cũ.

Bước 2 "Thành phần hồ sơ hệ thống" (crawl 29/10/2026, Sở NN&MT Lào Cai): MỘT bảng 15 dòng, cổng TÍCH SẴN cả 15, KHÔNG
có dòng tiêu đề trường hợp, KHÔNG có dòng "giấy tờ khác". Cổng cũ chỉ có một nhánh 8 dòng; cổng mới tách theo ba
trường hợp trong tên thủ tục, mỗi nhóm mở đầu bằng dòng Đơn Mẫu số 24:
   1–7   chia, tách, hợp nhất, sáp nhập tổ chức : Đơn · GCN đã cấp · ĐKDN/thành lập tổ chức sau thay đổi
                                                 · QĐ chia tách sáp nhập · Bản vẽ Mẫu 28 · Mảnh trích đo · Đại diện
   8–11  điều chỉnh quy hoạch XD chi tiết       : Đơn · GCN đã cấp · QĐ phê duyệt ĐIỀU CHỈNH quy hoạch · Đại diện
   12–15 cấp GCN từng thửa theo quy hoạch       : Đơn · GCN đã cấp · QĐ phê duyệt quy hoạch XD chi tiết · Đại diện
Chọn nhóm: có giấy tờ riêng của nhóm 1 (QĐ chia tách, ĐKDN sau thay đổi, bản vẽ tách/hợp thửa, mảnh trích đo) → nhóm 1;
không có mà có quyết định quy hoạch → nhóm 2 nếu OCR là quyết định ĐIỀU CHỈNH quy hoạch, ngược lại nhóm 3; còn lại →
nhóm 1 (trường hợp chính của thủ tục). Đơn/GCN/Đại diện trùng tên giữa các nhóm → gửi componentIndex để FE chọn đúng.
Giấy tờ ngoài danh mục hoặc không có dòng trong nhóm → dòng Đơn của nhóm + cảnh báo. Không bỏ tệp nào.

Engine FE "attp-row" + untickUnplannedRows dùng chung với cho_thue_dat_thue_rung_igate_lao_cai: FE bỏ chọn tất cả rồi
chỉ tích dòng có tệp, nên dòng của hai nhóm còn lại tự được bỏ tick.
"""

import time

from app.pipelines._shared import fold
from app.pipelines.cho_thue_dat_thue_rung.attach import planner as _size
from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach import planner as _igate
from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_lao_cai.attach import planner as _goc
from app.process.schemas import FileItem
from app.services import ocr

_OCR_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}

_DON = "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND"
_GCN = "Giấy chứng nhận đã cấp"
_DAI_DIEN = (
    "Văn bản về việc đại diện theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ tục đăng ký đất "
    "đai, tài sản gắn liền với đất thông qua người đại diện"
)
# Bảng 15 dòng NGUYÊN VĂN (crawl 29/10/2026; dòng 4 bị cắt ở 400 ký tự trong ô — dùng bản đầy đủ của attachmentContext).
_DEFAULT_ROWS = [
    _DON,
    _GCN,
    "Cơ quan giải quyết thủ tục có trách nhiệm khai thác, sử dụng thông tin về đăng ký doanh nghiệp hoặc thành lập tổ "
    "chức sau khi thay đổi trên Cơ sở dữ liệu quốc gia về đăng ký doanh nghiệp, nếu không thể khai thác được thông tin "
    "này thì người yêu cầu đăng ký nộp giấy chứng nhận đăng ký doanh nghiệp hoặc văn bản về việc thành lập tổ chức sau "
    "khi thay đổi",
    "Quyết định của cơ quan, tổ chức có thẩm quyền hoặc văn bản về việc chia, tách, hợp nhất, sáp nhập, chuyển đổi mô "
    "hình tổ chức, chuyển đổi loại hình doanh nghiệp theo quy định của pháp luật về doanh nghiệp phù hợp với quy định "
    "của pháp luật, trong đó phải xác định rõ tổ chức được sử dụng đất, sở hữu tài sản gắn liền với đất sau khi chia, "
    "tách, hợp nhất, sáp nhập, chuyển đổi mô hình tổ chức, chuyển đổi loại hình doanh nghiệp",
    "Bản vẽ tách thửa đất, hợp thửa đất theo Mẫu số 28 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND đối với trường "
    "hợp phải tách thửa đất, hợp thửa đất",
    "Mảnh trích đo bản đồ địa chính thửa đất đối với trường hợp người sử dụng đất có nhu cầu đo đạc để xác định lại kích "
    "thước các cạnh, diện tích của thửa đất",
    _DAI_DIEN,
    _DON,
    _GCN,
    "Quyết định phê duyệt điều chỉnh quy hoạch xây dựng chi tiết của cơ quan có thẩm quyền kèm theo bản đồ điều chỉnh "
    "quy hoạch xây dựng chi tiết và bản đồ địa chính hoặc mảnh trích đo bản đồ địa chính; trường hợp phải xác định lại "
    "giá đất thì nộp thêm giấy tờ chứng minh đã hoàn thành nghĩa vụ tài chính về đất đai",
    _DAI_DIEN,
    _DON,
    _GCN,
    "Quyết định phê duyệt quy hoạch xây dựng chi tiết của cơ quan có thẩm quyền kèm theo bản đồ quy hoạch xây dựng chi "
    "tiết và bản đồ địa chính hoặc mảnh trích đo bản đồ địa chính",
    _DAI_DIEN,
]

_DON_KEYS = ["mau so 24"]
# docType (catalog cổng cũ) → từ khoá dòng; dò TRONG nhóm nên mỗi từ khoá chỉ khớp một dòng.
_ROW_KEYS: dict[str, list[str]] = {
    "don_mau_24": _DON_KEYS,
    "gcn_da_cap": ["giay chung nhan da cap"],
    "van_ban_thanh_lap_to_chuc": ["thanh lap to chuc sau khi thay doi"],
    "qd_chia_tach_sap_nhap": ["hop nhat, sap nhap, chuyen doi mo hinh to chuc"],
    "ban_ve_tach_hop_thua": ["mau so 28"],
    "manh_trich_do": ["xac dinh lai kich thuoc"],
    "van_ban_dai_dien": ["van ban ve viec dai dien"],
    "qd_dieu_chinh_quy_hoach": ["quy hoach xay dung chi tiet"],
}
# Giấy tờ CHỈ có ở nhóm chia, tách, hợp nhất, sáp nhập tổ chức.
_RIENG_NHOM_TO_CHUC = {"qd_chia_tach_sap_nhap", "van_ban_thanh_lap_to_chuc", "ban_ve_tach_hop_thua", "manh_trich_do"}
_DIEU_CHINH_MARKERS = (
    "phe duyet dieu chinh quy hoach", "dieu chinh quy hoach xay dung chi tiet", "dieu chinh quy hoach chi tiet",
)

_TO_CHUC, _DIEU_CHINH_QH, _THEO_QH = 0, 1, 2
_TEN_NHOM = {
    _TO_CHUC: "chia, tách, hợp nhất, sáp nhập tổ chức / chuyển đổi mô hình, loại hình doanh nghiệp (dòng 1–7)",
    _DIEU_CHINH_QH: "điều chỉnh quy hoạch xây dựng chi tiết (dòng 8–11)",
    _THEO_QH: "cấp Giấy chứng nhận cho từng thửa theo quy hoạch xây dựng chi tiết (dòng 12–15)",
}

Row = _igate.Row


def _default_rows() -> list[Row]:
    return [(i + 1, name, fold(name)) for i, name in enumerate(_DEFAULT_ROWS)]


def _groups(rows: list[Row]) -> list[list[Row]]:
    groups: list[list[Row]] = []
    for row in rows:
        if any(key in row[2] for key in _DON_KEYS) or not groups:
            groups.append([])
        groups[-1].append(row)
    return groups


def _chon_nhom(resolved: list[tuple[int, str, str, list[str]]], ocr_by_name: dict) -> int:
    types = {t for _, _, chinh, also in resolved for t in (chinh, *also)}
    if types & _RIENG_NHOM_TO_CHUC:
        return _TO_CHUC
    quy_hoach = [name for _, name, chinh, also in resolved if "qd_dieu_chinh_quy_hoach" in (chinh, *also)]
    if not quy_hoach:
        return _TO_CHUC
    texts = [fold(str(ocr_by_name.get(name, {}).get("text") or "")) for name in quy_hoach]
    return _DIEU_CHINH_QH if any(m in text for text in texts for m in _DIEU_CHINH_MARKERS) else _THEO_QH


def build_plan_items(
    files: list[dict],
    ocr_results: list[dict],
    llm_types: dict[int, tuple[str, list[str]] | str] | None = None,
    components: list[dict] | None = None,
) -> tuple[list[dict], list[str], list[dict]]:
    llm_types = llm_types or {}
    ocr_by_name = {item.get("name"): item for item in ocr_results}

    resolved: list[tuple[int, str, str, list[str]]] = []
    for index, file in enumerate(files):
        raw = llm_types.get(index)
        doc_type, also = raw if isinstance(raw, tuple) else (raw, [])
        if doc_type not in _goc._ALLOWED:
            doc_type = "other"
        also = _goc._normalize_also(also, doc_type) if doc_type != "other" else []
        resolved.append((index, str(file.get("name") or f"file-{index + 1}"), doc_type, also))

    groups = _groups(_igate._portal_rows(components) or _default_rows())
    nhom = _chon_nhom(resolved, ocr_by_name)
    rows = groups[nhom] if nhom < len(groups) else groups[0]
    row_of = {doc_type: _igate._find(keys, rows) for doc_type, keys in _ROW_KEYS.items()}

    warnings: list[str] = []
    don = row_of["don_mau_24"]
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
    da_dung: set[str] = set()
    for index, file_name, doc_type, also in resolved:
        if doc_type == "other":
            chon, row, document_name = "other", don, _goc._other_component_name(file_name)
            unknown.append(file_name)
        else:
            # MỖI TỆP MỘT DÒNG như cổng cũ: bản scan gộp dùng để PHỦ dòng còn trống của nhóm theo thứ tự ưu tiên.
            chua_co = [t for t in _goc._ROW_PRIORITY if t in (doc_type, *also) and t not in da_dung and row_of[t]]
            chon = chua_co[0] if chua_co else doc_type
            document_name = _goc._DISPLAY[chon]
            row = row_of[chon]
            if row is None:
                row = don
                missing.append(f"{file_name} ({document_name})")
            else:
                da_dung.add(chon)
        bytes_per_row[row[0]] = bytes_per_row.get(row[0], 0) + _size._data_url_size(files[index].get("dataUrl"))
        attachments.append(_igate._item(index, file_name, document_name, row, chon))
        classified.append({"fileName": file_name, "docType": doc_type, "alsoTypes": also, "assignedType": chon,
                           "source": "llm" if index in llm_types else "default", "componentIndex": row[0]})

    con_thieu = []
    for doc_type in _goc._ROW_PRIORITY:
        if doc_type in da_dung or not row_of[doc_type]:
            continue
        nguon = [name for _, name, chinh, also in resolved if doc_type in (chinh, *also)]
        if nguon:
            con_thieu.append(f'"{_goc._DISPLAY[doc_type]}" (có trong {", ".join(nguon)})')

    if attachments:
        warnings.append(
            f"Hồ sơ được xếp theo trường hợp {_TEN_NHOM[nhom]}. Trợ lý chỉ tích các dòng có tệp — cán bộ kiểm tra lại "
            "trường hợp trước khi nộp."
        )
    if con_thieu:
        warnings.append(
            "Mỗi tệp chỉ được đính vào MỘT dòng. Các dòng sau chưa có tệp nhưng nội dung nằm trong bản scan gộp — cán "
            "bộ cân nhắc nộp lại cùng tệp vào đó: " + "; ".join(con_thieu) + "."
        )
    if unknown:
        warnings.append(
            "Giấy tờ ngoài danh mục đã tạm đính vào dòng \"Đơn Mẫu số 24\" vì cổng mới không có dòng \"giấy tờ khác\" — "
            f"nếu cần tách riêng, cán bộ dùng nút \"Thêm giấy tờ\" của cổng: {', '.join(unknown)}."
        )
    if missing:
        warnings.append(
            "Nhóm thành phần hồ sơ của trường hợp này không có dòng cho các giấy tờ sau, đã đính vào dòng Đơn — cán bộ "
            f"kiểm tra lại: {', '.join(missing)}."
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
    llm_types: dict[int, tuple[str, list[str]]] = {}
    if llm_documents:
        try:
            llm_types = await _goc._classify_with_llm(llm_documents, errors)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"attachment_agent: {exc}")
    llm_ms = int((time.monotonic() - started) * 1000)

    attachments, warnings, classified = build_plan_items(raw_files, ocr_results, llm_types, components)
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
