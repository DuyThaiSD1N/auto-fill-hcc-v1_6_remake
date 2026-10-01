"""Cấp bản sao văn bằng từ sổ gốc — panel 'Phieu' form MỚI (thay panel Thongtincanhan cũ)."""

from app.pipelines.cap_ban_sao_van_bang_so_goc.process import mapper

_VALUES = {  # trích từ trace thật (Nguyễn Anh Quân)
    "VanBang_HoTen": "NGUYỄN ANH QUÂN",
    "VanBang_GioiTinh": "Nam",
    "VanBang_NgaySinh": "18/08/2002",
    "VanBang_Truong": "THPT NGÔ QUYỀN",
    "VanBang_LoaiTotNghiep": "THPT",
    "VanBang_KhoaThi": "2020",
    "VanBang_SoGiayTo": "048202003364",
    "VanBang_DienThoai": "0778501192",
    "VanBang_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Phước Mỹ", "diaChi": "Tổ 49"},
    "ChuHoSo_LoaiChuThe": "Cá nhân",
    "ChuHoSo_HoTen": "NGUYỄN ANH QUÂN",
    "ChuHoSo_NgaySinh": "18/08/2002",
    "ChuHoSo_SoGiayTo": "048202003364",
    "ChuHoSo_NgayCap": "19/12/2022",
    "ChuHoSo_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "ChuHoSo_DienThoai": "0778501192",
    "ChuHoSo_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Phước Mỹ", "diaChi": "Tổ 49"},
    "Phieu_KinhGui": "SỞ GIÁO DỤC VÀ ĐÀO TẠO ĐÀ NẴNG",
    "Phieu_TenVanBang": "BẰNG THPT",
    "Phieu_CoQuanCapVanBang": "Sở Giáo dục và Đào tạo Đà Nẵng",
    "Phieu_SoLuongBanSao": "1",
    "Phieu_LyDo": "làm mất",
    "Phieu_ThongTinKhac": "THPT NGÔ QUYỀN, 2020",
    "Phieu_LienHe": "0778501192, nguyenanhquan1882002@gmail.com, k227/69 nguyễn văn thoại",
    "Phieu_NgayLap": "07/09/2026",
    "Phieu_NguoiViet": "Nguyễn Anh Quân",
}

_DEAD_KEYS = [  # field-key panel cũ đã BỎ khỏi form — tuyệt đối không được emit lại
    "data[Nam]", "data[Nu]", "data[ngaySinh]", "data[DaHocLop12]", "data[THPT]", "data[THPT1]",
    "data[THCS]", "data[KhoaThi]", "data[HoiDongThi]", "data[LoaiGiayTo]", "data[SoGiayTo]",
    "data[NgayCap]", "data[identityAgency]", "data[TinhThanhPho]", "data[QuanHuyen]",
    "data[SoNhaDuong]", "data[DienThoai]", "data[select]", "data[ten1]", "data[NoiSinh]",
    "data[DanTocKhaiSinh1]", "data[TinhTP]", "data[PX1]",
]


def _map(values, form_context=None):
    fields = [{"name": k, "value": v} for k, v in values.items()]
    out, warnings = mapper.enrich(fields, {"formContext": form_context or {}})
    return {f["name"]: f["value"] for f in out}, warnings


def test_phieu_panel_new_keys_emitted():
    got, _ = _map(_VALUES)
    assert got["data[Kinhgui]"] == "SỞ GIÁO DỤC VÀ ĐÀO TẠO ĐÀ NẴNG"
    assert got["data[ToiTen]"] == "NGUYỄN ANH QUÂN"
    assert got["data[sinhNam]"] == "18/08/2002"
    assert got["data[Sodinhdanh]"] == "048202003364"
    assert got["data[Duoccap]"] == "BẰNG THPT"
    assert got["data[do]"] == "Sở Giáo dục và Đào tạo Đà Nẵng"
    assert got["data[requestQty]"] == "1"
    assert got["data[sogoc]"] is True
    assert got["data[lydo]"] == "làm mất"
    assert got["data[thongtinkhac]"] == "THPT NGÔ QUYỀN, 2020"
    assert "0778501192" in got["data[lienhe]"]
    assert got["data[ngay]"] == "07/09/2026"
    assert got["data[nguoidenghi]"] == "Nguyễn Anh Quân"


def test_dead_panel_keys_are_never_emitted():
    got, _ = _map(_VALUES)
    for dead in _DEAD_KEYS:
        assert dead not in got, f"emit lại field-key đã chết: {dead}"


