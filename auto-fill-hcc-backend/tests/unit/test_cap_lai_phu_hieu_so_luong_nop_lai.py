"""Cấp, cấp lại phù hiệu (Bộ XD): ô "Số lượng phù hiệu nộp lại" chỉ nhận số — Giấy đề nghị ghi cả câu vẫn phải ra số."""

import pytest

from app.pipelines.cap_lai_phu_hieu_xe_oto.process.mapper import enrich

_NAME = "data[ThamDinh][SoLuongNopLai]"


def _so_luong(value):
    out, _ = enrich([{"name": "DeNghi_SoLuongNopLai", "value": value}], {}, "")
    return next((f["value"] for f in out if f["name"] == _NAME), None)


@pytest.mark.parametrize("value,expected", [
    ("Không", "0"),
    ("Không nộp lại", "0"),
    ("Không có phù hiệu nộp lại", "0"),
    ("02", "2"),
    ("01 phù hiệu", "1"),
])
def test_so_luong_nop_lai_ra_so(value, expected):
    assert _so_luong(value) == expected


def test_o_trong_tren_mau_khong_dien():
    assert _so_luong("......") is None
