"""Regression tests cho mapper Thành lập công ty TNHH hai thành viên trở lên.

Khóa lại nhóm radio "Phương pháp tính thuế" (GĐN mục 9.9) trên trang TaxInformation.aspx:
bảng khớp tuyệt đối cũ làm rơi field khi LLM viết khác chữ, mà `add()` bỏ giá trị rỗng nên
cổng giữ nguyên bốn ô chưa tích và không có cảnh báo nào.
"""

import pytest

from app.pipelines.thanh_lap_ctythnn_2_nguoi.process import mapper
from app.pipelines.thanh_lap_ctythnn_2_nguoi.process.mapper import _tax_method_label

_RADIO_NAME = "ctl00$C$UC_DW_TAXEditCtl$TAX_CAL_METHOD_IDRbBox"


def _tax_radio(value):
    fields = mapper.enrich([{"name": "Thue_PhuongPhapGTGT", "value": value}], page="thong-tin-ve-thue")
    return next((field for field in fields if field["name"] == _RADIO_NAME), None)


@pytest.mark.parametrize("written", [
    "Khấu trừ",
    "khấu trừ",
    "KHẤU TRỪ",
    "Khấu  trừ",                 # OCR nhân đôi khoảng trắng
    "Phương pháp khấu trừ",
    "Khấu trừ thuế GTGT",
])
def test_tax_method_variants_still_reach_the_deduction_option(written):
    """Mọi cách viết cùng nghĩa đều phải ra đúng nhãn cổng hiển thị."""
    assert _tax_method_label(written) == "Khấu trừ"


def test_tax_method_covers_all_four_portal_options():
    assert _tax_method_label("Trực tiếp trên GTGT") == "Trực tiếp trên GTGT"
    assert _tax_method_label("Trực tiếp trên doanh số") == "Trực tiếp trên doanh số"
    assert _tax_method_label("Trực tiếp trên doanh số (%)") == "Trực tiếp trên doanh số"
    assert _tax_method_label("Không phải nộp thuế GTGT") == "Không phải nộp thuế GTGT"
    assert _tax_method_label("Không phải nộp thuế giá trị gia tăng") == "Không phải nộp thuế GTGT"


def test_tax_method_order_does_not_confuse_overlapping_wording():
    """"Không phải nộp thuế GTGT" chứa cả "gtgt"; "trực tiếp trên doanh số" chứa cả "trực tiếp"."""
    assert _tax_method_label("Không phải nộp thuế GTGT") != "Trực tiếp trên GTGT"
    assert _tax_method_label("Trực tiếp trên doanh số") != "Trực tiếp trên GTGT"


def test_tax_method_emits_dom_radio_field_for_the_portal():
    field = _tax_radio("Khấu trừ")

    assert field is not None
    assert field["comp"] == "dom-radio"
    assert field["value"] == "Khấu trừ"


@pytest.mark.parametrize("written", ["", None, "Hạch toán độc lập", "chưa rõ"])
def test_tax_method_never_guesses(written):
    """Mục 9.9 chỉ được tích đúng một ô — không nhận ra thì bỏ trống, không đoán bừa."""
    assert _tax_method_label(written) == ""
    assert _tax_radio(written) is None
