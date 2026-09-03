"""Unit test: 2 biến thể sửa chữa GPXD ép đúng nhánh element công trình qua constructionVariant."""

from app.pipelines.cap_giay_phep_xay_dung.process.mapper import _construction_branch, enrich


def _flds(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _names(vals: dict, options: dict) -> set[str]:
    fields, _ = enrich(_flds(vals), options)
    return {f["name"] for f in fields}


def test_construction_variant_ep_dung_nhanh():
    # option biến thể được ưu tiên TUYỆT ĐỐI, kể cả khi giấy tờ nói khác.
    assert _construction_branch({"CongTrinh_Nhanh": "khong_theo_tuyen"}, {"constructionVariant": "nha_o_rieng_le"}) == "nha_o_rieng_le"
    assert _construction_branch({"CongTrinh_Nhanh": "nha_o_rieng_le"}, {"constructionVariant": "khong_theo_tuyen"}) == "khong_theo_tuyen"


def test_khong_co_variant_van_auto_detect_nhu_cu():
    # Không truyền biến thể → giữ auto-detect từ giấy tờ (thủ tục cấp mới không bị ảnh hưởng).
    assert _construction_branch({"CongTrinh_Nhanh": "nha_o_rieng_le"}, {}) == "nha_o_rieng_le"
    assert _construction_branch({}, {}) is None


_VALS = {
    "ChuHo_HoTen": "TRẦN CHÂU",
    "ChuHo_SoDinhDanh": "049059000699",
    "CongTrinh_Cap": "Cấp III",
    "CongTrinh_TongDienTichSan": "134,43",
    "CongTrinh_SoTang": "2",
}


def test_variant_nha_o_phat_element_NhaO():
    names = _names(_VALS, {"constructionVariant": "nha_o_rieng_le"})
    assert "data[capCongTrinhNhaO]" in names
    assert "data[tongDienTichSanNhaO]" in names
    assert not any("KhongTheoTuyen" in n for n in names)


def test_variant_cong_trinh_phat_element_KhongTheoTuyen():
    names = _names(_VALS, {"constructionVariant": "khong_theo_tuyen"})
    assert "data[capCongTrinhKhongTheoTuyen]" in names
    assert "data[tongDienTichSanKhongTheoTuyen]" in names
    assert "data[loaiCongTrinh]" in names  # nhánh công trình có ô 'Loại hình công trình'
    assert not any(n.endswith("NhaO]") for n in names)
