"""Cấp bản sao văn bằng từ sổ gốc — panel 'Phieu' form MỚI (thay panel Thongtincanhan cũ)."""

from app.channels.handfree.chat.router import _keeps_account_anchor
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


def test_dien_lai_khong_lay_phan_i_vua_dien_lam_moc_tai_khoan():
    # Lượt 1 ghi chủ văn bằng vào Phần I; lượt "Điền lại" extension đọc lại chính Phần I đó làm formContext.
    # Router phải giữ mốc tài khoản cũ, không thì mapper tick "Người nộp là chủ hồ sơ" và cổng đổ đè "Sinh ngày".
    tai_khoan = {"applicantFullname": "LÊ THỊ CÁN BỘ", "applicantIdentityNumber": "001190000111"}
    luot_1, _ = _map(_TU_NOP, tai_khoan)
    assert "data[isOwnerDossier]" not in luot_1
    conv = {"form_context": dict(tai_khoan),
            "fields": [{"name": k, "value": v} for k, v in luot_1.items()]}
    doc_lai = {"applicantFullname": luot_1["data[fullname]"], "applicantIdentityNumber": luot_1["data[identityNumber]"]}
    assert _keeps_account_anchor(conv, doc_lai)
    conv["fields"] = []  # "Điền lại thông tin" xoá fields — vẫn nhớ giá trị đã điền
    assert _keeps_account_anchor(conv, doc_lai)
    # Tài khoản thật đổi người (không phải giá trị mình điền) → nhận mốc mới.
    assert not _keeps_account_anchor(conv, {"applicantFullname": "ĐỖ VĂN KHÁC", "applicantIdentityNumber": "001190000222"})


def test_tai_khoan_that_la_chu_van_bang_van_nhan_moc_moi():
    conv = {"form_context": {}, "fields": []}
    assert not _keeps_account_anchor(conv, {"applicantFullname": "TRẦN VĂN MẪU", "applicantIdentityNumber": "001203001234"})


def test_xa_doc_sai_khong_khop_danh_muc_lay_xa_mang_ten_huyen_cu():
    # CCCD "Khu 2, Đơn Thượng, Hạ Hòa, Phú Thọ": OCR đọc sai tên xã (thật là Đan Thượng) → không khớp danh mục.
    # Ô Phường/Xã của cổng là danh sách chung cả tỉnh → chọn xã mới mang tên huyện cũ, đánh dấu phỏng đoán.
    tt = {"quocGia": "Việt Nam", "tinh": "Phú Thọ", "huyen": "Hạ Hòa", "xa": "Đơn Thượng", "diaChi": "Khu 2"}
    v = dict(_TU_NOP, VanBang_ThuongTru=tt, ChuHoSo_ThuongTru=tt, VanBang_DienThoai="0900000000")
    fields, _ = mapper.enrich([{"name": k, "value": x} for k, x in v.items()], {"formContext": {}})
    by_name = {f["name"]: f for f in fields}
    for name in ("data[district]", "data[ownerDistrict]"):
        assert by_name[name]["value"] == "Xã Hạ Hòa"
        assert by_name[name].get("default") is True
    assert by_name["data[ownerProvince]"]["value"] == "Tỉnh Phú Thọ"
    assert "Hạ Hòa" not in (by_name.get("data[lienhe]", {}).get("value") or "")


# Cài đặt "Lấy người nộp theo tờ khai" (dữ liệu bịa): cán bộ đăng nhập tài khoản của mình, Phần I theo chủ văn bằng.
_THEO_TO_KHAI = {"submitterMode": "owner_as_submitter",
                 "formContext": {"applicantFullname": "LÊ THỊ CÁN BỘ", "applicantIdentityNumber": "001190000111"}}
_TU_NOP_DU = dict(_TU_NOP, ChuHoSo_NgayCap="10/10/2022", VanBang_DienThoai="0900000001",
                  ChuHoSo_ThuongTru={"quocGia": "Việt Nam", "tinh": "Phú Thọ", "xa": "Hạ Hòa", "diaChi": "Khu 2"})


def _map_opts(values, options):
    out, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    return {f["name"]: f for f in out}, warnings


