"""Trường THEN CHỐT (nguồn sự thật duy nhất) cho từng thủ tục auto-fill.

Định nghĩa: trường THÔNG TIN lấy từ giấy tờ (OCR/LLM) mà sai thì hồ sơ sai. KHÔNG tính giá trị
mặc định/bôi vàng (loại cư trú, radio trong/ngoài nước, quốc tịch VN mặc định, "Căn cước công dân",
loại/nghiệp vụ đăng ký, phương thức nhận KQ, cấp bản sao), trường trùng lặp (số giấy tờ = số định danh),
mã hoá nội bộ (Ma*). Xem docs/thong-ke-truong-then-chot.md.

Mỗi phần tử là TÊN field (str) hoặc TUPLE các tên thay thế (đếm là 1, "filled" nếu bất kỳ tên nào có
giá trị) — vd đất đai dùng CCCD HOẶC CMND.
"""

_KHAI_SINH_THUONG = [
    # Người yêu cầu
    "HoVaTenC", "SoDinhDanhC", "NgayCapDDC", "NoiCapDDC", "nycNoiCuTru_TrongNuoc", "QuanHe",
    # Con
    "HoTenKS", "NgaySinhChon", "GioiTinhKS", "DanTocKS", "nksNoiSinh_TrongNuoc", "nksQueQuan_TrongNuoc",
    # Cha
    "HoTenChaKS", "NamSinhChaKS", "DanTocChaKS", "SoDinhDanhCha", "NgayCapDDCha", "NoiCapDDCha", "ChaNoiCuTru_TrongNuoc",
    # Mẹ
    "HoTenMeKS", "NamSinhMeKS", "DanTocMeKS", "SoDinhDanhMe", "NgayCapDDMe", "NoiCapDDMe", "MeNoiCuTru_TrongNuoc",
]  # 26

_NHAN_CHA_ME_CON = [
    "HoVaTenC", "SoDinhDanhC", "NgayCapDDC", "NoiCapDDC", "TT_TinhThanhC", "TT_PhuongXaC",
    "HotenA", "ngaysinhA", "gioitinhA", "dantocA", "sodinhdanhA", "noicutruA_TrongNuoc",
    "hotenB", "ngaysinhB", "gioitinhB", "dantocB", "noicutruB_TrongNuoc", "loaiXacNhan",
]  # 18

_DANG_KY_LAI = _KHAI_SINH_THUONG + [
    "soDKTruocDay", "quyenSoDKTruocDay", "ngayDKTruocDay", "coQuanDKTruocDay_filter",
]  # 30

_KHAI_SINH_LIEN_THONG = [
    "ChaHoTen", "ChaNgaySinh", "ChaSoGiayTo", "ChaDiaChi",
    "MeNgaySinh", "MeSoGiayTo", "MeDiaChi",
    "NgaySinh", "GioiTinh", "NsDiaChi", "QqDiaChi",
    "GiayCNKHSo", "GiayCNKHQuyenSo", "GiayCNKHNgayCap", "GiayCNKHNoiCap",
    "NycSdt",
]  # 16

_KET_HON = [
    "HoTenBenNam", "NgaySinhBenNam", "DanTocBenNam", "SoDinhDanh_BenNam",
    "NgayCapDD_BenNam", "NoiCapDD_BenNam", "NoiCuTru_BenNam_TrongNuoc",
    "HoTenBenNu", "NgaySinhBenNu", "DanTocBenNu", "SoDinhDanh_BenNu",
    "NgayCapDD_BenNu", "NoiCapDD_BenNu", "NoiCuTru_BenNu_TrongNuoc",
]  # 14

