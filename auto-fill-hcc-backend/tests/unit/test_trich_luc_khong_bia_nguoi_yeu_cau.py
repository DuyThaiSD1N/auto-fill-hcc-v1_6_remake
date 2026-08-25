"""Nyc_*/ChuThe_* phải có người đó trong OCR; LLM chép mỏ neo VNeID vào là bịa → loại."""

from app.pipelines.trich_luc.process import mapper
from app.pipelines.trich_luc.process import runner as trich_runner

# Hồ sơ THẬT: CCCD của người cha + giấy khai sinh của con. Không có giấy tờ nào của người
# đang đăng nhập cổng (NGUYỄN DUY THÁI).
_OCR = """CĂN CƯỚC CÔNG DÂN
Số / No.: 024096001060
Họ và tên / Full name: NGUYỄN VĂN TUẤN
Ngày sinh: 06/04/1996
Nơi thường trú: Hưng Đạo, Đông Lỗ, Hiệp Hòa, Bắc Giang

GIẤY KHAI SINH  Số: 1934/2026
Họ, chữ đệm, tên: NGUYỄN NGỌC QUỲNH CHI
Số định danh cá nhân: 024326010634
Họ, chữ đệm, tên người đi khai sinh: NGUYỄN VĂN TUẤN
"""

_DOCUMENTS = [{"name": "ho-so.pdf", "text": _OCR}]

# Người đang đăng nhập VNeID — chỉ là mỏ neo, KHÔNG có giấy tờ nào trong hồ sơ.
_CONTEXT = {"formContext": {
    "applicantFullname": "NGUYỄN DUY THÁI",
    "applicantIdentityNumber": "001204018566",
}}

_HALLUCINATED_REQUESTER = {
    "Nyc_HoTen": "NGUYỄN DUY THÁI",
    "Nyc_SoDinhDanh": "001204018566",
    "Nyc_NgaySinh": "01/01/1980",
    "Nyc_NgayCap": "01/01/2020",
    "Nyc_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "Nyc_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Hà Nội",
                     "xa": "Phường Phúc Xá", "diaChi": "Số 10 phố Trúc Bạch"},
}

_BIRTH_EXTRACT = {
    "HoTich_LoaiSuKien": "birth",
    "HoTich_HoTenNguoiDuocDangKy": "NGUYỄN NGỌC QUỲNH CHI",
    "HoTich_NgaySinh": "09/08/2026",
    "HoTich_SoDinhDanh": "024326010634",
    "CopyRequest_QuanHe": "Bố đẻ",
}


def test_loai_nguoi_yeu_cau_khong_co_trong_ho_so():
    kept = trich_runner._compact_field_fallback({**_HALLUCINATED_REQUESTER, **_BIRTH_EXTRACT}, _DOCUMENTS)

    assert not [name for name in kept if name.startswith("Nyc_")]
    # Chỉ loại đúng nhóm thẻ bịa, dữ liệu đọc từ giấy hộ tịch giữ nguyên.
    assert kept["HoTich_SoDinhDanh"] == "024326010634"
    assert kept["CopyRequest_QuanHe"] == "Bố đẻ"


def test_khoi_nguoi_yeu_cau_khong_bi_ghi_de_bang_du_lieu_bia():
    kept = trich_runner._compact_field_fallback({**_HALLUCINATED_REQUESTER, **_BIRTH_EXTRACT}, _DOCUMENTS)
    result = {f["name"]: f["value"] for f in
              mapper.enrich([{"name": k, "value": v} for k, v in kept.items()], _CONTEXT)}

    # Mục I để nguyên cho cổng tự điền theo tài khoản VNeID, không đắp người lạ vào.
    for name in ("HoVaTenC", "SoDinhDanhC", "NgayCapDDC", "NYC_NoiCuTru_TrongNuoc"):
        assert name not in result
    # Mục II và phần hồ sơ vẫn đầy đủ.
    assert result["NDK_HoVaTen"] == "NGUYỄN NGỌC QUỲNH CHI"
    assert result["NDK_SoDinhDanh"] == "024326010634"
    assert result["NYC_QuanHe"] == "Bố Đẻ"


def test_giu_the_co_that_trong_ho_so():
    fields = {
        "Nyc_HoTen": "NGUYỄN VĂN TUẤN",
        "Nyc_SoDinhDanh": "024096001060",
        "Nyc_NgayCap": "25/04/2021",
        **_BIRTH_EXTRACT,
    }

    kept = trich_runner._compact_field_fallback(fields, _DOCUMENTS)

    assert kept == fields


def test_khop_mot_mo_neo_la_du_khi_ocr_rot_mo_neo_con_lai():
    # OCR ghi số định danh có dấu cách / rớt số: chỉ cần họ tên khớp là giữ.
    fields = {"Nyc_HoTen": "Nguyễn Văn Tuấn", "Nyc_SoDinhDanh": "024O96OO106O"}

    assert trich_runner._compact_field_fallback(fields, _DOCUMENTS) == fields


def test_loai_ca_nhom_chu_the_bia():
    fields = {
        "Nyc_HoTen": "NGUYỄN VĂN TUẤN",
        "ChuThe_HoTen": "NGƯỜI KHÔNG CÓ TRONG HỒ SƠ",
        "ChuThe_SoDinhDanh": "111111111111",
        **_BIRTH_EXTRACT,
    }

    kept = trich_runner._compact_field_fallback(fields, _DOCUMENTS)

    assert not [name for name in kept if name.startswith("ChuThe_")]
    assert kept["Nyc_HoTen"] == "NGUYỄN VĂN TUẤN"


def test_khong_co_mo_neo_thi_khong_loai():
    # LLM chỉ trả ngày cấp/nơi cấp, không có tên lẫn số → không đủ căn cứ để kết luận bịa.
    fields = {"Nyc_NgayCap": "25/04/2021", "Nyc_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"}

    assert trich_runner._compact_field_fallback(fields, _DOCUMENTS) == fields


def test_ho_tro_dang_list_field():
    fields = [
        {"name": "Nyc_HoTen", "value": "NGUYỄN DUY THÁI"},
        {"name": "Nyc_SoDinhDanh", "value": "001204018566"},
        {"name": "HoTich_So", "value": "1934/2026"},
    ]

    kept = trich_runner._compact_field_fallback(fields, _DOCUMENTS)

    assert [f["name"] for f in kept] == ["HoTich_So"]


def test_requester_hint_cam_dung_mo_neo_lam_gia_tri():
    hint = trich_runner._requester_hint(_CONTEXT)

    assert "TUYỆT ĐỐI KHÔNG dùng tên/số định danh này" in hint
    assert "Mọi giá trị PHẢI đọc được trong tài liệu" in hint
