"""[Lào Cai] 1.115693 — hai chế độ xác định NGƯỜI NỘP (theo tài khoản / theo tờ khai).

Schema chỉ có hai khối phẳng `NguoiNop_*` (bên được ủy quyền, không ủy quyền thì chép chủ hồ sơ) và
`ChuHoSo_*`. Hai ô readonly Họ tên/Số Căn cước: chế độ tài khoản KHÔNG phát; chế độ tờ khai ghi theo
người đã chọn, đứng trước các ô CongDan_* khác, và xoá mọi ô nhân thân tài khoản mà hồ sơ không có.
"""

from app.pipelines.dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi.process import mapper

_CHU_HO_SO = "001099000001"
_UY_QUYEN = "001099000002"
_TO_KHAI = {"submitterMode": "owner_as_submitter"}

_CHU_HO_SO_FACTS = [
    {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
    {"name": "ChuHoSo_LaToChuc", "value": False},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
    {"name": "ChuHoSo_NgaySinh", "value": "01/02/1970"},
    {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
    {"name": "ChuHoSo_NgayCap", "value": "10/06/2021"},
    {"name": "ChuHoSo_NoiCap", "value": "Bộ Công an"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Bắc Ninh", "xa": "Kinh Bắc", "diaChi": "Khu 1"}},
    {"name": "ChuHoSo_DienThoai", "value": "0987000111"},
]
_NGUOI_NOP_FACTS = [
    {"name": "NguoiNop_HoTen", "value": "Trần Văn B"},
    {"name": "NguoiNop_SoDinhDanh", "value": _UY_QUYEN},
    {"name": "NguoiNop_NgaySinh", "value": "03/04/1990"},
    {"name": "NguoiNop_GioiTinh", "value": "Nam"},
    {"name": "NguoiNop_NgayCap", "value": "05/05/2022"},
    {"name": "NguoiNop_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 5"}},
    {"name": "NguoiNop_DienThoai", "value": "0912000222"},
    {"name": "UyQuyen_SoGiay", "value": "0055"},
]
_FACTS = _CHU_HO_SO_FACTS + _NGUOI_NOP_FACTS


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _ctx(name, number):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}}


def test_tat_toggle_giu_hanh_vi_theo_tai_khoan():
    # Tài khoản là chủ hồ sơ → khối người nộp lấy khối chủ hồ sơ, dù hồ sơ có người được ủy quyền.
    fields, warnings = mapper.enrich(_FACTS, _ctx("NGUYỄN VĂN A", _CHU_HO_SO))
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "01/02/1970"
    assert values["CongDan_diaChi"] == "Khu 1"
    assert "CongDan_tenCongDan" not in values and "CongDan_soCmnd" not in values
    assert not any("TỜ KHAI" in w for w in warnings)


def test_tat_toggle_khong_moc_thi_bo_trong():
    fields, warnings = mapper.enrich(_FACTS, {})
    values = _values(fields)

    assert "CongDan_ngaySinhCongDan" not in values
    assert any("Chưa đọc được tài khoản định danh" in w for w in warnings)


def test_bat_toggle_co_uy_quyen_lay_nguoi_duoc_uy_quyen_va_canh_bao_lech():
    fields, warnings = mapper.enrich(_FACTS, {**_ctx("NGUYỄN VĂN A", _CHU_HO_SO), **_TO_KHAI})
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "03/04/1990"
    assert values["CongDan_ngayCapCmnd"] == "05/05/2022"
    assert values["CongDan_diaChi"] == "Tổ 5"
    assert values["CongDan_diDong"] == "0912000222"
    assert values["CongDan_tenCongDan"] == "Trần Văn B"
    assert values["CongDan_soCmnd"] == _UY_QUYEN
    assert any("TỜ KHAI" in w and "bị chặn" in w for w in warnings)
    assert not any("Chưa đọc được tài khoản định danh" in w for w in warnings)
    # Khối chủ hồ sơ giữ nguyên, không lẫn người được ủy quyền.
    assert values["ChuHoSo_tenChuHoSo"] == "Nguyễn Văn A"
    assert values["ChuHoSo_ngaySinhChuHoSo"] == "01/02/1970"
    assert values["ChuHoSo_diDongLienLacCHS"] == "0987000111"


def test_bat_toggle_khong_uy_quyen_lay_chu_ho_so_ca_nhan():
    fields, warnings = mapper.enrich(_CHU_HO_SO_FACTS, _TO_KHAI)
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "01/02/1970"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_diaChi"] == "Khu 1"
    assert values["CongDan_diDong"] == "0987000111"
    assert not any("bị chặn" in w or "Chưa đọc được tài khoản" in w for w in warnings)


