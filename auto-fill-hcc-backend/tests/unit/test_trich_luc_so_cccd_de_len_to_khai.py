"""Mục I trích lục: mọi ô theo TỜ KHAI, RIÊNG số giấy tờ tùy thân thì thẻ CCCD ghi đè.

Số trên tờ khai là chữ viết tay nên OCR hay rơi/đổi vài chữ số; số trên thẻ là số in sẵn.
Thứ tự cuối cùng của ô số: CCCD (đúng người yêu cầu) → tờ khai → tài khoản VNeID.
"""

from app.pipelines.trich_luc.process import mapper

_BIRTH_EXTRACT = [
    {"name": "HoTich_LoaiSuKien", "value": "birth"},
    {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "DƯƠNG VĂN ÁNH"},
    {"name": "HoTich_SoDinhDanh", "value": "024200006467"},
]

_VNEID_NGUOI_KHAC = {"formContext": {
    "applicantFullname": "NGUYỄN DUY THÁI",
    "applicantIdentityNumber": "001204018566",
}}


def _enrich(fields, options=None):
    return {f["name"]: f["value"] for f in mapper.enrich(fields, options)}


def test_so_tren_the_de_len_so_ocr_sai_cua_to_khai():
    # Cùng một người (tên khớp) nhưng tờ khai bị OCR mất số: thẻ sửa lại ô số,
    # các ô còn lại vẫn là của tờ khai.
    result = _enrich(_BIRTH_EXTRACT + [
        {"name": "TkNyc_HoTen", "value": "HÀ THỊ THƯ"},
        {"name": "TkNyc_SoGiayToTuyThan", "value": "02417700846"},  # thiếu 1 chữ số
        {"name": "TkNyc_NgayCapGiayToTuyThan", "value": "17/12/2021"},
        {"name": "TkNyc_NoiCuTru", "value": {
            "quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Hiệp Hòa", "diaChi": "Thôn Đại Đồng"}},
        {"name": "CopyRequest_QuanHe", "value": "Mẹ đẻ"},
        {"name": "Nyc_HoTen", "value": "HÀ THỊ THƯ"},
        {"name": "Nyc_SoDinhDanh", "value": "024177008469"},
        {"name": "Nyc_NgayCap", "value": "01/01/2019"},
        {"name": "Nyc_NoiCuTru", "value": {
            "quocGia": "Việt Nam", "tinh": "Bắc Giang", "xa": "Danh Thắng", "diaChi": "Đại Đồng 2"}},
    ], _VNEID_NGUOI_KHAC)

    assert result["SoDinhDanhC"] == "024177008469"
    assert result["NYC_SoGiayToTuyThan"] == "024177008469"
    # Các ô khác vẫn ưu tiên tờ khai.
    assert result["HoVaTenC"] == "HÀ THỊ THƯ"
    assert result["NgayCapDDC"] == "17/12/2021"
    assert result["NYC_NoiCuTru_TrongNuoc"]["diaChi"] == "Thôn Đại Đồng"


def test_khong_co_the_thi_so_van_lay_tu_to_khai():
    result = _enrich(_BIRTH_EXTRACT + [
        {"name": "TkNyc_HoTen", "value": "HÀ THỊ THƯ"},
        {"name": "TkNyc_SoGiayToTuyThan", "value": "024177008469"},
        {"name": "CopyRequest_QuanHe", "value": "Mẹ đẻ"},
    ], _VNEID_NGUOI_KHAC)

    assert result["SoDinhDanhC"] == "024177008469"
    assert result["HoVaTenC"] == "HÀ THỊ THƯ"


def test_the_cua_nguoi_khac_khong_duoc_de_len_so_cua_to_khai():
    # Thẻ trong hồ sơ là của người CON (lệch cả tên lẫn số) → không đụng vào ô số của mục I.
    result = _enrich(_BIRTH_EXTRACT + [
        {"name": "TkNyc_HoTen", "value": "HÀ THỊ THƯ"},
        {"name": "TkNyc_SoGiayToTuyThan", "value": "024177008469"},
        {"name": "CopyRequest_QuanHe", "value": "Mẹ đẻ"},
        {"name": "Nyc_HoTen", "value": "DƯƠNG VĂN ÁNH"},
        {"name": "Nyc_SoDinhDanh", "value": "024200006467"},
    ], _VNEID_NGUOI_KHAC)

    assert result["SoDinhDanhC"] == "024177008469"
    assert result["HoVaTenC"] == "HÀ THỊ THƯ"


def test_khong_to_khai_khong_the_thi_de_im_cho_vneid():
    result = _enrich(_BIRTH_EXTRACT, _VNEID_NGUOI_KHAC)

    assert "SoDinhDanhC" not in result
    assert "HoVaTenC" not in result
