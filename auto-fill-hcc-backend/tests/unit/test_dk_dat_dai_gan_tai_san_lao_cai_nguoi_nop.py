"""[Lào Cai] 1.115688 — hai chế độ xác định NGƯỜI NỘP.

Mặc định (toggle tắt) giữ nguyên hành vi theo tài khoản. Bật "Lấy người nộp theo tờ khai" thì người nộp là chủ hồ
sơ CÁ NHÂN; schema không tách vai bên nhận ủy quyền nên hồ sơ có Giấy ủy quyền/chủ hồ sơ tổ chức → để trống
nhân thân khối người nộp + cảnh báo. `enrich` giữ hợp đồng cũ (chỉ trả field), cảnh báo ở
`enrich_with_warnings`.
"""

from app.pipelines.dk_dat_dai_gan_tai_san_lao_cai.process import mapper
from app.pipelines._shared.lao_cai_nguoi_nop import O_NHAN_THAN_XOA_DUOC

_CHU_HO_SO = "001099000001"
_NGUOI_NOP = "001199000002"
_NGUOI_KHAC = "001088000003"

_CARD_A = {
    "HoTen": "NGUYỄN VĂN A", "SoDinhDanh": _CHU_HO_SO, "NgaySinh": "02/03/1985", "GioiTinh": "Nam",
    "DanToc": "Kinh", "NgayCap": "10/06/2021", "NoiCap": "Bộ Công an",
    "NoiCuTru": {"tinh": "Lào Cai", "xa": "Sa Pa", "diaChi": "Tổ 1"},
}
_CARD_C = {
    "HoTen": "LÊ VĂN C", "SoDinhDanh": _NGUOI_KHAC, "NgaySinh": "15/08/1970", "GioiTinh": "Nam",
    "DanToc": "Tày", "NgayCap": "20/11/2022", "NoiCap": "Bộ Công an",
    "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 9"},
}

_CA_NHAN = [
    {"name": "DanhSachCccd", "value": [_CARD_A, _CARD_C]},
    {"name": "NguoiTrongGiayTo", "value": [
        {"HoTen": "Nguyễn Văn A", "SoDinhDanh": _CHU_HO_SO, "NgaySinh": "1985"},
    ]},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
    {"name": "ChuHoSo_NgaySinh", "value": "1985"},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Sa Pa", "diaChi": "Tổ 1"}},
    {"name": "Don_DienThoai", "value": "0912000001"},
]

_TO_KHAI = {"submitterMode": "owner_as_submitter"}


def _ctx(name, number):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}}


def _values(fields):
    return {f["name"]: f["value"] for f in fields}


def test_toggle_tat_giu_hanh_vi_theo_tai_khoan():
    options = _ctx("LÊ VĂN C", _NGUOI_KHAC)
    fields = mapper.enrich(_CA_NHAN, options)
    values = _values(fields)

    # Hợp đồng cũ của runner: chỉ trả danh sách field.
    assert isinstance(fields, list)
    assert values["CongDan_ngaySinhCongDan"] == "15/08/1970"
    assert values["CongDan_danTocCongDan"] == "Tày"
    assert values["CongDan_diaChi"] == "Tổ 9"
    # Người đăng nhập không phải chủ hồ sơ → không chép Di động trên Đơn.
    assert "CongDan_diDong" not in values
    assert mapper.enrich_with_warnings(_CA_NHAN, options) == (fields, [])


