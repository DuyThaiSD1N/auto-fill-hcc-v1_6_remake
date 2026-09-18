"""Cột "Mối quan hệ" của datagrid thành viên gia đình (NOXH 1.012896).

Dòng (a) mục 9 của đơn in sẵn nhãn "Họ và tên vợ (hoặc chồng)" — không có gì trong đơn nói người đó là
vợ hay chồng. Mặc định "Vợ" là bịa. Chốt lại bằng chữ số thứ 4 của CCCD (mã giới tính).
"""

import inspect

from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.process import mapper

# CCCD 12 số, chữ số thứ 4: chẵn = Nam, lẻ = Nữ.
_CCCD_NAM = "049061002750"
_CCCD_NU = "040168007428"
_CCCD_NU_2 = "049304012492"


def test_gender_from_cccd():
    assert mapper._gender_from_cccd(_CCCD_NAM) == "Nam"
    assert mapper._gender_from_cccd(_CCCD_NU) == "Nữ"
    # CMND 9 số / số rác không suy được → None, KHÔNG đoán bừa.
    assert mapper._gender_from_cccd("123456789") is None
    assert mapper._gender_from_cccd("") is None
    assert mapper._gender_from_cccd(None) is None


def test_cccd_nam_o_dong_vo_chong_phai_ra_chong():
    assert mapper._resolve_quan_he("Vợ", _CCCD_NAM, _CCCD_NU_2) == "Chồng"


def test_cccd_nu_o_dong_vo_chong_van_ra_vo():
    assert mapper._resolve_quan_he("Vợ", _CCCD_NU, _CCCD_NAM) == "Vợ"


def test_nhan_day_du_tu_llm_cung_duoc_chot_lai():
    assert mapper._resolve_quan_he("Vợ (hoặc chồng)", _CCCD_NAM, None) == "Chồng"
    assert mapper._resolve_quan_he("vợ/chồng", _CCCD_NU, None) == "Vợ"


def test_thieu_cccd_thanh_vien_thi_dao_vai_theo_nguoi_viet_don():
    assert mapper._resolve_quan_he("Vợ (hoặc chồng)", "", _CCCD_NAM) == "Vợ"
    assert mapper._resolve_quan_he("Vợ (hoặc chồng)", None, _CCCD_NU) == "Chồng"


def test_khong_co_cccd_nao_thi_giu_nhan_in_tren_don_khong_mac_dinh_vo():
    assert mapper._resolve_quan_he("Vợ", None, None) == "Vợ (hoặc chồng)"
    assert mapper._resolve_quan_he("Chồng", None, None) == "Vợ (hoặc chồng)"


def test_cac_dong_khac_giu_nguyen_chu_nguoi_dan_viet():
    for value in ("Con", "Con dâu", "Con rể", "Con gái", "Cháu", "Cháu nội", "Mẹ"):
        assert mapper._resolve_quan_he(value, _CCCD_NAM, _CCCD_NU) == value


def test_o_trong_van_de_trong():
    assert mapper._resolve_quan_he("", _CCCD_NAM, _CCCD_NU) is None
    assert mapper._resolve_quan_he(None, _CCCD_NAM, _CCCD_NU) is None


def test_datagrid_phat_dung_quan_he_cho_tung_dong():
    fields, _ = mapper.enrich([
        {"name": "NguoiNop_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "NguoiNop_SoDinhDanh", "value": _CCCD_NU_2},
        {"name": "ThanhVienGiaDinh", "value": [
            {"hoTen": "LÊ VĂN DŨNG", "soCccd": _CCCD_NAM, "quanHe": "Vợ"},
            {"hoTen": "LÊ THỊ B", "soCccd": _CCCD_NU, "quanHe": "Con gái"},
        ]},
    ])
    by_name = {f["name"]: f["value"] for f in fields}

    assert by_name["data[dtgrid1][0][namsanxuat1]"] == "Chồng"
    assert by_name["data[dtgrid1][1][namsanxuat1]"] == "Con gái"
    assert by_name["data[dtgrid1][0][identityNumber1]"] == _CCCD_NAM


def test_khong_doan_quan_he_theo_ten_dem():
    """"Văn"/"Thị" trong tên KHÔNG được dùng làm bằng chứng giới tính."""
    src = inspect.getsource(mapper._quan_he_vo_chong) + inspect.getsource(mapper._resolve_quan_he)
    assert "Thị" not in src and "hoTen" not in src


def test_prompt_cam_tu_chon_mot_nua_nhan_in_san():
    from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.process.prompt import EXTRA_RULES
    from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.process.schema import FIELDS

    assert "NHÃN IN SẴN" in EXTRA_RULES
    assert "Vợ (hoặc chồng)" in EXTRA_RULES
    desc = next(f["desc"] for f in FIELDS if f["name"] == "ThanhVienGiaDinh")
    assert "Vợ (hoặc chồng)" in desc
