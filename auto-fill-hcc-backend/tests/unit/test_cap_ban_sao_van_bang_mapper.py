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



_DIA_CHI_VALUES = {  # dữ liệu bịa
    "VanBang_HoTen": "TRẦN VĂN MINH",
    "VanBang_NgaySinh": "01/02/1990",
    "VanBang_LoaiTotNghiep": "THPT",
    "ChuHoSo_HoTen": "TRẦN VĂN MINH",
    "ChuHoSo_SoGiayTo": "001090000001",
    "ChuHoSo_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Lào Cai", "xa": "Phường Nam Cường", "diaChi": "Số 1 Ngõ A"},
}
_OLD_EXAM_AREA = {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Phước Mỹ", "diaChi": "Tổ 9"}


def _owner_area(got):
    return got.get("data[ownerProvince]"), got.get("data[ownerDistrict]"), got.get("data[ownerAddress]")


def test_owner_address_prefers_cccd_over_phieu_exam_address():
    """Phiếu ghi 'Hộ khẩu thường trú khi dự thi' (cũ) → địa chỉ chủ hồ sơ vẫn lấy theo CCCD (hiện tại)."""
    v = dict(_DIA_CHI_VALUES, VanBang_ThuongTru=_OLD_EXAM_AREA)
    got, _ = _map(v)
    assert _owner_area(got) == ("Tỉnh Lào Cai", "Phường Nam Cường", "Số 1 Ngõ A")


def test_phieu_address_dropped_when_it_is_exam_address():
    """Không có CCCD chủ, và VanBang_ThuongTru chính là địa chỉ dự thi → KHÔNG điền địa chỉ chủ."""
    v = {k: val for k, val in _DIA_CHI_VALUES.items() if not k.startswith("ChuHoSo_")}
    v["VanBang_ThuongTru"] = _OLD_EXAM_AREA
    v["VanBang_DiaChiDuThi"] = "Tổ 9, Phước Mỹ, Đà Nẵng"
    got, _ = _map(v)
    assert _owner_area(got) == (None, None, None)


def test_phieu_address_used_as_fallback_without_cccd():
    """Không có CCCD chủ, phiếu có địa chỉ thường trú hiện nay (khác địa chỉ dự thi) → dùng dự phòng."""
    v = {k: val for k, val in _DIA_CHI_VALUES.items() if not k.startswith("ChuHoSo_")}
    v["VanBang_ThuongTru"] = _DIA_CHI_VALUES["ChuHoSo_ThuongTru"]
    v["VanBang_DiaChiDuThi"] = "Tổ 9, Phước Mỹ, Đà Nẵng"
    got, _ = _map(v)
    assert got["data[ownerDistrict]"] == "Phường Nam Cường"


def test_old_area_is_remapped_to_current_units():
    """Địa danh cũ trên CCCD (trước sáp nhập) → remap sang xã mới; ô liên hệ cũng dùng địa chỉ mới."""
    v = dict(_DIA_CHI_VALUES, ChuHoSo_ThuongTru={
        "quocGia": "Việt Nam", "tinh": "Tỉnh Yên Bái", "huyen": "Thành phố Yên Bái", "xa": "Xã Tuy Lộc",
        "diaChi": "Thôn A"})
    got, _ = _map(v)
    assert _owner_area(got) == ("Tỉnh Lào Cai", "Phường Nam Cường", "Thôn A")
    assert "Yên Bái" not in got["data[lienhe]"]


def test_remap_takes_district_hint_from_ocr_when_llm_drops_it():
    """LLM bỏ khoá huyen mà tên xã trùng ở nhiều huyện → lấy cấp huyện đứng sau tên xã trong OCR."""
    v = dict(_DIA_CHI_VALUES, ChuHoSo_ThuongTru={
        "quocGia": "Việt Nam", "tinh": "Yên Bái", "xa": "Tuy Lộc", "diaChi": "Thôn A"})
    ocr = "Nơi thường trú / Place of residence: Thôn A\nTuy Lộc, Thành phố Yên Bái, Yên Bái\n"
    fields = [{"name": k, "value": val} for k, val in v.items()]
    out, _ = mapper.enrich(fields, {"formContext": {}}, ocr_text=ocr)
    got = {f["name"]: f["value"] for f in out}
    assert _owner_area(got) == ("Tỉnh Lào Cai", "Phường Nam Cường", "Thôn A")


def test_submitter_address_is_remapped():
    """Phần I (người nộp thay) cũng remap địa danh cũ."""
    v = dict(_DIA_CHI_VALUES, NguoiNop_HoTen="LÊ THỊ HOA", NguoiNop_SoDinhDanh="001190000002",
             NguoiNop_ThuongTru=_OLD_EXAM_AREA)
    got, _ = _map(v)
    assert got["data[province]"] == "Thành phố Đà Nẵng"
    assert got["data[district]"] == "Phường An Hải"
