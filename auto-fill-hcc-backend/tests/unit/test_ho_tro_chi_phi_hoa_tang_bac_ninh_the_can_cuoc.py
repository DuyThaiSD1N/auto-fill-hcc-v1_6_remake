"""Hỏa táng Bắc Ninh: họ tên / ngày sinh theo bản sao CCCD in máy cùng số định danh."""

from app.pipelines.ho_tro_chi_phi_hoa_tang_bac_ninh.process import the_can_cuoc as tc

_CARD = (
    "───── Trang 1/2 ─────\nCĂN CƯỚC CÔNG DÂN\nCitizen Identity Card\nSố / No.: 027175000001\n"
    "Họ và tên / Full name: TRẦN THỊ BẮC\nNgày sinh / Date of birth: 06/07/1975\n"
    "Ngày, tháng, năm / Date, month, year: 14/04/2021\n"
    "IDVNM1750000011027175000001<<1\n7507092F3507094VNM<<<<<<<<<<<<<<6\nTRAN<<THI<BAC<CNHO<SAO<ĐÚNG\n"
)


def _apply(values):
    return {f["name"]: f["value"] for f in tc.apply([{"name": k, "value": v} for k, v in values.items()], _CARD)}


def test_ho_ten_lech_chu_cai_theo_the_khi_mrz_xac_nhan():
    out = _apply({"NguoiDungRa_HoTen": "Trần Thị Bầu", "NguoiDungRa_SoDinhDanh": "027175000001",
                  "NguoiDungRa_NgayCap": "14/04/2020"})
    assert out["NguoiDungRa_HoTen"] == "TRẦN THỊ BẮC"
    # Ngày cấp không lấy theo thẻ: cán bộ giữ theo Đơn.
    assert out["NguoiDungRa_NgayCap"] == "14/04/2020"


def test_ho_ten_chi_lech_dau_thi_giu_nguyen():
    out = _apply({"NguoiDungRa_HoTen": "Trần Thị Bác", "NguoiDungRa_SoDinhDanh": "027175000001"})
    assert out["NguoiDungRa_HoTen"] == "Trần Thị Bác"


def test_khong_co_the_cung_so_thi_giu_nguyen():
    out = _apply({"NguoiDungRa_HoTen": "Trần Thị Bầu", "NguoiDungRa_SoDinhDanh": "027175000002"})
    assert out["NguoiDungRa_HoTen"] == "Trần Thị Bầu"


def test_ngay_sinh_theo_mrz():
    out = _apply({"NguoiUyQuyen_HoTen": "Trần Thị Bắc", "NguoiUyQuyen_SoDinhDanh": "027175000001",
                  "NguoiUyQuyen_NgaySinh": "06/07/1975"})
    assert out["NguoiUyQuyen_NgaySinh"] == "09/07/1975"


def test_dien_dot_hai_form_bac_ninh_can_nang_luc_rieng():
    from app.channels.handfree.chat.router import _clean_client_capabilities
    from app.second_pass import service

    assert service.capability({"secondPass": "bacninh"}) == "secondPassBacNinh"
    assert _clean_client_capabilities({"supportsSecondPassBacNinh": True})["supportsSecondPassBacNinh"] is True
    assert _clean_client_capabilities({})["supportsSecondPassBacNinh"] is False
