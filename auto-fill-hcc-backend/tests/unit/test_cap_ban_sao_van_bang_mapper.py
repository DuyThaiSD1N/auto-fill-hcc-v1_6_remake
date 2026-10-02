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


def test_sinh_ngay_phieu_is_date_comp():
    # Ô "Sinh ngày" là datetime flatpickr: dom-input chỉ ghi ô gốc bị ẩn → cổng hiển thị trống.
    out, _ = mapper.enrich([{"name": k, "value": v} for k, v in _VALUES.items()], {"formContext": {}})
    comps = {f["name"]: f["comp"] for f in out}
    assert comps["data[sinhNam]"] == "dom-date"


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


_PHIEU_MOI_OCR = """PHIẾU ĐỀ NGHỊ
Kính gửi: Sở Giáo dục và Đào tạo (1)
Tên tôi là: TRẦN THỊ MẪU
Sinh ngày: 01/02/1990
Số định danh cá nhân: 001190000123
Đã được cấp (tên văn bằng, chứng chỉ)(2) ...THPT....
"""


def test_so_dinh_danh_phieu_moi_lay_tu_ocr_khi_llm_bo_sot():
    values = {
        "VanBang_HoTen": "TRẦN THỊ MẪU",
        "VanBang_NgaySinh": "01/02/1990",
        "VanBang_LoaiTotNghiep": "THPT",
    }
    out, _ = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], {"formContext": {}},
                           ocr_text=_PHIEU_MOI_OCR)
    got = {f["name"]: f["value"] for f in out}
    assert got["data[ownerIdentityNumber]"] == "001190000123"
    assert got["data[Sodinhdanh]"] == "001190000123"


def test_so_dinh_danh_cccd_ngoai_phieu_khong_lay():
    # CCCD gắn chip của người khác cũng in "Số định danh cá nhân" nhưng không nằm sau "Tên tôi là".
    ocr = "CĂN CƯỚC\nSố định danh cá nhân: 001090000999\nHọ, chữ đệm và tên: LÊ VĂN KHÁC\n"
    out, _ = mapper.enrich([{"name": "VanBang_HoTen", "value": "TRẦN THỊ MẪU"}], {"formContext": {}}, ocr_text=ocr)
    got = {f["name"]: f["value"] for f in out}
    assert "data[ownerIdentityNumber]" not in got
    assert "data[Sodinhdanh]" not in got


def test_cccd_can_bo_khong_lan_vao_chu_ho_so_khi_llm_bo_trong_van_bang():
    # LLM bỏ trống VanBang_* và nhét CCCD cán bộ tiếp nhận vào ChuHoSo_* → chủ hồ sơ phải theo PHIẾU.
    values = {
        "ChuHoSo_HoTen": "PHẠM VĂN CÁNBỘ",
        "ChuHoSo_SoGiayTo": "001099000555",
        "ChuHoSo_NgaySinh": "03/03/1999",
        "ChuHoSo_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": "Phường Láng", "diaChi": "Số 1"},
        "Phieu_KinhGui": "Sở Giáo dục và Đào tạo",
    }
    ocr = _PHIEU_MOI_OCR + "Số điện thoại, E-mail, địa chỉ liên hệ (8): 0912 345 678\n"
    ctx = {"applicantFullname": "Phạm Văn Cánbộ", "applicantIdentityNumber": "001099000555"}
    out, _ = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], {"formContext": ctx},
                           ocr_text=ocr)
    got = {f["name"]: f["value"] for f in out}
    assert got["data[ownerFullname]"] == "TRẦN THỊ MẪU"
    assert got["data[ToiTen]"] == "TRẦN THỊ MẪU"
    assert got["data[ownerIdentityNumber]"] == "001190000123"
    assert got["data[Sodinhdanh]"] == "001190000123"
    assert got["data[ownerBirthday]"] == "01/02/1990"
    assert got["data[sinhNam]"] == "01/02/1990"
    assert got["data[ownerPhoneNumber]"] == "0912345678"
    # Phần I (người nộp) = CCCD cán bộ vì số trùng tài khoản; phần chủ/phiếu không mang dữ liệu cán bộ.
    assert got["data[identityNumber]"] == "001099000555"
    assert got["data[birthday]"] == "03/03/1999"
    assert "data[fullname]" not in got and "data[phoneNumber]" not in got
    phan_i = {"data[identityNumber]", "data[birthday]", "data[gender]", "data[identityDate]", "data[idIssuePlace]",
              "data[province]", "data[district]", "data[address]"}
    for k, v in got.items():
        if k not in phan_i:
            assert "001099000555" not in str(v) and "03/03/1999" not in str(v) and "Láng" not in str(v)


def test_cccd_khong_trung_so_tai_khoan_thi_khong_dien_phan_i():
    values = {"ChuHoSo_HoTen": "PHẠM VĂN CÁNBỘ", "ChuHoSo_SoGiayTo": "001099000555", "ChuHoSo_NgaySinh": "03/03/1999"}
    ctx = {"applicantIdentityNumber": "001099000777"}
    out, _ = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], {"formContext": ctx},
                           ocr_text=_PHIEU_MOI_OCR)
    names = {f["name"] for f in out}
    assert not names & {"data[identityNumber]", "data[birthday]", "data[gender]", "data[identityDate]"}


def test_ngay_cap_phan_i_lay_tu_mat_sau_cccd_theo_mrz():
    ocr = (_PHIEU_MOI_OCR
           + "\n===== mat_sau_khac.jpg (x) =====\nNgày, tháng, năm / Date, month, year: 05/05/2020\n"
             "IDVNM0990007771001099000777<<1\n"
           + "\n===== mat_sau_can_bo.jpg (x) =====\nNgày, tháng, năm / Date, month, year: 20/12/2021\n"
             "IDVNM0990005551001099000555<<3\n")
    values = {"ChuHoSo_HoTen": "PHẠM VĂN CÁNBỘ", "ChuHoSo_SoGiayTo": "001099000555"}
    ctx = {"applicantIdentityNumber": "001099000555"}
    out, _ = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], {"formContext": ctx}, ocr_text=ocr)
    got = {f["name"]: f["value"] for f in out}
    assert got["data[identityDate]"] == "20/12/2021"


def test_thong_tin_khac_lay_nam_tot_nghiep_khong_lay_nam_sinh():
    values = {
        "VanBang_HoTen": "TRẦN THỊ MẪU",
        "VanBang_NamSinh": "1990",
        "VanBang_Truong": "Trường THPT Mẫu",
        "Phieu_SoHieu": "Năm tốt nghiệp 2008",
    }
    out, _ = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], {"formContext": {}})
    got = {f["name"]: f["value"] for f in out}
    assert got["data[thongtinkhac]"] == "Trường THPT Mẫu, 2008"

    del values["Phieu_SoHieu"]
    values["VanBang_KhoaThi"] = "2007-2008"
    out, _ = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], {"formContext": {}})
    assert {f["name"]: f["value"] for f in out}["data[thongtinkhac]"] == "Trường THPT Mẫu, 2008"

    del values["VanBang_KhoaThi"]
    out, _ = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], {"formContext": {}})
    assert {f["name"]: f["value"] for f in out}["data[thongtinkhac]"] == "Trường THPT Mẫu"
