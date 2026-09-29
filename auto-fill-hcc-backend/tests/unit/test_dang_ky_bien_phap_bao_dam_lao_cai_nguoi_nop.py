"""[Lào Cai] 1.011441.H38 — khối NGƯỜI NỘP theo hai chế độ (tài khoản / tờ khai). Dữ liệu giả.

Tài khoản: khớp mốc theo số định danh (thiếu số mới theo tên), không ghi hai ô readonly, không mốc thì
trống + cảnh báo. Tờ khai: người được giới thiệu/ủy quyền → chủ hồ sơ cá nhân; hai ô readonly đứng đầu
khối, nhân thân tài khoản mà hồ sơ không có thì xoá. Không ghép nhân thân giữa hai người.
"""

from app.pipelines.dang_ky_bien_phap_bao_dam_lao_cai.process import mapper
from app.pipelines.dang_ky_bien_phap_bao_dam_lao_cai.process.schema import UI_COMP_BY_NAME

_CHU = {
    "HoTen": "Phạm Văn Giả", "SoDinhDanh": "001080000011", "NgaySinh": "1980", "GioiTinh": "Nam",
    "NgayCap": "01/02/2021", "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "DienThoai": "0900000011", "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 1"},
}
# Người vay cùng họ, khác số định danh — không được ghép vào chủ hồ sơ.
_NGUOI_KHAC = {
    "HoTen": "Phạm Văn Khác", "SoDinhDanh": "001075000099", "NgaySinh": "05/06/1975", "GioiTinh": "Nam",
    "NgayCap": "03/04/2021", "NoiCap": "Bộ Công an", "DienThoai": "0900000099",
    "NoiCuTru": {"tinh": "Lào Cai", "xa": "Xuân Tăng", "diaChi": "Số 99"},
}
_CCCD_CAN_BO = {
    "HoTen": "Lê Thị Cán Bộ", "SoDinhDanh": "001190000033", "NgaySinh": "07/08/1990", "GioiTinh": "Nữ",
    "NgayCap": "09/10/2022", "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 5"},
}

_FACTS = [
    {"name": "ChuHoSo_HoTen", "value": "Phạm Văn Giả"},
    {"name": "ChuHoSo_LaToChuc", "value": False},
    {"name": "ChuHoSo_SoDinhDanh", "value": "001080000011"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 1"}},
    {"name": "ChuHoSo_DienThoai", "value": "0900000011"},
    {"name": "NguoiTrongGiayTo", "value": [_CHU, _NGUOI_KHAC]},
]
_FACTS_GIOI_THIEU = [
    *_FACTS,
    {"name": "NguoiDuocUyQuyen", "value": {
        "hoTen": "Lê Thị Cán Bộ", "soDinhDanh": "001190000033", "donVi": "QUỸ TÍN DỤNG GIẢ ĐỊNH",
        "maSoThueDonVi": "5300000001",
    }},
    {"name": "DanhSachCccd", "value": [_CCCD_CAN_BO]},
]
_TK_KHAC = {"applicantFullname": "NGUYỄN TÀI KHOẢN", "applicantIdentityNumber": "001199000001"}


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _congdan(fields):
    return [f["name"] for f in fields if f["name"].startswith("CongDan_")]


# ------------------------------------------------------------------ theo tài khoản

def test_tai_khoan_khop_so_dinh_danh_lay_dung_nguoi_khong_ghi_readonly():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": {
        "applicantFullname": "PHẠM VĂN KHÁC", "applicantIdentityNumber": "001075000099",
    }})
    values = _values(fields)

    assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & set(values)
    assert values["CongDan_ngaySinhCongDan"] == "05/06/1975"
    assert values["CongDan_diDong"] == "0900000099"
    assert values["CongDan_maPhuongXa"] == "Xuân Tăng"
    assert not any(f.get("clear") for f in fields)
    # Khối chủ hồ sơ vẫn là người yêu cầu, không lẫn người nộp.
    assert values["ChuHoSo_soCMNDChuHoSo"] == "001080000011"
    assert "05/06/1975" not in [v for k, v in values.items() if k.startswith("ChuHoSo_")]
    assert not any("NGƯỜI ĐANG ĐI NỘP" in w for w in warnings)


def test_tai_khoan_khop_theo_ten_khi_ung_vien_khong_co_so():
    facts = [
        {"name": "ChuHoSo_HoTen", "value": "Phạm Văn Giả"},
        {"name": "ChuHoSo_LaToChuc", "value": False},
        {"name": "NguoiTrongGiayTo", "value": [{"HoTen": "Phạm Văn Giả", "DienThoai": "0900000011"}]},
    ]
    fields, _ = mapper.enrich(facts, {"formContext": {
        "applicantFullname": "PHAM VAN GIA", "applicantIdentityNumber": "001080000011",
    }})
    assert _values(fields)["CongDan_diDong"] == "0900000011"


