"""Unit tests cho mapper thủ tục hỗ trợ mai táng: người chết là chủ hồ sơ trên cổng (mọi tài khoản)."""

from app.pipelines.ho_tro_mai_tang.process import mapper
from app.pipelines.ho_tro_mai_tang.process.runner import _keep_proposer_area, _owner_section, _requester_context


def _run(values: dict, form_context: dict | None = None):
    compact = [{"name": name, "value": value} for name, value in values.items()]
    fields, warnings = mapper.enrich(
        compact,
        {"formContext": form_context or {}},
    )
    return {field["name"]: field["value"] for field in fields}, warnings


def _run_mode(values: dict, mode: str = "owner_as_submitter", form_context: dict | None = None):
    compact = [{"name": name, "value": value} for name, value in values.items()]
    fields, warnings = mapper.enrich(compact, {"submitterMode": mode, "formContext": form_context or {}})
    return {field["name"]: field["value"] for field in fields}, warnings


# Người đứng ra mai táng (ChuHoSo_*) và người chết (NguoiMat_*) — dữ liệu bịa.
_NGUOI_MAI_TANG = {
    "ChuHoSo_HoTen": "KA TUI",
    "ChuHoSo_NgaySinh": "01/01/1975",
    "ChuHoSo_SoDinhDanh": "068175007976",
    "ChuHoSo_NgayCap": "27/12/2002",
    "ChuHoSo_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "ChuHoSo_NoiCuTru": {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Đơn Dương",
        "diaChi": "Kambutte",
    },
    "ChuHoSo_DienThoai": "0378877127",
}
_NGUOI_MAT = {
    "NguoiMat_HoTen": "KA NANG",
    "NguoiMat_NgaySinh": "02/02/1945",
    "NguoiMat_GioiTinh": "Nam",
    "NguoiMat_SoDinhDanh": "068145000123",
    "NguoiMat_NgayCap": "01/09/2021",
    "NguoiMat_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "NguoiMat_NoiCuTru": {"tinh": "Lâm Đồng", "xa": "Đơn Dương", "diaChi": "Kambutte"},
}
_KA_TUI_UI = {"applicantFullname": "KA TUI", "applicantIdentityNumber": "068175007976"}


def test_nguoi_chet_la_chu_ho_so_nguoi_mai_tang_khop_ui_la_nguoi_nop():
    got, warnings = _run({**_NGUOI_MAI_TANG, **_NGUOI_MAT}, _KA_TUI_UI)

    assert got["data[isOwnerDossierCheck]"] is False          # không bao giờ tick tự nộp
    assert got["data[fullname]"] == "KA TUI"
    assert got["data[birthday]"] == "01/01/1975"
    assert got["data[identityNumber]"] == "068175007976"
    assert got["data[identityDate]"] == "27/12/2002"
    assert got["data[province]"] == "Lâm Đồng"
    assert got["data[district]"] == "Đơn Dương"
    assert got["data[address]"] == "Kambutte"
    assert got["data[phoneNumber]"] == "0378877127"

    assert got["data[ownerFullname]"] == "KA NANG"
    assert got["data[ownerBirthday]"] == "02/02/1945"
    assert got["data[ownerGender]"] == "Nam"
    assert got["data[ownerIdentityNumber]"] == "068145000123"
    assert got["data[ownerIdentityDate]"] == "01/09/2021"
    assert got["data[ownerProvince]"] == "Lâm Đồng"
    assert got["data[ownerDistrict]"] == "Đơn Dương"
    assert got["data[ownerAddress]"] == "Kambutte"
    assert got["data[ownerNation]"] == "Việt Nam"
    assert not warnings


