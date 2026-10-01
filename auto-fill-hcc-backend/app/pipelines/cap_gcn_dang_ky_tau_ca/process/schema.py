"""Compact schema cho "Cấp giấy chứng nhận đăng ký tàu cá, tàu phục vụ nuôi trồng thủy sản" (cổng Nông
nghiệp & Môi trường — Form.io). Field-key nhân thân data[...] TRÙNG KHÍT #66/#92/#101.

Nhóm field nguồn:
- NguoiDeNghi_* : nhân thân CHỦ TÀU = CHỦ HỒ SƠ (người CHÍNH, chủ MỚI đứng tên đăng ký).
- NguoiNop_*    : nhân thân NGƯỜI NỘP (chỉ khi có người khác nộp thay & có CCCD riêng).
- ChuTau_*      : loại chủ thể (Cá nhân/Tổ chức) + tên tổ chức + mã số thuế/mã số DN (khi chủ là Tổ chức).
- ToKhai_* / Tau_* : Phần III — Tờ khai đăng ký tàu cá 02a (cổng bổ sung sub-form 09/2026).
"""

# --- Nhân thân (dùng chung template cho NguoiDeNghi_ và NguoiNop_) ---
_PERSON_FIELDS = [
    ("HoTen", "Họ và tên {who}. Lấy từ {src}. Ghi IN HOA đúng như trên CCCD."),
    ("NgaySinh", "Ngày sinh {who}, dd/mm/yyyy — CCCD (hoặc 'Bên mua – Sinh ngày' của Hợp đồng mua bán)."),
    ("GioiTinh", 'Giới tính {who}: "Nam" hoặc "Nữ" — CCCD.'),
    ("SoDinhDanh", "Số CCCD/CMND/căn cước/định danh cá nhân {who}. Đọc CCCD (mặt trước/MRZ), hoặc Tờ khai "
        "02a.ĐKT mục 'Số CCCD/CC', hoặc Hợp đồng mua bán ('Căn cước công dân số'). Chỉ chữ số. Ưu tiên số "
        "12 chữ số (CCCD/căn cước/định danh) hơn số 9 chữ số (CMND) nếu có cả hai."),
    ("NgayCap", "Ngày cấp CCCD/CMND {who}, dd/mm/yyyy — mặt sau CCCD hoặc dòng '… cấp ngày' của Hợp đồng "
        "mua bán."),
    ("NoiCap", 'Nơi cấp/cơ quan cấp giấy tờ tùy thân {who}. CCCD gắn chip KHÔNG in nhãn "Nơi cấp" riêng → '
        'ghi "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → '
        '"Bộ Công an". Có thể lấy ở Quyết định chấp thuận (mục "Cơ quan cấp") nếu hồ sơ có.'),
    ("ThuongTru", "NƠI THƯỜNG TRÚ {who}, object {{quocGia,tinh,xa,diaChi}}. Ưu tiên CCCD (Nơi thường trú); "
        "bổ sung Tờ khai 02a.ĐKT (Thường trú tại) / Hợp đồng mua bán (Nơi cư trú). tinh='Tỉnh/Thành phố …', "
        "xa=phường/xã, diaChi=số nhà/khóm/ấp/thôn/tổ (KHÔNG kèm phường/xã/tỉnh). ⚠ Giấy chứng nhận đăng ký "
        "tàu cá cũ có thể còn ghi địa danh CŨ trước sáp nhập → ưu tiên CCCD/Hợp đồng."),
    ("DienThoai", "Số điện thoại DI ĐỘNG {who}. Ưu tiên Tờ khai 02a.ĐKT (Số điện thoại) / Thông báo thuế "
        "(Điện thoại). Chỉ chữ số; KHÔNG có trên CCCD."),
    ("Email", "Email liên hệ {who} nếu giấy tờ có; thường không có → bỏ."),
    ("QuocTich", 'Quốc tịch {who} từ CCCD/Hợp đồng; thường là "Việt Nam".'),
]

_DENGHI_SRC = "CCCD / Tờ khai 02a.ĐKT / Hợp đồng mua bán của CHỦ TÀU (chủ mới đứng tên đăng ký)"

FIELDS: list[dict] = []
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiDeNghi_{_name}",
        "desc": _tmpl.format(who="CHỦ TÀU (chủ hồ sơ, chủ MỚI đứng tên đăng ký)", src=_DENGHI_SRC),
    })
for _name, _tmpl in _PERSON_FIELDS:
    FIELDS.append({
        "name": f"NguoiNop_{_name}",
        "desc": _tmpl.format(who="NGƯỜI NỘP (chỉ khi nộp thay & có CCCD người nộp)", src="CCCD của NGƯỜI NỘP"),
    })

