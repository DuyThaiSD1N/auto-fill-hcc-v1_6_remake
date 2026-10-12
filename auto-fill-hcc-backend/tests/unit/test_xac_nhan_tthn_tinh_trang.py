"""Mapper TTHN: chốt option tình trạng hôn nhân từ mã LLM trả + giấy tờ ly hôn/khai tử."""

from app.pipelines.xac_nhan_tthn.process.mapper import _TINH_TRANG_HON_NHAN, enrich

_BAN_AN = {"DivorceDecision_Number": "12/2011/HNGĐ-ST", "DivorceDecision_Date": "15/07/2011",
           "DivorceDecision_Agency": "Tòa án nhân dân thành phố A"}
_CHUNG_TU = {"DeathCert_Number": "12", "DeathCert_Date": "28/02/2005", "DeathCert_Agency": "Ủy ban nhân dân xã B"}


def _status(values: dict) -> str:
    out = enrich([{"name": k, "comp": "x-input", "value": v} for k, v in values.items()], None)
    return next(f["value"] for f in out if f["name"] == "TinhTrangHonNhanC1")


def test_ma_chua_dang_ky_nhung_co_ban_an_thi_chon_da_ly_hon():
    assert _status({"TinhTrangHonNhanC1": "chua_ket_hon", **_BAN_AN}) == _TINH_TRANG_HON_NHAN["3"]


def test_nhan_chu_chua_dang_ky_nhung_co_giay_chung_tu_thi_chon_goa():
    assert _status({"TinhTrangHonNhanC1": "Hiện tại chưa đăng ký kết hôn với ai", **_CHUNG_TU}) == _TINH_TRANG_HON_NHAN["4"]


def test_ma_dang_co_vo_chong_giu_nguyen_du_co_ban_an_cu():
    assert _status({"TinhTrangHonNhanC1": "co_vo_chong", **_BAN_AN}) == _TINH_TRANG_HON_NHAN["1"]


def test_ma_tra_thang_duoc_nhan():
    assert _status({"TinhTrangHonNhanC1": "ly_hon", **_BAN_AN}) == _TINH_TRANG_HON_NHAN["3"]
    assert _status({"TinhTrangHonNhanC1": "chua_ket_hon"}) == _TINH_TRANG_HON_NHAN["2"]


def test_so_chu_thich_tren_mau_khong_phai_ma():
    # "(4)" in sẵn cạnh dòng tình trạng hôn nhân: LLM lỡ chép số thì không được hiểu thành "vợ/chồng đã chết".
    out = enrich([{"name": "TinhTrangHonNhanC1", "comp": "x-input", "value": "4"}], None)
    assert not any(f["name"] == "TinhTrangHonNhanC1" and f["value"] for f in out)


def test_van_ban_ban_an_thang_dong_to_khai_chep_nham():
    to_khai = {"DivorceDecision_Number": "12/2011/HNGĐ-ST", "DivorceDecision_Date": "15/07/2021",
               "DivorceDecision_Agency": "Tòa án nhân dân thành phố C"}
    ban_an = {"BanAn_Date": "15/07/2011", "BanAn_Agency": "Tòa án nhân dân thành phố A"}
    out = enrich([{"name": k, "comp": "x-input", "value": v}
                  for k, v in {"TinhTrangHonNhanC1": "ly_hon", **to_khai, **ban_an}.items()], None)
    detail = next(f["value"] for f in out if f["name"] == "nxnLoaiTinhTrangHonNhan=3")
    assert detail == {"soBanAnQuyetDinhLyHon": "12/2011/HNGĐ-ST", "ngayCapBanAnQuyetDinhLyHon": "15/07/2011",
                      "coQuanCapBanAnQuyetDinhLyHon": "Tòa án nhân dân thành phố A"}