def test_owner_mode_nguoi_nop_la_nguoi_mai_tang_bo_moc_ui():
    """Toggle owner_as_submitter (Nghĩa Hưng): người nộp = người đứng ra mai táng theo Tờ khai, không so UI."""
    got, warnings = _run_mode(
        {**_NGUOI_MAI_TANG, **_NGUOI_MAT},
        form_context={"applicantFullname": "Người Khác", "applicantIdentityNumber": "999999999999"},
    )
    assert got["data[isOwnerDossierCheck]"] is False
    assert got["data[fullname]"] == "KA TUI"
    assert got["data[ownerFullname]"] == "KA NANG"
    assert not warnings


def test_owner_mode_khong_lay_nguoi_nop_ocr_khi_co_nguoi_mai_tang():
    values = {**_NGUOI_MAI_TANG, **_NGUOI_MAT, "NguoiNop_HoTen": "Phan Mỹ Dung", "NguoiNop_SoDinhDanh": "024193003267"}
    got, _ = _run_mode(values)
    assert got["data[fullname]"] == "KA TUI"
    assert "Phan Mỹ Dung" not in str(list(got.values()))


def test_khong_khop_ui_van_dien_nguoi_chet_va_canh_bao():
    got, warnings = _run({**_NGUOI_MAI_TANG, **_NGUOI_MAT}, {"applicantFullname": "HA YONG", "applicantIdentityNumber": "012345678901"})

    assert got["data[isOwnerDossierCheck]"] is False
    assert "data[fullname]" not in got
    assert got["data[ownerFullname]"] == "KA NANG"
    assert "không điền phần người nộp" in warnings[0]


def test_ui_phai_khop_ca_ten_va_so_dinh_danh():
    got, warnings = _run({**_NGUOI_MAI_TANG, **_NGUOI_MAT}, {"applicantFullname": "KA TUI", "applicantIdentityNumber": "999999999999"})

    assert "data[fullname]" not in got
    assert got["data[ownerFullname]"] == "KA NANG"
    assert warnings


def test_khong_co_moc_ui_chi_dien_nguoi_chet():
    got, warnings = _run({**_NGUOI_MAI_TANG, **_NGUOI_MAT})

    assert got["data[isOwnerDossierCheck]"] is False
    assert "data[fullname]" not in got
    assert got["data[ownerFullname]"] == "KA NANG"
    assert not warnings


def test_nguoi_nop_khac_khop_ui_vao_khoi_nguoi_nop():
    values = {
        **_NGUOI_MAI_TANG,
        **_NGUOI_MAT,
        "NguoiNop_HoTen": "TRẦN THỊ THANH THẢO",
        "NguoiNop_SoDinhDanh": "036192014693",
        "NguoiNop_NoiCuTru": {"tinh": "Ninh Bình", "xa": "Gia Thắng", "diaChi": "Xóm 2"},
    }
    got, warnings = _run(values, {"applicantFullname": "TRẦN THỊ THANH THẢO", "applicantIdentityNumber": "036192014693"})

    assert got["data[fullname]"] == "TRẦN THỊ THANH THẢO"
    assert got["data[province]"] == "Ninh Bình"
    assert got["data[ownerFullname]"] == "KA NANG"
    assert "KA TUI" not in str(list(got.values()))
    assert not warnings


def test_nguoi_chet_khong_bao_gio_la_nguoi_nop():
    """LLM lỡ trộn vai (ChuHoSo = người chết) thì không điền người chết vào khối người nộp."""
    values = {**_NGUOI_MAT, "ChuHoSo_HoTen": "KA NANG", "ChuHoSo_SoDinhDanh": "068145000123"}
    got, _ = _run_mode(values)

    assert "data[fullname]" not in got
    assert got["data[ownerFullname]"] == "KA NANG"


def test_thieu_nguoi_chet_canh_bao_nhung_van_dien_nguoi_nop():
    got, warnings = _run(_NGUOI_MAI_TANG, _KA_TUI_UI)

    assert got["data[fullname]"] == "KA TUI"
    assert "data[ownerFullname]" not in got
    assert "Không đọc được thông tin người chết" in warnings[0]


