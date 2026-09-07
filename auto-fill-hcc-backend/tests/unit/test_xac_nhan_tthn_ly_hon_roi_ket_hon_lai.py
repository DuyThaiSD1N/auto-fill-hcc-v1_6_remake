"""XNTTHN: ly hôn xong CƯỚI LẠI, xin xác nhận khoảng giữa hai mốc.

Ca thật ngoài quầy (Nghĩa Hưng, Ninh Bình): tờ khai ghi "Đã kết hôn, ly hôn theo bản án số
12/2016 ngày 27/4/2016 ... Từ ngày 27/4/2016 đến 14/9/2016 chưa đăng ký kết hôn với ai. Hiện
tại đã kết hôn với <vợ>". Cổng có option riêng (=5) cho ca này; extension từng chọn nhầm
"…đã ly hôn; hiện tại chưa đăng ký kết hôn với ai" (=3) — khai sai với người đã cưới lại và
mất luôn hai ô mốc thời gian.
"""
from app.pipelines.xac_nhan_tthn.process.mapper import enrich


def _fields(**kv):
    return [{"name": k, "value": v} for k, v in kv.items()]


def _by_name(out):
    return {f["name"]: f["value"] for f in out}


_LY_HON = dict(
    DivorceDecision_Number="12/2016",
    DivorceDecision_Date="27/04/2016",
    DivorceDecision_Agency="Tòa án nhân dân tỉnh Nam Định",
)


def test_khoang_thoi_gian_chon_option_5_kem_hai_moc():
    values = _by_name(enrich(_fields(
        **_LY_HON,
        Marriage_SpouseName="Cao Thị Trang",
        Marriage_Number="64",
        Marriage_Date="14/09/2016",
        Marriage_Agency="UBND xã Nghĩa Trung, huyện Nghĩa Hưng",
        Period_TuNgay="27/04/2016",
        Period_DenNgay="14/09/2016",
    )))

    assert values["TinhTrangHonNhanC1"].startswith("Từ ngày")
    assert "hiện tại đang có vợ/chồng" in values["TinhTrangHonNhanC1"]
    assert values["nxnLoaiTinhTrangHonNhan=5"] == {
        "voChongHoTen": "Cao Thị Trang",
        "thoiDiemBatDau": "27/04/2016",
        "thoiDiemKetThuc": "14/09/2016",
    }
    # Vùng =5 dùng chung bộ ô "Số / Ngày cấp / Cơ quan cấp giấy chứng nhận kết hôn".
    assert values["soGiayTo"] == "64"
    assert values["coQuanCapGiayTo"] == "UBND xã Nghĩa Trung, huyện Nghĩa Hưng"
    assert values["ngayCapGiayTo-day"] == "14"
    assert values["ngayCapGiayTo-month"] == "09"
    assert values["ngayCapGiayTo-year"] == "2016"
    # Không được rơi về vùng ly hôn.
    assert "nxnLoaiTinhTrangHonNhan=3" not in values


def test_ket_hon_lai_sau_ly_hon_khong_chon_option_da_ly_hon():
    """Không có khoảng thời gian, nhưng giấy kết hôn đăng ký SAU bản án ly hôn."""
    values = _by_name(enrich(_fields(
        **_LY_HON,
        Marriage_SpouseName="Cao Thị Trang",
        Marriage_Number="64",
        Marriage_Date="14/09/2016",
        Marriage_Agency="UBND xã Nghĩa Trung, huyện Nghĩa Hưng",
    )))

    assert values["TinhTrangHonNhanC1"] == "Hiện tại đang có vợ/chồng"
    assert values["nxnLoaiTinhTrangHonNhan=2"]["voChongHoTen"] == "Cao Thị Trang"
    assert "nxnLoaiTinhTrangHonNhan=3" not in values


def test_ly_hon_chua_cuoi_lai_van_giu_option_da_ly_hon():
    values = _by_name(enrich(_fields(**_LY_HON)))

    assert values["TinhTrangHonNhanC1"].startswith("Đã đăng ký kết hôn")
    assert values["nxnLoaiTinhTrangHonNhan=3"] == {
        "soBanAnQuyetDinhLyHon": "12/2016",
        "ngayCapBanAnQuyetDinhLyHon": "27/04/2016",
        "coQuanCapBanAnQuyetDinhLyHon": "Tòa án nhân dân tỉnh Nam Định",
    }


def test_giay_ket_hon_cu_truoc_ngay_ly_hon_khong_lat_thanh_dang_co_vo_chong():
    """Giấy kết hôn của chính cuộc hôn nhân đã bị hủy → vẫn là ĐÃ LY HÔN."""
    values = _by_name(enrich(_fields(
        **_LY_HON,
        Marriage_SpouseName="Nguyễn Thị B",
        Marriage_Number="20",
        Marriage_Date="10/01/2010",
        Marriage_Agency="UBND xã Nghĩa Trung",
    )))

    assert values["TinhTrangHonNhanC1"].startswith("Đã đăng ký kết hôn")
    assert "nxnLoaiTinhTrangHonNhan=3" in values


def test_so_luong_ban_sao_mac_dinh_mot_ban():
    """Ô (17) bắt buộc trên cổng nhưng tờ khai giấy không có mục này → mặc định 1, viền vàng."""
    out = {f["name"]: f for f in enrich(_fields(Purpose="Bổ sung hồ sơ giao dịch dân sự"))}

    assert out["SoLuong"]["value"] == "1"
    assert out["SoLuong"]["default"] is True