_KHAI_TU = [
    # Người yêu cầu
    "HoVaTenC", "SoDinhDanhC", "NgayCapDDC", "NoiCapDDC", "nycNoiCuTru_TrongNuoc",
    # Người mất
    "HoTen", "NgaySinh", "GioiTinh", "nktDanToc", "SoDinhDanh", "NgayCapDD", "NoiCapDD",
    "nktNoiCuTru_TrongNuoc", "nktNoiChet_TrongNuoc",
    # Sự kiện chết
    "NgayMat", "GioMat", "PhutMat", "NguyenNhanMat",
    # Giấy báo tử
    "gbtSo", "gbtCoQuanCap", "gbtNgay",
]  # 21

_THAY_DOI_HO_TICH = [
    "SoGiayToTuyThanC",
    "ntdHoTen", "ntdNgaySinh", "ntdGioiTinh", "ntdDanToc", "ntdSoDDCN",
    "ntdNgayCapGiayToTuyThan", "ntdNoiCapGiayToTuyThan", "ntdNoiCuTru_TrongNuoc",
    "soDangKyHSGoc", "quyenDangKyHSGoc", "ngayDangKyHSGoc", "noiDangKyHSGoc",
]  # 13

_TRICH_LUC = [
    "HoVaTenC", "SoDinhDanhC", "NgayCapDDC", "NoiCapDDC", "NYC_NoiCuTru_TrongNuoc",
    "NDK_HoVaTen", "NDK_NgaySinh", "NDK_GioiTinh", "NDK_DanToc", "NDK_SoDinhDanh",
    "NDK_NgayCap", "NDK_NoiCap", "NDK_NoiCuTru_TrongNuoc",
    "HoSo_TenGiayTo", "HoSo_CoQuanDangKy", "HoSo_So", "HoSo_QuyenSo", "HoSo_NgayCapSo",
]  # 18

_TTHN = [
    "HoVaTenC", "SoDinhDanhC", "NgayCapDDC", "NoiCapDDC", "nycNoiCuTru_TrongNuoc",
    "HoVaTenC1", "NgaySinhC1", "GioiTinhC1", "DanTocC1", "SoDinhDanhC1",
    "NgayCapDDC1", "NoiCapDDC1", "nxnNoiCuTru_TrongNuoc", "TinhTrangHonNhanC1",
    "quanhevoinguoiduocxacminh",
]  # 15

_DAT_DAI = [
    "CongDan_tenCongDan", "CongDan_ngaySinhCongDan", "CongDan_gioiTinhCongDan", "CongDan_danTocCongDan",
    ("CongDan_soCCCD", "CongDan_soCmnd"),
    "CongDan_ngayCapCmnd", "CongDan_noiCapCmnd",
    "CongDan_tenCoQuanToChuc", "CongDan_maSoThueNguoiNop",
    "CongDan_soGCNGP", "CongDan_ngayCapGCNGP", "CongDan_noiCapGCNGP",
]  # 12

_CAP_NUOC_SACH = [
    "CongDan_tenCongDan", "CongDan_ngaySinhCongDan", "CongDan_gioiTinhCongDan", "CongDan_danTocCongDan",
    ("CongDan_soCCCD", "CongDan_soCmnd"),
    "CongDan_ngayCapCmnd", "CongDan_noiCapCmnd",
    "CongDan_maTinhThanh", "CongDan_maPhuongXa", "CongDan_diaChi",
    "CongDan_diDong", "CongDan_soGCNGP", "CongDan_ngayCapGCNGP", "CongDan_noiCapGCNGP",
    "CongDan_noiOHienTai", "CongDan_diaChiThuongTru",
]  # 16

_MAI_TANG = [
    "data[fullname]", "data[birthday]", "data[gender]", "data[identityNumber]",
    "data[identityDate]", "data[idIssuePlace]", "data[address]", "data[province]",
    "data[ownerFullname]", "data[ownerBirthday]", "data[ownerGender]", "data[ownerIdentityNumber]",
    "data[ownerIdentityDate]", "data[ownerIdIssuePlace]", "data[ownerAddress]", "data[ownerProvince]",
]  # 16

