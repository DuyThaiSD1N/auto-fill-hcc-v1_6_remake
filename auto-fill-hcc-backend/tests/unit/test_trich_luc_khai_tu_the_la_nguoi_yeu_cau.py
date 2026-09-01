"""Trích lục khai tử: người được đăng ký ĐÃ CHẾT nên CCCD trong hồ sơ là của NGƯỜI YÊU CẦU.

Hồ sơ thật: trích lục khai tử của NGUYỄN THỊ NGÂN (1928) + CCCD của VŨ THỊ PHƯƠNG đi xin bản sao,
tài khoản VNeID đăng nhập lại là NGUYỄN DUY THÁI (nộp hộ). Agent nhét thẻ vào ChuThe_* vì không thấy
mỏ neo nào khớp → mục I bị bỏ trống và cổng giữ nguyên người đăng nhập. Mapper phải đổi vai lại.
"""

from app.pipelines.trich_luc.process import mapper

_NOI_CU_TRU_NGUOI_MAT = {
    "quocGia": "Việt Nam", "tinh": "Bắc Giang", "xa": "Hoàng Văn Thụ",
    "diaChi": "Tổ dân phố Hoàng Hoa Thám 2",
}

# Đúng payload LLM trả về cho hồ sơ này (rút gọn phần không liên quan tới phân vai).
_HO_SO = [
    {"name": "ToKhai_LoaiSuKien", "value": "death"},
    {"name": "ToKhai_TenGiayTo", "value": "Trích lục khai tử"},
    {"name": "ToKhai_HoTenNguoiDuocCap", "value": "NGUYỄN THỊ NGÂN"},
    {"name": "HoTich_LoaiSuKien", "value": "death"},
    {"name": "HoTich_TenGiayTo", "value": "Trích lục khai tử"},
    {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGUYỄN THỊ NGÂN"},
    {"name": "HoTich_NgaySinh", "value": "1928"},
    {"name": "HoTich_GioiTinh", "value": "Nữ"},
    {"name": "HoTich_DanToc", "value": "Kinh"},
    {"name": "HoTich_QuocTich", "value": "Việt Nam"},
    {"name": "HoTich_SoGiayToTuyThan", "value": "120018017"},
    {"name": "HoTich_NgayCapGiayToTuyThan", "value": "04/05/2017"},
    {"name": "HoTich_NoiCapGiayToTuyThan", "value": "Công an tỉnh Bắc Giang"},
    {"name": "HoTich_NoiCuTru", "value": _NOI_CU_TRU_NGUOI_MAT},
    {"name": "HoTich_CoQuanDangKy",
     "value": "UBND phường Hoàng Văn Thụ, thành phố Bắc Giang, tỉnh Bắc Giang"},
    {"name": "HoTich_So", "value": "28"},
    {"name": "HoTich_NgayDangKy", "value": "01/06/2022"},
    # Thẻ của người đi xin — agent gán nhầm sang ChuThe_*.
    {"name": "ChuThe_HoTen", "value": "VŨ THỊ PHƯƠNG"},
    {"name": "ChuThe_SoDinhDanh", "value": "020152000758"},
    {"name": "ChuThe_NgaySinh", "value": "01/09/1952"},
    {"name": "ChuThe_GioiTinh", "value": "Nữ"},
    {"name": "ChuThe_QuocTich", "value": "Việt Nam"},
    {"name": "ChuThe_LoaiGiayTo", "value": "Căn cước công dân"},
    {"name": "ChuThe_NgayCap", "value": "27/04/2021"},
    {"name": "ChuThe_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "ChuThe_NoiCuTru", "value": {
        "quocGia": "Việt Nam", "tinh": "Bắc Giang", "xa": "Hoàng Văn Thụ", "diaChi": ""}},
]

_VNEID_NGUOI_NOP_HO = {"formContext": {
    "applicantFullname": "NGUYỄN DUY THÁI",
    "applicantIdentityNumber": "001204018566",
}}


def _enrich(fields, options=None):
    return {f["name"]: f["value"] for f in mapper.enrich(fields, options)}


def test_the_di_kem_trich_luc_khai_tu_do_ve_muc_i():
    result = _enrich(_HO_SO, _VNEID_NGUOI_NOP_HO)

    # Mục I = chủ thẻ, ghi đè người đăng nhập VNeID.
    assert result["HoVaTenC"] == "VŨ THỊ PHƯƠNG"
    assert result["SoDinhDanhC"] == "020152000758"
    assert result["NYC_SoGiayToTuyThan"] == "020152000758"
    assert result["NgayCapDDC"] == "27/04/2021"
    assert result["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"

    # Mục II vẫn là người đã mất, KHÔNG bị thẻ đè lên.
    assert result["NDK_HoVaTen"] == "NGUYỄN THỊ NGÂN"
    assert result["NDK_NgaySinh"] == "1928"
    assert result["NDK_SoGiayToTuyThan"] == "120018017"
    assert result["NDK_NgayCap"] == "04/05/2017"
    assert result["NDK_NoiCap"] == "Công an tỉnh Bắc Giang"


def test_the_dung_cua_chu_the_thi_khong_bi_doi_vai():
    # Trích lục khai sinh + CCCD của CHÍNH người được đăng ký → thẻ ở lại mục II.
    result = _enrich([
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "DƯƠNG VĂN ÁNH"},
        {"name": "HoTich_SoDinhDanh", "value": "024200006467"},
        {"name": "ChuThe_HoTen", "value": "DƯƠNG VĂN ÁNH"},
        {"name": "ChuThe_SoDinhDanh", "value": "024200006467"},
        {"name": "ChuThe_NgayCap", "value": "01/01/2021"},
    ], _VNEID_NGUOI_NOP_HO)

    assert "HoVaTenC" not in result
    assert result["NDK_HoVaTen"] == "DƯƠNG VĂN ÁNH"
    assert result["NDK_SoDinhDanh"] == "024200006467"


def test_khong_du_moc_neo_thi_giu_nguyen_phan_vai_cua_agent():
    # Giấy hộ tịch không nêu tên/số chủ thể → không có căn cứ kết luận thẻ là của ai.
    result = _enrich([
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_TenGiayTo", "value": "Giấy khai sinh"},
        {"name": "ChuThe_HoTen", "value": "VŨ THỊ PHƯƠNG"},
        {"name": "ChuThe_SoDinhDanh", "value": "020152000758"},
    ], _VNEID_NGUOI_NOP_HO)

    assert "HoVaTenC" not in result
    assert result["NDK_HoVaTen"] == "VŨ THỊ PHƯƠNG"
