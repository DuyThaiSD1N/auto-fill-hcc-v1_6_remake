"""Khai sinh liên thông: hồ sơ CHƯA có thông tin con thì không được làm sập pipeline.

Lỗi thật gặp tại quầy: cán bộ gửi mỗi giấy chứng nhận kết hôn + một giấy tờ khác (chưa có
giấy chứng sinh, chưa có tờ khai) → `has_child` = False → nhánh quê quán đọc `is_lam_dong` vốn
chỉ được gán BÊN TRONG khối `if has_child:` → UnboundLocalError. Công dân chỉ thấy
"Xử lý giấy tờ chưa xong được — cannot access local variable 'is_lam_dong'".

Đây là ca RẤT dễ gặp: công dân đưa giấy tờ theo từng đợt, đợt đầu thường chưa có chứng sinh.
"""
from app.pipelines.khai_sinh_lien_thong.process.mapper import enrich


def _run(values: dict):
    """enrich nhận LIST field (không phải dict) — dựng đúng hình dạng thật."""
    return enrich([{"name": k, "value": v} for k, v in values.items()])


def _fields(rows):
    return {f["name"]: f.get("value") for f in rows}


def test_thieu_hoan_toan_thong_tin_con_van_chay_duoc():
    # Đúng bộ giấy tờ của ca lỗi: chỉ có cha/mẹ, không một trường nào của con.
    result = _run({
        "ThongTinBo_HoTen": "NGUYỄN VĂN A",
        "ThongTinBo_SoDinhDanh": "001234567890",
        "ThongTinMe_HoTen": "TRẦN THỊ B",
        "ThongTinMe_SoDinhDanh": "001234567891",
    })
    assert isinstance(result, list), "không được ném UnboundLocalError"


def test_khong_co_noi_sinh_thi_khong_ap_ngoai_le_lam_dong():
    # is_lam_dong phải là False chứ không phải "chưa gán": quê quán con vẫn lấy theo CHA.
    result = _run({
        "ThongTinBo_HoTen": "NGUYỄN VĂN A",
        "ThongTinBo_QueQuan": {"tinh": "Tỉnh Lai Châu", "xa": "Xã Tân Phong"},
        "ThongTinMe_HoTen": "TRẦN THỊ B",
        "ThongTinMe_QueQuan": {"tinh": "Tỉnh Lâm Đồng", "xa": "Xã Khác"},
    })
    qq = _fields(result).get("QqDiaChi") or {}
    if qq:
        assert "Lâm Đồng" not in str(qq), "không có nơi sinh thì không được lấy quê mẹ theo lệ Lâm Đồng"


def test_sinh_o_lam_dong_van_lay_que_quan_me():
    # Hành vi CŨ phải giữ nguyên sau khi dời phép tính ra ngoài khối.
    result = _run({
        "Gcs_NoiSinh": {"tinh": "Tỉnh Lâm Đồng", "xa": "Phường Xuân Hương"},
        "Tk_HoTenCon": "NGUYỄN VĂN C",
        "ThongTinBo_HoTen": "NGUYỄN VĂN A",
        "ThongTinBo_QueQuan": {"tinh": "Tỉnh Lai Châu", "xa": "Xã Tân Phong"},
        "ThongTinMe_HoTen": "TRẦN THỊ B",
        "ThongTinMe_SoDinhDanh": "001234567891",
        "ThongTinMe_QueQuan": {"tinh": "Tỉnh Lâm Đồng", "xa": "Phường Xuân Hương"},
    })
    qq = _fields(result).get("QqDiaChi") or {}
    assert "Lâm Đồng" in str(qq), "sinh ở Lâm Đồng thì quê quán con theo MẸ"


# --- Cấu hình theo tài khoản: 4 phường Đà Lạt chọn sẵn mục "Thông tin cấp thẻ BHYT" ---
import pytest

from app.pipelines.khai_sinh_lien_thong.process.mapper import (
    DA_LAT_BHYT_OPTION,
    with_account_process_options,
)

_HO_SO = {
    "ThongTinBo_HoTen": "NGUYỄN VĂN A",
    "ThongTinMe_HoTen": "TRẦN THỊ B",
}


