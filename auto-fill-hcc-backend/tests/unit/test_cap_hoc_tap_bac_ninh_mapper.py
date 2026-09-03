"""Unit test mapper hỗ trợ chi phí học tập Bắc Ninh: HocSinh_* → doiTuongKhac* (khối được ủy quyền)."""

from app.pipelines.cap_hoc_tap_bac_ninh.process import mapper


def _flds(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _run(vals: dict):
    fields, warnings = mapper.enrich(_flds(vals), {"purpose": "authorized_person"})
    return {f["name"]: f for f in fields}, warnings


_HSSV = {
    "HocSinh_HoTen": "NGUYỄN VĂN HIỆP",
    "HocSinh_GioiTinh": "Nam",
    "HocSinh_SoDinhDanh": "024209011449",
    "HocSinh_NgayCap": "06/12/2023",
    "HocSinh_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "HocSinh_NgaySinh": "30/10/2009",
    "HocSinh_SoDienThoai": "0358487622",
    "HocSinh_ThuongTru": {"tinh": "Bắc Ninh", "xa": "Phường Bắc Giang", "diaChi": "Số nhà 10, ngõ 77, Tổ dân phố Hà Vị"},
}


def test_map_day_du_khoi_uy_quyen_la_hoc_sinh():
    d, w = _run(_HSSV)
    assert not w
    assert d["doiTuongKhachoTen"]["value"] == "NGUYỄN VĂN HIỆP"
    assert d["doiTuongKhacsoDinhDanh"]["value"] == "024209011449"
    assert d["doiTuongKhacngaySinh"]["value"] == "30/10/2009"
    assert d["doiTuongKhacngayCap"]["value"] == "06/12/2023"
    assert d["doiTuongKhacsoDienThoai"]["value"] == "0358487622"
    # Giới tính là select native, option đầy đủ.
    assert d["doiTuongKhacgioiTinhId"]["value"] == "Giới tính Nam"
    assert d["doiTuongKhacgioiTinhId"]["comp"] == "bn-select"
    # Địa chỉ tách 3 cấp; tỉnh/xã là bn-select (select2), chi tiết là input.
    assert d["doiTuongKhactinhThanhId"]["value"] == "Bắc Ninh"
    assert d["doiTuongKhactinhThanhId"]["comp"] == "bn-select"
    assert d["doiTuongKhacphuongXaId"]["value"] == "Phường Bắc Giang"
    assert d["doiTuongKhacdiaChiChiTiet"]["value"].startswith("Số nhà 10")
    assert d["doiTuongKhacdiaChiChiTiet"]["comp"] == "bn-input"


def test_gioi_tinh_nu_map_dung_option():
    d, _ = _run({**_HSSV, "HocSinh_GioiTinh": "Nữ"})
    assert d["doiTuongKhacgioiTinhId"]["value"] == "Giới tính Nữ"


def test_thieu_ho_ten_hoac_cccd_tra_canh_bao_khong_crash():
    d, w = _run({"HocSinh_HoTen": "NGUYỄN VĂN HIỆP"})
    assert "doiTuongKhachoTen" in d
    assert w and "định danh" in w[0].lower()

    d2, w2 = _run({"HocSinh_SoDinhDanh": "024209011449"})
    assert w2 and ("họ tên" in w2[0].lower() or "sinh viên" in w2[0].lower())


def test_email_trong_khong_phat():
    d, _ = _run({**_HSSV, "HocSinh_Email": ""})
    assert "doiTuongKhacemail" not in d