# --- Loại chủ thể chủ tàu (Cá nhân / Tổ chức) ---
FIELDS += [
    {"name": "ChuTau_LoaiChuThe", "desc": 'Loại chủ thể của CHỦ TÀU (chủ hồ sơ): trả "Tổ chức" nếu chủ '
        'tàu là công ty/hợp tác xã/doanh nghiệp/cơ quan (có tên tổ chức + mã số thuế/mã số DN trên Giấy '
        'chứng nhận ĐKDN, Hợp đồng, Thông báo thuế); ngược lại trả "Cá nhân". Đa số hồ sơ là "Cá nhân".'},
    {"name": "ChuTau_TenToChuc", "desc": "CHỈ khi ChuTau_LoaiChuThe='Tổ chức': tên đầy đủ tổ chức/doanh "
        "nghiệp/hợp tác xã chủ tàu (Giấy chứng nhận ĐKDN / Hợp đồng / Giấy chứng nhận đăng ký tàu cá)."},
    {"name": "ChuTau_MaSoThue", "desc": "CHỈ khi ChuTau_LoaiChuThe='Tổ chức': mã số thuế / mã số doanh "
        "nghiệp / mã số HTX của tổ chức chủ tàu. Chỉ chữ số. Nguồn: Thông báo thuế / Giấy chứng nhận ĐKDN."},
]