def test_khong_doc_duoc_ai():
    got, warnings = _run({})
    assert got == {}
    assert warnings


async def test_current_form_04_owner_block_matches_ui_requester_context():
    ocr = """I. THÔNG TIN NGƯỜI CHẾT ĐƯỢC MAI TÁNG
Họ và tên: KA NANG
II. THÔNG TIN CƠ QUAN, TỔ CHỨC, HỘ GIA ĐÌNH, CÁ NHÂN ĐỨNG RA MAI TÁNG
2. Trường hợp hộ gia đình, cá nhân đứng ra mai táng
a) Họ và tên (Chủ hộ hoặc người đại diện): KA TUI
Ngày, tháng, năm sinh: 01/01/1975
Giấy CCCD số: 068175007976 cấp ngày: 27/12/2002
b) Hộ khẩu thường trú: Kambutte, xã Đơn Dương, Lâm Đồng
Tôi xin cam đoan những lời khai trên là đúng.
"""

    assert "KA TUI" in _owner_section(ocr)
    assert "KA NANG" not in _owner_section(ocr)

    context = await _requester_context(
        [{"name": "image.jpg", "text": ocr}],
        {"formContext": _KA_TUI_UI},
    )

    assert 'result="owner_match"' in context
    assert "người đứng ra mai táng" in context


def test_owner_section_mau_03_lay_muc_3_1():
    """Mẫu số 03 (NĐ 176/2025): khối người đứng ra mai táng là mục 3.1, dừng trước mục 3.2 tổ chức."""
    ocr = """2. Thông tin người chết được tổ chức mai táng
Họ và tên: KA NANG
3. Người, tổ chức nhận hỗ trợ chi phí mai táng
3.1. Trường hợp cá nhân, thân nhân đứng ra tổ chức mai táng:
Họ và tên: KA TUI
Số căn cước hoặc số định danh cá nhân: 068175007976
3.2. Trường hợp cơ quan, tổ chức đứng ra tổ chức mai táng:
Tên tổ chức: UBND XÃ MẪU
"""
    section = _owner_section(ocr)
    assert "KA TUI" in section
    assert "KA NANG" not in section
    assert "UBND XÃ MẪU" not in section


# Cờ requesterAsOwner (phường Nha Trang): chủ hồ sơ = người đề nghị trên tờ khai — dữ liệu bịa.
def _run_nha_trang(values: dict, form_context: dict | None = None, mode: str | None = None):
    compact = [{"name": name, "value": value} for name, value in values.items()]
    options = {mapper.REQUESTER_AS_OWNER_OPTION: True, "formContext": form_context or {}}
    if mode:
        options["submitterMode"] = mode
    fields, warnings = mapper.enrich(compact, options)
    return {field["name"]: field["value"] for field in fields}, warnings


def test_with_account_process_options_chi_bat_cho_phuong_nha_trang():
    nha_trang = {"tinh": "Tỉnh Khánh Hòa", "xa": "Phường Nha Trang"}
    for procedure in ("ho-tro-mai-tang", "ho-tro-mai-tang-1116910"):
        assert mapper.with_account_process_options({}, nha_trang, procedure)[mapper.REQUESTER_AS_OWNER_OPTION] is True
    assert mapper.with_account_process_options({}, {"tinh": "Khánh Hoà", "xa": "Nha Trang"}, "ho-tro-mai-tang")[
        mapper.REQUESTER_AS_OWNER_OPTION
    ] is True
    for user in (
        {"tinh": "Tỉnh Khánh Hòa", "xa": "Phường Nam Nha Trang"},
        {"tinh": "Tỉnh Khánh Hòa", "xa": "Phường Bắc Nha Trang"},
        {"tinh": "Tỉnh Lâm Đồng", "xa": "Phường Nha Trang"},
        None,
    ):
        assert mapper.REQUESTER_AS_OWNER_OPTION not in mapper.with_account_process_options({}, user, "ho-tro-mai-tang")
    assert mapper.REQUESTER_AS_OWNER_OPTION not in mapper.with_account_process_options(
        {}, nha_trang, "ho-tro-mai-tang-huu-tri-xa-hoi"
    )
    # Client tự gửi cờ cũng bị gỡ khi tài khoản không phải phường Nha Trang.
    assert mapper.REQUESTER_AS_OWNER_OPTION not in mapper.with_account_process_options(
        {mapper.REQUESTER_AS_OWNER_OPTION: True}, {"tinh": "Đà Nẵng", "xa": "Hải Châu"}, "ho-tro-mai-tang"
    )


