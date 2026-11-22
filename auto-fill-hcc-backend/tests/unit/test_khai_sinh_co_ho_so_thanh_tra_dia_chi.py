"""Khai sinh người đã có hồ sơ: tên đường viết tay OCR đọc lệch → theo CCCD in của chính người đó."""
from app.pipelines.khai_sinh_co_ho_so.thanh_tra import dia_chi

_THE = """CĂN CƯỚC CÔNG DÂN
Citizen Identity Card
Số / No.: 001071000001
Họ và tên / Full name:
NGUYỄN VĂN AN
Nơi thường trú / Place of residence: 12 Lê Văn
Lợi, Phường Một, Thành phố Hai
"""
_TO_KHAI = """TỜ KHAI ĐĂNG KÝ KHAI SINH
Họ, chữ đệm, tên người yêu cầu: NGUYỄN VĂN AN
Nơi cư trú: 12 Lê Văn Lới - Phường Ba
Người yêu cầu
(Ký, ghi rõ họ, chữ đệm, tên)
"""


def _values(detail, so="001071000001"):
    return {"Requester_IdNumber": so,
            "Requester_ResidenceDomestic": {"quocGia": "Việt Nam", "tinh": "Hai", "xa": "Phường Ba", "diaChi": detail}}


def _docs():
    return [{"name": "cccd.pdf", "text": _THE}, {"name": "to_khai.pdf", "text": _TO_KHAI}]


def test_ten_duong_lech_mot_chu_theo_cccd_cua_chinh_nguoi_do():
    values = _values("12 Lê Văn Lới")
    finding = dia_chi.street_finding("Requester_ResidenceDomestic", values["Requester_ResidenceDomestic"], _docs(), values)
    assert finding.values["Requester_ResidenceDomestic"]["diaChi"] == "12 Lê Văn Lợi"
    assert finding.backed


def test_khong_sua_khi_the_la_cua_nguoi_khac_hoac_khac_so_nha():
    values = _values("12 Lê Văn Lới", so="001071000009")
    assert dia_chi.street_finding("Requester_ResidenceDomestic", values["Requester_ResidenceDomestic"], _docs(), values) is None
    values = _values("15 Lê Văn Lới")
    assert dia_chi.street_finding("Requester_ResidenceDomestic", values["Requester_ResidenceDomestic"], _docs(), values) is None


def test_khong_sua_khi_ten_duong_khac_han_hoac_da_dung():
    for detail in ("12 Trần Hưng Đạo", "12 Lê Văn Lợi"):
        values = _values(detail)
        assert dia_chi.street_finding(
            "Requester_ResidenceDomestic", values["Requester_ResidenceDomestic"], _docs(), values) is None
