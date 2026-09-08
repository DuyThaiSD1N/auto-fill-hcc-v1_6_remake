# -*- coding: utf-8 -*-
"""Chuẩn hóa địa chỉ ở MỘT chỗ chung cho mọi thủ tục, và chốt chặn cặp tỉnh–xã.

Trước đây mỗi mapper tự gọi remap_area sau khi dựng lại dict 4 khóa, nên gợi ý cấp huyện bị rơi
mất trước khi remap nhìn thấy, và mỗi thủ tục rơi một kiểu. Nay việc này làm ở
compact_agent.runner.validate() (mọi pipeline đều đi qua) và app.process.service.execute_process().
"""
import pytest

from app.pipelines._shared.area_remap import (
    drop_fabricated_province,
    flag_unselectable_areas,
    is_current_area,
    remap_area_deep,
)
from app.pipelines._shared.compact_agent.runner import validate


# --------------------------------------------------------------------------------------
# Bước chung: gợi ý cấp huyện được tiêu thụ ngay trong validate()
# --------------------------------------------------------------------------------------

def test_validate_go_nhap_nhang_bang_goi_y_huyen():
    comp = {"NoiCuTru": "x-select-area"}
    out = validate(
        {"NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Phường 1",
                      "diaChi": "36/12 Nguyễn Văn Trỗi", "huyen": "Đà Lạt"}},
        set(comp), comp,
    )
    assert out[0]["value"]["xa"] == "Phường Xuân Hương - Đà Lạt"
    # Khóa gợi ý không được lọt ra giá trị field.
    assert "huyen" not in out[0]["value"]


def test_dia_chi_long_trong_list_cung_duoc_chuan_hoa():
    """Mapper riêng lẻ chưa bao giờ với tới địa chỉ nằm trong list — bước chung thì có."""
    value = [{"NoiCuTru": {"tinh": "Lâm Đồng", "xa": "Phường 1", "diaChi": "x", "huyen": "Bảo Lộc"}}]
    assert remap_area_deep(value)[0]["NoiCuTru"]["xa"] == "Phường 1 Bảo Lộc"


def test_gia_tri_khong_phai_dia_chi_thi_khong_dung_toi():
    for value in ("Nguyễn Văn A", 5, None, {"HoTen": "A"}, [{"HoTen": "B"}]):
        assert remap_area_deep(value) == value


# --------------------------------------------------------------------------------------
# Chốt chặn: tỉnh của nơi này không được ghép với phường/xã của nơi khác
# --------------------------------------------------------------------------------------

def test_cap_tinh_xa_khong_khop_thi_bo_trong_va_to_vang():
    """"Phường Nghĩa Lộ" có ở Lào Cai và Quảng Ngãi, KHÔNG có ở Hà Nội."""
    fields = [{"name": "NoiCuTru", "comp": "x-select-area",
               "value": {"quocGia": "Việt Nam", "tinh": "Thành phố Hà Nội",
                         "xa": "Phường Nghĩa Lộ", "diaChi": "Tổ 3"}}]
    flag_unselectable_areas(fields)
    assert fields[0]["value"]["xa"] == ""
    assert fields[0]["default"] is True
    # Tỉnh và phần chi tiết KHÔNG bị đụng — chỉ ô không chọn được mới bỏ trống.
    assert fields[0]["value"]["tinh"] == "Thành phố Hà Nội"
    assert fields[0]["value"]["diaChi"] == "Tổ 3"


def test_cap_hop_le_tuyet_doi_khong_bi_dung():
    fields = [{"name": "NoiCuTru", "comp": "x-select-area",
               "value": {"tinh": "Lâm Đồng", "xa": "Phường Xuân Hương - Đà Lạt", "diaChi": "36/12"}}]
    flag_unselectable_areas(fields)
    assert fields[0]["value"]["xa"] == "Phường Xuân Hương - Đà Lạt"
    assert "default" not in fields[0]


def test_ten_xa_trung_o_nhieu_tinh_van_hop_le_neu_dung_tinh():
    """Ngoại lệ: cùng tên phường ở nhiều tỉnh thì cặp nào cũng hợp lệ, không được chặn."""
    assert is_current_area("Lào Cai", "Phường Nghĩa Lộ")
    assert is_current_area("Quảng Ngãi", "Phường Nghĩa Lộ")


