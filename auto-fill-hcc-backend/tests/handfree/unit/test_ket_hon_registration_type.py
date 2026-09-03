"""Loại đăng ký kết hôn chỉ được điền khi tờ khai cung cấp rõ ràng."""

from app.pipelines.ket_hon.process.mapper import enrich


def _mapped(*fields: tuple[str, object]) -> dict[str, dict]:
    return {
        item["name"]: item
        for item in enrich([{"name": name, "value": value} for name, value in fields])
    }


def test_khong_mac_dinh_dang_ky_lan_dau():
    out = _mapped(("CccdNam_HoTen", "NGƯỜI NAM"))

    assert "loaiDangKy" not in out


def test_to_khai_ghi_ro_dang_ky_lan_dau_thi_van_dien_khong_default():
    out = _mapped(
        ("CccdNam_HoTen", "NGƯỜI NAM"),
        ("ToKhai_LoaiDangKy", "Đăng ký lần đầu"),
    )

    assert out["loaiDangKy"]["value"] == "1"
    assert "default" not in out["loaiDangKy"]
