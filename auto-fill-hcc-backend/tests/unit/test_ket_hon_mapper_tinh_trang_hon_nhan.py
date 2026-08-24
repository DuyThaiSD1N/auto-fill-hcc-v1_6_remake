"""Kết hôn lần 1 → tình trạng hôn nhân "Hiện tại chưa đăng ký kết hôn với ai"."""

from app.pipelines.ket_hon.process import mapper

_CHUA_DANG_KY = "Hiện tại chưa đăng ký kết hôn với ai"


def _enrich(**extra):
    fields = [
        {"name": "CccdNam_HoTen", "value": "NGƯỜI NAM"},
        {"name": "CccdNam_SoDinhDanh", "value": "079000000001"},
    ]
    fields += [{"name": k, "value": v} for k, v in extra.items()]
    return {f["name"]: f for f in mapper.enrich(fields)}


def test_ket_hon_lan_1_suy_ra_chua_dang_ky_ket_hon():
    out = _enrich(CccdNam_SoLanKetHon="1")

    assert out["SoLanKetHon_BenNam"]["value"] == "1"
    assert out["LoaiTinhTrangHonNhan_BenNam"]["value"] == _CHUA_DANG_KY
    # Suy ra chắc chắn từ số lần kết hôn → không tô vàng.
    assert "default" not in out["LoaiTinhTrangHonNhan_BenNam"]


def test_ket_hon_lan_2_khong_suy_ra_tinh_trang():
    out = _enrich(CccdNam_SoLanKetHon="2")

    assert out["SoLanKetHon_BenNam"]["value"] == "2"
    assert "LoaiTinhTrangHonNhan_BenNam" not in out


def test_tinh_trang_ghi_ro_thang_so_lan_ket_hon():
    # Tờ khai ghi lần 1 nhưng có tình trạng rõ ràng → giữ nguyên tình trạng của tờ khai.
    out = _enrich(CccdNam_SoLanKetHon="1", CccdNam_TinhTrangHonNhan="3")

    assert out["SoLanKetHon_BenNam"]["value"] == "1"
    assert out["LoaiTinhTrangHonNhan_BenNam"]["value"].startswith("Đã đăng ký kết hôn")