def test_theo_to_khai_phan_i_la_chu_van_bang_du_ho_ten():
    got, warnings = _map_opts(_TU_NOP_DU, _THEO_TO_KHAI)
    assert got["data[fullname]"]["value"] == "TRẦN VĂN MẪU"
    assert got["data[identityNumber]"]["value"] == "001203001234"
    assert got["data[birthday]"]["value"] == "01/02/2003"
    assert got["data[identityDate]"]["value"] == "10/10/2022"
    assert got["data[province]"]["value"] == "Tỉnh Phú Thọ"
    assert got["data[phoneNumber]"]["value"] == "0900000001"
    assert got["data[isOwnerDossier]"]["value"] is True
    names = list(got)
    assert names.index("data[isOwnerDossier]") > names.index("data[phoneNumber]")  # điền Phần I rồi mới tích
    assert got["data[ownerFullname]"]["value"] == "TRẦN VĂN MẪU"
    assert any("Lấy người nộp theo tờ khai" in w and "LÊ THỊ CÁN BỘ" in w for w in warnings)


def test_tat_cai_dat_tai_khoan_khac_khong_ghi_phan_i():
    got, _ = _map_opts({k: v for k, v in _TU_NOP.items() if not k.startswith("ChuHoSo_")},
                       {"formContext": _THEO_TO_KHAI["formContext"]})
    assert "data[fullname]" not in got and "data[identityNumber]" not in got


def test_theo_to_khai_thieu_ngay_cap_thi_xoa_gia_tri_tai_khoan():
    got, _ = _map_opts({k: v for k, v in _TU_NOP.items() if not k.startswith("ChuHoSo_")}, _THEO_TO_KHAI)
    assert got["data[fullname]"]["value"] == "TRẦN VĂN MẪU"
    assert got["data[identityDate]"].get("clear") is True


def test_theo_to_khai_bo_qua_cccd_ten_khac():
    v = dict(_TU_NOP_DU, NguoiNop_HoTen="PHẠM VĂN NỘP", NguoiNop_SoGiayTo="002199005678")
    got, warnings = _map_opts(v, _THEO_TO_KHAI)
    assert got["data[fullname]"]["value"] == "TRẦN VĂN MẪU"
    assert got["data[identityNumber]"]["value"] == "001203001234"
    assert any("PHẠM VĂN NỘP" in w and "Lấy người nộp theo tờ khai" in w for w in warnings)


def test_theo_to_khai_tai_khoan_la_chu_van_bang_dien_du_phan_i_roi_moi_tich():
    # Tích trước thì cổng chép Phần I còn trống SĐT/tỉnh xuống chủ hồ sơ rồi khoá → phải điền Phần I trước.
    opts = {"submitterMode": "owner_as_submitter",
            "formContext": {"applicantFullname": "Trần Văn Mẫu", "applicantIdentityNumber": "001203001234"}}
    got, warnings = _map_opts(_TU_NOP_DU, opts)
    assert got["data[isOwnerDossier]"]["value"] is True
    assert "data[fullname]" not in got and "data[birthday]" not in got  # giữ VNeID
    assert got["data[phoneNumber]"]["value"] == "0900000001"
    assert got["data[province]"]["value"] == "Tỉnh Phú Thọ"
    assert got["data[identityDate]"]["value"] == "10/10/2022"
    names = list(got)
    assert names.index("data[isOwnerDossier]") > names.index("data[province]")
    assert not any("Lấy người nộp theo tờ khai" in w for w in warnings)


def test_theo_to_khai_co_uy_quyen_van_lay_ben_duoc_uy_quyen():
    v = dict(_TU_NOP_DU, NguoiNop_HoTen="PHẠM VĂN NỘP", NguoiNop_SoGiayTo="002199005678")
    got, _ = mapper.enrich([{"name": k, "value": x} for k, x in v.items()], _THEO_TO_KHAI,
                           ocr_text="GIẤY ỦY QUYỀN\nBÊN ĐƯỢC ỦY QUYỀN: Phạm Văn Nộp")
    by_name = {f["name"]: f["value"] for f in got}
    assert by_name["data[fullname]"] == "PHẠM VĂN NỘP"


