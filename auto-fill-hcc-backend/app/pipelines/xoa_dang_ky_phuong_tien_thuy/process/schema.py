"""Compact schema cho "Xóa đăng ký phương tiện thủy nội địa" (cổng DVC Bộ Xây dựng dvc.moc.gov.vn —
Form.io, engine fillFormStandard dom-*). CÙNG cổng/engine với #63 liên vận & quy-hoach.

Nguồn giấy tờ: Đơn đề nghị xóa đăng ký phương tiện thủy nội địa (Mẫu số 3/10, file 'Mauon.docx' trên
eform) + CCCD (nếu chủ phương tiện là cá nhân).

MỘT subject = CHỦ PHƯƠNG TIỆN (đối tượng đề nghị xóa đăng ký), có thể CÁ NHÂN / TỔ CHỨC. Điền vào Block 1
của cổng (mapper toggle Select #1). Mẫu là TỔ CHỨC (Cty CP DVHH An Phát).
- ChuPhuongTien_*   : nhân thân/tổ chức chủ phương tiện. Loại đối tượng route TẤT ĐỊNH ở mapper.
- PhuongTien_*      : đặc điểm phương tiện (tên, số ĐK, số GCN, lý do xóa).
- ToKhai_*          : nơi lập đơn, ngày ký, người ký.
"""

# --- Chủ phương tiện (subject CHÍNH đề nghị xóa đăng ký) ---
FIELDS: list[dict] = [
    {"name": "ChuPhuongTien_LoaiDoiTuong", "desc": '"Tổ chức" nếu chủ phương tiện là công ty/doanh '
        'nghiệp/HTX/cơ quan (tên có "Công ty", "Doanh nghiệp", "HTX", "Hợp tác xã", hoặc có Mã định danh '
        'tổ chức); "Cá nhân" nếu là một người. Đọc Đơn mục "Tổ chức, cá nhân đăng ký".'},
    {"name": "ChuPhuongTien_HoTen", "desc": "Tên chủ phương tiện — nếu CÁ NHÂN: họ và tên (IN HOA như "
        "CCCD); nếu TỔ CHỨC: tên đầy đủ của tổ chức. Đọc Đơn mục 'Tổ chức, cá nhân đăng ký' hoặc CCCD."},
    {"name": "ChuPhuongTien_MaDinhDanhToChuc", "desc": "Mã định danh tổ chức / MST (CHỈ khi chủ là TỔ "
        "CHỨC). Đơn mục 'Mã định danh tổ chức (nếu chủ phương tiện là tổ chức)'. Chỉ chữ số."},
    {"name": "ChuPhuongTien_SoDinhDanh", "desc": "Số định danh cá nhân/CCCD/căn cước/hộ chiếu của chủ "
        "phương tiện (CHỈ khi chủ là CÁ NHÂN). Đọc CCCD hoặc Đơn mục 'Số định danh cá nhân...'. Chỉ chữ số."},
    {"name": "ChuPhuongTien_NgaySinh", "desc": "Ngày sinh chủ phương tiện (CHỈ khi CÁ NHÂN, có CCCD), "
        "dd/mm/yyyy — từ CCCD."},
    {"name": "ChuPhuongTien_GioiTinh", "desc": 'Giới tính chủ phương tiện (CHỈ khi CÁ NHÂN): "Nam"/"Nữ" — CCCD.'},
    {"name": "ChuPhuongTien_NgayCap", "desc": "Ngày cấp CCCD chủ phương tiện (CHỈ khi CÁ NHÂN), dd/mm/yyyy."},
    {"name": "ChuPhuongTien_NguoiDaiDien", "desc": "Người/đơn vị đại diện cho các đồng sở hữu (CHỈ khi "
        "phương tiện có nhiều đồng sở hữu). Đơn mục 'đại diện cho các đồng sở hữu'. Thường bỏ trống."},
    {"name": "ChuPhuongTien_TruSo", "desc": "TRỤ SỞ CHÍNH (tổ chức) hoặc NƠI THƯỜNG TRÚ (cá nhân) của chủ "
        "phương tiện, object {quocGia,tinh,xa,diaChi}. Đọc Đơn mục 'Trụ sở chính (1)' / CCCD 'Nơi thường "
        "trú'. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/thôn/xóm (KHÔNG kèm phường/xã/tỉnh)."},
    {"name": "ChuPhuongTien_DienThoai", "desc": "Số điện thoại chủ phương tiện. Đơn mục 'Điện thoại'. Chỉ chữ số."},
    {"name": "ChuPhuongTien_Email", "desc": "Email chủ phương tiện. Đơn mục 'Email'. Chép nguyên văn."},
]