def test_bat_toggle_cung_so_thi_bo_khuyet_khac_nguoi_thi_khong_ghep():
    # Cùng số định danh với chủ hồ sơ → cùng một người, được bổ khuyết ngày sinh/nơi cư trú.
    same = _CHU_HO_SO_FACTS + [
        {"name": "NguoiNop_HoTen", "value": "Nguyễn Văn A"},
        {"name": "NguoiNop_SoDinhDanh", "value": _CHU_HO_SO},
    ]
    values = _values(mapper.enrich(same, _TO_KHAI)[0])
    assert values["CongDan_ngaySinhCongDan"] == "01/02/1970"
    assert values["CongDan_diaChi"] == "Khu 1"

    # Trùng họ tên nhưng người nộp không có số và năm sinh mâu thuẫn → hai người, không ghép; ngày
    # sinh chỉ có năm thì xoá ô ngày sinh cổng đổ từ tài khoản.
    other = _CHU_HO_SO_FACTS + [
        {"name": "NguoiNop_HoTen", "value": "Nguyễn Văn A"},
        {"name": "NguoiNop_NgaySinh", "value": "1995"},
    ]
    values = _values(mapper.enrich(other, _TO_KHAI)[0])
    assert values["CongDan_ngaySinhCongDan"] == ""
    assert values["CongDan_ngayCapCmnd"] == ""
    assert values["CongDan_diaChi"] == ""
    assert values["CongDan_diDong"] == ""


def test_bat_toggle_chu_ho_so_to_chuc_khong_nguoi_nop_thi_bo_trong():
    facts = [
        {"name": "ChuHoSo_LaToChuc", "value": True},
        {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Mẫu"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300000001"},
        {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 2"}},
    ]
    fields, warnings = mapper.enrich(facts, _TO_KHAI)
    values = _values(fields)

    assert not any(name.startswith("CongDan_") for name in values)
    assert any("để trống nhân thân" in w for w in warnings)
    assert values["ChuHoSo_tenCoQuanToChucCHS"] == "Công ty TNHH Mẫu"


# Người được ủy quyền chỉ có họ tên + số + năm sinh; tài khoản đăng nhập là người khác. Dữ liệu giả.
_THIEU = _CHU_HO_SO_FACTS + [
    {"name": "NguoiNop_HoTen", "value": "Lò Thị D"},
    {"name": "NguoiNop_SoDinhDanh", "value": "001099000004"},
    {"name": "NguoiNop_NgaySinh", "value": "1985"},
]


def test_to_khai_ho_ten_can_cuoc_dung_dau_va_xoa_o_nhan_than_thieu():
    fields, warnings = mapper.enrich(_THIEU, {**_ctx("HOÀNG VĂN TÀI KHOẢN", "001099000009"), **_TO_KHAI})
    values = _values(fields)
    names = [f["name"] for f in fields if f["name"].startswith("CongDan_")]

    assert names[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    assert values["CongDan_tenCongDan"] == "Lò Thị D"
    assert values["CongDan_soCmnd"] == "001099000004"
    cleared = {f["name"] for f in fields if f.get("clear")}
    # Nơi cấp có mặc định theo số căn cước (default_issuer) nên không nằm trong danh sách xoá.
    for name in ("CongDan_ngaySinhCongDan", "CongDan_danTocCongDan", "CongDan_ngayCapCmnd",
                 "CongDan_maTinhThanh", "CongDan_diaChi", "CongDan_diDong",
                 "CongDan_email", "CongDan_fax"):
        assert name in cleared and values[name] == "", name
    # Không mượn nhân thân/liên hệ của chủ hồ sơ (người khác).
    assert not {"01/02/1970", "10/06/2021", "Khu 1", "0987000111"} & {
        v for n, v in values.items() if n.startswith("CongDan_")
    }
    assert any("Giới tính" in w for w in warnings)


def test_tai_khoan_khong_ghi_o_readonly_khong_xoa():
    fields, _ = mapper.enrich(_THIEU, _ctx("NGUYỄN VĂN A", _CHU_HO_SO))
    names = {f["name"] for f in fields}

    assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & names
    assert not any(f.get("clear") for f in fields)
    assert _values(fields)["CongDan_ngaySinhCongDan"] == "01/02/1970"
