"""[Lào Cai] 1.115694 — hai chế độ xác định NGƯỜI NỘP (theo tài khoản / theo tờ khai).

Hai ô readonly Họ tên/Số Căn cước: chế độ tài khoản KHÔNG phát; chế độ tờ khai ghi theo người đã chọn,
đứng trước các ô CongDan_* khác, và xoá mọi ô nhân thân tài khoản mà hồ sơ không có.
"""

from app.pipelines.dk_giay_cn_thua_dat_dien_tich_tang_them.process import mapper

_CHU_HO_SO = "001099000001"
_UY_QUYEN = "001099000002"
_NGUOI_KHAC = "001099000003"
_TO_KHAI = {"submitterMode": "owner_as_submitter"}

_FACTS = [
    {"name": "NguoiDuocUyQuyen", "value": {
        "hoTen": "Ông Trần Văn B", "soDinhDanh": _UY_QUYEN, "ngaySinh": "1990",
        "dienThoai": "0912000222",
        "thuongTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 5"},
    }},
    {"name": "DanhSachCccd", "value": [
        {"HoTen": "NGUYỄN VĂN A", "SoDinhDanh": _CHU_HO_SO, "NgaySinh": "01/02/1970", "GioiTinh": "Nam",
         "NgayCap": "10/06/2021", "NoiCap": "Bộ Công an",
         "NoiCuTru": {"tinh": "Hà Nội", "xa": "Hai Bà Trưng", "diaChi": "Số 1 phố X"}},
        {"HoTen": "TRẦN VĂN B", "SoDinhDanh": _UY_QUYEN, "NgaySinh": "03/04/1990", "GioiTinh": "Nam",
         "DanToc": "Tày", "NgayCap": "05/05/2022", "NoiCap": "Bộ Công an",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 5"}},
    ]},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Hà Nội", "xa": "Hai Bà Trưng", "diaChi": "Số 1 phố X"}},
    {"name": "Don_DienThoai", "value": "0987000111"},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _ctx(name, number):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}}


def test_tat_toggle_giu_hanh_vi_theo_tai_khoan():
    # Tài khoản là chủ hồ sơ → nhân thân + liên hệ trên Đơn của chủ hồ sơ, không dính bên được ủy quyền.
    fields, warnings = mapper.enrich(_FACTS, _ctx("NGUYỄN VĂN A", _CHU_HO_SO))
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "01/02/1970"
    assert values["CongDan_maPhuongXa"].endswith("Hai Bà Trưng")
    assert values["CongDan_diDong"] == "0987000111"
    assert "CongDan_tenCongDan" not in values and "CongDan_soCmnd" not in values
    assert not warnings


def test_tat_toggle_khong_co_moc_thi_bo_trong():
    fields, warnings = mapper.enrich(_FACTS, {})
    values = _values(fields)

    assert "CongDan_ngaySinhCongDan" not in values
    assert any("Không xác định được NGƯỜI ĐANG ĐI NỘP" in w for w in warnings)


def test_bat_toggle_co_uy_quyen_lay_ben_duoc_uy_quyen_va_canh_bao_lech():
    fields, warnings = mapper.enrich(_FACTS, {**_ctx("NGUYỄN VĂN A", _CHU_HO_SO), **_TO_KHAI})
    values = _values(fields)

    # Ngày sinh chỉ có năm trong giấy ủy quyền → bù ngày đủ từ CCCD CỦA CHÍNH bên được ủy quyền.
    assert values["CongDan_ngaySinhCongDan"] == "03/04/1990"
    assert values["CongDan_danTocCongDan"] == "Tày"
    assert values["CongDan_ngayCapCmnd"] == "05/05/2022"
    assert values["CongDan_maPhuongXa"].endswith("Cam Đường")
    assert values["CongDan_diDong"] == "0912000222"
    assert values["CongDan_tenCongDan"] == "Trần Văn B"
    assert values["CongDan_soCmnd"] == _UY_QUYEN
    assert any("TỜ KHAI" in w and "bị chặn" in w for w in warnings)
    # Khối chủ hồ sơ giữ nguyên.
    assert values["ChuHoSo_tenChuHoSo"] == "NGUYỄN VĂN A"
    assert values["ChuHoSo_soCMNDChuHoSo"] == _CHU_HO_SO


def test_bat_toggle_khong_moc_khong_bao_thieu_moc():
    _, warnings = mapper.enrich(_FACTS, _TO_KHAI)

    assert not any("Không xác định được NGƯỜI ĐANG ĐI NỘP" in w for w in warnings)
    assert not any("bị chặn" in w for w in warnings)


def test_bat_toggle_khong_uy_quyen_lay_chu_ho_so_ca_nhan():
    facts = [f for f in _FACTS if f["name"] != "NguoiDuocUyQuyen"]
    fields, warnings = mapper.enrich(facts, {**_ctx("TRẦN VĂN B", _UY_QUYEN), **_TO_KHAI})
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "01/02/1970"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_maPhuongXa"].endswith("Hai Bà Trưng")
    # Người nộp chính là chủ hồ sơ → số trên Đơn là của người đó.
    assert values["CongDan_diDong"] == "0987000111"
    assert any("bị chặn" in w for w in warnings)


