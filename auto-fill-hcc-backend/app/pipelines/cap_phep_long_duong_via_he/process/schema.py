"""Compact schema cho "Cấp phép sử dụng tạm thời lòng đường, vỉa hè vào mục đích khác" — cổng DVC Bộ Xây dựng dvc.moc.gov.vn (Form.io, engine fillFormStandard dom-*). CÙNG cổng #76/#78 (Bộ Xây dựng); là là
EFORM RIÊNG, nhiều phần, field-key data[...] KHÁC (không có ownerFullname/isOwnerDossier/noidung...).

Cấu trúc form:
- Phần I  : NGƯỜI NỘP (cá nhân đại diện) — fullname/birthday/gender/email/CCCD/địa chỉ + chonDoiTuong.
- Phần I-b: DOANH NGHIỆP (panel điều kiện, chỉ hiện khi chonDoiTuong="Tổ chức") — organization/taxCode/
            organizationPhoneNumber/nation1/province1/district1/address1.
- Phần II : ĐƠN đề nghị (header) — tenDonVi/tenCoQuanDeNghi/kinhGui/TinhThanh(nơi lập)/ngayThangNam.
- Phần III: THÔNG TIN ĐỀ NGHỊ — tenSuKien(mục đích)/tenDoanDuong/tenTuyenDuong/diaBan/tuNgay/denNgay.
- Phần IV : LIÊN HỆ — diaChiLienHe/soDienThoai.

Mẫu = Công ty TNHH Dana Fine Foods (tổ chức), đại diện Bà Lê Thị Mỹ Dung (giám đốc, tự nộp).
"""

# --- Người nộp (cá nhân đại diện / hoặc cá nhân tự nộp) ---
FIELDS: list[dict] = [
    {"name": "ChonDoiTuong", "desc": '"Tổ chức" nếu hồ sơ nộp dưới danh nghĩa công ty/doanh nghiệp/HTX/cơ '
        'quan (có Giấy chứng nhận đăng ký doanh nghiệp, tên có "Công ty"/"Doanh nghiệp"/"HTX"); "Cá nhân" '
        'nếu một người tự đề nghị. Suy từ giấy tờ: có GCN ĐKDN → Tổ chức.'},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP HỒ SƠ (cá nhân trực tiếp ký/nộp; nếu tổ chức "
        "thì là người đại diện theo pháp luật). IN HOA như CCCD. Lấy ở Đơn đề nghị / Giấy cam kết / GCN "
        "ĐKDN (mục Người đại diện)."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người nộp, dd/mm/yyyy — CCCD / Đơn đề nghị / GCN ĐKDN (mục 5)."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người nộp: "Nam"/"Nữ" — CCCD / GCN ĐKDN (mục Người đại '
        'diện). Nếu không có nhãn, suy từ danh xưng Ông/Bà.'},
    {"name": "NguoiNop_Email", "desc": "Email người nộp; nếu giấy tờ chỉ có email công ty (GCN ĐKDN) thì "
        "dùng email đó. Bỏ nếu không có."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND/định danh cá nhân NGƯỜI NỘP. Đọc CCCD / Đơn đề "
        "nghị / Giấy cam kết / GCN ĐKDN (Số giấy tờ pháp lý của cá nhân). Chỉ chữ số, ưu tiên 12 số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD người nộp, dd/mm/yyyy — mặt sau CCCD / Đơn đề nghị / GCN ĐKDN."},
    {"name": "NguoiNop_NoiCap", "desc": 'Cơ quan cấp CCCD người nộp. CCCD gắn chip: "Cục Cảnh sát quản lý '
        'hành chính về trật tự xã hội". Giấy tờ có thể viết tắt (CCS.QLHCVTTXH) → chuẩn hóa tên đầy đủ.'},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại CÁ NHÂN người nộp (Đơn đề nghị / Giấy cam kết: "
        "'Điện thoại số'). Chỉ chữ số. KHÁC điện thoại doanh nghiệp."},
    {"name": "NguoiNop_DiaChi", "desc": "Địa chỉ thường trú/liên hệ NGƯỜI NỘP, object {quocGia,tinh,xa,"
        "diaChi}. ƯU TIÊN lấy ở ĐƠN ĐỀ NGHỊ / Giấy cam kết (dòng 'Thường trú tại') — đây là tờ khai của "
        "chính hồ sơ này; CHỈ dùng CCCD hoặc GCN ĐKDN (mục 5) khi Đơn KHÔNG ghi địa chỉ. Nếu Đơn và GCN "
        "khác nhau, LẤY THEO ĐƠN. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường (KHÔNG kèm "
        "phường/xã/tỉnh)."},
]

