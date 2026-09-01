"""Xã mới lấy tên huyện cũ, và xã đã mang sẵn tên mới — hai ca trước đây bị XÓA TRẮNG.

Sau sáp nhập 2025 rất nhiều xã mới lấy chính tên huyện cũ (huyện Hiệp Hòa, Bắc Giang -> "Xã Hiệp
Hòa", Bắc Ninh). Bảng remap chỉ có key theo tên XÃ cũ, nên khi OCR/LLM trả tên HUYỆN thì tra trượt,
rơi xuống nhánh "tỉnh đã đổi tên -> bỏ trống xã". Đó là lý do cùng một hồ sơ lúc remap được lúc
không: phụ thuộc agent trả "Đoàn Bái" (tên xã cũ) hay "Hiệp Hòa" (tên huyện).
"""

from app.pipelines._shared.area_remap import remap_area, _fold_accent


def _xa(tinh: str, xa: str) -> tuple[str, str]:
    r = remap_area({"quocGia": "Việt Nam", "tinh": tinh, "xa": xa, "diaChi": "Phú Thuận"})
    return r["tinh"], r["xa"]


def test_ten_xa_cu_van_remap_nhu_cu():
    """Đường đi cũ qua bảng remap không được đổi. OCR rơi/thêm dấu vẫn phải khớp."""
    for viet in ("Đoan Bái", "Đoàn Bái", "Đoàn Bài"):
        assert _xa("Bắc Giang", viet) == ("Bắc Ninh", "Xã Hiệp Hòa"), viet


def test_ten_huyen_cu_lam_xa_van_ra_dung_xa_moi():
    """Agent trả tên HUYỆN: trước đây ra xã rỗng, giờ phải ra đúng xã mới cùng tên."""
    assert _xa("Bắc Giang", "Hiệp Hòa") == ("Bắc Ninh", "Xã Hiệp Hòa")
    assert _xa("Bắc Giang", "Hiệp Hoà") == ("Bắc Ninh", "Xã Hiệp Hòa")   # dấu kiểu mới


def test_xa_da_mang_ten_moi_khong_bi_xoa_trang():
    """Giấy tờ ghi tỉnh CŨ nhưng xã đã là tên MỚI — không được xóa mất xã."""
    assert _xa("Bắc Giang", "Xã Hiệp Hòa") == ("Bắc Ninh", "Xã Hiệp Hòa")


def test_khong_dong_nham_xa_khac_chi_vi_trung_khi_bo_dau():
    """"Thạnh" và "Thành" bỏ dấu thì trùng — so tên phải GIỮ dấu, nếu không sẽ điền nhầm xã."""
    assert _fold_accent("Bình Thạnh") != _fold_accent("Bình Thành")
    # Hai kiểu đặt dấu cũ/mới của cùng một chữ thì vẫn phải coi là một.
    assert _fold_accent("Hòa") == _fold_accent("Hoà")


def test_tinh_chua_doi_ten_thi_khong_dung_vao_xa():
    """Nhánh cứu chỉ chạy khi tỉnh cũ ĐÃ đổi tên; tỉnh chưa đổi thì giữ nguyên như trước."""
    assert _xa("Nghệ An", "Tam Hợp") == ("Nghệ An", "Tam Hợp")
    assert _xa("Lâm Đồng", "Phường Xuân Hương") == ("Lâm Đồng", "Phường Xuân Hương")
    assert _xa("Đồng Tháp", "Bình Thạnh") == ("Đồng Tháp", "Bình Thạnh")