@pytest.mark.parametrize("xa", [
    "Phường Xuân Hương - Đà Lạt",
    "Phường Lâm Viên - Đà Lạt",
    "Phường Cam Ly - Đà Lạt",
    "Phường Lang Biang - Đà Lạt",
    "Lâm Viên",
])
def test_bon_phuong_da_lat_bat_co_bhyt(xa):
    opts = with_account_process_options({}, {"tinh": "Tỉnh Lâm Đồng", "xa": xa}, "khai-sinh-dang-ky")
    assert opts.get(DA_LAT_BHYT_OPTION) is True


@pytest.mark.parametrize("user, procedure", [
    ({"tinh": "Tỉnh Lâm Đồng", "xa": "Xã Đơn Dương"}, "khai-sinh-dang-ky"),
    ({"tinh": "Tỉnh Bắc Ninh", "xa": "Phường Hiệp Hòa"}, "khai-sinh-dang-ky"),
    ({"tinh": "Tỉnh Lâm Đồng", "xa": "Phường Xuân Hương - Đà Lạt"}, "khai-tu-lien-thong"),
    (None, "khai-sinh-dang-ky"),
])
def test_tai_khoan_khac_khong_bat_co_va_client_khong_tu_bat(user, procedure):
    opts = with_account_process_options({DA_LAT_BHYT_OPTION: True}, user, procedure)
    assert DA_LAT_BHYT_OPTION not in opts


def test_phuong_da_lat_chon_me_va_bv_san_nhi():
    rows = enrich([{"name": k, "value": v} for k, v in _HO_SO.items()], {DA_LAT_BHYT_OPTION: True})
    by = {f["name"]: f for f in rows}
    assert by["NguoiGiamHo"]["value"] == "Thông tin mẹ"
    assert by["CskcbbdMa"]["value"] == "Bệnh viện Sản - Nhi tỉnh Lâm Đồng"
    assert by["CskcbbdMa"]["comp"] == "select" and by["CskcbbdMa"].get("default") is True
    assert [f["name"] for f in rows].count("NguoiGiamHo") == 1


def test_khong_co_co_giu_mac_dinh_cha_va_bo_trong_noi_kcb():
    fields = _fields(_run(_HO_SO))
    assert fields["NguoiGiamHo"] == "Thông tin cha"
    assert "CskcbbdMa" not in fields


# --- Phường Hải Châu - Đà Nẵng: chỉ chọn giám hộ trên thẻ BHYT = mẹ ---
from app.pipelines.khai_sinh_lien_thong.process.mapper import HAI_CHAU_BHYT_OPTION


@pytest.mark.parametrize("user", [
    {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu"},
    {"tinh": "Đà Nẵng", "xa": "Hải Châu"},
])
def test_hai_chau_bat_co_bhyt(user):
    opts = with_account_process_options({}, user, "khai-sinh-dang-ky")
    assert opts.get(HAI_CHAU_BHYT_OPTION) is True
    assert DA_LAT_BHYT_OPTION not in opts


@pytest.mark.parametrize("user, procedure", [
    ({"tinh": "Thành phố Đà Nẵng", "xa": "Phường Liên Chiểu"}, "khai-sinh-dang-ky"),
    ({"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu"}, "khai-tu-lien-thong"),
    ({"tinh": "Tỉnh Lâm Đồng", "xa": "Phường Xuân Hương - Đà Lạt"}, "khai-sinh-dang-ky"),
])
def test_ngoai_hai_chau_khong_bat_co_va_client_khong_tu_bat(user, procedure):
    opts = with_account_process_options({HAI_CHAU_BHYT_OPTION: True}, user, procedure)
    assert HAI_CHAU_BHYT_OPTION not in opts


def test_hai_chau_chon_me_va_khong_dien_noi_kcb():
    rows = enrich([{"name": k, "value": v} for k, v in _HO_SO.items()], {HAI_CHAU_BHYT_OPTION: True})
    by = {f["name"]: f for f in rows}
    assert by["NguoiGiamHo"]["value"] == "Thông tin mẹ"
    assert "CskcbbdMa" not in by
    assert [f["name"] for f in rows].count("NguoiGiamHo") == 1