def test_nha_trang_nguoi_de_nghi_la_chu_ho_so_khi_khong_khop_ui():
    got, warnings = _run_nha_trang(
        {**_NGUOI_MAI_TANG, **_NGUOI_MAT},
        {"applicantFullname": "HA YONG", "applicantIdentityNumber": "012345678901"},
    )

    assert got["data[isOwnerDossierCheck]"] is False
    assert "data[fullname]" not in got
    assert got["data[ownerFullname]"] == "KA TUI"
    assert got["data[ownerIdentityNumber]"] == "068175007976"
    assert got["data[ownerIdentityDate]"] == "27/12/2002"
    assert got["data[ownerProvince]"] == "Lâm Đồng"
    assert got["data[ownerDistrict]"] == "Đơn Dương"
    assert got["data[ownerAddress]"] == "Kambutte"
    assert got["data[ownerPhoneNumber]"] == "0378877127"
    assert "KA NANG" not in str(list(got.values()))
    assert "không điền phần người nộp" in warnings[0]


def test_nha_trang_nguoi_de_nghi_khop_ui_tick_nguoi_nop_la_chu_ho_so():
    got, warnings = _run_nha_trang({**_NGUOI_MAI_TANG, **_NGUOI_MAT}, _KA_TUI_UI)

    assert got["data[isOwnerDossierCheck]"] is True
    assert got["data[fullname]"] == "KA TUI"
    assert got["data[identityNumber]"] == "068175007976"
    assert got["data[ownerBirthday]"] == "01/01/1975"
    assert "KA NANG" not in str(list(got.values()))
    assert not warnings


def test_nha_trang_owner_mode_tick_nguoi_de_nghi():
    got, warnings = _run_nha_trang(
        {**_NGUOI_MAI_TANG, **_NGUOI_MAT},
        {"applicantFullname": "Người Khác", "applicantIdentityNumber": "999999999999"},
        mode="owner_as_submitter",
    )

    assert got["data[isOwnerDossierCheck]"] is True
    assert got["data[fullname]"] == "KA TUI"
    assert not warnings


def test_nha_trang_nguoi_nop_khac_khop_ui():
    values = {
        **_NGUOI_MAI_TANG,
        **_NGUOI_MAT,
        "NguoiNop_HoTen": "TRẦN THỊ THANH THẢO",
        "NguoiNop_SoDinhDanh": "036192014693",
    }
    got, warnings = _run_nha_trang(values, {"applicantFullname": "TRẦN THỊ THANH THẢO", "applicantIdentityNumber": "036192014693"})

    assert got["data[isOwnerDossierCheck]"] is False
    assert got["data[fullname]"] == "TRẦN THỊ THANH THẢO"
    assert got["data[ownerFullname]"] == "KA TUI"
    assert not warnings


def test_nha_trang_khong_lay_nguoi_chet_lam_chu_ho_so():
    """LLM lỡ trộn vai (ChuHoSo = người chết) thì bỏ trống chủ hồ sơ và cảnh báo."""
    values = {**_NGUOI_MAT, "ChuHoSo_HoTen": "KA NANG", "ChuHoSo_SoDinhDanh": "068145000123"}
    got, warnings = _run_nha_trang(values)

    assert "data[ownerFullname]" not in got
    assert "data[fullname]" not in got
    assert "Không đọc được người đề nghị" in warnings[0]


