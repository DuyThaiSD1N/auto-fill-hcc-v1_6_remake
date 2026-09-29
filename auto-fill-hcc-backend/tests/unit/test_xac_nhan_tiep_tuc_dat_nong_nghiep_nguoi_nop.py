"""[Lào Cai] 1.115677 — hai chế độ xác định NGƯỜI NỘP (theo tài khoản / theo tờ khai).

Theo tờ khai: bên được ủy quyền → người ký "Người làm đơn" của Đơn Mẫu số 39 → chủ hồ sơ cá nhân. Hai ô
readonly Họ tên/Số Căn cước: chế độ tài khoản KHÔNG phát; chế độ tờ khai ghi theo người đã chọn, đứng
trước các ô CongDan_* khác, và xoá mọi ô nhân thân tài khoản mà hồ sơ không có.
"""

from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process import mapper

_CHU_HO_SO = "001099000001"
_UY_QUYEN = "001099000002"
_NGUOI_KHAC = "001099000003"
_VO = "001099000004"
_TO_KHAI = {"submitterMode": "owner_as_submitter"}
_DIA_CHI_DON = {"tinh": "Lào Cai", "xa": "Văn Phú", "diaChi": "Thôn 1"}

_FACTS = [
    {"name": "DanhSachCccd", "value": [
        {"HoTen": "NGUYỄN VĂN A", "SoDinhDanh": _CHU_HO_SO, "NgaySinh": "01/02/1970", "GioiTinh": "Nam",
         "NgayCap": "10/06/2021", "NoiCap": "Bộ Công an",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Văn Phú", "diaChi": "Thôn 1"}},
        {"HoTen": "LÊ THỊ D", "SoDinhDanh": _VO, "NgaySinh": "05/06/1972", "GioiTinh": "Nữ",
         "NgayCap": "11/07/2021", "NoiCap": "Bộ Công an"},
    ]},
    {"name": "Don_NguoiSuDungDat", "value": [
        {"HoTen": "Nguyễn Văn A", "SoDinhDanh": _CHU_HO_SO},
        {"HoTen": "Lê Thị D", "SoDinhDanh": _VO},
    ]},
    {"name": "Don_NguoiLamDon", "value": "Bà Lê Thị D"},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
    {"name": "ChuHoSo_DiaChiDon", "value": _DIA_CHI_DON},
    {"name": "Don_DienThoai", "value": "0987000111"},
]

_UY_QUYEN_FACT = {"name": "NguoiDuocUyQuyen", "value": {
    "hoTen": "Trần Văn B", "soDinhDanh": _UY_QUYEN, "ngaySinh": "03/04/1990", "gioiTinh": "Nam",
    "ngayCapCccd": "05/05/2022", "dienThoai": "0912000222",
    "thuongTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 5"},
}}


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def _ctx(name, number):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}}


def test_tat_toggle_giu_hanh_vi_theo_tai_khoan():
    # Vợ đăng nhập nộp → nhân thân của vợ, địa chỉ/số chung của hộ ở mục 2 Đơn.
    fields, warnings = mapper.enrich(_FACTS + [_UY_QUYEN_FACT], _ctx("LÊ THỊ D", _VO))
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "05/06/1972"
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"
    assert values["CongDan_diaChi"] == "Thôn 1"
    assert values["CongDan_diDong"] == "0987000111"
    assert "CongDan_tenCongDan" not in values and "CongDan_soCmnd" not in values
    assert not warnings


def test_bat_toggle_co_uy_quyen_lay_ben_duoc_uy_quyen_va_canh_bao_lech():
    fields, warnings = mapper.enrich(
        _FACTS + [_UY_QUYEN_FACT], {**_ctx("NGUYỄN VĂN A", _CHU_HO_SO), **_TO_KHAI}
    )
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "03/04/1990"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_ngayCapCmnd"] == "05/05/2022"
    assert values["CongDan_diaChi"] == "Tổ 5"
    # Bên được ủy quyền ngoài hộ → không lấy số chung của hộ trên Đơn.
    assert values["CongDan_diDong"] == "0912000222"
    assert values["CongDan_tenCongDan"] == "Trần Văn B"
    assert values["CongDan_soCmnd"] == _UY_QUYEN
    assert any("TỜ KHAI" in w and "bị chặn" in w for w in warnings)
    assert values["ChuHoSo_tenChuHoSo"] == "NGUYỄN VĂN A"