# --------------------------------------------------------------------------------------
# Toàn vẹn dữ liệu: mọi đích đến của bảng remap phải chọn được trên cổng
# --------------------------------------------------------------------------------------

def test_moi_xa_moi_trong_bang_remap_deu_co_trong_danh_muc():
    """Sai một dấu ở xa_moi là remap ra một option KHÔNG tồn tại — hỏng âm thầm.

    Từng có 22 cặp sai kiểu này (vd "Xã Sì Lờ Lầu" thay vì "Xã Sì Lở Lầu", "Xã Cư M’gar" dùng dấu
    nháy cong thay vì nháy thẳng, "Phú Quốc" thiếu tiền tố "Đặc khu").
    """
    import glob, json, io
    bad = set()
    for path in sorted(glob.glob("app/pipelines/_shared/data/remap_*.json")):
        for row in json.load(io.open(path, encoding="utf-8-sig")):
            tinh_moi, xa_moi = row.get("tinh_moi"), row.get("xa_moi")
            if tinh_moi and xa_moi and not is_current_area(tinh_moi, xa_moi):
                bad.add((tinh_moi, xa_moi))
    assert not bad, f"xa_moi không có trong danh mục hiện hành: {sorted(bad)}"


# --------------------------------------------------------------------------------------
# Không để LLM bịa cấp trên: tỉnh/huyện phải có trong chính giấy tờ
# --------------------------------------------------------------------------------------

_OCR_KET_HON = """TỜ KHAI ĐĂNG KÝ KẾT HÔN
Kính gửi: UBND Phường Nghĩa Lộ
Nơi cư trú: Tổ 3 Phường Nghĩa Lộ
Nghĩa Lộ, ngày 09 năm 2026"""


def test_bo_tinh_huyen_bia_ra():
    """Tờ khai không có một chữ nào về tỉnh, LLM vẫn trả "Hà Nội" + "Quận Hà Đông"."""
    comp = {"NoiCuTru": "x-select-area"}
    out = validate(
        {"NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Thành phố Hà Nội",
                      "huyen": "Quận Hà Đông", "xa": "Phường Nghĩa Lộ", "diaChi": "Tổ 3"}},
        set(comp), comp, ocr_text=_OCR_KET_HON,
    )
    value = out[0]["value"]
    assert value["tinh"] == ""
    assert "huyen" not in value
    # Phường và địa chỉ chi tiết CÓ trong giấy → giữ nguyên, không được xóa lây.
    assert value["xa"] == "Phường Nghĩa Lộ"
    assert value["diaChi"] == "Tổ 3"


def test_suy_ra_tinh_tu_ten_xa_thi_khong_bi_xoa():
    """Tỉnh không xuất hiện trong OCR NHƯNG khớp xã → là suy luận đúng, phải giữ.

    Đây là ranh giới của cả chốt chặn: xóa nhầm nhóm này là làm hỏng các hồ sơ đang chạy tốt.
    """
    area = {"tinh": "Lâm Đồng", "xa": "Phường Xuân Hương - Đà Lạt", "diaChi": "Số 5"}
    assert drop_fabricated_province(dict(area), "Số 5 Phường Xuân Hương - Đà Lạt")["tinh"] == "Lâm Đồng"


def test_khong_co_ocr_thi_khong_dong_gi():
    area = {"tinh": "Thành phố Hà Nội", "xa": "Phường Nghĩa Lộ", "diaChi": "Tổ 3"}
    assert drop_fabricated_province(dict(area), "") == area


def test_khong_doi_tinh_theo_ten_xa():
    """"Phường Nguyễn Du" (Hà Nội cũ) trùng khóa với "Xã Nguyễn Du" (Hưng Yên) vì cùng bỏ tiền tố.

    Tự sửa tỉnh theo tên xã sẽ kéo địa chỉ Hà Nội sang Hưng Yên — chốt chặn chỉ được XÓA, không đoán.
    """
    out = drop_fabricated_province({"tinh": "Hà Nội", "xa": "Phường Nguyễn Du", "diaChi": "Số 1"}, "Số 1 Phường Nguyễn Du")
    assert out["tinh"] == ""
    assert out["xa"] == "Phường Nguyễn Du"
