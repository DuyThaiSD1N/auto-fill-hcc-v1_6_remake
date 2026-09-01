"""Hồ sơ "CCCD + GIẤY KHAI SINH của chính người đăng nhập" chỉ nói về MỘT người.

Người đó vừa là NGƯỜI YÊU CẦU (mục I) vừa là NGƯỜI ĐƯỢC CẤP (mục II) → ô quan hệ tick "Bản thân".
Giấy khai sinh còn in tên cha, tên mẹ (trích lục mẫu mới in cả số định danh của cha/mẹ) nên agent
hay đẩy họ sang khối "người yêu cầu" hoặc "người được cấp"; lọt là mục I/II mang tên cha/mẹ.
"""

from app.pipelines.xac_nhan_tthn.process.mapper import enrich


def _by_name(fields: list[dict]) -> dict[str, dict]:
    return {field["name"]: field for field in fields}


_NGUOI_DANG_NHAP = {"formContext": {
    "applicantFullname": "NGUYỄN HOÀI NAM",
    "applicantIdentityNumber": "001066023420",
}}

_CCCD = [
    {"name": "Cccd_HoTen", "value": "NGUYỄN HOÀI NAM"},
    {"name": "Cccd_SoDinhDanh", "value": "001066023420"},
    {"name": "Cccd_NgaySinh", "value": "30/07/1966"},
    {"name": "Cccd_NgayCap", "value": "16/07/2026"},
    {"name": "Cccd_NoiCap", "value": "Bộ Công an"},
    {"name": "Cccd_NoiCuTru",
     "value": {"quocGia": "Việt Nam", "tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu",
               "diaChi": "K57/10 Nguyễn Chí Thanh"}},
]
_GKS = [
    {"name": "Gks_HoTen", "value": "Nguyễn Hoài Nam"},
    {"name": "Gks_NgaySinh", "value": "30/07/1966"},
    {"name": "Gks_GioiTinh", "value": "Nam"},
    {"name": "Gks_DanToc", "value": "Kinh"},
    {"name": "Gks_QuocTich", "value": "Việt Nam"},
    {"name": "Gks_ChaHoTen", "value": "Nguyễn Văn Bảy"},
    {"name": "Gks_MeHoTen", "value": "Trần Thị Tám"},
]


def test_cccd_va_gks_cung_nguoi_thi_muc_i_va_muc_ii_deu_la_nguoi_do():
    result = _by_name(enrich(_CCCD + _GKS, _NGUOI_DANG_NHAP))

    assert result["HoVaTenC"]["value"] == "NGUYỄN HOÀI NAM"
    assert result["SoDinhDanhC"]["value"] == "001066023420"
    assert result["HoVaTenC1"]["value"] == "NGUYỄN HOÀI NAM"
    assert result["SoDinhDanhC1"]["value"] == "001066023420"
    assert result["quanhevoinguoiduocxacminh"]["value"] == "1"
    assert "quanhekhac" not in result


def test_ten_me_tren_gks_khong_duoc_thanh_nguoi_yeu_cau():
    """Ca hỏng: agent đọc "Người mẹ" thành khối người yêu cầu, kèm cả số định danh của mẹ."""
    fields = _CCCD + _GKS + [
        {"name": "ToKhaiYeuCau_HoTen", "value": "Trần Thị Tám"},
        {"name": "ToKhaiYeuCau_SoDinhDanh", "value": "001140009999"},
    ]
    result = _by_name(enrich(fields, _NGUOI_DANG_NHAP))

    assert result["HoVaTenC"]["value"] == "NGUYỄN HOÀI NAM", "Mục I không được mang tên mẹ"
    assert result["SoDinhDanhC"]["value"] == "001066023420"
    assert result["quanhevoinguoiduocxacminh"]["value"] == "1"
    assert "quanhekhac" not in result


