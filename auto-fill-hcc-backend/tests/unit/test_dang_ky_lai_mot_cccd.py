"""Đăng ký lại khai sinh: hồ sơ chỉ có ĐÚNG MỘT thẻ → người trên thẻ là người được đăng ký lại."""

import re

from app.pipelines.khai_sinh_dang_ky_lai.process import reason


def _card(name: str, number: str, birth: str, gender: str = "Nam") -> str:
    return (
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
        "CĂN CƯỚC CÔNG DÂN\n"
        "Citizen Identity Card\n"
        f"Số / No.: {number}\n"
        f"Họ và tên / Full name: {name}\n"
        f"Ngày sinh / Date of birth: {birth}\n"
        f"Giới tính / Sex: {gender} Quốc tịch / Nationality: Việt Nam\n"
        "Quê quán / Place of origin: Xã A, Huyện B, Tỉnh C\n"
        "Nơi thường trú / Place of residence: Thôn D, Xã A, Huyện B, Tỉnh C"
    )


def _section(context: str, tag: str) -> str:
    found = re.search(rf"<{tag}>(.*?)</{tag}>", context, re.S)
    return found.group(1).strip() if found else ""


def _label(context: str, tag: str, label: str) -> str:
    found = re.search(rf"^{label}:\s*(.*)$", _section(context, tag), re.M)
    return found.group(1).strip() if found else ""


_ONE_CARD = [{"name": "cccd.jpg", "text": _card("NGUYỄN VĂN A", "024096001060", "06/04/1996")}]


def test_mot_the_thi_gan_het_thong_tin_cho_nguoi_duoc_dang_ky_lai():
    context = reason._render_context("", {}, _ONE_CARD)

    assert _label(context, "con", "Họ tên") == "NGUYỄN VĂN A"
    assert _label(context, "con", "Số CCCD/CMND") == "024096001060"
    assert _label(context, "con", "Ngày sinh") == "06/04/1996"
    assert _label(context, "con", "Giới tính") == "Nam"
    assert _label(context, "con", "Quốc tịch") == "Việt Nam"
    # Không bịa cha/mẹ từ chính thẻ đó.
    assert "Không xác định" in _label(context, "cha", "Họ tên")
    assert "Không xác định" in _label(context, "me", "Họ tên")


def test_hai_the_tro_len_thi_khong_ap_dung():
    documents = _ONE_CARD + [
        {"name": "cccd-2.jpg", "text": _card("NGUYỄN VĂN B", "024075019811", "20/08/1975")},
    ]

    context = reason._render_context("", {}, documents)

    # Hai thẻ = có người thân đi nộp hộ → phải phân vai theo nhãn/thế hệ, không gán bừa.
    assert _label(context, "con", "Họ tên") in ("", "Không xác định")


def test_khong_de_len_nguoi_da_duoc_chi_dich_danh():
    raw = """<con>
Họ tên: NGUYỄN NGỌC C
Số CCCD/CMND: Không xác định
Ngày sinh: 09/08/2016
Giới tính: Nữ
Trạng thái: còn sống
Nguồn: giay-khai-sinh.jpg
Căn cứ phân vai: Nhãn con trên giấy khai sinh.
</con>"""
    documents = _ONE_CARD + [
        {"name": "ks.jpg", "text": "GIẤY KHAI SINH\nHọ, chữ đệm, tên: NGUYỄN NGỌC C"},
    ]

    context = reason._render_context(raw, {}, documents)

    # Giấy khai sinh đã chỉ rõ người được đăng ký lại → thẻ trong hồ sơ là của người thân.
    assert _label(context, "con", "Họ tên") == "NGUYỄN NGỌC C"


def test_giay_khai_tu_khong_tinh_la_the_can_cuoc():
    documents = [{
        "name": "khai-tu.jpg",
        "text": (
            "TRÍCH LỤC KHAI TỬ\n"
            "Phần ghi về người được khai tử:\n"
            "Họ và tên: NGUYỄN VĂN D\n"
            "Ngày sinh: 01/01/1940\n"
            "Giới tính: Nam"
        ),
    }]

    context = reason._render_context("", {}, documents)

    # Người trên giấy khai tử không phải người đi đăng ký lại khai sinh cho mình.
    assert _label(context, "con", "Họ tên") in ("", "Không xác định")


def test_tai_khoan_dang_nhap_chinh_la_nguoi_do_thi_quan_he_ban_than():
    context = reason._render_context("", {"formContext": {
        "applicantFullname": "NGUYỄN VĂN A",
        "applicantIdentityNumber": "024096001060",
    }}, _ONE_CARD)

    assert _label(context, "quan_he_nguoi_yeu_cau", "Kết luận") == "bản thân"