def test_tai_khoan_khong_thay_trong_ho_so_thi_trong_va_canh_bao():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": _TK_KHAC})
    assert _congdan(fields) == []
    assert any("CHÍNH người đang đăng nhập" in w for w in warnings)


def test_khong_co_form_context_nhu_khong_moc():
    for options in ({}, None, {"formContext": {}}):
        fields, warnings = mapper.enrich(_FACTS, options)
        assert _congdan(fields) == []
        assert any("F5" in w and "Người nộp = chủ hồ sơ" in w for w in warnings)


def test_tai_khoan_la_nguoi_duoc_gioi_thieu_thi_o_to_chuc_la_don_vi():
    fields, _ = mapper.enrich(_FACTS_GIOI_THIEU, {"formContext": {
        "applicantFullname": "LÊ THỊ CÁN BỘ", "applicantIdentityNumber": "001190000033",
    }})
    values = _values(fields)
    assert values["CongDan_tenCoQuanToChuc"] == "QUỸ TÍN DỤNG GIẢ ĐỊNH"
    assert values["CongDan_maSoThueNguoiNop"] == "5300000001"
    assert values["CongDan_ngaySinhCongDan"] == "07/08/1990"


# ------------------------------------------------------------------ theo tờ khai

def test_to_khai_co_giay_gioi_thieu_lay_nguoi_duoc_gioi_thieu_va_don_vi():
    fields, warnings = mapper.enrich(
        _FACTS_GIOI_THIEU, {"submitterMode": "owner_as_submitter", "formContext": _TK_KHAC}
    )
    values = _values(fields)

    assert _congdan(fields)[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    assert values["CongDan_tenCongDan"] == "LÊ THỊ CÁN BỘ"
    assert values["CongDan_soCmnd"] == "001190000033"
    # Nhân thân bù từ CCCD của CHÍNH người được giới thiệu.
    assert values["CongDan_ngaySinhCongDan"] == "07/08/1990"
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"
    assert values["CongDan_tenCoQuanToChuc"] == "QUỸ TÍN DỤNG GIẢ ĐỊNH"
    assert values["CongDan_maSoThueNguoiNop"] == "5300000001"
    assert any("TỜ KHAI" in w for w in warnings)


def test_to_khai_khong_uy_quyen_lay_chu_ho_so_ca_nhan_va_xoa_o_thieu():
    fields, _ = mapper.enrich(_FACTS, {"submitterMode": "owner_as_submitter", "formContext": _TK_KHAC})
    values = _values(fields)

    assert _congdan(fields)[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    assert values["CongDan_tenCongDan"] == "PHẠM VĂN GIẢ"
    assert values["CongDan_soCmnd"] == "001080000011"
    assert values["CongDan_diDong"] == "0900000011"
    # Chỉ có năm sinh → ô ngày sinh tài khoản bị xoá, không ghép ngày của người khác.
    cleared = {f["name"] for f in fields if f.get("clear")}
    assert "CongDan_ngaySinhCongDan" in cleared and values["CongDan_ngaySinhCongDan"] == ""
    assert "CongDan_email" in cleared
    for foreign in ("001075000099", "05/06/1975", "03/04/2021", "0900000099", "Xuân Tăng"):
        assert foreign not in values.values(), foreign
    assert "CongDan_tenCoQuanToChuc" not in values


def test_to_khai_lenh_xoa_dung_comp_va_danh_dau():
    fields, _ = mapper.enrich(_FACTS, {"submitterMode": "owner_as_submitter"})
    fax = next(f for f in fields if f["name"] == "CongDan_fax")
    assert fax == {"name": "CongDan_fax", "comp": UI_COMP_BY_NAME["CongDan_fax"], "value": "", "clear": True,
                   "markEmpty": False}
    # Lệnh xoá nằm trong khối người nộp, trước khối chủ hồ sơ.
    names = [f["name"] for f in fields]
    assert names.index("CongDan_fax") < names.index("ChuHoSo_maDoiTuongNopHS")


def test_khong_ghep_cheo_ten_trung_nhieu_so():
    # Hai người cùng họ tên, khác số định danh; khối phẳng không có số → không được gộp vào ai.
    trung_1 = {"HoTen": "Phạm Văn Giả", "SoDinhDanh": "001080000011", "NgaySinh": "01/01/1981"}
    trung_2 = {"HoTen": "Phạm Văn Giả", "SoDinhDanh": "001060000022", "NgaySinh": "02/02/1960"}
    facts = [
        {"name": "ChuHoSo_HoTen", "value": "Phạm Văn Giả"},
        {"name": "ChuHoSo_LaToChuc", "value": False},
        {"name": "NguoiTrongGiayTo", "value": [trung_1, trung_2]},
    ]
    fields, _ = mapper.enrich(facts, {"submitterMode": "owner_as_submitter"})
    values = _values(fields)
    assert "001080000011" not in values.values() and "001060000022" not in values.values()
    assert values.get("CongDan_ngaySinhCongDan") in (None, "")
