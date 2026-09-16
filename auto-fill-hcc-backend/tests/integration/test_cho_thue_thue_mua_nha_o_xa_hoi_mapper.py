# -*- coding: utf-8 -*-
"""Mapper "Cho thuê, cho thuê mua nhà ở xã hội…": suy địa chỉ khi đơn chỉ ghi MỘT trong hai mục 5/6."""

from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.process import mapper


def _fields(src: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in src.items()]


def _values(mapped: list[dict]) -> dict:
    return {(f["name"], f.get("occurrence")): f["value"] for f in mapped}


_BASE = {
    "ChonDoiTuong": "Cá nhân",
    "NguoiNop_HoTen": "TRƯƠNG THỊ XUÂN",
    "NguoiNop_SoDinhDanh": "049140005446",
    "NguoiNop_NgayCap": "05/07/2021",
    "NguoiNop_NoiCap": "Công an TP Đà Nẵng",
    "Don_HinhThuc": "Thuê",
}
_HIEN_TAI = {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "phường An Hải", "diaChi": "Tổ Mỹ An"}


def test_thieu_thuong_tru_thi_suy_tu_noi_o_hien_tai():
    """Đơn viết tay bỏ trống mục 6 + hồ sơ không kèm CCCD → cả 3 nhóm địa chỉ vẫn phải có giá trị."""
    mapped, warnings = mapper.enrich(_fields({**_BASE, "NguoiNop_NoiOHienTai": _HIEN_TAI}))
    values = _values(mapped)

    # Phần I (occ0) = thường trú, suy từ nơi ở hiện tại.
    assert values[("data[province]", 0)] == "Thành phố Đà Nẵng"
    assert values[("data[district]", 0)] == "phường An Hải"
    assert values[("data[address]", 0)] == "Tổ Mỹ An"
    # Phần III thường trú (key riêng province1/district1/address1).
    assert values[("data[province1]", None)] == "Thành phố Đà Nẵng"
    assert values[("data[district1]", None)] == "phường An Hải"
    assert values[("data[address1]", None)] == "Tổ Mỹ An"
    # Phần III nơi ở hiện tại (occ1).
    assert values[("data[address]", 1)] == "Tổ Mỹ An"
    assert not [w for w in warnings if "địa chỉ" in w]


def test_thieu_noi_o_hien_tai_thi_suy_tu_thuong_tru():
    mapped, _ = mapper.enrich(_fields({**_BASE, "NguoiNop_ThuongTru": _HIEN_TAI}))
    values = _values(mapped)

    assert values[("data[address]", 0)] == "Tổ Mỹ An"
    assert values[("data[address]", 1)] == "Tổ Mỹ An"
    assert values[("data[address1]", None)] == "Tổ Mỹ An"


def test_thieu_ca_hai_dia_chi_thi_canh_bao():
    _, warnings = mapper.enrich(_fields(_BASE))

    assert any("địa chỉ" in w for w in warnings)
