"""Thay đổi/cải chính/xác định lại dân tộc: quan hệ "Bản thân" → Mục II lấy giấy tờ từ THẺ CCCD.

Hồ sơ thật (cải chính chữ đệm người cha, ông NGUYỄN VĂN QUỲNH tự đứng tên): tờ khai viết tay bị OCR
rơi chữ số đầu của số định danh — "024078019726" thành "04078019726" (11 số). Mục I đã tự đảo sang
thẻ nên đúng, nhưng Mục II vẫn giữ số hỏng của tờ khai → hai mục lệch số trong cùng một hồ sơ.
"""

from app.pipelines.thay_doi_ho_tich.process import mapper

_CCCD_THAT = "024078019726"
_CCCD_OCR_HONG = "04078019726"  # tờ khai viết tay, rơi chữ số đầu
_NOI_CU_TRU_TO_KHAI = {
    "quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Hiệp Hòa", "diaChi": "Thôn Đức Thịnh",
}

_HO_SO = [
    {"name": "DanhSachCccd", "value": [{
        "HoTen": "NGUYỄN VĂN QUỲNH",
        "SoDinhDanh": _CCCD_THAT,
        "NgaySinh": "28/12/1978",
        "GioiTinh": "Nam",
        "QuocTich": "Việt Nam",
        "NgayCap": "17/11/2022",
        "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        "NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Bắc Giang",
                     "xa": "Thị trấn Thắng", "diaChi": "Tdp Đức Thịnh"},
    }]},
    {"name": "NguoiYeuCau_HoTen", "value": "Nguyễn Văn Quỳnh"},
    {"name": "NguoiYeuCau_NgaySinh", "value": "28/12/1978"},
    {"name": "NguoiYeuCau_SoDinhDanh", "value": _CCCD_OCR_HONG},
    {"name": "NguoiYeuCau_LoaiGiayTo", "value": "Thẻ căn cước công dân"},
    {"name": "NguoiYeuCau_NgayCap", "value": "17/11/2022"},
    {"name": "NguoiYeuCau_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "NguoiYeuCau_NoiCuTru", "value": _NOI_CU_TRU_TO_KHAI},
    {"name": "NguoiYeuCau_QuanHe", "value": "Bản thân"},
    {"name": "Cccd_HoTen", "value": "NGUYỄN VĂN QUỲNH"},
    {"name": "Cccd_SoDinhDanh", "value": _CCCD_THAT},
    {"name": "Cccd_NgayCap", "value": "17/11/2022"},
    {"name": "Cccd_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "LoaiSuKien", "value": "birth"},
    {"name": "ViecDangKy", "value": "Cải chính"},
    {"name": "NoiDungThayDoi", "value": "Cải chính chữ đệm của người cha từ Văn Thành Xuân"},
    {"name": "ChuThe_HoTen", "value": "Nguyễn Văn Quỳnh"},
    {"name": "ChuThe_NgaySinh", "value": "21/12/1978"},
    {"name": "ChuThe_GioiTinh", "value": "Nam"},
    {"name": "ChuThe_DanToc", "value": "Kinh"},
    {"name": "ChuThe_QuocTich", "value": "Việt Nam"},
    {"name": "ChuThe_SoDinhDanh", "value": _CCCD_OCR_HONG},
    {"name": "ChuThe_NgayCapGiayTo", "value": "17/11/2022"},
    {"name": "ChuThe_NoiCapGiayTo", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "ChuThe_NoiCuTru", "value": _NOI_CU_TRU_TO_KHAI},
]


def _enrich(fields, options=None):
    return {f["name"]: f["value"] for f in mapper.enrich(fields, options)}


def test_ban_than_thi_muc_ii_lay_so_va_ngay_cap_tu_the():
    result = _enrich(_HO_SO)

    assert result["nycQuanHe"] == "Bản thân"
    # Mục II: số định danh + số giấy tờ + ngày/nơi cấp đều theo THẺ.
    assert result["ntdSoDDCN"] == _CCCD_THAT
    assert result["ntdSoGiayToTuyThan"] == _CCCD_THAT
    assert result["ntdNgayCapGiayToTuyThan"] == "17/11/2022"
    assert result["ntdNoiCapGiayToTuyThan"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    # Mục I không đổi, và giờ khớp số với Mục II.
    assert result["SoDinhDanhC"] == _CCCD_THAT
    assert result["SoGiayToTuyThanC"] == _CCCD_THAT
    # Các ô còn lại của Mục II vẫn theo tờ khai.
    assert result["ntdHoTen"] == "Nguyễn Văn Quỳnh"
    assert result["ntdNgaySinh"] == "21/12/1978"
    assert result["ntdDanToc"] == "Kinh"
    assert result["ntdNoiCuTru_TrongNuoc"]["diaChi"] == "Thôn Đức Thịnh"


def test_quan_he_khac_thi_khong_dap_the_nguoi_yeu_cau_sang_muc_ii():
    # Bố đứng tên cải chính cho con: thẻ trong hồ sơ là của BỐ, không được đè sang Mục II.
    result = _enrich([
        {"name": "DanhSachCccd", "value": [{
            "HoTen": "NGUYỄN VĂN QUỲNH",
            "SoDinhDanh": _CCCD_THAT,
            "NgayCap": "17/11/2022",
            "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        }]},
        {"name": "NguoiYeuCau_HoTen", "value": "Nguyễn Văn Quỳnh"},
        {"name": "NguoiYeuCau_SoDinhDanh", "value": _CCCD_THAT},
        {"name": "NguoiYeuCau_QuanHe", "value": "Khác"},
        {"name": "Cccd_HoTen", "value": "NGUYỄN VĂN QUỲNH"},
        {"name": "Cccd_SoDinhDanh", "value": _CCCD_THAT},
        {"name": "LoaiSuKien", "value": "birth"},
        {"name": "ViecDangKy", "value": "Cải chính"},
        {"name": "ChuThe_HoTen", "value": "Nguyễn Minh Khôi"},
        {"name": "ChuThe_NgaySinh", "value": "05/03/2015"},
        {"name": "ChuThe_SoDinhDanh", "value": "024215000111"},
    ])

    assert result["nycQuanHe"] == "Khác"
    assert result["ntdSoDDCN"] == "024215000111"
    assert result["SoDinhDanhC"] == _CCCD_THAT