# --- TỜ KHAI ĐĂNG KÝ TÀU CÁ (Mẫu 02a.ĐKT) — sub-form "1.003650_M2a.H38" cổng thêm vào form (09/2026).
# Nguồn chính: Tờ khai 02a.ĐKT; thiếu thì bổ sung Giấy chứng nhận an toàn kỹ thuật / Biên bản kiểm tra /
# GCN đăng ký tàu cá cũ / Hợp đồng mua bán.
_SO = " Chỉ trả CON SỐ (dấu thập phân là dấu chấm, vd 12.9); không kèm đơn vị."
FIELDS += [
    {"name": "ToKhai_KinhGui", "desc": "Mục 'Kính gửi' của Tờ khai 02a.ĐKT (tên cơ quan đăng ký tàu cá). "
        "Chép nguyên văn."},
    {"name": "ToKhai_DiaDanh", "desc": "Địa danh nơi lập Tờ khai — phần '……, ngày … tháng … năm …' ở đầu Tờ "
        "khai 02a.ĐKT (vd 'Đà Nẵng'). Chỉ tên địa danh."},
    {"name": "ToKhai_NgayKhai", "desc": "Ngày lập Tờ khai 02a.ĐKT, dd/mm/yyyy. CHỈ trả khi đủ cả ngày, tháng, "
        "năm; Tờ khai để trống ngày (vd 'ngày … tháng 9 năm 2026') → BỎ TRỐNG."},
    {"name": "Tau_Ten", "desc": "Tên tàu ở Tờ khai 02a.ĐKT. Tờ khai để trống/chấm chấm → BỎ TRỐNG, KHÔNG lấy "
        "số đăng ký thay tên tàu."},
    {"name": "Tau_CongDung", "desc": "Công dụng (nghề) của tàu — Tờ khai 02a.ĐKT; thiếu thì GCN an toàn kỹ "
        "thuật/GCN đăng ký cũ (vd 'Câu', 'Lưới rê')."},
    {"name": "Tau_NamDong", "desc": "NĂM đóng tàu (4 chữ số) — Tờ khai 02a.ĐKT mục 'Năm, nơi đóng' hoặc 'Năm "
        "và nơi đóng' của GCN an toàn kỹ thuật. Chỉ trả số năm."},
    {"name": "Tau_NoiDong", "desc": "NƠI đóng tàu (cơ sở/địa điểm) — cùng mục 'Năm, nơi đóng'. Chỉ phần nơi "
        "đóng, không kèm năm."},
    {"name": "Tau_CangDangKy", "desc": "Cảng đăng ký — Tờ khai 02a.ĐKT (vd 'Cảng cá …')."},
    {"name": "Tau_Lmax", "desc": "Chiều dài lớn nhất Lmax (m)." + _SO},
    {"name": "Tau_Bmax", "desc": "Chiều rộng lớn nhất Bmax (m)." + _SO},
    {"name": "Tau_D", "desc": "Chiều cao mạn D (m) — chữ D HOA trong 'Lmax, Bmax, D'." + _SO},
    {"name": "Tau_Ltk", "desc": "Chiều dài thiết kế Ltk (m)." + _SO},
    {"name": "Tau_Btk", "desc": "Chiều rộng thiết kế Btk (m)." + _SO},
    {"name": "Tau_d", "desc": "Chiều chìm d (m) — chữ d THƯỜNG trong 'Ltk, Btk, d'." + _SO},
    {"name": "Tau_VatLieuVo", "desc": "Vật liệu vỏ tàu (vd 'Gỗ', 'Thép', 'Composite')."},
    {"name": "Tau_TongDungTich", "desc": "Tổng dung tích GT." + _SO},
    {"name": "Tau_TrongTai", "desc": "Trọng tải toàn phần DW (tấn)." + _SO},
    {"name": "Tau_SoThuyenVien", "desc": "Số thuyền viên (người). Chỉ số nguyên (vd '04' → 4)."},
    {"name": "Tau_NgheKiem", "desc": "Nghề kiêm (nếu có) ở Tờ khai 02a.ĐKT. Ghi 'không'/để trống → BỎ TRỐNG."},
    {"name": "Tau_VungHoatDong", "desc": "Vùng hoạt động (vd 'Vùng lộng', 'Vùng khơi')."},
    {"name": "Tau_MayChinh", "desc": "Bảng MÁY CHÍNH, mảng object mỗi máy 1 phần tử: {kyHieu, soMay, "
        "congSuatKW, vongQuayRPM, ghiChu}. kyHieu = ký hiệu/model máy; soMay = số máy (dãy số in trên máy); "
        "congSuatKW = công suất định mức kW (chỉ số); vongQuayRPM = vòng quay định mức rpm (chỉ số). Ưu tiên "
        "bảng Máy chính của Tờ khai 02a.ĐKT; bảng trống thì lấy bảng máy của GCN an toàn kỹ thuật/Biên bản "
        "kiểm tra/GCN đăng ký cũ. Ô nào không có thì bỏ khóa đó. KHÔNG bịa."},
    {"name": "Tau_ChuSoHuu", "desc": "CHỈ khi tàu thuộc sở hữu NHIỀU chủ (mục 2 Tờ khai 02a.ĐKT có liệt kê): "
        "mảng object {hoTen, diaChi, soGiayTo}. Tàu một chủ / mục 2 để trống → BỎ TRỐNG."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _p in ("NguoiDeNghi_", "NguoiNop_"):
    COMPACT_COMP_BY_NAME[f"{_p}NgaySinh"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}NgayCap"] = "x-date"
    COMPACT_COMP_BY_NAME[f"{_p}ThuongTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["ToKhai_NgayKhai"] = "x-date"
COMPACT_COMP_BY_NAME["Tau_MayChinh"] = "x-array"
COMPACT_COMP_BY_NAME["Tau_ChuSoHuu"] = "x-array"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên lấy CHUẨN từ HTML thật + mapping xlsx.
UI_COMP_BY_NAME = {
    # Phần I — THÔNG TIN NGƯỜI NỘP HỒ SƠ.
    "data[chonDoiTuong]": "dom-select",   # "Cá nhân" / "Tổ chức/Doanh nghiệp" / "Cơ quan nhà nước".
    "data[organization]": "dom-input",    # ẩn khi Cá nhân — tên tổ chức (Phần I) khi Đối tượng = Tổ chức.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",  # DISABLED trên form (khóa theo VNeID) — điền vô hại, cổng tự khóa.
    "data[taxCode]": "dom-input",         # ẩn khi Cá nhân — mã số thuế (Phần I) khi Đối tượng = Tổ chức.
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",       # ⚠ label "Phường/Xã" nhưng field-key là district.
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",

    # BỎ TÍCH khi nộp thay; tự nộp → TICH (True) để cổng tự đổ Phần I → Phần II.
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Phần II — THÔNG TIN CHỦ HỒ SƠ (chủ tàu). Chỉ điền khi nộp thay (hoặc chủ là Tổ chức).
    "data[ownerOrganizationFullname]": "dom-input",  # ẩn khi Cá nhân.
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerTaxCode]": "dom-input",               # ẩn khi Cá nhân.
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerEmail]": "dom-input",
    "data[ownerNation]": "dom-select",

    # Phần III — TỜ KHAI ĐĂNG KÝ TÀU CÁ (sub-form "1.003650_M2a.H38"). data[fullname]/address/
    # identityNumber/phoneNumber TRÙNG key Phần I → mapper điền occurrence=1 (Phần I occurrence=0).
    "data[diaDanh]": "dom-input",
    "data[ngayBC]": "dom-date",
    "data[kinhGui]": "dom-input",
    "data[tenTau]": "dom-input",
    "data[congDungNghe]": "dom-input",
    "data[namDong]": "dom-input",
    "data[noiDong]": "dom-input",
    "data[cangDangKy]": "dom-input",
    "data[Lmax]": "dom-input",
    "data[Bmax]": "dom-input",
    "data[Dmax]": "dom-input",
    "data[Ltk]": "dom-input",
    "data[Btk]": "dom-input",
    "data[d]": "dom-input",
    "data[vatLieuVo]": "dom-input",
    "data[tongDungTich]": "dom-input",
    "data[trongTai]": "dom-input",
    "data[soThuyenVien]": "dom-input",
    "data[ngheKiem]": "dom-input",
    "data[vungHoatDong]": "dom-input",
    "data[mayChinh]": "dom-editgrid",   # editgrid: thuTu/kyHieuMay/soMay/congSuatDinhMucKW/vongQuayDinhMucRPM/ghiChu
    "data[chuSoHuu]": "dom-editgrid",   # editgrid: thuTu/hoTenChuSoHuu/diaChiChuSoHuu/soGiayToChuSoHuu
    "data[chuDN]": "dom-input",         # "ĐẠI DIỆN CHỦ TÀU" (họ tên người ký).
}