def test_bat_toggle_khong_ghep_nhan_than_nguoi_khac_so_va_nam_sinh_chi_co_nam():
    facts = [
        {"name": "NguoiDuocUyQuyen", "value": {
            "hoTen": "Trần Văn B", "soDinhDanh": _UY_QUYEN, "ngaySinh": "1990",
        }},
        # Trùng họ tên nhưng KHÁC số định danh → người khác, không được ghép.
        {"name": "DanhSachCccd", "value": [
            {"HoTen": "TRẦN VĂN B", "SoDinhDanh": _NGUOI_KHAC, "NgaySinh": "09/09/1990",
             "DanToc": "Kinh", "NgayCap": "01/01/2020",
             "NoiCuTru": {"tinh": "Lào Cai", "xa": "Bắc Lệnh", "diaChi": "Tổ 9"}},
        ]},
        # Giấy khác của CHÍNH bên được ủy quyền (cùng số) → được bù.
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "Trần Văn B", "SoDinhDanh": _UY_QUYEN, "NgayCap": "07/07/2021",
             "NoiCap": "Bộ Công an"},
        ]},
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
        {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
        {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
    ]
    fields, _ = mapper.enrich(facts, _TO_KHAI)
    values = _values(fields)

    # Chỉ có năm / không có của chính người đó → xoá ô cổng đổ từ tài khoản, không mượn người khác.
    assert values["CongDan_ngaySinhCongDan"] == "", "chỉ có năm thì xoá ô ngày sinh tài khoản"
    assert values["CongDan_danTocCongDan"] == ""
    assert "CongDan_maPhuongXa" not in values
    assert values["CongDan_ngayCapCmnd"] == "07/07/2021"
    assert values["CongDan_noiCapCmnd"] == "Bộ Công an"


def test_bat_toggle_chu_ho_so_to_chuc_khong_uy_quyen_thi_bo_trong():
    facts = [
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức"},
        {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Mẫu"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300000001"},
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "LÊ VĂN C", "SoDinhDanh": _NGUOI_KHAC, "NgaySinh": "02/02/1980"},
        ]},
    ]
    fields, warnings = mapper.enrich(facts, _TO_KHAI)
    values = _values(fields)

    assert "CongDan_ngaySinhCongDan" not in values
    assert any("để trống nhân thân" in w for w in warnings)
    assert values["CongDan_tenCoQuanToChuc"] == "CÔNG TY TNHH MẪU"
    assert values["ChuHoSo_maDoiTuongNopHS"] == "DN"


# Người được ủy quyền chỉ có họ tên + số + năm sinh; tài khoản đăng nhập là người khác. Dữ liệu giả.
_FACTS_THIEU = [
    {"name": "NguoiDuocUyQuyen", "value": {
        "hoTen": "Bà Lò Thị D", "soDinhDanh": "001099000004", "ngaySinh": "1985",
    }},
    {"name": "DanhSachCccd", "value": [
        {"HoTen": "PHẠM VĂN E", "SoDinhDanh": _NGUOI_KHAC, "NgaySinh": "05/05/1975", "DanToc": "Kinh",
         "NgayCap": "02/02/2022", "NoiCap": "Bộ Công an",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Bắc Lệnh", "diaChi": "Tổ 1"}},
    ]},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Phạm Văn E"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _NGUOI_KHAC},
    {"name": "Don_DienThoai", "value": "0987000333"},
]


def test_to_khai_ho_ten_can_cuoc_dung_dau_va_xoa_o_nhan_than_thieu():
    fields, warnings = mapper.enrich(_FACTS_THIEU, {**_ctx("HOÀNG VĂN TÀI KHOẢN", "001099000009"), **_TO_KHAI})
    values = _values(fields)
    names = [f["name"] for f in fields if f["name"].startswith("CongDan_")]

    assert names[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    assert values["CongDan_tenCongDan"] == "Lò Thị D"
    assert values["CongDan_soCmnd"] == "001099000004"
    cleared = {f["name"] for f in fields if f.get("clear")}
    for name in ("CongDan_ngaySinhCongDan", "CongDan_danTocCongDan", "CongDan_ngayCapCmnd",
                 "CongDan_noiCapCmnd", "CongDan_maTinhThanh", "CongDan_diaChi", "CongDan_diDong",
                 "CongDan_email", "CongDan_fax"):
        assert name in cleared and values[name] == "", name
    # Không lẫn nhân thân/liên hệ của chủ hồ sơ.
    assert not {"05/05/1975", "02/02/2022", "Kinh", "0987000333"} & {
        v for n, v in values.items() if n.startswith("CongDan_")
    }
    assert any("Giới tính" in w for w in warnings)


def test_tai_khoan_khong_ghi_o_readonly_khong_xoa():
    fields, _ = mapper.enrich(_FACTS_THIEU, _ctx("PHẠM VĂN E", _NGUOI_KHAC))
    names = {f["name"] for f in fields}

    assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & names
    assert not any(f.get("clear") for f in fields)
    assert _values(fields)["CongDan_ngaySinhCongDan"] == "05/05/1975"
