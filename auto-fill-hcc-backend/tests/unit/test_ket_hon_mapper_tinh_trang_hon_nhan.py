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


def test_ket_hon_tich_dang_ky_lan_dau_sau_khi_dien_thong_tin():
    out = mapper.enrich([
        {"name": "CccdNam_HoTen", "value": "NGƯỜI NAM"},
        {"name": "CccdNam_SoDinhDanh", "value": "079000000001"},
        {"name": "CccdNu_HoTen", "value": "NGƯỜI NỮ"},
        {"name": "CccdNu_SoDinhDanh", "value": "079000000002"},
    ])
    names = [f["name"] for f in out]
    loai = next(f for f in out if f["name"] == "loaiDangKy")

    assert loai["value"] == "1"
    assert loai["comp"] == "x-radio"
    # Suy diễn (không đọc từ giấy tờ) → FE tô vàng để người dân tự rà.
    assert loai["default"] is True
    # Tích sau khi đã điền xong thông tin hai bên.
    assert names.index("loaiDangKy") > names.index("HoTenBenNam")
    assert names.index("loaiDangKy") > names.index("HoTenBenNu")


def test_ket_hon_khong_tich_loai_dang_ky_khi_khong_co_du_lieu():
    assert mapper.enrich([]) == []


def _base_fields():
    return [
        {"name": "CccdNam_HoTen", "value": "NGƯỜI NAM"},
        {"name": "CccdNam_SoDinhDanh", "value": "079000000001"},
    ]


def test_loai_dang_ky_uu_tien_to_khai_lan_dau():
    out = {f["name"]: f for f in mapper.enrich(
        _base_fields() + [{"name": "ToKhai_LoaiDangKy", "value": "Đăng ký lần đầu"}]
    )}

    # Đọc được từ tờ khai → dùng mã id chắc chắn khớp radio và KHÔNG tô vàng.
    assert out["loaiDangKy"]["value"] == "1"
    assert "default" not in out["loaiDangKy"]


def test_loai_dang_ky_uu_tien_to_khai_nhan_khac():
    out = {f["name"]: f for f in mapper.enrich(
        _base_fields() + [{"name": "ToKhai_LoaiDangKy", "value": "Đăng ký lại"}]
    )}

    assert out["loaiDangKy"]["value"] == "Đăng ký lại"
    assert "default" not in out["loaiDangKy"]


def test_loai_dang_ky_fallback_khi_to_khai_khong_ghi():
    out = {f["name"]: f for f in mapper.enrich(_base_fields())}

    assert out["loaiDangKy"]["value"] == "1"
    assert out["loaiDangKy"]["default"] is True
