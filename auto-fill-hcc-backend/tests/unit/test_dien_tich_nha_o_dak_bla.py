"""Xác nhận điều kiện diện tích nhà ở thường trú: phường Đăk Bla chỉ ghi tên thủ tục ở nội dung yêu cầu giải quyết."""

import pytest

from app.pipelines.xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru.process import mapper
from app.pipelines.xac_nhan_dieu_kien_dien_tich_nha_o_dang_ky_thuong_tru.process.schema import TEN_THU_TUC

KEY = mapper.PROCEDURE_KEY
_FIELDS = [
    {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
    {"name": "ToKhai_TinhTrangChoO", "value": "Không tranh chấp"},
    {"name": "ToKhai_SoNguoiThueMuon", "value": "01"},
]


def _content(options):
    fields, _ = mapper.enrich(_FIELDS, options)
    return {f["name"]: f["value"] for f in fields}["data[noidungyeucaugiaiquyet]"]


@pytest.mark.parametrize("user", [
    {"tinh": "Tỉnh Quảng Ngãi", "xa": "Phường Đăk Bla"},
    {"tinh": "Quảng Ngãi", "xa": "Đắk Bla"},
    {"tinh": "Kon Tum", "xa": "phường đăk bla"},
])
def test_dak_bla_chi_ghi_ten_thu_tuc(user):
    assert _content(mapper.with_account_process_options({}, user, KEY)) == TEN_THU_TUC


@pytest.mark.parametrize("user", [
    None,
    {"tinh": "Quảng Ngãi", "xa": "Phường Kon Tum"},
    {"tinh": "Gia Lai", "xa": "Xã Đăk Bla"},
])
def test_noi_khac_giu_noi_dung_muc_iii(user):
    content = _content(mapper.with_account_process_options({}, user, KEY))
    assert content.startswith(TEN_THU_TUC + ". ") and "Tổng số người thuê, mượn, ở nhờ: 01" in content


def test_co_chi_do_server_dat_va_chi_cho_dung_thu_tuc():
    assert mapper.TITLE_ONLY_OPTION not in mapper.with_account_process_options(
        {mapper.TITLE_ONLY_OPTION: True}, {"tinh": "Gia Lai", "xa": "X"}, KEY
    )
    assert mapper.TITLE_ONLY_OPTION not in mapper.with_account_process_options(
        {}, {"tinh": "Quảng Ngãi", "xa": "Đăk Bla"}, "thu-tuc-khac"
    )
