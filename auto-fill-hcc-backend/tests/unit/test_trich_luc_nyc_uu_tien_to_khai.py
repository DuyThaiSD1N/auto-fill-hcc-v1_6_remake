"""Khối NGƯỜI YÊU CẦU (mục I) của trích lục: TỜ KHAI luôn thắng, CCCD chỉ bù ô còn thiếu."""

from app.pipelines.trich_luc.process import mapper

_TK_ADDRESS = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Hiệp Hòa", "diaChi": "Thôn Đại Đồng"}
_CARD_ADDRESS = {"quocGia": "Việt Nam", "tinh": "Bắc Giang", "xa": "Danh Thắng", "diaChi": "Đại Đồng 2"}

# Giấy khai sinh của người con — người được cấp bản sao ở mục II.
_BIRTH_EXTRACT = [
    {"name": "HoTich_LoaiSuKien", "value": "birth"},
    {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "DƯƠNG VĂN ÁNH"},
    {"name": "HoTich_SoDinhDanh", "value": "024200006467"},
]


def _enrich(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in mapper.enrich(fields)}


def test_to_khai_thang_cccd_cua_nguoi_khac_trong_ho_so():
    # Tờ khai: mẹ đứng tên yêu cầu. Hồ sơ có thêm CCCD của người con → không được đè lên mục I.
    result = _enrich(_BIRTH_EXTRACT + [
        {"name": "TkNyc_HoTen", "value": "HÀ THỊ THƯ"},
        {"name": "TkNyc_SoGiayToTuyThan", "value": "024177008469"},
        {"name": "TkNyc_LoaiGiayToTuyThan", "value": "Căn cước công dân"},
        {"name": "TkNyc_NgayCapGiayToTuyThan", "value": "17/12/2021"},
        {"name": "TkNyc_NoiCapGiayToTuyThan", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
        {"name": "TkNyc_NoiCuTru", "value": _TK_ADDRESS},
        {"name": "CopyRequest_QuanHe", "value": "Mẹ đẻ"},
        {"name": "Nyc_HoTen", "value": "DƯƠNG VĂN ÁNH"},
        {"name": "Nyc_SoDinhDanh", "value": "024200006467"},
        {"name": "Nyc_NgayCap", "value": "01/01/2020"},
        {"name": "Nyc_NoiCuTru", "value": _CARD_ADDRESS},
    ])

    assert result["HoVaTenC"] == "HÀ THỊ THƯ"
    assert result["SoDinhDanhC"] == "024177008469"
    assert result["NYC_SoGiayToTuyThan"] == "024177008469"
    assert result["NgayCapDDC"] == "17/12/2021"
    assert result["NoiCapDDC"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert result["NYC_NoiCuTru_TrongNuoc"]["tinh"] == "Bắc Ninh"
    # Ô tích quan hệ cũng theo tờ khai, không suy từ đối chiếu nhân thân.
    assert result["NYC_QuanHe"] == "Mẹ đẻ"


def test_cccd_chi_bu_o_to_khai_khong_ghi():
    # Tờ khai chỉ ghi họ tên; CCCD ĐÚNG người đó bù số/ngày cấp/nơi cư trú, không đổi tên.
    result = _enrich(_BIRTH_EXTRACT + [
        {"name": "TkNyc_HoTen", "value": "HÀ THỊ THƯ"},
        {"name": "CopyRequest_QuanHe", "value": "Mẹ đẻ"},
        {"name": "Nyc_HoTen", "value": "HÀ THỊ THƯ"},
        {"name": "Nyc_SoDinhDanh", "value": "024177008469"},
        {"name": "Nyc_NgayCap", "value": "17/12/2021"},
        {"name": "Nyc_NoiCuTru", "value": _CARD_ADDRESS},
    ])

    assert result["HoVaTenC"] == "HÀ THỊ THƯ"
    assert result["SoDinhDanhC"] == "024177008469"
    assert result["NgayCapDDC"] == "17/12/2021"
    # Địa chỉ lấy từ thẻ (tỉnh bị remap theo sáp nhập nên so bằng địa chỉ chi tiết).
    assert result["NYC_NoiCuTru_TrongNuoc"]["diaChi"] == "Đại Đồng 2"
    assert result["NYC_QuanHe"] == "Mẹ đẻ"


def test_quan_he_theo_to_khai_ke_ca_khi_nguoc_voi_doi_chieu_nhan_than():
    # Số định danh người yêu cầu TRÙNG chủ thể (đối chiếu sẽ ra "Bản thân") nhưng tờ khai ghi
    # "Con đẻ" → tick theo tờ khai, và KHÔNG đánh dấu default (đọc được từ giấy tờ).
    fields = _BIRTH_EXTRACT + [
        {"name": "TkNyc_HoTen", "value": "DƯƠNG VĂN ÁNH"},
        {"name": "TkNyc_SoGiayToTuyThan", "value": "024200006467"},
        {"name": "CopyRequest_QuanHe", "value": "Con đẻ"},
    ]
    quanhe = next(f for f in mapper.enrich(fields) if f["name"] == "NYC_QuanHe")

    assert quanhe["value"] == "Con Đẻ"  # đúng nhãn option trên form
    assert "default" not in quanhe


# --- Thứ tự nguồn của mục I: TỜ KHAI đè lên → CCCD đè lên → không có gì thì để im VNeID -------

_VNEID_NGUOI_KHAC = {"formContext": {
    "applicantFullname": "NGUYỄN DUY THÁI",
    "applicantIdentityNumber": "001204018566",
}}


def test_cccd_trong_ho_so_van_de_len_du_khac_tai_khoan_vneid():
    # Bố mang giấy tờ đi làm bản sao cho con, tài khoản đăng nhập lại là người khác.
    # Hồ sơ GIẤY là căn cứ → mục I phải mang thông tin trên CCCD, không giữ prefill VNeID.
    result = {f["name"]: f["value"] for f in mapper.enrich(_BIRTH_EXTRACT + [
        {"name": "Nyc_HoTen", "value": "NGUYỄN VĂN TUẤN"},
        {"name": "Nyc_SoDinhDanh", "value": "024096001060"},
        {"name": "Nyc_NgayCap", "value": "25/04/2021"},
    ], _VNEID_NGUOI_KHAC)}

    assert result["HoVaTenC"] == "NGUYỄN VĂN TUẤN"
    assert result["SoDinhDanhC"] == "024096001060"
    assert result["NgayCapDDC"] == "25/04/2021"


def test_to_khai_de_len_ca_cccd_lan_vneid():
    result = {f["name"]: f["value"] for f in mapper.enrich(_BIRTH_EXTRACT + [
        {"name": "TkNyc_HoTen", "value": "HÀ THỊ THƯ"},
        {"name": "TkNyc_SoGiayToTuyThan", "value": "024177008469"},
        {"name": "CopyRequest_QuanHe", "value": "Mẹ đẻ"},
        {"name": "Nyc_HoTen", "value": "NGUYỄN VĂN TUẤN"},
        {"name": "Nyc_SoDinhDanh", "value": "024096001060"},
    ], _VNEID_NGUOI_KHAC)}

    assert result["HoVaTenC"] == "HÀ THỊ THƯ"
    assert result["SoDinhDanhC"] == "024177008469"
    assert result["NYC_QuanHe"] == "Mẹ đẻ"


def test_khong_co_to_khai_lan_cccd_thi_de_im_vneid():
    result = {f["name"]: f["value"] for f in mapper.enrich(_BIRTH_EXTRACT, _VNEID_NGUOI_KHAC)}

    for name in ("HoVaTenC", "SoDinhDanhC", "NgayCapDDC", "NYC_NoiCuTru_TrongNuoc"):
        assert name not in result
    assert result["NDK_HoVaTen"] == "DƯƠNG VĂN ÁNH"


def test_the_cua_chinh_chu_the_khong_duoc_dap_sang_muc_i():
    # CCCD trong hồ sơ chính là thẻ của NGƯỜI ĐƯỢC ĐĂNG KÝ (vd CCCD của con) và tài khoản là người
    # khác → đây không phải giấy tờ người yêu cầu, giữ nguyên phần cổng đã điền.
    result = {f["name"]: f["value"] for f in mapper.enrich(_BIRTH_EXTRACT + [
        {"name": "Nyc_HoTen", "value": "DƯƠNG VĂN ÁNH"},
        {"name": "Nyc_SoDinhDanh", "value": "024200006467"},
    ], _VNEID_NGUOI_KHAC)}

    assert "HoVaTenC" not in result
    assert result["NDK_HoVaTen"] == "DƯƠNG VĂN ÁNH"


def test_tu_xin_cho_chinh_minh_thi_the_trung_chu_the_van_dien():
    # Thẻ trùng chủ thể NHƯNG khớp tài khoản đăng nhập → chính chủ tự xin, mục I vẫn phải điền.
    result = {f["name"]: f["value"] for f in mapper.enrich(_BIRTH_EXTRACT + [
        {"name": "Nyc_HoTen", "value": "DƯƠNG VĂN ÁNH"},
        {"name": "Nyc_SoDinhDanh", "value": "024200006467"},
    ], {"formContext": {
        "applicantFullname": "DƯƠNG VĂN ÁNH",
        "applicantIdentityNumber": "024200006467",
    }})}

    assert result["HoVaTenC"] == "DƯƠNG VĂN ÁNH"
    assert result["SoDinhDanhC"] == "024200006467"