# --- Doanh nghiệp (chỉ khi Tổ chức) ---
FIELDS += [
    {"name": "DoanhNghiep_Ten", "desc": "Tên đầy đủ DOANH NGHIỆP/tổ chức (khi nộp danh nghĩa tổ chức). Lấy "
        "ở GCN ĐKDN (Tên công ty viết bằng tiếng Việt) hoặc mục 'Đại diện (nếu là cơ quan, tổ chức)' trên "
        "Đơn. Bỏ nếu là cá nhân."},
    {"name": "DoanhNghiep_MaSoThue", "desc": "Mã số doanh nghiệp / mã số thuế (GCN ĐKDN đầu trang / HĐ thuê "
        "nhà: Mã số thuế Bên B). Chỉ chữ số. Bỏ nếu cá nhân."},
    {"name": "DoanhNghiep_DienThoai", "desc": "Số điện thoại DOANH NGHIỆP (GCN ĐKDN, mục Địa chỉ trụ sở "
        "chính). Chỉ chữ số. KHÁC điện thoại cá nhân người nộp."},
    {"name": "DoanhNghiep_DiaChi", "desc": "Địa chỉ TRỤ SỞ CHÍNH doanh nghiệp, object {quocGia,tinh,xa,"
        "diaChi}. Lấy ở GCN ĐKDN (mục 2 - Địa chỉ trụ sở chính). Bỏ nếu cá nhân."},
]

# --- Đơn đề nghị (header) ---
FIELDS += [
    {"name": "Don_KinhGui", "desc": "Cơ quan nhận đơn (dòng 'Kính gửi:' trên Đơn đề nghị / Giấy cam kết). "
        "Ví dụ 'Ủy ban nhân dân phường Hải Châu'."},
    {"name": "Don_NgayLap", "desc": "Ngày lập đơn, dd/mm/yyyy — dòng '..., ngày ... tháng ... năm ...' cuối "
        "Đơn đề nghị / Giấy cam kết."},
]

# --- Thông tin đề nghị (vị trí, mục đích, thời gian) ---
FIELDS += [
    {"name": "DeNghi_MucDich", "desc": "Mục đích/tên sự kiện sử dụng tạm thời lòng đường, vỉa hè. Đơn đề "
        "nghị 'Sử dụng vào mục đích' / Giấy cam kết 'Mục đích sử dụng vỉa hè' / Giấy phép vỉa hè cũ (mục 4). "
        "Ví dụ 'Để xe', 'Để xe mô tô, xe gắn máy và xe đạp'."},
    {"name": "DeNghi_DoanDuong", "desc": "Tên và phạm vi đoạn đường đề nghị sử dụng (khu vực trước nhà số "
        "…, đường …, phường …). Đơn đề nghị / Giấy phép vỉa hè cũ (Địa điểm)."},
    {"name": "DeNghi_TuyenDuong", "desc": "Tên tuyến đường (chỉ tên đường, ví dụ 'Đường Nguyễn Chí Thanh'). "
        "Đơn đề nghị / Giấy phép cũ."},
    {"name": "DeNghi_DiaBan", "desc": "Địa bàn (phường + thành phố), ví dụ 'Phường Hải Châu, thành phố Đà "
        "Nẵng'. Đơn đề nghị / Giấy phép cũ."},
    {"name": "DeNghi_TuNgay", "desc": "Ngày bắt đầu sử dụng, dd/mm/yyyy — Đơn đề nghị 'Từ ngày …'."},
    {"name": "DeNghi_DenNgay", "desc": "Ngày kết thúc sử dụng, dd/mm/yyyy — Đơn đề nghị 'đến hết ngày …'."},
    {"name": "LienHe_DiaChi", "desc": "Địa chỉ liên hệ (thường là địa chỉ kinh doanh/trụ sở), ví dụ '56 "
        "Nguyễn Chí Thanh, phường Hải Châu, TP Đà Nẵng'. Giấy cam kết (Địa chỉ kinh doanh) / GCN ĐKDN (trụ sở)."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _d in ("NguoiNop_NgaySinh", "NguoiNop_NgayCap", "Don_NgayLap", "DeNghi_TuNgay", "DeNghi_DenNgay"):
    COMPACT_COMP_BY_NAME[_d] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["DoanhNghiep_DiaChi"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Field-key CHUẨN từ HTML thật (flat, không nested panel).
UI_COMP_BY_NAME = {
    # Phần I — người nộp.
    "data[chonDoiTuong]": "dom-select",       # Cá nhân/Tổ chức.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[phoneNumber]": "dom-input",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    # Phần I-b — doanh nghiệp (khi Tổ chức).
    "data[organization]": "dom-input",
    "data[taxCode]": "dom-input",
    "data[organizationPhoneNumber]": "dom-input",
    "data[nation1]": "dom-select",
    "data[province1]": "dom-select",
    "data[district1]": "dom-select",
    "data[address1]": "dom-input",
    # Phần II — đơn đề nghị (header).
    "data[tenDonVi]": "dom-input",
    "data[tenCoQuanDeNghi]": "dom-input",
    "data[kinhGui]": "dom-input",
    "data[TinhThanh]": "dom-select",          # Nơi lập đơn (Tỉnh/TP).
    "data[ngayThangNam]": "dom-date",         # Ngày lập đơn.
    # Phần III — thông tin đề nghị.
    "data[tenSuKien]": "dom-input",
    "data[tenDoanDuong]": "dom-input",
    "data[tenTuyenDuong]": "dom-input",
    "data[diaBan]": "dom-input",
    "data[tuNgay]": "dom-date",
    "data[denNgay]": "dom-date",
    # Phần IV — liên hệ.
    "data[diaChiLienHe]": "dom-input",
    "data[soDienThoai]": "dom-input",
}