def test_khong_co_thuong_tru_lay_tinh_tu_dia_chi_lien_lac_tren_don():
    # Đơn tự soạn (dữ liệu bịa): "Tôi tên là (viết chữ in hoa):", chỉ có "Địa chỉ liên lạc khi cần"; LLM xếp nhầm
    # dòng này vào địa chỉ dự thi, CCCD tải lên là của người khác → chủ hồ sơ vẫn có ô Tỉnh, không đoán xã.
    ocr = ("Kính gửi: Giám đốc Sở Giáo dục và Đào tạo Khánh Hòa\n"
           "Tôi tên là (viết chữ in hoa): TRẦN VĂN MẪU\nSinh ngày 01 tháng 02 năm 1980\n"
           "Điện thoại: 0900000001\nĐịa chỉ liên lạc khi cần: Thôn Mẫu - Xã Bịa Đặt - Ninh Thuận\n")
    v = {"VanBang_HoTen": "TRẦN VĂN MẪU", "VanBang_DiaChiDuThi": "Thôn Mẫu - Xã Bịa Đặt - Ninh Thuận",
         "ChuHoSo_HoTen": "PHẠM VĂN NỘP", "ChuHoSo_SoGiayTo": "002199005678",
         "ChuHoSo_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": "Phường Từ Liêm", "diaChi": "Số 1"}}
    fields, _ = mapper.enrich([{"name": k, "value": x} for k, x in v.items()], {"formContext": {}}, ocr_text=ocr)
    got = {f["name"]: f["value"] for f in fields}
    assert got["data[ownerProvince]"] == "Tỉnh Khánh Hòa"  # Ninh Thuận đã nhập vào Khánh Hòa
    assert "data[ownerDistrict]" not in got and "data[ownerAddress]" not in got
    assert got["data[province]"] == "Thành phố Hà Nội"  # Phần I vẫn theo CCCD người nộp


def test_toi_ten_la_viet_chu_in_hoa_lam_neo():
    p = mapper._phieu_owner("Tôi tên là (viết chữ in hoa): TRẦN VĂN MẪU\nSinh ngày: 01/02/1980\n")
    assert p["name"] == "TRẦN VĂN MẪU" and p["dob"] == "01/02/1980"


def test_theo_to_khai_phan_i_cung_lay_tinh_tu_dia_chi_lien_lac():
    ocr = ("Tôi tên là (viết chữ in hoa): TRẦN VĂN MẪU\nSinh ngày 01 tháng 02 năm 1980\n"
           "Địa chỉ liên lạc khi cần: Thôn Mẫu - Xã Bịa Đặt - Khánh Hòa\n")
    v = {"VanBang_HoTen": "TRẦN VĂN MẪU", "VanBang_SoGiayTo": "001080001234",
         "ChuHoSo_HoTen": "PHẠM VĂN NỘP", "ChuHoSo_SoGiayTo": "002199005678",
         "ChuHoSo_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": "Phường Từ Liêm", "diaChi": "Số 1"}}
    fields, _ = mapper.enrich([{"name": k, "value": x} for k, x in v.items()], _THEO_TO_KHAI, ocr_text=ocr)
    got = {f["name"]: f["value"] for f in fields}
    assert got["data[fullname]"] == "TRẦN VĂN MẪU"
    assert got["data[province]"] == "Tỉnh Khánh Hòa" and got["data[ownerProvince]"] == "Tỉnh Khánh Hòa"
    assert "data[district]" not in got and "data[ownerDistrict]" not in got


def test_dia_chi_lien_lac_ghi_tinh_viet_tat():
    # Đơn viết tay ghi tỉnh viết tắt "KH" (dữ liệu bịa) → ô Tỉnh ra "Tỉnh Khánh Hòa", không ra "Tỉnh KH".
    ocr = ("Tôi tên là (viết chữ in hoa): TRẦN VĂN MẪU\nSinh ngày 01 tháng 02 năm 1980\n"
           "Địa chỉ liên lạc khi cần: Thôn Mẫu - Xã Bịa Đặt - KH\n")
    v = {"VanBang_HoTen": "TRẦN VĂN MẪU", "VanBang_SoGiayTo": "001080001234",
         "ChuHoSo_HoTen": "PHẠM VĂN NỘP", "ChuHoSo_SoGiayTo": "002199005678",
         "ChuHoSo_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": "Phường Từ Liêm", "diaChi": "Số 1"}}
    fields, _ = mapper.enrich([{"name": k, "value": x} for k, x in v.items()], _THEO_TO_KHAI, ocr_text=ocr)
    got = {f["name"]: f["value"] for f in fields}
    assert got["data[province]"] == "Tỉnh Khánh Hòa" and got["data[ownerProvince]"] == "Tỉnh Khánh Hòa"
