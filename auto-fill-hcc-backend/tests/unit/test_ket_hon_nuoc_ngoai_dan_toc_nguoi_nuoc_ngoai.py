"""Dân tộc của người mang quốc tịch nước ngoài phải đi vào ô "Khác", không vào dropdown.

Dropdown dân tộc của cổng chỉ liệt kê 54 dân tộc VIỆT NAM. Trước đây chú rể Trung Quốc khai dân
tộc "Hán" bị cổng gom vào option "Hoa" (đúng nghĩa dân tộc học, SAI so với hộ chiếu đang cầm). Đúng
cách: chọn "Khác" rồi ghi nguyên văn vào ô nhập "Nhập dân tộc:" ngay bên cạnh.
"""

from app.pipelines.ket_hon_nuoc_ngoai.process.mapper import enrich


def _by_name(fields: list[dict]) -> dict[str, dict]:
    return {field["name"]: field for field in fields}


def _order(fields: list[dict]) -> list[str]:
    return [field["name"] for field in fields]


# Hồ sơ thật: cô dâu Việt Nam + chú rể Trung Quốc (hộ chiếu EN7660049).
_CHU_RE_TRUNG_QUOC = [
    {"name": "CccdNam_HoTen", "value": "Sun Ying xiang"},
    {"name": "CccdNam_NgaySinh", "value": "14/07/1991"},
    {"name": "CccdNam_DanToc", "value": "Hán"},
    {"name": "CccdNam_QuocTich", "value": "Trung Quốc"},
    {"name": "CccdNam_SoDinhDanh", "value": "EN7660049"},
    {"name": "CccdNam_TenGiayTo", "value": "Hộ chiếu"},
    {"name": "CccdNam_NgayCap", "value": "22/11/2024"},
    {"name": "CccdNam_NoiCap", "value": "Giang Tô"},
    {"name": "CccdNam_NoiCuTru",
     "value": {"quocGia": "Trung Quốc", "tinh": "Giang Tô", "xa": "", "diaChi": "Thường Hải"}},
]
_CO_DAU_VIET = [
    {"name": "CccdNu_HoTen", "value": "Nguyễn Thị Hường"},
    {"name": "CccdNu_NgaySinh", "value": "19/07/1998"},
    {"name": "CccdNu_DanToc", "value": "Kinh"},
    {"name": "CccdNu_QuocTich", "value": "Việt Nam"},
    {"name": "CccdNu_SoDinhDanh", "value": "024198012245"},
    {"name": "CccdNu_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "CccdNu_NgayCap", "value": "19/12/2024"},
    {"name": "CccdNu_NoiCuTru",
     "value": {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Hiệp Hòa", "diaChi": "Thôn Đông Lỗ"}},
]


def test_quoc_tich_nuoc_ngoai_thi_dan_toc_chon_khac():
    result = _by_name(enrich(_CO_DAU_VIET + _CHU_RE_TRUNG_QUOC))

    assert result["DanTocBenNam"]["value"] == "Khác"
    assert result["NhapDanTocBenNamKhac"]["value"] == "Hán", "Ghi nguyên văn, không quy về 'Hoa'"
    assert result["QuocTichBenNam"]["value"] == "Trung Quốc"


def test_o_nhap_phat_ngay_sau_dropdown():
    """Ô "Nhập dân tộc:" chỉ được cổng render SAU khi dropdown chọn "Khác"."""
    names = _order(enrich(_CO_DAU_VIET + _CHU_RE_TRUNG_QUOC))

    assert names.index("DanTocBenNam") + 1 == names.index("NhapDanTocBenNamKhac")


def test_ben_viet_nam_giu_nguyen_dropdown():
    result = _by_name(enrich(_CO_DAU_VIET + _CHU_RE_TRUNG_QUOC))

    assert result["DanTocBenNu"]["value"] == "Kinh"
    assert "NhapDanTocBenNuKhac" not in result


def test_nguoi_viet_cu_tru_nuoc_ngoai_van_dung_dropdown():
    """Chỉ xét QUỐC TỊCH: người Việt sống ở nước ngoài vẫn mang dân tộc Việt Nam."""
    fields = _CO_DAU_VIET + [
        {"name": "CccdNam_HoTen", "value": "Trần Văn Hải"},
        {"name": "CccdNam_SoDinhDanh", "value": "001091004567"},
        {"name": "CccdNam_DanToc", "value": "Kinh"},
        {"name": "CccdNam_QuocTich", "value": "Việt Nam"},
        {"name": "CccdNam_NoiCuTru",
         "value": {"quocGia": "Nhật Bản", "tinh": "Osaka", "xa": "", "diaChi": "Naniwa-ku"}},
    ]
    result = _by_name(enrich(fields))

    assert result["DanTocBenNam"]["value"] == "Kinh"
    assert "NhapDanTocBenNamKhac" not in result


def test_khong_ro_dan_toc_van_chon_khac_cho_nguoi_nuoc_ngoai():
    """Quốc tịch nước ngoài thì "Khác" luôn đúng; ô nhập để trống cho người dùng gõ."""
    fields = _CO_DAU_VIET + [f for f in _CHU_RE_TRUNG_QUOC if f["name"] != "CccdNam_DanToc"]
    result = _by_name(enrich(fields))

    assert result["DanTocBenNam"]["value"] == "Khác"
    assert "NhapDanTocBenNamKhac" not in result


def test_khong_ro_quoc_tich_thi_giu_hanh_vi_cu():
    """Không có quốc tịch trong hồ sơ → không suy bừa là người nước ngoài."""
    fields = _CO_DAU_VIET + [f for f in _CHU_RE_TRUNG_QUOC if f["name"] != "CccdNam_QuocTich"]
    result = _by_name(enrich(fields))

    assert result["DanTocBenNam"]["value"] == "Hán"
    assert "NhapDanTocBenNamKhac" not in result