_MAI_TANG_DAN_CONG = [
    "data[fullname]", "data[birthday]", "data[gender]", "data[identityNumber]",
    "data[identityDate]", "data[idIssuePlace]", "data[phoneNumber]", "data[address]", "data[province]",
    "data[ownerFullname]", "data[ownerBirthday]", "data[ownerGender]", "data[ownerIdentityNumber]",
    "data[ownerIdentityDate]", "data[ownerIdIssuePlace]", "data[ownerPhoneNumber]",
    "data[ownerAddress]", "data[ownerProvince]",
]  # 18

_XET_TUYEN_VIEN_CHUC = [
    "data[fullname]", "data[birthday]", "data[gender]", "data[identityNumber]",
    "data[identityDate]", "data[idIssuePlace]", "data[address]", "data[province]",
    "data[ownerFullname]", "data[ownerBirthday]", "data[ownerGender]", "data[ownerIdentityNumber]",
    "data[ownerIdentityDate]", "data[ownerIdIssuePlace]", "data[ownerAddress]", "data[ownerProvince]",
]  # 16

_XET_TUYEN_CONG_CHUC = [
    "data[fullname]", "data[birthday]", "data[gender]", "data[identityNumber]",
    "data[identityDate]", "data[idIssuePlace]", "data[province]", "data[district]", "data[address]",
    "data[ownerFullname]", "data[ownerBirthday]", "data[ownerGender]", "data[ownerIdentityNumber]",
    "data[ownerIdentityDate]", "data[ownerIdIssuePlace]", "data[ownerProvince]", "data[ownerDistrict]",
    "data[ownerAddress]", "data[VtVlDt]", "data[CqTcDt]", "data[identityAgency]",
    "data[TonGiao]", "data[DanToc]", "data[province1]", "data[district1]", "data[province2]",
    "data[district2]", "data[TtSk]", "data[ChieuCao]", "data[CanNang]",
    "data[DataGrid][0][TenTruong]", "data[DataGrid][0][NgayCap1]",
    "data[DataGrid][0][TdVh1]", "data[DataGrid][0][ShVbCc]", "data[CoKhong]", "data[DtUt]",
    "data[Dut]", "data[DataGrid2][0][textField1]", "data[DataGrid2][0][textField2]",
]  # 39

_THI_TUYEN_CONG_CHUC = [
    "data[fullname]", "data[birthday]", "data[gender]", "data[identityNumber]",
    "data[identityDate]", "data[idIssuePlace]", "data[province]", "data[district]", "data[address]",
    "data[ownerFullname]", "data[ownerBirthday]", "data[ownerGender]", "data[ownerIdentityNumber]",
    "data[ownerIdentityDate]", "data[ownerIdIssuePlace]", "data[ownerProvince]", "data[ownerDistrict]",
    "data[ownerAddress]", "data[VtVlDt]", "data[CqTcDt]", "data[identityAgency]",
    "data[TonGiao]", "data[DanToc]", "data[province1]", "data[district1]", "data[province2]",
    "data[district2]", "data[village]", "data[TtSk]", "data[ChieuCao]", "data[CanNang]",
    "data[DataGrid][0][TenTruong]", "data[DataGrid][0][NgayCap1]",
    "data[DataGrid][0][TdVh1]", "data[DataGrid][0][ShVbCc]", "data[CoKhong]", "data[DtUt]",
    "data[Dut]", "data[DataGrid2][0][txtDonViNV]", "data[DataGrid2][0][txtNguyenVong]",
]  # 40

_KINH_DOANH = [
    "ctl00$C$NAMEFld", "ctl00$C$SHORT_NAMEFld", "ctl00$C$BUSINESS_ACT_TEXTFld", "ctl00$C$CPT_CHARTER_AMOUNTFld",
    "ctl00$C$OWN_PCtl$PERSCtl$FULL_NAMEFld", "ctl00$C$OWN_PCtl$PERSCtl$DATE_OF_BIRTHFld",
    "ctl00$C$OWN_PCtl$PERSCtl$GENDER_IDFld", "ctl00$C$OWN_PCtl$PERSCtl$PERS_DOC_NOFld",
    "ctl00$C$OWN_PCtl$PERSCtl$PHONEFld", "ctl00$C$OWN_PCtl$PERSCtl$EMAILFld",
    "ctl00$C$UC_DW_TAXEditCtl$TOTAL_OF_LABORSFld",
]  # 11

