"""[Lào Cai] 1.011442.H38 — hai chế độ xác định NGƯỜI NỘP (đăng ký thay đổi biện pháp bảo đảm).

Cổng đổ sẵn Họ tên + Số Căn cước của tài khoản vào hai ô readonly rồi gửi chính chúng (kèm ngày sinh)
sang CSDL quốc gia dân cư để xác thực trước khi cho nộp → cả khối phải là nhân thân của MỘT người.
Chủ hồ sơ điển hình là ngân hàng (bên nhận bảo đảm), người nộp là cán bộ được giới thiệu. Dữ liệu giả.
"""

from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_lao_cai.process import mapper
from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_lao_cai.process.schema import UI_COMP_BY_NAME

_NGAN_HANG = "NGÂN HÀNG TMCP GIẢ ĐỊNH - CHI NHÁNH MẪU"
_CAN_BO = {
    "HoTen": "NGUYỄN VĂN CÁN BỘ", "SoDinhDanh": "001090000011", "NgayCap": "17/11/2022", "GioiTinh": "Nam",
}
_GIAM_DOC = {
    "HoTen": "LÊ VĂN GIÁM ĐỐC", "SoDinhDanh": "001070000099", "NgaySinh": "01/02/1970", "GioiTinh": "Nam",
    "NgayCap": "03/04/2021", "DienThoai": "0900000099",
    "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 99"},
}
_BASE = [
    {"name": "ChuHoSo_LaToChuc", "value": True},
    {"name": "ChuHoSo_TenToChuc", "value": _NGAN_HANG},
    {"name": "ChuHoSo_MaSoThue", "value": "0100000000-001"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 1"}},
]
# Hồ sơ có Giấy giới thiệu cán bộ ngân hàng đi đăng ký.
_FACTS_GIOI_THIEU = _BASE + [
    {"name": "NguoiDuocUyQuyen", "value": {
        "hoTen": "Nguyễn Văn Cán Bộ", "soDinhDanh": "001090000011", "ngayCapCccd": "17/11/2022",
        "chucVu": "Chuyên viên", "donVi": _NGAN_HANG,
    }},
    {"name": "NguoiTrongGiayTo", "value": [_CAN_BO, _GIAM_DOC]},
]
# Hồ sơ không có giấy giới thiệu/ủy quyền, phiếu không ghi người liên hệ.
_FACTS_KHONG_UY_QUYEN = _BASE + [{"name": "NguoiTrongGiayTo", "value": [_GIAM_DOC]}]


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _congdan(fields):
    return [f["name"] for f in fields if f["name"].startswith("CongDan_")]


def test_tai_khoan_khop_so_dinh_danh_bu_nhan_than_khong_ghi_readonly():
    fields, warnings = mapper.enrich(_FACTS_GIOI_THIEU, {"formContext": {
        "applicantFullname": "NGUYỄN VĂN CÁN BỘ", "applicantIdentityNumber": "001090000011",
    }})
    values = _values(fields)

    assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & set(values)
    assert values["CongDan_ngayCapCmnd"] == "17/11/2022"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_tenCoQuanToChuc"] == _NGAN_HANG
    assert values["CongDan_maSoThueNguoiNop"] == "0100000000-001"
    assert not any(f.get("clear") for f in fields)
    # Không mượn nhân thân của giám đốc.
    for foreign in ("01/02/1970", "03/04/2021", "0900000099", "Số 99"):
        assert foreign not in values.values(), foreign
    assert not any("NGƯỜI ĐANG ĐI NỘP" in w for w in warnings)


def test_tai_khoan_khop_theo_ten_khi_giay_to_khong_co_so():
    facts = _BASE + [{"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "Trần Thị Liên Hệ", "DienThoai": "0911222333", "NgaySinh": "05/06/1991"},
    ]}]
    fields, _ = mapper.enrich(facts, {"formContext": {"applicantFullname": "TRẦN THỊ LIÊN HỆ"}})
    values = _values(fields)

    assert values["CongDan_diDong"] == "0911222333"
    assert values["CongDan_ngaySinhCongDan"] == "05/06/1991"


def test_tai_khoan_trung_ten_hai_so_khac_nhau_thi_khong_doan():
    facts = _BASE + [{"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "Phạm Văn Trùng", "SoDinhDanh": "001080000001", "NgaySinh": "01/01/1980"},
        {"HoTen": "Phạm Văn Trùng", "SoDinhDanh": "001095000002", "NgaySinh": "02/02/1995"},
    ]}]
    fields, warnings = mapper.enrich(facts, {"formContext": {"applicantFullname": "Phạm Văn Trùng"}})
    values = _values(fields)

    assert "CongDan_ngaySinhCongDan" not in values
    assert any("CHÍNH người đang đăng nhập" in w for w in warnings)


def test_tai_khoan_co_moc_nhung_ho_so_khong_co_nguoi_do():
    fields, warnings = mapper.enrich(_FACTS_GIOI_THIEU, {"formContext": {
        "applicantFullname": "NHÂN VIÊN KHÁC", "applicantIdentityNumber": "001199000777",
    }})
    values = _values(fields)

    for name in ("CongDan_ngaySinhCongDan", "CongDan_ngayCapCmnd", "CongDan_diDong", "CongDan_diaChi"):
        assert name not in values, name
    assert any("CHÍNH người đang đăng nhập" in w for w in warnings)
    # Dữ liệu TỔ CHỨC vẫn phát.
    assert values["CongDan_tenCoQuanToChuc"] == _NGAN_HANG
    assert values["ChuHoSo_tenCoQuanToChucCHS"] == _NGAN_HANG