def test_to_khai_khong_uy_quyen_lay_chu_ho_so_va_canh_bao_lech_tai_khoan():
    fields, warnings = mapper.enrich_with_warnings(_CA_NHAN, {**_ctx("LÊ VĂN C", _NGUOI_KHAC), **_TO_KHAI})
    values = _values(fields)

    assert values["CongDan_ngaySinhCongDan"] == "02/03/1985"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_danTocCongDan"] == "Kinh"
    assert values["CongDan_ngayCapCmnd"] == "10/06/2021"
    assert values["CongDan_diaChi"] == "Tổ 1"
    assert values["CongDan_diDong"] == "0912000001"
    assert values["CongDan_tenCongDan"] == "NGUYỄN VĂN A"
    assert values["CongDan_soCmnd"] == _CHU_HO_SO
    assert values["ChuHoSo_tenChuHoSo"] == "NGUYỄN VĂN A"
    assert any("TỜ KHAI" in w and "bị chặn" in w for w in warnings)
    # enrich (runner) vẫn chỉ trả field.
    assert mapper.enrich(_CA_NHAN, {**_ctx("LÊ VĂN C", _NGUOI_KHAC), **_TO_KHAI}) == fields


def test_to_khai_trung_tai_khoan_hoac_khong_co_moc_thi_khong_canh_bao():
    _, warnings = mapper.enrich_with_warnings(_CA_NHAN, {**_ctx("NGUYỄN VĂN A", _CHU_HO_SO), **_TO_KHAI})
    assert warnings == []
    _, warnings = mapper.enrich_with_warnings(_CA_NHAN, _TO_KHAI)
    assert warnings == []


def test_to_khai_co_giay_uy_quyen_thi_bo_trong_khong_doan_ben_nhan():
    facts = [f for f in _CA_NHAN if f["name"] != "NguoiTrongGiayTo"] + [
        {"name": "ChuHoSo_DiaChiUyQuyen", "value": {"tinh": "Lào Cai", "xa": "Sa Pa", "diaChi": "Tổ 1"}},
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "Nguyễn Văn A", "SoDinhDanh": _CHU_HO_SO},
            {"HoTen": "Trần Thị B", "SoDinhDanh": _NGUOI_NOP, "NgaySinh": "05/06/1990"},
        ]},
    ]
    fields, warnings = mapper.enrich_with_warnings(facts, {**_ctx("TRẦN THỊ B", _NGUOI_NOP), **_TO_KHAI})
    values = _values(fields)

    assert not [name for name in values if name.startswith("CongDan_")]
    assert any("Giấy ủy quyền" in w and "để trống" in w for w in warnings)
    assert values["ChuHoSo_tenChuHoSo"] == "NGUYỄN VĂN A"