_MAU_03_OCR = """TỜ KHAI ĐỀ NGHỊ HỖ TRỢ CHI PHÍ MAI TÁNG
1. Thông tin người người đề nghị
Họ và tên : KA TUI
Số căn cước hoặc số định danh cá nhân: 068175007976 ngày cấp 27/12/2002
Nơi cư trú: Kambutte, xã Đơn Dương
2. Thông tin người chết được tổ chức mai táng
Họ và tên: KA NANG
3. Người, tổ chức nhận hỗ trợ chi phí mai táng
3.1. Trường hợp cá nhân, thân nhân đứng ra tổ chức mai táng:
Họ và tên: KA TUI
Ngày sinh: 01/01/1975 Nam/Nữ: Nam
3.2. Trường hợp cơ quan, tổ chức đứng ra tổ chức mai táng:
Tên tổ chức: UBND XÃ MẪU
"""


async def test_nha_trang_owner_ocr_gom_muc_1_va_3_1():
    context = await _requester_context(
        [{"name": "to_khai.pdf", "text": _MAU_03_OCR}],
        {mapper.REQUESTER_AS_OWNER_OPTION: True, "formContext": _KA_TUI_UI},
    )

    assert "Nơi cư trú: Kambutte" in context        # mục 1 người đề nghị
    assert "Ngày sinh: 01/01/1975" in context       # mục 3.1 cùng người
    assert "KA NANG" not in context
    assert "UBND XÃ MẪU" not in context
    assert "mục 1 là nguồn chính" in context
    assert 'result="owner_match"' in context


async def test_khong_co_co_owner_ocr_chi_muc_3_1():
    context = await _requester_context(
        [{"name": "to_khai.pdf", "text": _MAU_03_OCR}],
        {"formContext": _KA_TUI_UI},
    )

    assert "Nơi cư trú: Kambutte" not in context
    assert "Ngày sinh: 01/01/1975" in context


def _area_field(value: dict) -> list[dict]:
    return [{"name": "ChuHoSo_NoiCuTru", "comp": "x-select-area", "value": value}]


def test_nha_trang_bo_tinh_xa_khong_co_tren_dong_noi_cu_tru_muc_1():
    """OCR mục 1 đọc lỗi tên phường, LLM lấy tỉnh/xã của mục 3.1 → bỏ trống, giữ chi tiết dưới xã."""
    ocr = _MAU_03_OCR.replace("Nơi cư trú: Kambutte, xã Đơn Dương", "Nơi cư trú: Kambutte, Phường Đơm Dươg")
    fields = _area_field({"quocGia": "Việt Nam", "tinh": "Ninh Bình", "xa": "Gia Thắng", "diaChi": "Kambutte"})

    warnings = _keep_proposer_area(fields, ocr)

    assert fields[0]["value"] == {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": "Kambutte"}
    assert "để trống" in warnings[0]


def test_nha_trang_giu_tinh_suy_tu_xa_co_tren_dong_muc_1():
    fields = _area_field({"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Đơn Dương", "diaChi": "Kambutte"})

    assert _keep_proposer_area(fields, _MAU_03_OCR) == []
    assert fields[0]["value"]["tinh"] == "Lâm Đồng"
    assert fields[0]["value"]["xa"] == "Đơn Dương"


def test_nha_trang_khong_co_muc_1_thi_khong_dung_dia_chi():
    fields = _area_field({"tinh": "Ninh Bình", "xa": "Gia Thắng", "diaChi": "Xóm 2"})

    assert _keep_proposer_area(fields, "2. Trường hợp hộ gia đình, cá nhân đứng ra mai táng\nHọ và tên: KA TUI") == []
    assert fields[0]["value"]["tinh"] == "Ninh Bình"