def test_khong_moc_hoac_khong_co_form_context_thi_trong_va_canh_bao():
    for options in ({}, None, {"formContext": {}}):
        fields, warnings = mapper.enrich(_FACTS_GIOI_THIEU, options)
        values = _values(fields)
        for name in ("CongDan_tenCongDan", "CongDan_soCmnd", "CongDan_ngayCapCmnd", "CongDan_gioiTinhCongDan"):
            assert name not in values, (options, name)
        assert any("NGƯỜI ĐANG ĐI NỘP" in w and "F5" in w and "Người nộp = chủ hồ sơ" in w for w in warnings)
        assert values["ChuHoSo_maDoiTuongNopHS"] == "DN"


def test_to_khai_co_giay_gioi_thieu_lay_nguoi_duoc_gioi_thieu():
    fields, warnings = mapper.enrich(_FACTS_GIOI_THIEU, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)

    assert _congdan(fields)[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    assert values["CongDan_tenCongDan"] == "Nguyễn Văn Cán Bộ"
    assert values["CongDan_soCmnd"] == "001090000011"
    assert values["CongDan_ngayCapCmnd"] == "17/11/2022"
    assert values["CongDan_tenCoQuanToChuc"] == _NGAN_HANG
    assert values["CongDan_maSoThueNguoiNop"] == "0100000000-001"
    # Hồ sơ không có ngày sinh/địa chỉ/di động của cán bộ → xoá giá trị tài khoản cổng đã đổ.
    cleared = {f["name"] for f in fields if f.get("clear")}
    for name in ("CongDan_ngaySinhCongDan", "CongDan_diaChi", "CongDan_diDong"):
        assert name in cleared and values[name] == "", name
    idx_last_congdan = max(i for i, f in enumerate(fields) if f["name"].startswith("CongDan_"))
    idx_first_chs = min(i for i, f in enumerate(fields) if f["name"].startswith("ChuHoSo_"))
    assert idx_last_congdan < idx_first_chs
    for foreign in ("01/02/1970", "0900000099", "001070000099"):
        assert foreign not in values.values(), foreign
    assert not any("không xác định được" in w for w in warnings)


def test_to_khai_lech_tai_khoan_thi_canh_bao():
    _, warnings = mapper.enrich(_FACTS_GIOI_THIEU, {
        "submitterMode": "owner_as_submitter",
        "formContext": {"applicantFullname": "NHÂN VIÊN KHÁC", "applicantIdentityNumber": "001199000777"},
    })
    assert any("TỜ KHAI" in w and "chặn" in w for w in warnings)


def test_to_khai_khong_uy_quyen_chu_ho_so_to_chuc_thi_trong_va_canh_bao():
    fields, warnings = mapper.enrich(_FACTS_KHONG_UY_QUYEN, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)

    assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & set(values)
    assert not any(f.get("clear") for f in fields)
    for foreign in ("01/02/1970", "0900000099", "001070000099"):
        assert foreign not in values.values(), foreign
    assert any("không xác định được" in w for w in warnings)
    assert values["CongDan_tenCoQuanToChuc"] == _NGAN_HANG


def test_to_khai_nguoi_lien_he_tren_phieu():
    facts = _FACTS_KHONG_UY_QUYEN + [
        {"name": "NguoiNop_HoTen", "value": "Trần Thị Liên Hệ"},
        {"name": "NguoiNop_DienThoai", "value": "0911.222.333"},
    ]
    fields, _ = mapper.enrich(facts, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)

    assert values["CongDan_tenCongDan"] == "Trần Thị Liên Hệ"
    assert values["CongDan_diDong"] == "0911222333"
    # Không có số của người liên hệ → xoá ô căn cước tài khoản, không để sót.
    so_cmnd = next(f for f in fields if f["name"] == "CongDan_soCmnd")
    assert so_cmnd == {"name": "CongDan_soCmnd", "comp": UI_COMP_BY_NAME["CongDan_soCmnd"], "value": "",
                       "clear": True, "markEmpty": True}
    # Không có đơn vị trong giấy giới thiệu → ô tổ chức lấy tổ chức chủ hồ sơ.
    assert values["CongDan_tenCoQuanToChuc"] == _NGAN_HANG


def test_khong_ghep_cheo_khi_ten_trung_nhung_ngay_sinh_khac():
    facts = _BASE + [
        {"name": "NguoiNop_HoTen", "value": "Đỗ Văn Trùng"},
        {"name": "NguoiNop_NgaySinh", "value": "10/10/1990"},
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "ĐỖ VĂN TRÙNG", "NgaySinh": "11/11/1960", "DienThoai": "0900000123", "NgayCap": "01/01/2020"},
        ]},
    ]
    fields, _ = mapper.enrich(facts, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "10/10/1990"
    assert values.get("CongDan_diDong") != "0900000123"
    assert values.get("CongDan_ngayCapCmnd") != "01/01/2020"