# --- Đặc điểm phương tiện (Phần III) ---
FIELDS += [
    {"name": "PhuongTien_Ten", "desc": "Tên phương tiện. Đơn mục 'Tên phương tiện' (vd 'AN PHÁT 02')."},
    {"name": "PhuongTien_SoDangKy", "desc": "Số đăng ký phương tiện. Đơn mục 'Số đăng ký' (vd 'Qna-1403'). "
        "Giữ nguyên như trên giấy tờ."},
    {"name": "PhuongTien_SoGiayChungNhan", "desc": "Số giấy chứng nhận đăng ký phương tiện. Đơn mục 'Số "
        "giấy chứng nhận đăng ký' (vd '43/ĐK')."},
    {"name": "PhuongTien_LyDoXoa", "desc": "Lý do xóa đăng ký. Đơn mục 'Lý do xóa đăng ký' (vd 'đã bán "
        "phương tiện', 'phương tiện hư hỏng không còn sử dụng'). Chép nguyên văn."},
]

# --- Nơi lập đơn (Phần IV) ---
FIELDS += [
    {"name": "ToKhai_DiaDanh", "desc": "Địa danh nơi lập đơn — dòng ký '……, ngày … tháng … năm …' cuối "
        "Đơn (tên tỉnh/thành phố, vd 'Đà Nẵng'). Chỉ lấy tên địa danh."},
    {"name": "ToKhai_NgayLap", "desc": "Ngày lập/ký đơn — dòng ký cuối Đơn, dd/mm/yyyy."},
    {"name": "ToKhai_NguoiLamDon", "desc": "Họ tên người ký đơn (mục 'CHỦ PHƯƠNG TIỆN — Ký và ghi rõ họ "
        "tên'). Nếu tổ chức là người đại diện ký (vd 'Hoàng Trí Nhân'). Bỏ chức danh, chỉ lấy họ tên."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["ChuPhuongTien_TruSo"] = "x-select-area"
COMPACT_COMP_BY_NAME["ChuPhuongTien_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["ChuPhuongTien_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["ToKhai_NgayLap"] = "x-date"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên field-key lấy CHUẨN từ HTML thật.
UI_COMP_BY_NAME = {
    # ----- Phần I: NGƯỜI NỘP HỒ SƠ (panel thongTinChung #1) -----
    "data[chonDoiTuong]": "dom-select",     # occ0 = "Cá nhân" (người nộp) / occ1 = loại chủ phương tiện.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[tenHoSo]": "dom-input",            # nhãn "Ghi chú".
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[phoneNumber]": "dom-input",        # occ0 = người nộp / occ1 = chủ phương tiện (cá nhân).
    "data[AuthorityApplicantPhoneNumber]": "dom-input",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",          # occ0 người nộp / occ1 chủ phương tiện (cá nhân).
    "data[district]": "dom-select",
    "data[address]": "dom-input",

    # ----- Phần II: CHỦ PHƯƠNG TIỆN — nhánh CÁ NHÂN (panel thongTinChung #2) -----
    "data[fullName]": "dom-input",           # KHÁC data[fullname] Phần I (chữ N hoa).
    "data[nguoiDaiDien]": "dom-input",
    "data[canCuocCongDan]": "dom-input",
    "data[email2]": "dom-input",
    "data[chuPhuongTien2]": "dom-input",     # "Hiện đang là chủ sở hữu phương tiện" = tên phương tiện.
    "data[soDangKy3]": "dom-input",

    # ----- Phần II: CHỦ PHƯƠNG TIỆN — nhánh TỔ CHỨC (panel thongTinDoanhNghiep, hiện khi chọn Tổ chức) -----
    "data[organization]": "dom-input",       # Tên Tổ chức đăng ký.
    "data[maDinhDanh]": "dom-input",         # Mã định danh tổ chức.
    "data[dongSoHuu]": "dom-input",          # Đại diện cho các đồng sở hữu.
    "data[province1]": "dom-select",
    "data[district1]": "dom-select",
    "data[address1]": "dom-input",
    "data[phoneNumber1]": "dom-input",
    "data[email1]": "dom-input",

    # ----- Phần III: ĐẶC ĐIỂM PHƯƠNG TIỆN -----
    "data[tenPhuongTien]": "dom-input",
    "data[soDangKy1]": "dom-input",
    "data[SoGiayChungNhan]": "dom-input",
    "data[lyDoCapLai]": "dom-input",         # textarea "Lý do xóa đăng ký".

    # ----- Phần IV: NƠI LẬP ĐƠN -----
    "data[TinTTTe]": "dom-select",           # địa danh (mặc định Thành phố Đà Nẵng).
    "data[TDTTK]": "dom-date",
    "data[nguoiLamDon]": "dom-input",
}
