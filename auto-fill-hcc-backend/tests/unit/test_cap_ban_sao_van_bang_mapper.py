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


_NOP_THAY = {
    "VanBang_HoTen": "TRẦN THỊ MẪU",
    "VanBang_NgaySinh": "01/02/1990",
    "VanBang_SoGiayTo": "001190000123",
    "VanBang_LoaiTotNghiep": "THPT",
    "NguoiNop_HoTen": "LÊ VĂN NỘP",
    "NguoiNop_SoDinhDanh": "001095000456",
    "NguoiNop_NgaySinh": "05/06/1995",
    "NguoiNop_GioiTinh": "Nam",
    "NguoiNop_NgayCap": "10/10/2021",
    "NguoiNop_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "NguoiNop_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Phước Mỹ", "diaChi": "Tổ 1"},
}


def test_cccd_nguoi_nop_thay_dien_phan_i_du_khong_trung_tai_khoan():
    got, _ = _map(_NOP_THAY, {"applicantIdentityNumber": "001099000777"})
    assert got["data[fullname]"] == "LÊ VĂN NỘP"
    assert got["data[identityNumber]"] == "001095000456"
    assert got["data[birthday]"] == "05/06/1995"
    assert got["data[gender]"] == "Nam"
    assert got["data[identityDate]"] == "10/10/2021"
    assert got["data[idIssuePlace]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert got["data[address]"] == "Tổ 1"
    # Chủ hồ sơ vẫn là chủ văn bằng, không lẫn CCCD người nộp.
    assert got["data[ownerFullname]"] == "TRẦN THỊ MẪU"
    assert got["data[ownerIdentityNumber]"] == "001190000123"


def test_cccd_nguoi_nop_bi_llm_xep_vao_chu_ho_so_van_dien_phan_i():
    v = {k: val for k, val in _NOP_THAY.items() if not k.startswith("NguoiNop_")}
    v.update({"ChuHoSo_HoTen": "LÊ VĂN NỘP", "ChuHoSo_SoGiayTo": "001095000456", "ChuHoSo_NgaySinh": "05/06/1995"})
    got, _ = _map(v)
    assert got["data[fullname]"] == "LÊ VĂN NỘP"
    assert got["data[identityNumber]"] == "001095000456"
    assert got["data[ownerIdentityNumber]"] == "001190000123"


def test_nguoi_nop_thieu_ngay_sinh_thi_xoa_gia_tri_tai_khoan():
    v = dict(_NOP_THAY)
    del v["NguoiNop_NgaySinh"]
    out, _ = mapper.enrich([{"name": k, "value": val} for k, val in v.items()],
                           {"formContext": {"applicantIdentityNumber": "001099000777"}})
    birthday = next(f for f in out if f["name"] == "data[birthday]")
    assert birthday.get("clear") is True


def test_chi_co_cccd_chu_van_bang_thi_chu_tu_nop():
    got, _ = _map(_VALUES, {"applicantIdentityNumber": "001099000777"})
    assert got["data[fullname]"] == "NGUYỄN ANH QUÂN"
    assert got["data[identityNumber]"] == "048202003364"
    assert got["data[identityDate]"] == "19/12/2022"


def test_khong_co_cccd_nao_va_khong_trung_tai_khoan_thi_bo_trong_phan_i():
    v = {k: val for k, val in _NOP_THAY.items() if not k.startswith("NguoiNop_")}
    got, _ = _map(v, {"applicantIdentityNumber": "001099000777"})
    assert not set(got) & {"data[fullname]", "data[identityNumber]", "data[birthday]"}