def test_bat_toggle_khong_uy_quyen_lay_nguoi_lam_don():
    fields, warnings = mapper.enrich(_FACTS, {**_ctx("LÊ THỊ D", _VO), **_TO_KHAI})
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "05/06/1972"
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"
    assert values["CongDan_ngayCapCmnd"] == "11/07/2021"
    # Vợ cùng đứng tên mục 1 → dùng địa chỉ/số chung ở mục 2 Đơn.
    assert values["CongDan_diaChi"] == "Thôn 1"
    assert values["CongDan_diDong"] == "0987000111"
    assert not any("bị chặn" in w for w in warnings)


def test_bat_toggle_khong_uy_quyen_khong_nguoi_lam_don_lay_chu_ho_so():
    facts = [f for f in _FACTS if f["name"] != "Don_NguoiLamDon"]
    fields, warnings = mapper.enrich(facts, _TO_KHAI)
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "01/02/1970"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_diaChi"] == "Thôn 1"
    assert values["CongDan_diDong"] == "0987000111"
    assert not any("Không xác định được NGƯỜI ĐANG ĐI NỘP" in w for w in warnings)


def test_bat_toggle_khong_ghep_nhan_than_nguoi_khac_so_va_nam_sinh_chi_co_nam():
    facts = [
        {"name": "NguoiDuocUyQuyen", "value": {
            "hoTen": "Trần Văn B", "soDinhDanh": _UY_QUYEN, "ngaySinh": "1990",
        }},
        {"name": "DanhSachCccd", "value": [
            {"HoTen": "TRẦN VĂN B", "SoDinhDanh": _NGUOI_KHAC, "NgaySinh": "09/09/1990",
             "DanToc": "Kinh", "NoiCuTru": {"tinh": "Lào Cai", "xa": "Bắc Lệnh", "diaChi": "Tổ 9"}},
        ]},
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "Trần Văn B", "SoDinhDanh": _UY_QUYEN, "NgayCap": "07/07/2021",
             "NoiCap": "Bộ Công an"},
        ]},
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
        {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
        {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
        {"name": "ChuHoSo_DiaChiDon", "value": _DIA_CHI_DON},
        {"name": "Don_DienThoai", "value": "0987000111"},
    ]
    fields, _ = mapper.enrich(facts, _TO_KHAI)
    values = _values(fields)

    # Chỉ có năm / không có của chính người đó → xoá ô cổng đổ từ tài khoản, không mượn người khác.
    assert values["CongDan_ngaySinhCongDan"] == "", "chỉ có năm thì xoá ô ngày sinh tài khoản"
    assert values["CongDan_danTocCongDan"] == ""
    assert values["CongDan_diaChi"] == ""
    assert values["CongDan_diDong"] == ""
    assert values["CongDan_ngayCapCmnd"] == "07/07/2021"


def test_bat_toggle_nguoi_lam_don_trung_ten_hai_so_thi_khong_ghep():
    facts = [
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "Phạm Văn E", "SoDinhDanh": _UY_QUYEN, "NgaySinh": "01/01/1980"},
            {"HoTen": "Phạm Văn E", "SoDinhDanh": _NGUOI_KHAC, "NgaySinh": "02/02/1985"},
        ]},
        {"name": "Don_NguoiLamDon", "value": "Phạm Văn E"},
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức"},
        {"name": "ChuHoSo_TenToChuc", "value": "Hợp tác xã Mẫu"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300000001"},
    ]
    fields, _ = mapper.enrich(facts, _TO_KHAI)
    values = _values(fields)

    # Không đoán được là ai trong hai người trùng tên → không số, không ngày sinh (xoá ô tài khoản).
    assert values["CongDan_tenCongDan"] == "Phạm Văn E"
    assert values["CongDan_soCmnd"] == ""
    assert values["CongDan_ngaySinhCongDan"] == ""
    assert values["CongDan_tenCoQuanToChuc"] == "HỢP TÁC XÃ MẪU"


