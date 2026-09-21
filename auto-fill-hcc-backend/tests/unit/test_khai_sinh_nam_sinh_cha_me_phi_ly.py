"""Năm sinh cha/mẹ đọc sai trên tờ khai KHÔNG được xoá trắng vai đó.

Hồ sơ thật (req_e69ec5d7224a): tờ khai đăng ký lại khai sinh ghi rõ "Họ, chữ đệm, tên người mẹ:
Hoàng Thị Hằng", nhưng dòng năm sinh viết tay bị OCR đọc "1938" thành "1981" — trẻ hơn cả người
con sinh 1971. Cổng kiểm tra thế hệ trong `_validate_family_sections` xoá TRẮNG cả khối <me>,
prompt trích xuất lại có luật "khối nào ghi Không xác định thì bỏ toàn bộ field của vai đó", nên
agent trả về ĐÚNG MỘT field Mother_* = không có field nào. Cha (năm sinh 1933 đọc đúng) vẫn đủ,
nên trên biểu mẫu chỉ riêng khối mẹ trống.

Nhãn quan hệ in sẵn trên tờ khai đã chốt AI là cha/mẹ; khi trích lục khai tử/CCCD của chính
người đó cho năm sinh hợp thế hệ thì chỉ sửa dòng năm sinh. Không giấy nào xác nhận thì vẫn xoá
vai như cũ. Đoạn code này nằm ở cả hai pipeline khai sinh.
"""
import pytest

from app.pipelines.khai_sinh_co_ho_so.process import reason as co_ho_so
from app.pipelines.khai_sinh_dang_ky_lai.process import reason as dang_ky_lai

REASON_MODULES = pytest.mark.parametrize(
    "reason",
    [dang_ky_lai, co_ho_so],
    ids=["dang_ky_lai", "co_ho_so"],
)

_DECLARATION_BASIS = "Nhãn quan hệ in sẵn trên tờ khai đăng ký lại khai sinh."
_AGENT_BASIS = "Người nữ thuộc thế hệ trước con."


def _section(name, birth, basis, gender="Nữ", ethnicity="Bít"):
    return (
        f"Họ tên: {name}\n"
        "Số CCCD/CMND: Không xác định\n"
        f"Ngày sinh: {birth}\n"
        f"Giới tính: {gender}\n"
        f"Dân tộc: {ethnicity}\n"
        "Quốc tịch: Việt Nam\n"
        "Trạng thái: đã chết\n"
        "Nguồn: to-khai.pdf\n"
        f"Căn cứ phân vai: {basis}"
    )


def _sections(mother_birth, mother_basis):
    return {
        "con": (
            "Họ tên: Nguyễn Văn Cẩn\n"
            "Số CCCD/CMND: 024071014517\n"
            "Ngày sinh: 06/02/1971\n"
            "Giới tính: Nam\n"
            "Dân tộc: Kinh\n"
            "Quốc tịch: Việt Nam\n"
            "Trạng thái: còn sống\n"
            "Nguồn: to-khai.pdf\n"
            f"Căn cứ phân vai: {_DECLARATION_BASIS}"
        ),
        "me": _section("Hoàng Thị Hằng", mother_birth, mother_basis),
        "cha": _section("Nguyễn Văn Lừ", "1933", _DECLARATION_BASIS, gender="Nam"),
    }


_TRICH_LUC_ME = {
    "name": "trich-luc-me.pdf",
    "text": (
        "TRÍCH LỤC KHAI TỬ\n"
        "(BẢN SAO)\n"
        "Họ, chữ đệm, tên: HOÀNG THỊ HẰNG\n"
        "Ngày, tháng, năm sinh: 1933\n"
        "Giới tính: Nữ Dân tộc: Kinh Quốc tịch: Việt Nam\n"
        "Đã chết vào lúc giờ phút, ngày 23/02/2020\n"
    ),
}


@REASON_MODULES
def test_giay_to_khac_xac_nhan_nam_sinh_thi_sua_nam_sinh_giu_ca_khoi(reason):
    result = reason._validate_family_sections(
        _sections("1981", _DECLARATION_BASIS), [_TRICH_LUC_ME]
    )

    assert "Hoàng Thị Hằng" in result["me"]
    assert reason._labeled_value(result["me"], "Ngày sinh") == "1933"
    # Phần còn lại của khối phải nguyên vẹn để mapper dựng được mục "Người mẹ".
    assert reason._labeled_value(result["me"], "Giới tính") == "Nữ"
    assert reason._labeled_value(result["me"], "Trạng thái") == "đã chết"
    assert "Nguyễn Văn Lừ" in result["cha"]


@REASON_MODULES
def test_khong_giay_nao_xac_nhan_thi_van_xoa_vai(reason):
    """Không nguồn nào sửa được năm sinh thì giữ luật cũ: xoá vai sai thế hệ."""
    result = reason._validate_family_sections(_sections("1981", _DECLARATION_BASIS))

    assert reason._is_unknown(result["me"])


@REASON_MODULES
def test_vai_suy_doan_khong_duoc_sua_nam_sinh(reason):
    """Vai KHÔNG do nhãn tờ khai chốt thì giấy tờ khác không cứu được: xoá cả khối."""
    result = reason._validate_family_sections(
        _sections("1981", _AGENT_BASIS), [_TRICH_LUC_ME]
    )

    assert reason._is_unknown(result["me"])


def test_khoi_me_song_sot_va_lay_lai_nam_sinh_tu_trich_luc_khai_tu():
    """Cả chuỗi phân vai: tờ khai sai năm sinh, trích lục khai tử của chính mẹ bù lại 1933."""
    to_khai = (
        "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH\n"
        "Họ, chữ đệm, tên người yêu cầu: Nguyễn Văn Cẩn\n"
        "Ngày, tháng, năm sinh: 06/02/1971\n"
        "Quan hệ với người được khai sinh: bản thân\n"
        "Đề nghị cơ quan đăng ký lại khai sinh cho người có tên dưới đây:\n"
        "Họ, chữ đệm, tên: Nguyễn Văn Cẩn\n"
        "Ngày, tháng, năm sinh: 06/02/1971\n"
        "Giới tính: nam Dân tộc: Kinh Quốc tịch: Việt Nam\n"
        "Họ, chữ đệm, tên người mẹ: Hoàng Thị Hằng\n"
        "Năm sinh: (5) 1981 Dân tộc: (2) Bít Quốc tịch: (2) Việt Nam\n"
        "Nơi cư trú: Đã chết\n"
        "Giấy tờ tùy thân:\n"
        "Họ, chữ đệm, tên người cha: Nguyễn Văn Lừ\n"
        "Năm sinh: (5) 1933 Dân tộc: (2) Bít Quốc tịch: (2) Việt Nam\n"
        "Nơi cư trú: Đã chết\n"
        "Giấy tờ tùy thân:\n"
    )
    documents = [
        {"name": "to-khai.pdf", "text": to_khai},
        _TRICH_LUC_ME,
    ]

    context = dang_ky_lai._render_context("", {}, documents)
    mother = dang_ky_lai._section(context, "me")

    assert "Hoàng Thị Hằng" in mother
    assert dang_ky_lai._labeled_value(mother, "Ngày sinh") == "1933"
    assert dang_ky_lai._labeled_value(mother, "Giới tính") == "Nữ"
    assert dang_ky_lai._labeled_value(mother, "Trạng thái") == "đã chết"
