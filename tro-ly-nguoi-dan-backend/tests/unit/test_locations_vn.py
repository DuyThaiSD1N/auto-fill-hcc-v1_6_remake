"""Danh mục tỉnh/xã quốc gia (vn_provinces_wards.json) — đủ 34 tỉnh, slug cũ
tương thích, kiểu bỏ dấu đã chuẩn hoá về "òa/ụy" khớp option cổng DVC."""
from app.locations.router import PROVINCES, _WARDS, _modern_tone, province_by_slug


def test_du_34_tinh_va_3321_xa():
    assert len(PROVINCES) == 34
    assert sum(len(w["communes"]) for w in _WARDS.values()) == 3321


def test_slug_cu_van_tra_duoc():
    # Slug thời danh sách 9 tỉnh nhập tay — conversation cũ lưu province_slug dạng này.
    for slug, text in [
        ("bacninh", "Tỉnh Bắc Ninh"),
        ("danang", "Thành phố Đà Nẵng"),
        ("khanhhoa", "Tỉnh Khánh Hòa"),
        ("laichau", "Tỉnh Lai Châu"),
        ("hanoi", "Thành phố Hà Nội"),
    ]:
        p = province_by_slug(slug)
        assert p and p["text"] == text, f"{slug} → {p}"


def test_chuan_hoa_dau_kieu_moi():
    # Cuối âm tiết: đổi; có phụ âm cuối hoặc sau q: giữ nguyên.
    assert _modern_tone("Tỉnh Khánh Hoà") == "Tỉnh Khánh Hòa"
    assert _modern_tone("Xã Thuỵ Anh") == "Xã Thụy Anh"
    assert _modern_tone("Xã Hoàng Vân") == "Xã Hoàng Vân"
    assert _modern_tone("Xã Quỳnh Lưu") == "Xã Quỳnh Lưu"
    assert _modern_tone("Xã Lê Quý Đôn") == "Xã Lê Quý Đôn"
    # Toàn bộ danh mục không còn sót kiểu cũ ở cuối âm tiết.
    for w in _WARDS.values():
        for name in w["communes"]:
            assert _modern_tone(name) == name


def test_wards_giu_nguyen_shape_va_noi_dung():
    bn = _WARDS["bacninh"]
    assert bn["province"] == "Tỉnh Bắc Ninh"
    assert len(bn["communes"]) == 99
    assert "Phường Kinh Bắc" in bn["communes"]
    # Đơn vị đặc thù sau sáp nhập vẫn có mặt.
    assert "Đặc khu Hoàng Sa" in _WARDS["danang"]["communes"]
