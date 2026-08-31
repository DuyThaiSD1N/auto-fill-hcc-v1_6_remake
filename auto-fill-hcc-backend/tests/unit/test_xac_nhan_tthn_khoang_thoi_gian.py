"""Xác nhận CHƯA ĐKKH trong một KHOẢNG THỜI GIAN đã qua, dù hiện tại đã có vợ/chồng (option =5)."""

from app.pipelines.xac_nhan_tthn.process.mapper import enrich

_PERIOD_STATUS = (
    "Từ ngày… tháng… năm… đến ngày… tháng… năm … chưa đăng ký kết hôn với ai; "
    "hiện tại đang có vợ/chồng"
)


def _by_name(fields: list[dict]) -> dict[str, dict]:
    return {field["name"]: field for field in fields}


# Hồ sơ thật: tờ khai ghi "Từ ngày 1 tháng 1 năm 2025 đến ngày 13 tháng 12 năm 2025. Tôi chưa đăng ký
# kết hôn với ai. Hiện tại đã kết hôn với vợ tên là: Nguyễn Phạm Thu Huyền" + giấy chứng nhận kết hôn.
_HO_SO = [
    {"name": "ToKhai_HoTen", "value": "Lê Hoàng Quý"},
    {"name": "ToKhai_SoDinhDanh", "value": "051205007090"},
    {"name": "ToKhai_LaBanThan", "value": True},
    {"name": "Period_TuNgay", "value": "01/01/2025"},
    {"name": "Period_DenNgay", "value": "13/12/2025"},
    {"name": "Marriage_SpouseName", "value": "Nguyễn Phạm Thu Huyền"},
    {"name": "Marriage_Number", "value": "201/2026"},
    {"name": "Marriage_Date", "value": "14/08/2026"},
    {"name": "Marriage_Agency", "value": "Ủy ban nhân dân phường Nghĩa Lộ, tỉnh Quảng Ngãi"},
    {"name": "Purpose", "value": "Bổ sung giấy tờ mua bán đất"},
]


def test_khoang_thoi_gian_va_dang_co_vo_chong_chon_option_5():
    result = _by_name(enrich(list(_HO_SO)))

    assert result["TinhTrangHonNhanC1"]["value"] == _PERIOD_STATUS
    area = result["nxnLoaiTinhTrangHonNhan=5"]
    assert area["comp"] == "x-select-area"
    assert area["value"] == {
        "voChongHoTen": "Nguyễn Phạm Thu Huyền",
        "thoiDiemBatDau": "01/01/2025",
        "thoiDiemKetThuc": "13/12/2025",
    }
    # Vùng =2 KHÔNG được phát kèm: chọn hai option cùng lúc là cổng render sai khối.
    assert "nxnLoaiTinhTrangHonNhan=2" not in result


def test_khoang_thoi_gian_van_phat_o_con_cua_giay_ket_hon():
    """Số/ngày/cơ quan cấp GCN kết hôn dùng CHUNG DOM name với vùng =2 → phải phát đủ."""
    result = _by_name(enrich(list(_HO_SO)))

    assert result["soGiayTo"]["value"] == "201/2026"
    assert result["ngayCapGiayTo-day"]["value"] == "14"
    assert result["ngayCapGiayTo-month"]["value"] == "08"
    assert result["ngayCapGiayTo-year"]["value"] == "2026"
    assert result["ngayCapGiayTo-name-date-input"]["value"] == "2026-08-14"
    assert result["coQuanCapGiayTo"]["value"].startswith("Ủy ban nhân dân phường Nghĩa Lộ")


def test_thieu_mot_dau_moc_thi_khong_dung_option_5():
    """Chỉ có ngày bắt đầu: không đủ một khoảng → quay về luồng "đang có vợ/chồng" (=2)."""
    fields = [f for f in _HO_SO if f["name"] != "Period_DenNgay"]
    result = _by_name(enrich(fields))

    assert result["TinhTrangHonNhanC1"]["value"] == "Hiện tại đang có vợ/chồng"
    assert "nxnLoaiTinhTrangHonNhan=5" not in result
    assert result["nxnLoaiTinhTrangHonNhan=2"]["value"]["voChongHoTen"] == "Nguyễn Phạm Thu Huyền"


def test_co_khoang_thoi_gian_nhung_khong_co_vo_chong_thi_khong_dung_option_5():
    """Option =5 chỉ đúng khi HIỆN TẠI đang có vợ/chồng; không có thì đây là ca khác."""
    fields = [f for f in _HO_SO if not f["name"].startswith("Marriage_")]
    result = _by_name(enrich(fields))

    assert "nxnLoaiTinhTrangHonNhan=5" not in result
    assert result.get("TinhTrangHonNhanC1", {}).get("value") != _PERIOD_STATUS
