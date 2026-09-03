"""Unit tests cho mapper mai táng phí dân công hỏa tuyến (hai vai Chủ hồ sơ / Người nộp)."""

from app.pipelines.mai_tang_dan_cong.process import mapper

_CHU_HO_SO = {
    "ChuHoSo_HoTen": "NGUYỄN VĂN THÀNH",
    "ChuHoSo_SoDinhDanh": "024064010233",
    "ChuHoSo_NgaySinh": "22/02/1964",
    "ChuHoSo_GioiTinh": "Nam",
    "ChuHoSo_NgayCap": "04/06/2024",
    "ChuHoSo_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "ChuHoSo_ThuongTru": {"tinh": "Bắc Ninh", "xa": "Hiệp Hòa", "diaChi": "Thôn số 1"},
    "ChuHoSo_DienThoai": "0366752439",
    "ChuHoSo_QuanHeNguoiTuTran": "Con đẻ",
}


def _flds(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _run(vals: dict, ctx: dict | None = None):
    fields, warnings = mapper.enrich(_flds(vals), ctx or {})
    return {f["name"]: f["value"] for f in fields}, warnings


def test_tu_nop_owner_matches_ui_ticks_and_fills_phan_i():
    d, w = _run(
        _CHU_HO_SO,
        {"formContext": {"applicantFullname": "NGUYỄN VĂN THÀNH", "applicantIdentityNumber": "024064010233"}},
    )
    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[fullname]"] == "NGUYỄN VĂN THÀNH"
    assert d["data[birthday]"] == "22/02/1964"
    assert d["data[phoneNumber]"] == "0366752439"
    assert d["data[province]"] == "Tỉnh Bắc Ninh"
    assert d["data[district]"] == "Hiệp Hòa"
    # Tự nộp: cổng tự đổ Phần II → KHÔNG phát owner_*.
    assert "data[ownerFullname]" not in d
    assert not w


def test_nop_thay_phan_i_la_nguoi_nop_ui_phan_ii_la_chu_ho_so():
    d, w = _run(
        {
            **_CHU_HO_SO,
            "NguoiNop_HoTen": "VŨ ĐÌNH THIẾT",
            "NguoiNop_SoDinhDanh": "040203015844",
            "NguoiNop_NgaySinh": "26/04/2003",
            "NguoiNop_GioiTinh": "Nam",
            "NguoiNop_NgayCap": "02/07/2021",
            "NguoiNop_ThuongTru": {"tinh": "Nghệ An", "xa": "Quỳ Hợp", "diaChi": "Xóm Long Thành"},
        },
        {"formContext": {"applicantFullname": "VŨ ĐÌNH THIẾT", "applicantIdentityNumber": "040203015844"}},
    )
    assert d["data[isOwnerDossierCheck]"] is False
    # Phần I = người nộp = người UI truyền lên.
    assert d["data[fullname]"] == "VŨ ĐÌNH THIẾT"
    assert d["data[identityNumber]"] == "040203015844"
    assert d["data[birthday]"] == "26/04/2003"
    assert d["data[province]"] == "Tỉnh Nghệ An"
    # Phần II = chủ hồ sơ (người đứng khai). KHÔNG lẫn dữ liệu hai người.
    assert d["data[ownerFullname]"] == "NGUYỄN VĂN THÀNH"
    assert d["data[ownerBirthday]"] == "22/02/1964"
    assert d["data[ownerIdentityNumber]"] == "024064010233"
    assert d["data[ownerProvince]"] == "Tỉnh Bắc Ninh"
    assert not w


def test_nop_thay_khong_co_cccd_nguoi_nop_van_giu_chu_ho_so():
    d, w = _run(
        _CHU_HO_SO,
        {"formContext": {"applicantFullname": "VŨ ĐÌNH THIẾT", "applicantIdentityNumber": "040203015844"}},
    )
    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[fullname]"] == "VŨ ĐÌNH THIẾT"
    assert d["data[identityNumber]"] == "040203015844"
    assert d["data[ownerFullname]"] == "NGUYỄN VĂN THÀNH"
    assert w and "cccd" in w[0].lower() and "nộp thay" in w[0].lower()


def test_khong_co_ui_context_mac_dinh_tu_nop():
    d, w = _run(_CHU_HO_SO, {})
    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[fullname]"] == "NGUYỄN VĂN THÀNH"
    assert "data[ownerFullname]" not in d
    assert not w


def test_khong_doc_duoc_chu_ho_so_tra_canh_bao_khong_crash():
    d, w = _run({"NguoiNop_HoTen": "X"}, {})
    assert d == {}
    assert w and "chủ hồ sơ" in w[0].lower()


def test_dia_chi_chuoi_duoc_tach_thanh_area():
    d, w = _run(
        {
            "ChuHoSo_HoTen": "NGUYỄN VĂN THÀNH",
            "ChuHoSo_SoDinhDanh": "024064010233",
            "ChuHoSo_ThuongTru": "Thôn số 1, xã Hiệp Hòa, tỉnh Bắc Ninh",
        },
        {},
    )
    assert d["data[province]"] == "Tỉnh Bắc Ninh"
    assert d["data[district]"] == "Hiệp Hòa"
    assert d["data[address]"] == "Thôn số 1"