def test_to_khai_chi_gop_nhan_than_cung_so_dinh_danh():
    trung_ten_khac_so = dict(_CARD_C, HoTen="NGUYỄN VĂN A")
    facts = [
        {"name": "DanhSachCccd", "value": [trung_ten_khac_so]},
        {"name": "NguoiTrongGiayTo", "value": [
            {"HoTen": "Nguyễn Văn A", "SoDinhDanh": _CHU_HO_SO, "NgaySinh": "1985",
             "NgayCap": "10/06/2021", "NoiCap": "Bộ Công an"},
        ]},
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
        {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
        {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
        {"name": "ChuHoSo_NgaySinh", "value": "1985"},
    ]
    values = _values(mapper.enrich(facts, _TO_KHAI))

    # Ngày cấp/nơi cấp từ giấy tờ ghi CÙNG số định danh.
    assert values["CongDan_ngayCapCmnd"] == "10/06/2021"
    assert values["CongDan_noiCapCmnd"] == "Bộ Công an"
    # Thẻ trùng họ tên nhưng KHÁC số là người khác → không lấy ngày sinh/dân tộc/địa chỉ của thẻ đó; ô cổng
    # đổ từ tài khoản thì XOÁ.
    for name in ("CongDan_ngaySinhCongDan", "CongDan_danTocCongDan", "CongDan_diaChi"):
        assert values[name] == "", name
    assert "CongDan_maPhuongXa" not in values


def test_to_khai_chu_ho_so_to_chuc_thi_bo_trong_nhan_than_nhung_giu_ten_to_chuc():
    facts = [
        {"name": "DanhSachCccd", "value": [_CARD_C]},
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Doanh nghiệp"},
        {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Thử Nghiệm"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300000001"},
        {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Sa Pa", "diaChi": "Tổ 1"}},
    ]
    fields, warnings = mapper.enrich_with_warnings(facts, _TO_KHAI)
    values = _values(fields)

    assert values["CongDan_tenCoQuanToChuc"] == "Công ty TNHH Thử Nghiệm"
    assert values["CongDan_maSoThueNguoiNop"] == "5300000001"
    assert "CongDan_ngaySinhCongDan" not in values
    assert "CongDan_danTocCongDan" not in values
    assert any("TỔ CHỨC" in w for w in warnings)
    assert values["ChuHoSo_maDoiTuongNopHS"] == "DN"


def _congdan_names(fields):
    return [f["name"] for f in fields if f["name"].startswith("CongDan_")]


def test_to_khai_ho_ten_can_cuoc_dung_dau_khoi_va_xoa_o_tai_khoan_ho_so_khong_co():
    """Chỉ có thẻ của tài khoản (người khác) → nhân thân/địa chỉ/liên hệ chủ hồ sơ thiếu thì xoá, không mượn."""
    facts = [{"name": "DanhSachCccd", "value": [_CARD_C]}] + [
        f for f in _CA_NHAN if f["name"] not in ("DanhSachCccd", "ChuHoSo_DiaChiDon", "Don_DienThoai")
    ]
    fields, _ = mapper.enrich_with_warnings(facts, {**_ctx("LÊ VĂN C", _NGUOI_KHAC), **_TO_KHAI})

    assert _congdan_names(fields)[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    values = _values(fields)
    assert values["CongDan_tenCongDan"] == "NGUYỄN VĂN A"
    assert values["CongDan_soCmnd"] == _CHU_HO_SO
    cleared = {f["name"] for f in fields if f.get("clear")}
    # Mọi form Lào Cai chung bộ ô CongDan_*: hồ sơ không có mục nào thì xoá đủ ô tài khoản đã đổ.
    assert cleared == set(O_NHAN_THAN_XOA_DUOC)
    assert all(f["value"] == "" for f in fields if f.get("clear"))
    assert not {"15/08/1970", "Tày", "20/11/2022", "Tổ 9", _NGUOI_KHAC} & set(values.values())


def test_to_khai_khong_so_dinh_danh_thi_xoa_o_can_cuoc_ngay_sau_ho_ten():
    facts = [f for f in _CA_NHAN if f["name"] not in ("ChuHoSo_SoDinhDanh", "DanhSachCccd", "NguoiTrongGiayTo")]
    fields, _ = mapper.enrich_with_warnings(facts, _TO_KHAI)

    assert _congdan_names(fields)[:2] == ["CongDan_tenCongDan", "CongDan_soCmnd"]
    so_cmnd = next(f for f in fields if f["name"] == "CongDan_soCmnd")
    assert so_cmnd["value"] == "" and so_cmnd.get("clear") is True


def test_tai_khoan_khong_ghi_o_readonly_va_khong_xoa_o_nao():
    for options in (_ctx("LÊ VĂN C", _NGUOI_KHAC), _ctx("NGUYỄN VĂN A", _CHU_HO_SO), {}):
        fields = mapper.enrich(_CA_NHAN, options)
        assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & set(_congdan_names(fields))
        assert not any(f.get("clear") for f in fields)


def test_to_khai_khong_doc_duoc_ho_ten_thi_khong_ghi_o_readonly_va_khong_xoa():
    """Chưa biết người nộp là ai (chỉ có số, không có họ tên) → không đổi riêng Số Căn cước, không xoá gì."""
    facts = [f for f in _CA_NHAN if f["name"] not in ("ChuHoSo_HoTen", "DanhSachCccd", "NguoiTrongGiayTo")]
    fields = mapper.enrich(facts, _TO_KHAI)
    assert not {"CongDan_tenCongDan", "CongDan_soCmnd"} & set(_congdan_names(fields))
    assert not any(f.get("clear") for f in fields)