def test_ten_cha_tren_gks_khong_duoc_thanh_nguoi_duoc_cap():
    """Cùng ca đó nhưng agent đẩy tên cha sang khối "người được cấp" (mục II)."""
    fields = _CCCD + _GKS + [
        {"name": "ToKhai_HoTen", "value": "Nguyễn Văn Bảy"},
        {"name": "ToKhai_SoDinhDanh", "value": "001140001111"},
    ]
    result = _by_name(enrich(fields, _NGUOI_DANG_NHAP))

    assert result["HoVaTenC1"]["value"] == "NGUYỄN HOÀI NAM", "Mục II không được mang tên cha"
    assert result["SoDinhDanhC1"]["value"] == "001066023420"
    assert result["quanhevoinguoiduocxacminh"]["value"] == "1"


def test_gks_bu_dan_toc_cho_the_can_cuoc_mau_moi():
    """Thẻ căn cước mẫu mới không in dân tộc — giấy khai sinh là nguồn duy nhất."""
    result = _by_name(enrich(_CCCD + _GKS, _NGUOI_DANG_NHAP))

    assert result["DanTocC1"]["value"] == "Kinh"
    assert result["GioiTinhC1"]["value"] == "Nam"


def test_to_khai_that_co_dong_quan_he_van_thang_gks():
    """Có TỜ KHAI thật ghi rõ quan hệ (trường hợp C) thì không được dọn khối người yêu cầu."""
    fields = _CCCD + _GKS + [
        {"name": "ToKhaiYeuCau_HoTen", "value": "Nguyễn Thị Lan"},
        {"name": "ToKhaiYeuCau_SoDinhDanh", "value": "001199004567"},
        {"name": "ToKhaiYeuCau_QuanHe", "value": "là con đẻ"},
        {"name": "ToKhai_HoTen", "value": "NGUYỄN HOÀI NAM"},
        {"name": "ToKhai_SoDinhDanh", "value": "001066023420"},
    ]
    result = _by_name(enrich(fields, _NGUOI_DANG_NHAP))

    assert result["HoVaTenC"]["value"] == "Nguyễn Thị Lan"
    assert result["quanhevoinguoiduocxacminh"]["value"] == "2"
    assert result["quanhekhac"]["value"] == "Con đẻ"


def test_gks_cua_nguoi_khac_khong_bi_coi_la_ho_so_mot_nguoi():
    """GKS của con kèm CCCD của bố: người được khai sinh KHÁC chủ thẻ → không dọn khối nào."""
    fields = _CCCD + [
        {"name": "Gks_HoTen", "value": "Nguyễn Hoài An"},
        {"name": "Gks_ChaHoTen", "value": "Nguyễn Hoài Nam"},
        {"name": "Gks_MeHoTen", "value": "Trần Thị Tám"},
        {"name": "ToKhaiYeuCau_HoTen", "value": "Nguyễn Thị Lan"},
        {"name": "ToKhaiYeuCau_SoDinhDanh", "value": "001199004567"},
        {"name": "ToKhaiYeuCau_NgayCapGiayTo", "value": "02/03/2022"},
        {"name": "ToKhai_HoTen", "value": "NGUYỄN HOÀI NAM"},
        {"name": "ToKhai_SoDinhDanh", "value": "001066023420"},
    ]
    result = _by_name(enrich(fields, _NGUOI_DANG_NHAP))

    assert result["HoVaTenC"]["value"] == "Nguyễn Thị Lan"
    assert result["quanhevoinguoiduocxacminh"]["value"] == "2"


def test_uy_quyen_khong_bi_gks_lam_lech():
    """Có giấy ủy quyền thì mục II vẫn là người ủy quyền, GKS không được chen vào."""
    fields = _CCCD + _GKS + [
        {"name": "PoA_SubjectName", "value": "NGUYỄN THỊ HOA"},
        {"name": "PoA_SubjectIdNumber", "value": "001165000999"},
    ]
    result = _by_name(enrich(fields, _NGUOI_DANG_NHAP))

    assert result["HoVaTenC1"]["value"] == "NGUYỄN THỊ HOA"
    assert result["quanhevoinguoiduocxacminh"]["value"] == "2"
