"""Cột "Mối quan hệ" của datagrid thành viên gia đình + nhân thân người viết đơn (NOXH 1.012896).

Dòng (a) mục 9 của đơn in sẵn nhãn "Họ và tên vợ (hoặc chồng)" — không có gì trong đơn nói người đó là
vợ hay chồng (dân còn hay ghi bố/mẹ vào dòng này) → luôn trả nhãn gốc để cán bộ chọn. Dữ liệu giả.
"""

from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.process import mapper

# CCCD 12 số, chữ số thứ 4: chẵn = Nam, lẻ = Nữ.
_CCCD_NAM = "001060000001"
_CCCD_NU = "001165000002"
_CCCD_NU_2000 = "001304000003"


def _by_name(values):
    fields, _ = mapper.enrich([{"name": k, "value": v} for k, v in values.items()])
    return {(f["name"], f.get("occurrence")): f["value"] for f in fields}


def test_gender_from_cccd():
    assert mapper._gender_from_cccd(_CCCD_NAM) == "Nam"
    assert mapper._gender_from_cccd(_CCCD_NU) == "Nữ"
    assert mapper._gender_from_cccd(_CCCD_NU_2000) == "Nữ"
    # CMND 9 số / số rác không suy được → None, KHÔNG đoán bừa.
    assert mapper._gender_from_cccd("123456789") is None
    assert mapper._gender_from_cccd("") is None
    assert mapper._gender_from_cccd(None) is None


def test_dong_vo_chong_luon_tra_nhan_goc():
    for value in ("Vợ", "Chồng", "Vợ (hoặc chồng)", "vợ/chồng"):
        assert mapper._resolve_quan_he(value) == "Vợ (hoặc chồng)"


def test_cac_dong_khac_giu_nguyen_chu_nguoi_dan_viet():
    for value in ("Con", "Con dâu", "Con rể", "Con gái", "Cháu", "Cháu nội", "Mẹ"):
        assert mapper._resolve_quan_he(value) == value


def test_o_trong_van_de_trong():
    assert mapper._resolve_quan_he("") is None
    assert mapper._resolve_quan_he(None) is None


def test_datagrid_phat_dung_quan_he_cho_tung_dong():
    d = _by_name({
        "NguoiNop_HoTen": "NGUYỄN THỊ A",
        "NguoiNop_SoDinhDanh": _CCCD_NU_2000,
        "ThanhVienGiaDinh": [
            {"hoTen": "NGUYỄN VĂN B", "soCccd": _CCCD_NAM, "quanHe": "Vợ (hoặc chồng)"},
            {"hoTen": "TRẦN THỊ C", "soCccd": _CCCD_NU},
        ],
    })
    assert d[("data[dtgrid1][0][namsanxuat1]", None)] == "Vợ (hoặc chồng)"
    assert d[("data[dtgrid1][0][identityNumber1]", None)] == _CCCD_NAM
    # Dòng người dân không ghi quan hệ → ô quan hệ bỏ trống.
    assert ("data[dtgrid1][1][namsanxuat1]", None) not in d


def test_gioi_tinh_lech_cccd_thi_theo_cccd():
    d = _by_name({"NguoiNop_HoTen": "NGUYỄN THỊ A", "NguoiNop_SoDinhDanh": _CCCD_NU_2000, "NguoiNop_GioiTinh": "Nam"})
    assert d[("data[gender]", None)] == "Nữ"


def test_khong_co_cccd_12_so_thi_giu_gioi_tinh_llm():
    d = _by_name({"NguoiNop_HoTen": "NGUYỄN VĂN A", "NguoiNop_GioiTinh": "Nam"})
    assert d[("data[gender]", None)] == "Nam"


def test_ngay_sinh_chi_co_nam_thi_bo_trong():
    d = _by_name({"NguoiNop_HoTen": "NGUYỄN VĂN A", "NguoiNop_NgaySinh": "2004"})
    assert ("data[birthday]", None) not in d


def test_ngay_sinh_du_ngay_thang_thi_dien():
    d = _by_name({"NguoiNop_HoTen": "NGUYỄN VĂN A", "NguoiNop_NgaySinh": "6/5/2004"})
    assert d[("data[birthday]", None)] == "06/05/2004"


def test_prompt_cam_suy_quan_he_va_ghep_ngay_sinh():
    from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.process.prompt import EXTRA_RULES
    from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.process.schema import FIELDS

    assert "NHÃN IN SẴN" in EXTRA_RULES
    assert "Vợ (hoặc chồng)" in EXTRA_RULES
    assert "KHÔNG suy quan hệ từ năm sinh" in EXTRA_RULES
    assert "lấy ngày/tháng đầy đủ theo CCCD" not in EXTRA_RULES
    desc = {f["name"]: f["desc"] for f in FIELDS}
    assert "Vợ (hoặc chồng)" in desc["ThanhVienGiaDinh"]
    assert "Mẹ, Bố" not in desc["ThanhVienGiaDinh"]
    assert "KHÔNG ghép ngày/tháng" in desc["NguoiNop_NgaySinh"]
