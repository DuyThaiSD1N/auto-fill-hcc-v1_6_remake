"""Unit test mapper "[Bắc Ninh] Điền thông tin tài khoản" — điền hồ sơ tài khoản từ CCCD.

Dữ liệu GIẢ. Kiểm tra: remap tỉnh/xã sau sáp nhập, default (loại định danh/quốc tịch/nơi cấp CCCD gắn chip),
soDinhDanh=soCCCD & ngayCap=ngayCapCCCD, nơi ở hiện tại CHỈ khi có nguồn (không copy thường trú), giới tính.
"""

from app.pipelines.dien_thong_tin_tai_khoan_bac_ninh.process import mapper


def _run(vals: dict) -> dict:
    fields = [{"name": k, "value": v} for k, v in vals.items()]
    return {f["name"]: f for f in mapper.enrich(fields)}


_BASE = {
    "HoTen": "NGUYỄN VĂN A",
    "GioiTinh": "Nam",
    "NgaySinh": "01/01/1990",
    "SoCCCD": "012345678901",
    "NgayCapCCCD": "05/03/2021",
    "NoiCapCCCD": "",                       # trống → default CCCD gắn chip
    "QueQuan": "Xã Tân Mỹ, thành phố Bắc Giang, tỉnh Bắc Giang",
    "ThuongTru": {"tinh": "Bắc Giang", "xa": "Xã Tân Mỹ", "diaChi": "Thôn Đồng Lý"},
}


def test_dien_co_ban_va_default():
    d = _run(_BASE)
    assert d["hoTen"]["value"] == "NGUYỄN VĂN A"
    assert d["gioiTinhId"]["value"] == "Giới tính Nam" and d["gioiTinhId"]["comp"] == "bn-select"
    assert d["loaiDinhDanh"]["value"] == "Căn cước công dân"      # default
    assert d["quocGiaId"]["value"] == "Việt Nam"                  # default
    # soDinhDanh (ô chính) = soCCCD (khối giấy tờ); ngayCap = ngayCapCCCD.
    assert d["soDinhDanh"]["value"] == "012345678901"
    assert d["soCCCD"]["value"] == "012345678901"
    assert d["ngayCap"]["value"] == "05/03/2021"
    assert d["ngayCapCCCD"]["value"] == "05/03/2021"
    assert d["ngaySinh"]["value"] == "01/01/1990"
    # CCCD gắn chip 12 số + OCR không đọc nơi cấp → default Cục Cảnh sát QLHC về TTXH.
    assert d["noiCapCCCD"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert d["queQuan"]["value"].startswith("Xã Tân Mỹ")


def test_remap_thuong_tru_sau_sap_nhap():
    d = _run(_BASE)
    # Bắc Giang / Xã Tân Mỹ (cũ) → Bắc Ninh / Phường Đa Mai (sau sáp nhập) để khớp SELECT.
    assert d["thuongTrutinhThanhId"]["value"] == "Bắc Ninh"
    assert d["thuongTruphuongXaId"]["value"] == "Phường Đa Mai"
    assert d["thuongTru"]["value"] == "Thôn Đồng Lý"


def test_khong_co_dia_chi_hien_tai_thi_bo_trong():
    d = _run(_BASE)
    assert "diaChiHienTaitinhThanhId" not in d
    assert "diaChiHienTai" not in d


def test_co_dia_chi_hien_tai_rieng_thi_dien():
    d = _run({**_BASE, "DiaChiHienTai": {"tinh": "Hà Nội", "xa": "Phường Láng Thượng", "diaChi": "Số 5 ngõ 1"}})
    assert d["diaChiHienTaitinhThanhId"]["value"] == "Hà Nội"
    assert d["diaChiHienTai"]["value"] == "Số 5 ngõ 1"
    # Thường trú vẫn giữ nguyên (không bị đè bởi hiện tại).
    assert d["thuongTruphuongXaId"]["value"] == "Phường Đa Mai"


def test_noi_cap_that_thi_giu():
    d = _run({**_BASE, "NoiCapCCCD": "Bộ Công an"})
    assert d["noiCapCCCD"]["value"] == "Bộ Công an"


def test_gioi_tinh_nu():
    d = _run({**_BASE, "GioiTinh": "Nữ"})
    assert d["gioiTinhId"]["value"] == "Giới tính Nữ"
