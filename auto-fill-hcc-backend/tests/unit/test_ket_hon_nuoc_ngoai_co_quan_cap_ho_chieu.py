"""Ô "Cơ quan cấp" hỏi CƠ QUAN, không hỏi địa danh.

Hộ chiếu Trung Quốc in HAI dòng rất dễ lẫn:
    "Nơi cấp / Place of issue: Giang Tô"                             ← ĐỊA DANH
    "Cơ quan có thẩm quyền cấp hộ chiếu: Cục Quản lý Di dân Quốc gia
     nước Cộng hòa Nhân dân Trung Hoa"                               ← CƠ QUAN
Field tên là *_NoiCap nên agent bám vào dòng đầu, cổng ra "Cơ quan cấp: Giang Tô". Tên tỉnh nằm ở
ô cơ quan trông vẫn "có dữ liệu" nên người soát hồ sơ dễ cho qua — phải chặn tất định.
"""

from app.pipelines.ket_hon_nuoc_ngoai.process import mapper, prompt, schema
from app.pipelines.ket_hon_nuoc_ngoai.process.mapper import _looks_like_issuer, enrich


def _by_name(fields: list[dict]) -> dict[str, dict]:
    return {field["name"]: field for field in fields}


# Hồ sơ thật: cô dâu Việt Nam + chú rể Trung Quốc (hộ chiếu EN7660049).
_CO_DAU_VIET = [
    {"name": "CccdNu_HoTen", "value": "Nguyễn Thị Hương"},
    {"name": "CccdNu_SoDinhDanh", "value": "024198012215"},
    {"name": "CccdNu_QuocTich", "value": "Việt Nam"},
    {"name": "CccdNu_NgayCap", "value": "17/12/2021"},
    {"name": "CccdNu_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
]


def _chu_re(noi_cap):
    return [
        {"name": "CccdNam_HoTen", "value": "Sun Ying xiang"},
        {"name": "CccdNam_SoDinhDanh", "value": "EN7660049"},
        {"name": "CccdNam_QuocTich", "value": "Trung Quốc"},
        {"name": "CccdNam_TenGiayTo", "value": "Hộ chiếu"},
        {"name": "CccdNam_NgayCap", "value": "22/11/2024"},
        {"name": "CccdNam_NoiCap", "value": noi_cap},
    ]


_CO_QUAN = "Cục Quản lý Di dân Quốc gia nước Cộng hòa Nhân dân Trung Hoa"


def test_co_quan_cap_ho_chieu_duoc_giu_nguyen_van():
    result = _by_name(enrich(_CO_DAU_VIET + _chu_re(_CO_QUAN)))

    assert result["NoiCapDD_BenNam"]["value"] == _CO_QUAN


def test_dia_danh_khong_duoc_dien_vao_o_co_quan_cap():
    """Ca hỏng thật: agent đọc dòng "Nơi cấp: Giang Tô" thay vì dòng cơ quan."""
    result = _by_name(enrich(_CO_DAU_VIET + _chu_re("Giang Tô")))

    assert "NoiCapDD_BenNam" not in result, "Tên tỉnh không phải cơ quan cấp"
    assert result["HoTenBenNam"]["value"] == "Sun Ying xiang", "Các ô còn lại vẫn phải điền"
    assert result["SoDinhDanh_BenNam"]["value"] == "EN7660049"


def test_co_quan_cap_cua_chung_minh_thu_van_qua():
    """Thẻ 居民身份证 ghi "Cơ quan cấp phép: Phân cục Công an Cao Thuần" — vẫn là cơ quan."""
    co_quan = "Phân cục Công an Cao Thuần, thành phố Nam Kinh"
    result = _by_name(enrich(_CO_DAU_VIET + _chu_re(co_quan)))

    assert result["NoiCapDD_BenNam"]["value"] == co_quan


def test_ben_viet_nam_khong_bi_anh_huong():
    result = _by_name(enrich(_CO_DAU_VIET + _chu_re("Giang Tô")))

    assert result["NoiCapDD_BenNu"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"


def test_nhan_dien_co_quan_theo_tu_chi_vai_tro():
    """Tên cơ quan ở mọi nước đều mang một từ chỉ vai trò; địa danh trơ trọi thì không."""
    for value in (_CO_QUAN, "Bộ Công an", "Ministry of Foreign Affairs",
                  "National Immigration Administration", "Phân cục Công an Cao Thuần"):
        assert _looks_like_issuer(value) is True, value
    for value in ("Giang Tô", "Nam Kinh", "Vân Nam", "", None):
        assert _looks_like_issuer(value) is False, value


def test_schema_va_prompt_deu_canh_bao_bay_hai_dong_cua_ho_chieu():
    """Chốt chặn ở mapper chỉ biến giá trị sai thành ô trống; muốn ĐÚNG thì agent phải đọc đúng."""
    descs = {f["name"]: f["desc"] for f in schema.FIELDS}
    for name in ("CccdNam_NoiCap", "CccdNu_NoiCap"):
        assert "Cơ quan có thẩm quyền cấp hộ chiếu" in descs[name], name
        assert "Place of issue" in descs[name], name
    assert "Cơ quan có thẩm quyền cấp hộ chiếu" in prompt.EXTRA_RULES
    assert "Giang Tô" in prompt.EXTRA_RULES, "Phải có ví dụ ca hỏng thật trong prompt"
