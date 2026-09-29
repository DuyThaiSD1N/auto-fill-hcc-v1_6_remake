"""[Lào Cai] 1.115671 — hai chế độ xác định NGƯỜI NỘP.

Chế độ theo tài khoản (mặc định) bù nhân thân của CHÍNH người đang đăng nhập. Chế độ theo tờ khai
(`submitterMode="owner_as_submitter"`) bỏ mốc: schema thủ tục này không tách vai bên được uỷ quyền nên
người nộp là chủ hồ sơ cá nhân. Hai ô Họ tên/Số Căn cước readonly: tài khoản không phát, tờ khai ghi theo
người đó và xoá ô nhân thân tài khoản mà hồ sơ không có.
"""

from app.pipelines.dang_ky_bien_dong_lao_cai.process import mapper
from app.pipelines._shared.lao_cai_nguoi_nop import O_NHAN_THAN_XOA_DUOC

_CHU_HO_SO = "001099000001"
_NGUOI_KHAC = "001199000002"
_TRUNG_TEN = "001099000009"

_FACTS = [
    {"name": "DanhSachCccd", "value": [
        {"HoTen": "NGUYỄN VĂN A", "SoDinhDanh": _CHU_HO_SO, "NgaySinh": "02/03/1985",
         "GioiTinh": "Nam", "DanToc": "Kinh", "NgayCap": "10/06/2021", "NoiCap": "Bộ Công an"},
        {"HoTen": "TRẦN THỊ B", "SoDinhDanh": _NGUOI_KHAC, "NgaySinh": "04/05/1990",
         "GioiTinh": "Nữ", "DanToc": "Tày", "NgayCap": "01/02/2022",
         "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    ]},
    {"name": "NguoiTrongGiayTo", "value": [
        # Người trùng họ tên chủ hồ sơ nhưng khác số định danh — không được ghép nhân thân.
        {"HoTen": "Nguyễn Văn A", "SoDinhDanh": _TRUNG_TEN, "NgaySinh": "07/08/1960",
         "GioiTinh": "Nam", "NgayCap": "03/03/2015", "NoiCap": "Công an tỉnh Lào Cai"},
    ]},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
    {"name": "ChuHoSo_NgaySinh", "value": "1985"},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 1"}},
]

_TO_KHAI = {"submitterMode": "owner_as_submitter"}
_MOC_NGUOI_KHAC = {"applicantFullname": "TRẦN THỊ B", "applicantIdentityNumber": _NGUOI_KHAC}


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def test_che_do_tai_khoan_giu_hanh_vi_cu_theo_moc():
    fields, warnings = mapper.enrich(_FACTS, {"formContext": _MOC_NGUOI_KHAC})
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "04/05/1990"
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"
    assert values["CongDan_danTocCongDan"] == "Tày"
    assert values["CongDan_ngayCapCmnd"] == "01/02/2022"
    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values
    assert warnings == []


def test_che_do_to_khai_lay_chu_ho_so_du_moc_la_nguoi_khac_va_canh_bao_lech():
    fields, warnings = mapper.enrich(_FACTS, {**_TO_KHAI, "formContext": _MOC_NGUOI_KHAC})
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "02/03/1985"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_danTocCongDan"] == "Kinh"
    assert values["CongDan_ngayCapCmnd"] == "10/06/2021"
    assert values["CongDan_noiCapCmnd"] == "Bộ Công an"
    assert values["CongDan_tenCongDan"] == "NGUYỄN VĂN A"
    assert values["CongDan_soCmnd"] == _CHU_HO_SO
    assert any("TỜ KHAI" in w and "bị chặn" in w for w in warnings)


def test_che_do_to_khai_khong_moc_thi_khong_canh_bao_thieu_moc():
    fields, warnings = mapper.enrich(_FACTS, _TO_KHAI)

    assert _values(fields)["CongDan_ngaySinhCongDan"] == "02/03/1985"
    assert warnings == []


def test_che_do_to_khai_moc_trung_chu_ho_so_khong_canh_bao():
    _, warnings = mapper.enrich(_FACTS, {**_TO_KHAI, "formContext": {
        "applicantFullname": "NGUYỄN VĂN A", "applicantIdentityNumber": _CHU_HO_SO,
    }})

    assert warnings == []


def test_che_do_to_khai_khong_ghep_nhan_than_nguoi_khac_so_va_bo_nam_sinh_tro():
    """Không có CCCD của chủ hồ sơ: người trùng tên khác số KHÔNG được ghép; Đơn chỉ ghi năm sinh → bỏ."""
    facts = [f for f in _FACTS if f["name"] != "DanhSachCccd"]
    fields, _ = mapper.enrich(facts, _TO_KHAI)
    values = _values(fields)

    # Không có nguồn của chính người đó → XOÁ ô cổng đổ từ tài khoản.
    assert values["CongDan_ngaySinhCongDan"] == ""
    assert values["CongDan_ngayCapCmnd"] == ""
    assert values["CongDan_noiCapCmnd"] == ""
    assert values["CongDan_gioiTinhCongDan"] == "Nam", "suy từ xưng hô Ông của chính chủ hồ sơ"


def test_che_do_to_khai_ghep_theo_ho_ten_khi_thieu_so_va_ngay_sinh_khong_mau_thuan():
    facts = [f for f in _FACTS if f["name"] not in ("ChuHoSo_SoDinhDanh", "NguoiTrongGiayTo")]
    fields, _ = mapper.enrich(facts, _TO_KHAI)
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "02/03/1985"
    assert values["CongDan_danTocCongDan"] == "Kinh"


def test_che_do_to_khai_chu_ho_so_to_chuc_thi_bo_trong_va_canh_bao():
    facts = [
        {"name": "DanhSachCccd", "value": _FACTS[0]["value"]},
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức khác"},
        {"name": "ChuHoSo_TenToChuc", "value": "Cơ quan Ủy ban Mặt trận Tổ quốc Việt Nam tỉnh Lào Cai"},
    ]
    fields, warnings = mapper.enrich(facts, _TO_KHAI)
    values = _values(fields)

    assert not any(name.startswith("CongDan_") and name != "CongDan_tenCoQuanToChuc" for name in values)
    assert any("để trống nhân thân" in w for w in warnings)
    # Ô tên cơ quan của khối người nộp và khối chủ hồ sơ là dữ liệu TỔ CHỨC — vẫn phát.
    assert values["CongDan_tenCoQuanToChuc"].startswith("Cơ quan Ủy ban Mặt trận")
    assert values["ChuHoSo_maDoiTuongNopHS"] == "TC"


def _congdan_names(fields):
    return [f["name"] for f in fields if f["name"].startswith("CongDan_")]


def test_to_khai_ho_ten_can_cuoc_dung_dau_khoi_va_xoa_o_tai_khoan_ho_so_khong_co():
    """Chủ hồ sơ chỉ có năm sinh trên Đơn, không có thẻ → ô nhân thân của tài khoản phải bị xoá."""
    facts = [f for f in _FACTS if f["name"] != "DanhSachCccd"]
    fields, _ = mapper.enrich(facts, {**_TO_KHAI, "formContext": _MOC_NGUOI_KHAC})

    names = _congdan_names(fields)
    assert names[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    values = _values(fields)
    assert values["CongDan_tenCongDan"] == "NGUYỄN VĂN A"
    assert values["CongDan_soCmnd"] == _CHU_HO_SO
    cleared = {f["name"] for f in fields if f.get("clear")}
    # Mọi form Lào Cai chung bộ ô CongDan_*: hồ sơ không có mục nào thì xoá đủ ô tài khoản đã đổ.
    assert cleared == set(O_NHAN_THAN_XOA_DUOC)
    for f in fields:
        if f.get("clear"):
            assert f["value"] == "" and f["comp"]
    # Không lẫn nhân thân của người trùng tên khác số hay của tài khoản.
    assert not {"07/08/1960", "03/03/2015", "04/05/1990", _NGUOI_KHAC, _TRUNG_TEN} & set(values.values())


def test_to_khai_khong_so_dinh_danh_thi_xoa_o_can_cuoc_ngay_sau_ho_ten():
    facts = [f for f in _FACTS if f["name"] not in ("ChuHoSo_SoDinhDanh", "DanhSachCccd", "NguoiTrongGiayTo")]
    fields, _ = mapper.enrich(facts, _TO_KHAI)

    assert _congdan_names(fields)[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    so_cmnd = next(f for f in fields if f["name"] == "CongDan_soCmnd")
    assert so_cmnd["value"] == "" and so_cmnd.get("clear") is True


def test_tai_khoan_khong_ghi_o_readonly_va_khong_xoa_o_nao():
    for ctx in ({"formContext": _MOC_NGUOI_KHAC}, {}):
        fields, _ = mapper.enrich(_FACTS, ctx)
        assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & set(_congdan_names(fields))
        assert not any(f.get("clear") for f in fields)


def test_to_khai_khong_doc_duoc_ho_ten_thi_khong_ghi_o_readonly_va_khong_xoa():
    """Chưa biết người nộp là ai (chỉ có số, không có họ tên) → không đổi riêng Số Căn cước, không xoá gì."""
    facts = [f for f in _FACTS if f["name"] not in ("ChuHoSo_HoTen", "DanhSachCccd", "NguoiTrongGiayTo")]
    fields = mapper.enrich(facts, _TO_KHAI)[0]
    assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & set(_congdan_names(fields))
    assert not any(f.get("clear") for f in fields)
