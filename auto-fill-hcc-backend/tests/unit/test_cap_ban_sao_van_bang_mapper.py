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


# Chủ tự nộp bằng chính tài khoản VNeID (dữ liệu bịa). Số trên phiếu OCR lệch 1 chữ số so với tài khoản.
_TU_NOP = {
    "VanBang_HoTen": "TRẦN VĂN MẪU",
    "VanBang_GioiTinh": "Nam",
    "VanBang_NgaySinh": "01/02/2003",
    "VanBang_SoGiayTo": "001203001234",
    "ChuHoSo_LoaiChuThe": "Cá nhân",
    "ChuHoSo_HoTen": "TRẦN VĂN MẪU",
    "ChuHoSo_SoGiayTo": "001203001234",
    "ChuHoSo_NgaySinh": "01/02/2003",
    "Phieu_LyDo": "làm mất",
}
_PHAN_I = ["data[fullname]", "data[identityNumber]", "data[gender]", "data[birthday]", "data[identityDate]",
           "data[idIssuePlace]", "data[province]", "data[district]", "data[address]", "data[phoneNumber]",
           "data[email]"]


def test_tai_khoan_la_chu_van_bang_giu_phan_i_va_tick_nguoi_nop_la_chu():
    got, warnings = _map(_TU_NOP, {"applicantFullname": "Trần Văn Mẫu", "applicantIdentityNumber": "001203004234"})
    assert got["data[isOwnerDossier]"] is True
    for name in _PHAN_I:
        assert name not in got, f"không được ghi đè Phần I VNeID: {name}"
    assert got["data[ownerIdentityNumber]"] == "001203004234"  # số tài khoản là chuẩn
    assert got["data[Sodinhdanh]"] == "001203004234"
    assert any("lệch với tài khoản VNeID" in w for w in warnings)


def test_tai_khoan_khac_ten_chu_van_bang_khong_tick():
    got, _ = _map(_TU_NOP, {"applicantFullname": "LÊ THỊ KHÁC", "applicantIdentityNumber": "001203004234"})
    assert "data[isOwnerDossier]" not in got
    assert got["data[identityNumber]"] == "001203001234"


def test_tai_khoan_cung_ten_nhung_so_lech_nhieu_khong_tick():
    got, _ = _map(_TU_NOP, {"applicantFullname": "TRẦN VĂN MẪU", "applicantIdentityNumber": "079188999999"})
    assert "data[isOwnerDossier]" not in got


def test_co_nguoi_nop_thay_khong_tick():
    v = dict(_TU_NOP, NguoiNop_HoTen="PHẠM VĂN NỘP", NguoiNop_SoGiayTo="002199005678")
    got, _ = _map(v, {"applicantFullname": "TRẦN VĂN MẪU", "applicantIdentityNumber": "001203001234"})
    assert "data[isOwnerDossier]" not in got
    assert got["data[fullname]"] == "PHẠM VĂN NỘP"
