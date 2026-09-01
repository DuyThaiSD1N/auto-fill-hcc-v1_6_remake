"""Số 9 chữ số CHỈ có thể là CMND — căn cước/CCCD luôn 12 chữ số.

Giấy hộ tịch cũ (trích lục khai tử của người sinh trước 1960...) hay ghi CMND 9 số, mà OCR thì hay
rơi mất chữ "CMND". Thiếu luật đếm chữ số thì loại giấy tờ rơi về mặc định "Căn cước" rồi chọn nhầm
option "Thẻ Căn cước" cho một số 9 chữ số — sai hiển nhiên nhưng nhìn vẫn hợp lệ nên khó soát.
"""

import pytest

from app.pipelines.trich_luc.process.mapper import enrich, _id_doc_type_with_number

_CUC = "Cục Cảnh sát quản lý hành chính về trật tự xã hội"

# Trích lục khai tử bà Nguyễn Thị Ngân: giấy chỉ có CMND 9 số 120018017.
_HO_SO = [
    {"name": "ToKhai_LoaiSuKien", "value": "death"},
    {"name": "ToKhai_HoTenNguoiDuocCap", "value": "NGUYỄN THỊ NGÂN"},
    {"name": "HoTich_LoaiSuKien", "value": "death"},
    {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGUYỄN THỊ NGÂN"},
    {"name": "HoTich_SoGiayToTuyThan", "value": "120018017"},
    {"name": "HoTich_NgayCapGiayToTuyThan", "value": "04/05/2017"},
    {"name": "HoTich_NoiCapGiayToTuyThan", "value": "Công an tỉnh Bắc Giang"},
    {"name": "HoTich_CoQuanDangKy", "value": "UBND phường Hoàng Văn Thụ"},
    {"name": "Nyc_HoTen", "value": "VŨ THỊ PHƯƠNG"},
    {"name": "Nyc_SoDinhDanh", "value": "020152000758"},
]


def _ndk_loai(extra: list[dict] | None = None) -> str:
    out = {f["name"]: f["value"] for f in enrich(_HO_SO + (extra or []))}
    return out.get("NDK_LoaiGiayToTuyThan")


@pytest.mark.parametrize("hint", [
    None,               # OCR không đọc được loại → trước đây rơi về "Căn cước"
    "CMND",             # OCR đọc đúng
    "Thẻ căn cước",     # OCR đọc SAI → số chữ số phải thắng
    "Căn cước công dân",
])
def test_muc_ii_so_9_chu_so_luon_ra_cmnd(hint):
    extra = [{"name": "HoTich_LoaiGiayToTuyThan", "value": hint}] if hint else []
    assert _ndk_loai(extra) == "Chứng minh nhân dân"


def test_muc_ii_the_chu_the_9_so_cung_ra_cmnd():
    """Nhánh đắp mục II từ thẻ ChuThe_* cũng phải theo luật đếm số."""
    out = {f["name"]: f["value"] for f in enrich([
        {"name": "Nyc_HoTen", "value": "VŨ THỊ PHƯƠNG"},
        {"name": "Nyc_SoDinhDanh", "value": "020152000758"},
        {"name": "ChuThe_HoTen", "value": "NGUYỄN THỊ NGÂN"},
        {"name": "ChuThe_SoDinhDanh", "value": "120018017"},
        {"name": "ChuThe_NgayCap", "value": "04/05/2017"},
    ])}
    assert out.get("NDK_LoaiGiayToTuyThan") == "Chứng minh nhân dân"


def test_12_so_van_phan_biet_theo_noi_cap():
    """Chỉ chặn số 9 chữ số; 12 chữ số vẫn để nơi cấp quyết định như cũ."""
    assert _id_doc_type_with_number("020152000758", None, _CUC) == "Thẻ căn cước công dân"
    assert _id_doc_type_with_number("020152000758", None, "Bộ Công an") == "Thẻ Căn cước"


def test_loai_giay_to_khac_khong_bi_ep_thanh_cmnd():
    """Hộ chiếu/thẻ thường trú giữ nguyên, không bị luật đếm số nuốt."""
    assert _id_doc_type_with_number("C1234567", "Hộ chiếu", "") == "Hộ chiếu"
    assert _id_doc_type_with_number("TT1234567", "Thẻ thường trú", "") == "Thẻ thường trú"
