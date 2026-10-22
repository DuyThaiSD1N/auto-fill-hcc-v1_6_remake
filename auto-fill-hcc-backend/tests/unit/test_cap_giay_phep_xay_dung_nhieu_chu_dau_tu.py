"""GPXD: đơn đứng tên nhiều chủ đầu tư → người đăng nhập VNeID là người nộp kiêm chủ hộ. Dữ liệu giả."""

from app.pipelines.cap_giay_phep_xay_dung.process import mapper

_VALUES = {
    "Applicant_HoTen": "TRẦN THỊ B",               # người ký đơn
    "Applicant_SoDinhDanh": "001175000002",
    "Applicant_NgaySinh": "01/02/1975",
    "Applicant_GioiTinh": "Nữ",
    "Applicant_DienThoai": "0900000001",
    "ChuDauTu_Loai": "Chủ hộ",
    "ChuHo_HoTen": "NGUYỄN VĂN A",
    "ChuHo_SoDinhDanh": "010072000001",
    "ChuHo_DienThoai": "0900000001",
    "ChuDauTu_DanhSach": [{"hoTen": "Nguyễn Văn A", "soDinhDanh": "010072000001"},
                          {"hoTen": "Trần Thị B", "soDinhDanh": "001175000002"}],
}


def _run(ctx):
    out, _ = mapper.enrich([{"name": k, "value": v} for k, v in _VALUES.items()],
                           {"formContext": ctx} if ctx else {})
    return {(f["name"], f.get("occurrence")): f["value"] for f in out}


def test_dang_nhap_la_chu_ho_dung_dau():
    d = _run({"applicantFullname": "Nguyễn Văn A", "applicantIdentityNumber": "010072000001"})
    assert d[("data[fullname]", None)] == "NGUYỄN VĂN A" or d[("data[fullname]", None)] == "Nguyễn Văn A"
    assert d[("data[identityNumber]", None)] == "010072000001"
    assert d[("data[soDinhDanhChuHo]", None)] == "010072000001"
    # Ngày sinh/giới tính của người ký đơn (người khác) không được gán sang.
    assert d.get(("data[birthday]", None)) in (None, "")
    assert d.get(("data[gender]", None)) != "Nữ"


def test_dang_nhap_la_nguoi_ky_don_thi_chu_ho_cung_la_nguoi_do():
    d = _run({"applicantFullname": "Trần Thị B", "applicantIdentityNumber": "001175000002"})
    assert d[("data[fullname]", None)] == "TRẦN THỊ B"
    assert d[("data[tenChuHo]", None)] == "Trần Thị B"
    assert d[("data[soDinhDanhChuHo]", None)] == "001175000002"
    assert d[("data[birthday]", None)] == "01/02/1975"


def test_khong_co_tai_khoan_hoac_khong_khop_giu_cach_cu():
    for ctx in (None, {"applicantFullname": "Lê Văn C", "applicantIdentityNumber": "001099000009"}):
        d = _run(ctx)
        assert d[("data[tenChuHo]", None)] == "NGUYỄN VĂN A"
