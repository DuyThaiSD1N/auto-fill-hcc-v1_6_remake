"""Bên nam/nữ trùng chủ tài khoản đăng nhập → điền lại theo dữ liệu tài khoản (3 thủ tục kết hôn)."""
import pytest

from app.pipelines.ket_hon.process import mapper as ket_hon
from app.pipelines.ket_hon_lai.process import mapper as ket_hon_lai
from app.pipelines.ket_hon_nuoc_ngoai.process import mapper as ket_hon_nuoc_ngoai

_NAM = {
    "CccdNam_HoTen": "TRẦN VĂN AN",
    "CccdNam_SoDinhDanh": "012086005221",
    "CccdNam_NgaySinh": "01/01/1986",
    "CccdNam_NgayCap": "06/01/2022",
    "CccdNam_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "CccdNam_NoiCuTru_TrongNuoc": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Tân Phong", "diaChi": "Tổ 1"},
}
_NU = {
    "CccdNu_HoTen": "LÊ THỊ BÌNH",
    "CccdNu_SoDinhDanh": "012189003303",
    "CccdNu_NgaySinh": "02/02/1989",
    "CccdNu_NgayCap": "16/03/2024",
    "CccdNu_NoiCap": "Bộ Công an",
}
# Tài khoản = bên nam, nhưng OCR đọc lệch tên/ngày cấp; tài khoản có thêm dân tộc, nơi cư trú.
_ACCOUNT_NAM = {"formContext": {
    "applicantFullname": "Trần Văn Ân",
    "applicantIdentityNumber": "012086005221",
    "applicantBirthday": "01/01/1986",
    "applicantGender": "Nam",
    "applicantEthnicity": "Tày",
    "applicantIdDate": "16/01/2022",
    "applicantIdIssuer": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "applicantAddress": {"tinh": "Lai Châu", "xa": "Đoàn Kết", "diaChi": "Số 5"},
}}

MAPPERS = [ket_hon, ket_hon_lai, ket_hon_nuoc_ngoai]


def _fields(*dicts):
    return [{"name": k, "value": v} for d in dicts for k, v in d.items()]


def _values(out):
    return {f["name"]: f["value"] for f in out}


@pytest.mark.parametrize("mapper", MAPPERS)
def test_ben_nam_trung_tai_khoan_ghi_de_toan_bo(mapper):
    out = _values(mapper.enrich(_fields(_NAM, _NU), _ACCOUNT_NAM))
    assert out["HoTenBenNam"] == "TRẦN VĂN ÂN"
    assert out["SoDinhDanh_BenNam"] == out["SoGiayToDinhDanh_BenNam"] == "012086005221"
    assert out["NgayCapDD_BenNam"] == "16/01/2022"
    assert out["DanTocBenNam"] == "Tày"
    assert out["NoiCuTru_BenNam"] == "1"
    assert out["NoiCuTru_BenNam_TrongNuoc"]["diaChi"] == "Số 5"
    # Bên nữ không đụng.
    assert out["HoTenBenNu"] == "LÊ THỊ BÌNH"
    assert out["NgayCapDD_BenNu"] == "16/03/2024"


@pytest.mark.parametrize("mapper", MAPPERS)
def test_ben_nu_khop_theo_ten_va_ngay_sinh(mapper):
    account = {"formContext": {"applicantFullname": "Lê Thị Bình", "applicantBirthday": "02/02/1989",
                               "applicantIdentityNumber": "012189003309", "applicantIdDate": "20/03/2024"}}
    out = _values(mapper.enrich(_fields(_NAM, _NU), account))
    assert out["SoDinhDanh_BenNu"] == "012189003309"
    assert out["NgayCapDD_BenNu"] == "20/03/2024"
    assert out["HoTenBenNam"] == "TRẦN VĂN AN"


@pytest.mark.parametrize("mapper", MAPPERS)
def test_tai_khoan_nguoi_khac_khong_doi(mapper):
    account = {"formContext": {"applicantFullname": "Phạm Văn Cường", "applicantIdentityNumber": "001090000001",
                               "applicantBirthday": "03/03/1990"}}
    assert mapper.enrich(_fields(_NAM, _NU), account) == mapper.enrich(_fields(_NAM, _NU))


@pytest.mark.parametrize("mapper", MAPPERS)
def test_gioi_tinh_trai_ben_khong_doi(mapper):
    account = {"formContext": {**_ACCOUNT_NAM["formContext"], "applicantGender": "Nữ"}}
    assert mapper.enrich(_fields(_NAM, _NU), account) == mapper.enrich(_fields(_NAM, _NU))


def test_so_lech_mot_chu_so_van_khop_khi_ten_gan_giong():
    account = {"formContext": {**_ACCOUNT_NAM["formContext"], "applicantIdentityNumber": "012086005228"}}
    out = _values(ket_hon.enrich(_fields(_NAM, _NU), account))
    assert out["SoDinhDanh_BenNam"] == "012086005228"
