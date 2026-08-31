"""Map compact facts của kết hôn CÓ YẾU TỐ NƯỚC NGOÀI → field UI.

Hồ sơ mẫu: vợ Việt Nam (đã ly hôn theo bản án của Tòa án, kết hôn lần 2) + chồng Trung Quốc
(chứng minh thư + hộ chiếu, dân tộc Hán).
"""

from app.pipelines.ket_hon_nuoc_ngoai.process import mapper, schema
from app.pipelines.ket_hon_nuoc_ngoai.process.prompt import EXTRA_RULES

_VO = {  # bên nữ — người Việt Nam, đã ly hôn
    "CccdNu_HoTen": "NGUYỄN THỊ HƯƠNG",
    "CccdNu_SoDinhDanh": "024198012215",
    "CccdNu_NgaySinh": "19/07/1998",
    "CccdNu_NgayCap": "17/12/2021",
    "CccdNu_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "CccdNu_QuocTich": "Việt Nam",
    "CccdNu_DanToc": "Kinh",
    "CccdNu_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Hiệp Hòa",
                        "diaChi": "Thôn Đông Vân"},
    "CccdNu_SoLanKetHon": "2",
    "CccdNu_TinhTrangHonNhan": "ly_hon",
    "CccdNu_BanAnLyHon_So": "65/2024/HNGĐ-ST",
    "CccdNu_BanAnLyHon_Ngay": "27/12/2024",
    "CccdNu_BanAnLyHon_CoQuan": "Tòa án nhân dân huyện Hiệp Hòa, tỉnh Bắc Giang",
}
_CHONG = {  # bên nam — người Trung Quốc
    "CccdNam_HoTen": "SUN YINGXIANG",
    "CccdNam_SoDinhDanh": "EN7660049",
    "CccdNam_NgaySinh": "14/07/1991",
    "CccdNam_NgayCap": "22/11/2024",
    "CccdNam_NoiCap": "Giang Tô",
    "CccdNam_QuocTich": "Trung Quốc",
    "CccdNam_DanToc": "Hán",
    "CccdNam_TenGiayTo": "Hộ chiếu",
    "CccdNam_NoiCuTru": {"quocGia": "Trung Quốc", "tinh": "", "xa": "",
                         "diaChi": "Số 52, Từ Gia, thôn Thương Khê, trấn Dương Giang, "
                                   "quận Cao Thuần, thành phố Nam Kinh"},
    "CccdNam_SoLanKetHon": "1",
}


def _fields(*dicts):
    merged = {}
    for d in dicts:
        merged.update(d)
    return [{"name": k, "value": v} for k, v in merged.items()]


def _by_name(out):
    return {f["name"]: f["value"] for f in out}


def test_ban_an_ly_hon_duoc_dien_khi_da_ly_hon():
    out = mapper.enrich(_fields(_VO, _CHONG))
    values = _by_name(out)

    assert values["LoaiTinhTrangHonNhan_BenNu"].startswith(
        "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng đã ly hôn"
    )
    assert values["TTHN_LyHonBenNu"] == {
        "soBanAnQuyetDinhLyHon": "65/2024/HNGĐ-ST",
        "ngayCapBanAnQuyetDinhLyHon": "27/12/2024",
        "coQuanCapBanAnQuyetDinhLyHon": "Tòa án nhân dân huyện Hiệp Hòa, tỉnh Bắc Giang",
    }
    # Khối bản án chỉ được cổng render SAU khi dropdown tình trạng hôn nhân chọn xong.
    names = [f["name"] for f in out]
    assert names.index("TTHN_LyHonBenNu") > names.index("LoaiTinhTrangHonNhan_BenNu")
    comps = {f["name"]: f["comp"] for f in out}
    assert comps["TTHN_LyHonBenNu"] == "x-select-area"

    # Bên nam chưa từng kết hôn → không có khối bản án nào.
    assert "TTHN_LyHonBenNam" not in values


def test_khong_co_ban_an_thi_khong_dien_khoi_ly_hon():
    vo = {k: v for k, v in _VO.items() if not k.startswith("CccdNu_BanAnLyHon")}
    values = _by_name(mapper.enrich(_fields(vo, _CHONG)))
    assert "TTHN_LyHonBenNu" not in values


def test_dan_toc_nuoc_ngoai_giu_nguyen():
    """Dân tộc chồng người Trung Quốc là "Hán" (extension chọn option "Hán (Hoa)")."""
    values = _by_name(mapper.enrich(_fields(_VO, _CHONG)))
    assert values["DanTocBenNam"] == "Hán"
    assert values["DanTocBenNu"] == "Kinh"


def test_schema_khai_bao_du_field_ban_an():
    for side in ("CccdNam", "CccdNu"):
        assert f"{side}_BanAnLyHon_So" in schema.ALLOWED
        assert f"{side}_BanAnLyHon_CoQuan" in schema.ALLOWED
        assert schema.COMPACT_COMP_BY_NAME[f"{side}_BanAnLyHon_Ngay"] == "x-date"
    assert schema.UI_COMP_BY_NAME["TTHN_LyHonBenNam"] == "x-select-area"
    assert schema.UI_COMP_BY_NAME["TTHN_LyHonBenNu"] == "x-select-area"
    assert "BẢN ÁN/QUYẾT ĐỊNH LY HÔN" in EXTRA_RULES
