"""Test [Tỉnh Lâm Đồng] "Đăng ký, cấp Giấy chứng nhận đối với thửa đất có DIỆN TÍCH TĂNG THÊM do thay
đổi ranh giới...; đăng ký, cấp Giấy chứng nhận đối với toàn bộ diện tích đất đang sử dụng" (1.116356).

Khoá các điểm RIÊNG của thủ tục:
1. ĐÍNH KÈM (attp-row, bảng 6 dòng) — quy tắc MỘT TỆP = MỘT LOẠI = MỘT DÒNG (số plan item LUÔN bằng
   số tệp), CCCD đi chung dòng Đơn, và cảnh báo khi tệp quét gộp làm dòng đôi bị trống. Kèm test
   chống-va-chạm componentName chạy ĐÚNG thuật toán khớp dòng của extension trên 6 dòng DOM verbatim.
2. CAM KẾT không bỏ sót file ở mọi kịch bản hỏng.
3. PROCESS: form GIỐNG HỆT 1.116365 → có test khoá việc hai UI_COMP_BY_NAME trùng khít, để sau này
   một trong hai cổng đổi form thì phát hiện ngay.

KHÔNG chạy LLM live (môi trường test không có key): mọi test đính kèm inject sẵn llm_types.
"""

import re
import unicodedata

from app.pipelines.chuyen_muc_dich_su_dung_dat_lam_dong.process.schema import (
    UI_COMP_BY_NAME as UI_1_116365,
)
from app.pipelines.dang_ky_dien_tich_tang_them_lam_dong.attach import planner
from app.pipelines.dang_ky_dien_tich_tang_them_lam_dong.attach.prompt import SYSTEM_PROMPT
from app.pipelines.dang_ky_dien_tich_tang_them_lam_dong.process import mapper
from app.pipelines.dang_ky_dien_tich_tang_them_lam_dong.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_dien_tich_tang_them_lam_dong.process.schema import FIELDS, UI_COMP_BY_NAME
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEY = "dang-ky-dien-tich-tang-them-lam-dong"

# 6 dòng DOM thật, lấy VERBATIM từ cột "Tên giấy tờ" của 'đính kèm.html'.
_ROWS = [
    "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất, Mẫu số 18 Phụ lục VI ban hành kèm theo "
    "Quyết định số 40/2026/QĐ-UBND ngày 01/7/2026 của UBND tỉnh Lâm Đồng",
    "Giấy chứng nhận đã cấp, trừ trường hợp thực hiện quyết định hoặc bản án của Tòa án nhân dân, "
    "quyết định thi hành án của cơ quan thi hành án đã có hiệu lực thi hành hoặc trường hợp đấu giá, "
    "giao quyền sử dụng đất, tài sản gắn liền với đất theo yêu cầu của Tòa án, cơ quan thi hành án mà "
    "không thu hồi được Giấy chứng nhận đã cấp",
    "Giấy tờ chứng minh phần diện tích tăng thêm",
    "Mảnh trích đo bản đồ địa chính thửa đất",
    "Tờ khai thuế theo quy định của pháp luật thuế hiện hành",
    "Văn bản về việc đại diện theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ "
    "tục đăng ký đất đai, tài sản gắn liền với đất thông qua người đại diện",
]

_ROW_DON = 1
_ROW_GCN = 2
_ROW_CHUNG_MINH = 3
_ROW_DO_DAC = 4
_ROW_THUE = 5
_ROW_DAI_DIEN = 6