def test_derive_when_phieu_lines_missing():
    """Không có Phiếu (chỉ CCCD + văn bằng) → suy 'Đã được cấp', 'Thông tin khác', 'liên hệ'."""
    v = dict(_VALUES)
    for k in ("Phieu_TenVanBang", "Phieu_ThongTinKhac", "Phieu_LienHe"):
        v.pop(k)
    got, _ = _map(v)
    assert got["data[Duoccap]"] == "Bằng tốt nghiệp THPT"       # suy từ loại tốt nghiệp
    assert got["data[thongtinkhac]"] == "THPT NGÔ QUYỀN, 2020"  # suy Trường + năm
    assert "0778501192" in got["data[lienhe]"]                  # suy SĐT + địa chỉ


def test_owner_block_still_maps():
    """Panel Phần III-V (owner) KHÔNG đổi — vẫn ra data[owner*]."""
    got, _ = _map(_VALUES)
    assert got["data[ownerFullname]"] == "NGUYỄN ANH QUÂN"
    assert got["data[ownerIdentityNumber]"] == "048202003364"
    assert got["data[ChuHS]"] == "Cá nhân"


_UY_QUYEN_OCR = """GIẤY ỦY QUYỀN
Hôm nay tại: Trung tâm phục vụ hành chính công xã Trung Thuần, tỉnh Quảng Trị
I. BÊN ỦY QUYỀN:
Họ, chữ đệm, tên: TRẦN VĂN AN
Hộ khẩu thường trú: Thôn Mới - Xã Trung Thiên - Quảng Trị
II. BÊN ĐƯỢC ỦY QUYỀN:
Họ, chữ đệm, tên: TRẦN VĂN BÌNH
Ngày tháng năm sinh: 01-01
CCCD/CMND số: 044000000002 cấp ngày 10/09 tại: Bộ Công an
"""

_UY_QUYEN_VALUES = {
    "VanBang_HoTen": "TRẦN VĂN AN",
    "VanBang_NgaySinh": "02/03/1990",
    "VanBang_SoGiayTo": "044000000001",
    "VanBang_DienThoai": "0912345678",
    "VanBang_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Quảng Trị", "xa": "Xã Trung Thiên", "diaChi": "Thôn Mới"},
    "NguoiNop_HoTen": "TRẦN VĂN BÌNH",
    "NguoiNop_SoDinhDanh": "044000000002",
    "NguoiNop_NgaySinh": "01/01/1985",   # LLM bịa năm — giấy chỉ ghi "01-01"
    "NguoiNop_NgayCap": "10/09/2026",
    "NguoiNop_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Quảng Trị", "xa": "Xã Trung Thiên", "diaChi": "Thôn Mới"},
}


def _map_full(values, ocr_text):
    fields = [{"name": k, "value": v} for k, v in values.items()]
    out, _ = mapper.enrich(fields, {"formContext": {"applicantIdentityNumber": "001000000009"}}, ocr_text=ocr_text)
    return {f["name"]: f for f in out}


def test_uy_quyen_xoa_ngay_sinh_tai_khoan_khi_giay_khong_ghi_du():
    by = _map_full(_UY_QUYEN_VALUES, _UY_QUYEN_OCR)
    assert by["data[fullname]"]["value"] == "TRẦN VĂN BÌNH"
    assert by["data[birthday]"].get("clear") is True and by["data[birthday]"]["value"] == ""
    assert by["data[identityDate]"].get("clear") is True


def test_uy_quyen_sdt_theo_ho_so_va_xa_sai_duoc_go_theo_ho_so():
    by = _map_full(_UY_QUYEN_VALUES, _UY_QUYEN_OCR)
    assert by["data[phoneNumber]"]["value"] == "0912345678"
    assert by["data[province]"]["value"] == "Tỉnh Quảng Trị"
    # "Trung Thiên" không có trong danh mục; hồ sơ nhắc "xã Trung Thuần, tỉnh Quảng Trị" → gợi ý, tô vàng.
    assert by["data[district]"]["value"] == "Xã Trung Thuần"
    assert by["data[district]"].get("default") is True
    assert by["data[ownerDistrict]"]["value"] == "Xã Trung Thuần"


def test_xa_chet_khong_go_duoc_thi_bo_trong_giu_tinh():
    by = _map_full(_UY_QUYEN_VALUES, _UY_QUYEN_OCR.replace("xã Trung Thuần, ", ""))
    assert by["data[province]"]["value"] == "Tỉnh Quảng Trị"
    assert "data[district]" not in by
    assert "data[ownerDistrict]" not in by