def test_bat_toggle_chu_ho_so_to_chuc_khong_ai_thi_bo_trong():
    facts = [
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức"},
        {"name": "ChuHoSo_TenToChuc", "value": "Hợp tác xã Mẫu"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300000001"},
    ]
    fields, warnings = mapper.enrich(facts, _TO_KHAI)
    values = _values(fields)

    assert "CongDan_ngaySinhCongDan" not in values
    assert any("để trống nhân thân" in w for w in warnings)
    assert values["ChuHoSo_maDoiTuongNopHS"] == "DN"


def test_to_khai_ho_ten_can_cuoc_dung_dau_va_xoa_o_nhan_than_thieu():
    # Người làm đơn là vợ cùng đứng tên nhưng hồ sơ không có CCCD của vợ; tài khoản là người khác.
    facts = [f for f in _FACTS if f["name"] != "DanhSachCccd"] + [
        {"name": "DanhSachCccd", "value": [_FACTS[0]["value"][0]]},
    ]
    facts = [f for f in facts if f["name"] != "Don_DienThoai"]
    fields, warnings = mapper.enrich(facts, {**_ctx("HOÀNG VĂN TÀI KHOẢN", "001099000009"), **_TO_KHAI})
    values = _values(fields)
    names = [f["name"] for f in fields if f["name"].startswith("CongDan_")]

    assert names[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    assert values["CongDan_tenCongDan"] == "Lê Thị D"
    assert values["CongDan_soCmnd"] == _VO
    cleared = {f["name"] for f in fields if f.get("clear")}
    for name in ("CongDan_ngaySinhCongDan", "CongDan_danTocCongDan", "CongDan_ngayCapCmnd",
                 "CongDan_noiCapCmnd", "CongDan_diDong", "CongDan_email", "CongDan_fax"):
        assert name in cleared and values[name] == "", name
    # Không lẫn nhân thân của chồng (chủ hồ sơ).
    assert not {"01/02/1970", "10/06/2021", _CHU_HO_SO} & {
        v for n, v in values.items() if n.startswith("CongDan_")
    }
    # Vợ cùng đứng tên → địa chỉ chung của hộ ở mục 2 Đơn vẫn được dùng.
    assert values["CongDan_diaChi"] == "Thôn 1"
    assert any("Giới tính" in w for w in warnings)


def test_tai_khoan_khong_ghi_o_readonly_khong_xoa():
    fields, _ = mapper.enrich(_FACTS + [_UY_QUYEN_FACT], _ctx("TRẦN VĂN B", _UY_QUYEN))
    names = {f["name"] for f in fields}

    assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & names
    assert not any(f.get("clear") for f in fields)
    assert _values(fields)["CongDan_ngaySinhCongDan"] == "03/04/1990"


def test_dia_chi_don_ten_lech_cua_llm_van_duoc_nhan():
    """Qwen hay đặt tên Don_DiaChi / Don_DiaChiDon cho địa chỉ mục 2 của Đơn — không được mất địa chỉ."""
    from app.pipelines._shared.compact_agent.runner import validate
    from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process import schema

    dia_chi = {"quocGia": "Việt Nam", "tinh": "Lào Cai", "xa": "Xã Giả", "diaChi": "Thôn Giả"}
    for ten in ("Don_DiaChi", "Don_DiaChiDon"):
        raw = {"ChuHoSo_LoaiDoiTuong": "Cá nhân", "ChuHoSo_HoTen": "Nguyễn Văn Giả",
               "ChuHoSo_SoDinhDanh": "001099000001", ten: dia_chi,
               "Don_NguoiSuDungDat": [{"HoTen": "Nguyễn Văn Giả", "SoDinhDanh": "001099000001", "GioiTinh": "Nam"}],}
        fields = validate(raw, schema.ALLOWED, schema.COMPACT_COMP_BY_NAME, schema.ALIASES)
        out, _ = mapper.enrich(fields, {})
        values = {f["name"]: f["value"] for f in out}
        assert values.get("ChuHoSo_diaChiChuHoSo") == "Thôn Giả", ten
    # Tên chuẩn có mặt thì thắng tên lệch.
    raw = {"ChuHoSo_LoaiDoiTuong": "Cá nhân", "ChuHoSo_HoTen": "Nguyễn Văn Giả",
           "ChuHoSo_SoDinhDanh": "001099000001", "Don_NguoiSuDungDat": [{"HoTen": "Nguyễn Văn Giả", "SoDinhDanh": "001099000001", "GioiTinh": "Nam"}],
           "ChuHoSo_DiaChiDon": dia_chi, "Don_DiaChi": {**dia_chi, "diaChi": "Thôn Khác"}}
    out, _ = mapper.enrich(validate(raw, schema.ALLOWED, schema.COMPACT_COMP_BY_NAME, schema.ALIASES), {})
    assert {f["name"]: f["value"] for f in out}.get("ChuHoSo_diaChiChuHoSo") == "Thôn Giả"