def _fold(value: str) -> str:
    """Bản rút gọn của foldChoiceText trong content.js: bỏ dấu, đ→d, gộp khoảng trắng, lowercase."""
    text = unicodedata.normalize("NFD", value)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    text = re.sub(r"[–—]", "-", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _row_matches(row_text: str, component_name: str) -> bool:
    """componentTextMatches() của content.js — khớp HAI CHIỀU (dòng chứa tên, hoặc tên chứa dòng)."""
    row = _fold(row_text)
    want = _fold(component_name)
    if not row or not want:
        return False
    return row == want or want in row or row in want


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _ocr(files: list[dict]) -> list[dict]:
    return [{"name": item["name"], "text": "ocr"} for item in files]


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM — bảng 6 dòng
# --------------------------------------------------------------------------------------
def test_bo_ho_so_mau_route_dung_tung_dong():
    """Bộ 3 tệp của ảnh ánh xạ: Đơn+CCCD → dòng 1; GCN → dòng 2; tệp gộp đo đạc+ranh giới → dòng 3."""
    files = _files(["don-va-cccd.pdf", "gcn.pdf", "do-dac-va-ranh-gioi.pdf"])
    llm_types = {0: "don_bien_dong", 1: "giay_chung_nhan", 2: "chung_minh_tang_them"}

    attachments, warnings, classified = planner.build_plan_items(files, _ocr(files), llm_types)

    assert [(item["fileIndex"], item["componentIndex"]) for item in attachments] == [
        (0, _ROW_DON), (1, _ROW_GCN), (2, _ROW_CHUNG_MINH),
    ]
    assert all(item["target"] == "attp-row" for item in attachments)
    # Cả 6 dòng của cổng ghi cứng "1 Bản chính" (không có radio) → không set loaiBan.
    assert all("loaiBan" not in item for item in attachments)
    # Không gộp PDF ở bất kỳ dòng nào.
    assert all("sourceFileIndexes" not in item for item in attachments)
    assert classified[2]["componentIndexes"] == [_ROW_CHUNG_MINH]
    # Dòng 4 (mảnh trích đo) không có tệp riêng → phải cảnh báo, không im lặng.
    assert any("Mảnh trích đo bản đồ địa chính thửa đất" in w for w in warnings)


def test_so_plan_item_luon_bang_so_tep():
    """Quy tắc MỘT TỆP = MỘT DÒNG: không docType nào sinh 2 item (trước đây gây 'đã đính 4/3 file')."""
    doc_types = list(planner._ROUTES)
    files = _files([f"{name}.pdf" for name in doc_types])

    attachments, _, classified = planner.build_plan_items(
        files, _ocr(files), dict(enumerate(doc_types))
    )

    assert len(attachments) == len(files)
    assert [item["fileIndex"] for item in attachments] == list(range(len(files)))
    assert all(len(item["componentIndexes"]) == 1 for item in classified)
    # Map route phải là 1-1: mỗi docType đúng một dòng.
    assert all(isinstance(route, tuple) and len(route) == 2 for route in planner._ROUTES.values())


def test_canh_bao_khi_dong_doi_bi_trong_do_tep_quet_gop():
    """Mảnh đo đạc và giấy tờ chứng minh hay nằm chung một tệp; tệp chỉ vào được một dòng nên dòng kia
    trống — phải cảnh báo cho cán bộ, cả hai chiều."""
    for doc_type, missing in (
        ("chung_minh_tang_them", "Mảnh trích đo bản đồ địa chính thửa đất"),
        ("manh_do_dac", "Giấy tờ chứng minh phần diện tích tăng thêm"),
    ):
        files = _files(["scan-gop.pdf"])
        _, warnings, _ = planner.build_plan_items(files, _ocr(files), {0: doc_type})
        assert any(missing in w for w in warnings), doc_type

    # Có đủ tệp riêng cho cả hai dòng → KHÔNG cảnh báo thừa.
    files = _files(["do-dac.pdf", "ranh-gioi.pdf"])
    _, warnings, _ = planner.build_plan_items(
        files, _ocr(files), {0: "manh_do_dac", 1: "chung_minh_tang_them"}
    )
    assert warnings == []


def test_do_dac_va_chung_minh_rieng_le_chi_di_dong_cua_no():
    """Tệp CHỈ có mảnh đo đạc (hoặc CHỈ có giấy chứng minh) thì KHÔNG được nhân bản sang dòng kia."""
    files = _files(["do-dac.pdf", "ranh-gioi.pdf"])
    llm_types = {0: "manh_do_dac", 1: "chung_minh_tang_them"}

    attachments, warnings, _ = planner.build_plan_items(files, _ocr(files), llm_types)

    assert warnings == []
    assert [(item["fileIndex"], item["componentIndex"]) for item in attachments] == [
        (0, _ROW_DO_DAC), (1, _ROW_CHUNG_MINH),
    ]


def test_cccd_di_chung_dong_don_vi_khong_bam_duoc_nut_them_giay_to():
    """Nút '+ Thêm giấy tờ' nằm NGOÀI <table> nên engine attp-row không bấm được → CCCD vào dòng Đơn."""
    files = _files(["cccd.pdf"])

    attachments, warnings, _ = planner.build_plan_items(files, _ocr(files), {0: "cccd"})

    assert warnings == []
    assert attachments[0]["componentIndex"] == _ROW_DON
    assert attachments[0]["documentName"] == "Căn cước công dân của người sử dụng đất"


def test_moi_docType_tro_dung_dong_cua_no():
    expected = {
        "don_bien_dong": [_ROW_DON],
        "giay_chung_nhan": [_ROW_GCN],
        "chung_minh_tang_them": [_ROW_CHUNG_MINH],
        "manh_do_dac": [_ROW_DO_DAC],
        "to_khai_thue": [_ROW_THUE],
        "van_ban_dai_dien": [_ROW_DAI_DIEN],
        "cccd": [_ROW_DON],
    }
    files = _files([f"{name}.pdf" for name in expected])
    llm_types = dict(enumerate(expected))

    attachments, warnings, classified = planner.build_plan_items(files, _ocr(files), llm_types)

    assert {item["docType"]: item["componentIndexes"] for item in classified} == expected
    assert len(attachments) == len(files), "mỗi tệp đúng một item"


def test_moi_componentName_chi_khop_dung_mot_dong():
    """CHỐNG VA CHẠM: chạy đúng thuật toán khớp dòng của extension trên cả 6 dòng DOM thật.

    Bẫy trên bảng này: dòng 1 và dòng 6 cùng chứa cụm "đất đai, tài sản gắn liền với đất".
    """
    seen: dict[int, str] = {route["index"]: route["name"] for route, _label in planner._ROUTES.values()}
    for route, _label in planner._SCAN_GOP_PAIR.values():
        seen[route["index"]] = route["name"]

    assert sorted(seen) == [1, 2, 3, 4, 5, 6], "phải phủ đủ 6 dòng của bảng"
    for row_index, component_name in sorted(seen.items()):
        hits = [i + 1 for i, row in enumerate(_ROWS) if _row_matches(row, component_name)]
        assert hits == [row_index], f"componentName của dòng {row_index} khớp {hits}"


def test_tuyet_doi_khong_miss_file_o_moi_kich_ban_hong():
    """CAM KẾT: mọi file tải lên LUÔN có ít nhất một plan item, kể cả khi LLM im lặng/trả loại lạ."""
    files = _files(["don.pdf", "gcn.pdf", "khong-ocr.docx", "anh-mo.png", "la.pdf"])
    scenarios = {
        "LLM im lặng hoàn toàn": {},
        "LLM chỉ trả một phần": {0: "don_bien_dong", 1: "giay_chung_nhan"},
        "LLM trả loại ngoài allowed_types": {0: "don_bien_dong", 2: "so_ho_khau", 3: "", 4: "khong_biet"},
        "LLM lệch index": {0: "don_bien_dong", 99: "giay_chung_nhan"},
    }

    for label, llm_types in scenarios.items():
        attachments, warnings, _ = planner.build_plan_items(files, _ocr(files), llm_types)
        planned = {item["fileIndex"] for item in attachments}
        assert planned == set(range(len(files))), f"{label}: rơi file {set(range(len(files))) - planned}"
        for item in attachments:
            if item["detectedType"] == "other":
                assert item["componentIndex"] == _ROW_DON, label
                assert item["documentName"].startswith("Tài liệu khác - "), label
                assert any(item["fileName"] in w for w in warnings), label


def test_plan_end_to_end_khong_bo_sot_file_kieu_la_va_khi_llm_loi():
    """Chạy cả hàm plan(): file không OCR được (.docx/.zip) không bao giờ tới LLM, và LLM thì ném lỗi
    — vẫn phải ra kế hoạch đủ 3/3 file."""
    import asyncio

    from app.process.schemas import FileItem
    from app.services import ocr as ocr_service

    files = [
        FileItem(name="don.pdf", role="other", type="application/pdf",
                 dataUrl="data:application/pdf;base64,AA=="),
        FileItem(name="phu-luc.docx", role="other",
                 type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                 dataUrl="data:application/octet-stream;base64,AA=="),
        FileItem(name="ho-so.zip", role="other", type="application/zip",
                 dataUrl="data:application/zip;base64,AA=="),
    ]

    async def fake_ocr(items):
        return [{"name": item["name"], "text": "ocr"} for item in items]

    async def fake_chat(*args, **kwargs):
        raise RuntimeError("LLM down")

    original_ocr, original_chat = ocr_service.ocr_per_file, planner.client.chat
    ocr_service.ocr_per_file, planner.client.chat = fake_ocr, fake_chat
    try:
        result = asyncio.run(planner.plan(files))
    finally:
        ocr_service.ocr_per_file, planner.client.chat = original_ocr, original_chat

    assert {item["fileIndex"] for item in result["attachments"]} == {0, 1, 2}
    assert all(item["componentIndex"] == _ROW_DON for item in result["attachments"])
    assert any("LLM down" in err for err in result["errors"])


# --------------------------------------------------------------------------------------
# PROCESS
# --------------------------------------------------------------------------------------
def _owner_facts() -> list[dict]:
    return [
        {"name": "Nguoi_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "Nguoi_NgaySinh", "value": "04/11/1956"},
        {"name": "Nguoi_GioiTinh", "value": "Nam"},
        {"name": "Nguoi_SoDinhDanh", "value": "000000000001"},
        {"name": "Nguoi_NgayCapCccd", "value": "12/08/2021"},
        {"name": "Nguoi_NoiCapCccd", "value": "Bộ Công an"},
        {"name": "Nguoi_DienThoai", "value": "0900000001"},
        {"name": "Nguoi_ThuongTru", "value": {"tinh": "Lâm Đồng", "xa": "Phường Xuân Trường - Đà Lạt",
                                              "diaChi": "Số nhà mẫu"}},
    ]


def test_tu_nop_bam_nut_nguoi_nop_la_chu_ho_so():
    values = _values(mapper.enrich(_owner_facts())[0])

    assert values["data[BUTTON3]"] is True
    owner_fields = [n for n in values if n.startswith("data[owner")] + [
        n for n in values if n in {"data[gender1]", "data[nation1]", "data[province1]", "data[district1]"}
    ]
    assert owner_fields == []


def test_nop_thay_dien_ca_hai_khoi_va_khong_bam_nut():
    fields = _owner_facts() + [
        {"name": "NguoiDuocUyQuyen", "value": {
            "hoTen": "TRẦN VĂN B", "soDinhDanh": "000000000002", "ngaySinh": "13/09/1995",
            "gioiTinh": "Nam", "ngayCapCccd": "05/06/2022", "noiCapCccd": "Bộ Công an",
            "thuongTru": {"tinh": "Lâm Đồng", "xa": "Xã D'Ran", "diaChi": "Tổ dân phố X"},
        }},
    ]

    values = _values(mapper.enrich(fields)[0])

    assert "data[BUTTON3]" not in values
    assert values["data[fullname]"] == "TRẦN VĂN B"
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    # SĐT ở mục 1d Đơn Mẫu 18 là của chủ hồ sơ — không mượn sang ô người nộp.
    assert values["data[ownerPhoneNumber]"] == "0900000001"
    assert values["data[phoneNumber]"] == ""


def test_ghi_chu_mang_noi_dung_bien_dong_va_dien_tich_tang_them():
    """Form KHÔNG có ô riêng cho 'Nội dung biến động' của Đơn 18 → phải nằm ở ô Ghi chú."""
    fields = _owner_facts() + [
        {"name": "Don_NoiDungDeNghi", "value": "Đăng ký biến động do thay đổi diện tích theo kết quả đo đạc"},
        {"name": "DienTich_TangThem", "value": "163,8 m2"},
        {"name": "ThuaDat_So", "value": "64"},
        {"name": "ThuaDat_ToBanDo", "value": "32"},
    ]

    ghi_chu = _values(mapper.enrich(fields)[0])["data[ghiChu]"]

    assert "thay đổi diện tích theo kết quả đo đạc" in ghi_chu
    assert "Diện tích tăng thêm: 163,8 m2." in ghi_chu
    assert "Thửa đất số 64, tờ bản đồ số 32." in ghi_chu


def test_dien_tich_tang_them_chi_lay_so_ghi_san_khong_tu_tru():
    """Không có con số tăng thêm ghi sẵn → ô Ghi chú KHÔNG được bịa ra phép trừ."""
    fields = _owner_facts() + [{"name": "Don_NoiDungDeNghi", "value": "Đăng ký biến động diện tích"}]

    ghi_chu = _values(mapper.enrich(fields)[0])["data[ghiChu]"]

    assert "Diện tích tăng thêm" not in ghi_chu
    to_chuc = next(f for f in FIELDS if f["name"] == "DienTich_TangThem")
    assert "không tự trừ hai số" in to_chuc["desc"].lower() or "không tự trừ" in to_chuc["desc"].lower()


def test_phan_iv_gcn_dung_flatpickr_va_lau_dai_de_trong():
    fields = _owner_facts() + [
        {"name": "Gcn_SoPhatHanh", "value": "G 875845"},
        {"name": "Gcn_NgayCap", "value": "25/08/1997"},
        {"name": "Gcn_DonViCap", "value": "ỦY BAN NHÂN DÂN THÀNH PHỐ MẪU"},
        {"name": "Gcn_NoiCap", "value": "Thành phố Mẫu, tỉnh Lâm Đồng"},
        {"name": "Gcn_ThoiHan", "value": "Lâu dài"},
    ]

    values = _values(mapper.enrich(fields)[0])

    assert values["data[licenseCode]"] == "G 875845"
    assert values["data[licenseDate]"] == "1997/08/25"
    assert values["data[effectiveDate]"] == "1997/08/25"
    assert "data[expirationDate]" not in values
    assert values["data[licensingPlace]"] == "UBND THÀNH PHỐ MẪU"


def test_thoi_han_chi_co_thang_nam_thi_de_trong_khong_bia_ngay():
    """GCN gia hạn thường chỉ ghi 'tháng 10/2063' — form cần ngày cụ thể, KHÔNG được bịa."""
    fields = _owner_facts() + [{"name": "Gcn_ThoiHan", "value": "Gia hạn sử dụng đất đến tháng 10/2063"}]

    values = _values(mapper.enrich(fields)[0])

    assert "data[expirationDate]" not in values


def test_ca_nhan_khong_dien_o_co_quan_to_chuc():
    assert "data[organization]" not in _values(mapper.enrich(_owner_facts())[0])


def test_mapper_khong_phat_o_ngoai_form():
    for item in mapper.enrich(_owner_facts())[0]:
        assert item["name"] in UI_COMP_BY_NAME


# --------------------------------------------------------------------------------------
# HỢP ĐỒNG SCHEMA / REGISTRY
# --------------------------------------------------------------------------------------
def test_form_trung_khit_voi_thu_tuc_1_116365():
    """Hai cổng dùng CHUNG một form 35 ô. Nếu một trong hai đổi, test này vỡ để ta biết mà tách."""
    assert UI_COMP_BY_NAME == UI_1_116365
    assert len(UI_COMP_BY_NAME) == 35
    assert UI_COMP_BY_NAME["data[BUTTON3]"] == "dom-owner-copy"


def test_prompt_nhac_doc_het_trang_va_chu_moi_tren_gcn():
    assert "MỘT FILE PDF THƯỜNG GỘP NHIỀU GIẤY TỜ" in EXTRA_RULES
    assert "Những thay đổi sau khi cấp Giấy chứng nhận" in EXTRA_RULES
    assert "Không bịa thông tin còn thiếu" in EXTRA_RULES


def test_prompt_dinh_kem_ep_mot_tep_mot_loai():
    assert "một tệp KHÔNG BAO GIỜ được gán hai loại" in SYSTEM_PROMPT
    assert "TUYỆT ĐỐI KHÔNG trả hai docType cho một tệp" in SYSTEM_PROMPT
    assert "do_dac_kem_chung_minh" not in SYSTEM_PROMPT
    assert "không bỏ sót index nào" in SYSTEM_PROMPT


def test_registry_wiring():
    procedure = get_procedure(_KEY)
    assert procedure is not None
    assert procedure["hasAttachmentStep"] is True
    assert procedure["mode"] == "agent"
    assert procedure["detect"]["urlScope"] == ["lamdong.gov.vn"]
    assert "1.116356" in procedure["detect"]["textIncludes"]
    assert get_pipeline(_KEY) is not None
    assert get_attach_pipeline(_KEY) is not None