KEY_FIELDS_BY_PROCEDURE: dict[str, list] = {
    "khai-sinh-dang-ky-thuong": _KHAI_SINH_THUONG,
    "khai-sinh-ket-hop-nhan-cha-me-con": _KHAI_SINH_THUONG,
    "khai-sinh-dang-ky-lai": _DANG_KY_LAI,
    # Cùng bộ trường then chốt với khai sinh thường: thủ tục này KHÔNG có khối "đăng ký trước đây".
    "khai-sinh-da-co-ho-so": _KHAI_SINH_THUONG,
    "khai-sinh-dang-ky": _KHAI_SINH_LIEN_THONG,
    "ket-hon": _KET_HON,
    "khai-tu": _KHAI_TU,
    "thay-doi-cai-chinh-ho-tich": _THAY_DOI_HO_TICH,
    "trich-luc-ks": _TRICH_LUC,
    "xac-nhan-tinh-trang-hon-nhan": _TTHN,
    "dinh-chinh-sai-sot": _DAT_DAI,
    "dang-ky-lap-dat-su-dung-nuoc-sach": _CAP_NUOC_SACH,
    "chuyen-doi-ten-hop-dong-nuoc-sach": _CAP_NUOC_SACH,
    "dieu-chinh-dat-dai": _DAT_DAI,
    "dang-ky-dat-dai-lan-dau": _DAT_DAI,
    "dang-ky-dat-dai-tai-san-lan-dau-nguoi-o-nuoc-ngoai": _DAT_DAI,
    "ho-tro-mai-tang": _MAI_TANG,
    "ho-tro-mai-tang-huu-tri-xa-hoi": _MAI_TANG,
    "dieu-chinh-huu-tri-xa-hoi": _MAI_TANG,
    "mai-tang-dan-cong-hoa-tuyen": _MAI_TANG_DAN_CONG,
    "xet-tuyen-vien-chuc": _XET_TUYEN_VIEN_CHUC,
    "xet-tuyen-cong-chuc": _XET_TUYEN_CONG_CHUC,
    "thi-tuyen-cong-chuc": _THI_TUYEN_CONG_CHUC,
    "dang-ky-kinh-doanh": _KINH_DOANH,
}


def key_fields_total(procedure: str) -> int:
    """Tổng số trường then chốt của thủ tục (0 nếu không phải thủ tục auto-fill có định nghĩa)."""
    return len(KEY_FIELDS_BY_PROCEDURE.get(procedure, []))


def count_key_fields(procedure: str, fields: list[dict] | None) -> tuple[int, int]:
    """Trả (tổng trường then chốt, số trường BÓC TÁCH ĐƯỢC) cho 1 hồ sơ.

    fields: list UI field [{name, value, ...}] (mapper enrich / process_requests.fields).
    """
    if procedure == "khai-sinh-ket-hop-nhan-cha-me-con":
        names = {item.get("name") for item in (fields or []) if isinstance(item, dict)}
        entries = _NHAN_CHA_ME_CON if {"HotenA", "hotenB", "loaiXacNhan"} & names else _KHAI_SINH_THUONG
    else:
        entries = KEY_FIELDS_BY_PROCEDURE.get(procedure)
    if not entries:
        return (0, 0)
    values = {
        f.get("name"): f.get("value")
        for f in (fields or [])
        if isinstance(f, dict)
    }

    def _has(name: str) -> bool:
        return values.get(name) not in (None, "", {}, [])

    filled = 0
    for entry in entries:
        names = entry if isinstance(entry, tuple) else (entry,)
        if any(_has(n) for n in names):
            filled += 1
    return (len(entries), filled)
