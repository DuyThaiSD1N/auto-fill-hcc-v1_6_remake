# -*- coding: utf-8 -*-
"""Gỡ nhập nhằng tên phường/xã TRÙNG nhau giữa nhiều huyện bằng gợi ý cấp huyện.

"Phường 1" của tỉnh Lâm Đồng tồn tại ở CẢ HAI thành phố cũ: Đà Lạt (nay là "Phường Xuân Hương -
Đà Lạt") và Bảo Lộc (nay vẫn là "Phường 1 Bảo Lộc"). Bảng remap 2 khóa (tỉnh, xã) buộc phải bỏ qua
cả hai vì không đủ căn cứ → backend trả nguyên "Phường 1", extension dò dropdown và vớ phải
"Phường 1 Bảo Lộc" cho một người ở Đà Lạt.

Khóa "huyen" là gợi ý CHỈ để chọn đúng đơn vị mới; biểu mẫu không có ô cấp huyện nên nó phải bị bỏ
khỏi kết quả, không lọt ra ngoài thành một khóa lạ trong giá trị field.
"""
from app.pipelines._shared.area_remap import remap_area


def _remap(xa, huyen=None, tinh="Lâm Đồng", dia="36/12 Nguyễn Văn Trỗi"):
    area = {"quocGia": "Việt Nam", "tinh": tinh, "xa": xa, "diaChi": dia}
    if huyen:
        area["huyen"] = huyen
    return remap_area(area)


# --------------------------------------------------------------------------------------
# Ca báo lỗi: CCCD ghi "36/12 Nguyễn Văn Trỗi, P1, Đà Lạt, Lâm Đồng"
# --------------------------------------------------------------------------------------

def test_phuong_1_da_lat_khong_ra_bao_loc():
    assert _remap("Phường 1", "Đà Lạt")["xa"] == "Phường Xuân Hương - Đà Lạt"


def test_phuong_1_bao_loc_van_dung():
    """Ranh giới quan trọng nhất: gợi ý phải chọn ĐÚNG bên, không phải luôn chọn Đà Lạt."""
    assert _remap("Phường 1", "Bảo Lộc")["xa"] == "Phường 1 Bảo Lộc"


def test_viet_tat_phuong_va_tien_to_cap_huyen():
    """OCR trả "P1" + "TP Đà Lạt"/"Thành phố Đà Lạt" — đều phải khớp cùng một khóa."""
    for huyen in ("TP Đà Lạt", "TP. Đà Lạt", "Thành phố Đà Lạt", "TP Đà Lạt cũ"):
        assert _remap("P1", huyen)["xa"] == "Phường Xuân Hương - Đà Lạt", huyen


def test_khoa_huyen_bi_bo_khoi_ket_qua():
    out = _remap("Phường 1", "Đà Lạt")
    assert "huyen" not in out and "quanHuyen" not in out
    assert out["diaChi"] == "36/12 Nguyễn Văn Trỗi"
    assert out["tinh"] == "Lâm Đồng"


# --------------------------------------------------------------------------------------
# Không có gợi ý → giữ nguyên hành vi cũ (thà để trống còn hơn đoán bừa)
# --------------------------------------------------------------------------------------

def test_khong_co_goi_y_thi_giu_nguyen():
    assert _remap("Phường 1")["xa"] == "Phường 1"


def test_goi_y_sai_huyen_thi_khong_dong_bua():
    """Huyện không có trong bảng → rơi xuống luồng cũ, không tự chọn một bên."""
    assert _remap("Phường 1", "Đơn Dương")["xa"] == "Phường 1"


# --------------------------------------------------------------------------------------
# Địa chỉ KHÔNG nhập nhằng: gợi ý không được làm đổi kết quả vốn đã đúng
# --------------------------------------------------------------------------------------

def test_xa_khong_nhap_nhang_khong_bi_anh_huong():
    assert _remap("Phường 7", "Đà Lạt")["xa"] == "Phường Lang Biang - Đà Lạt"
    assert _remap("Phường 7")["xa"] == "Phường Lang Biang - Đà Lạt"


def test_huyen_ghi_trong_ngoac_cua_xa_cu_van_go_duoc_nhap_nhang():
    """Bảng Lạng Sơn ghi "Tân Thành (huyện Bắc Sơn)" thay vì khóa huyen_cu.

    Ca báo lỗi: CCCD "Tân Thành, Bắc Sơn, Lạng Sơn" ra "Tân Thành" (xã khác ở Hữu Lũng) thay vì
    "Xã Nhất Hòa".
    """
    assert _remap("Tân Thành", "Bắc Sơn", tinh="Lạng Sơn", dia="")["xa"] == "Xã Nhất Hòa"
    assert _remap("Tân Thành", "huyện Cao Lộc", tinh="Lạng Sơn", dia="")["xa"] == "Xã Tân Đoàn"
    assert _remap("Tân Thành", "Hữu Lũng", tinh="Lạng Sơn", dia="")["xa"] == "Xã Tân Thành"
    # Không có gợi ý huyện → giữ nguyên hành vi cũ, không tự chọn một bên.
    assert _remap("Tân Thành", tinh="Lạng Sơn", dia="")["xa"] == "Tân Thành"


def test_ngoac_ghi_chu_khong_bi_hieu_la_huyen():
    from app.pipelines._shared.area_remap import _split_xa_cu_district

    for xa_cu in ("Phú Hội (phần còn lại)", "Ea Bia (một phần)", "An Phú (thị trấn)", "Kiên Hải (huyện)"):
        assert _split_xa_cu_district(xa_cu) == (xa_cu, "")
    assert _split_xa_cu_district("Thạnh Lộc (Châu Thành, KG)") == ("Thạnh Lộc", "Châu Thành")


def test_cap_tinh_khac_van_go_duoc_nhap_nhang():
    """Tân Hà (Bình Thuận cũ) có ở cả huyện Hàm Tân và huyện Đức Linh, về hai xã mới khác nhau."""
    assert _remap("Tân Hà", "Hàm Tân", tinh="Bình Thuận", dia="")["xa"] == "Xã Hàm Tân"
    assert _remap("Tân Hà", "Đức Linh", tinh="Bình Thuận", dia="")["xa"] == "Xã Trà Tân"
