"""Compact schema cho "Cấp Giấy chứng nhận đủ điều kiện ATTP đối với cơ sở sản xuất, kinh doanh thực
phẩm" — cổng DVC Bộ Công Thương dichvucong-tthc.moit.gov.vn (Form.io). CÙNG cổng #42 "Cấp lại"
(cap_lai_an_toan_thuc_pham) — tái dùng helper mapper, engine attach attp-row. KHÁC: đây là bản CẤP LẦN
ĐẦU, form kê khai cơ sở SXKD (Mẫu 01a) chứ không phải đơn cấp lại.

Nguồn: CCCD người nộp + GCN đăng ký hộ kinh doanh/DN + Đơn 01a + Bản thuyết minh 02a/02b + DS tập huấn +
Giấy khám sức khỏe.

⚠ ĐẶC THÙ: field-key data[...] TRÙNG giữa Phần I (tài khoản nộp) và Phần IV (cơ sở SXKD) — 3 key xuất
hiện 2× trong DOM: province, address, phoneNumber. Phân biệt bằng OCCURRENCE (0 = Phần I, 1 = Phần IV)
trong mapper. Phường/xã tài khoản = data[district]; phường/xã cơ sở = data[village] (KEY KHÁC, không trùng).
"""

FIELDS: list[dict] = [
    # --- Người nộp hồ sơ (Phần I: tài khoản; nếu nộp thay → CCCD người nộp thay) ---
    {"name": "Applicant_HoTen", "desc": "Họ tên NGƯỜI NỘP HỒ SƠ (chủ tài khoản đăng nhập). CCCD / đại diện "
        "cơ sở nếu chính chủ. IN HOA."},
    {"name": "Applicant_SoDinhDanh", "desc": "Số CCCD/CMND/định danh NGƯỜI NỘP. Chỉ chữ số, ưu tiên 12 số."},
    {"name": "Applicant_NgaySinh", "desc": "Ngày sinh người nộp, dd/mm/yyyy — CCCD."},
    {"name": "Applicant_NgayCap", "desc": "Ngày cấp CCCD người nộp, dd/mm/yyyy."},
    {"name": "Applicant_NoiCap", "desc": 'Nơi cấp CCCD người nộp. CCCD gắn chip: "Cục Cảnh sát quản lý hành '
        'chính về trật tự xã hội"; thẻ căn cước mới: "Bộ Công an".'},
    {"name": "Applicant_NoiCuTru", "desc": "Nơi thường trú/cư trú NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi,"
        "fullText}. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường (KHÔNG kèm phường/xã/tỉnh)."},
    {"name": "Applicant_DienThoai", "desc": "Số điện thoại người nộp. Chỉ chữ số."},
    {"name": "Applicant_Email", "desc": "Email người nộp nếu có; thường không có → bỏ."},
    {"name": "Applicant_MaSoThue", "desc": "Mã định danh tổ chức/MST của TÀI KHOẢN nộp (nếu đăng nhập bằng "
        "tài khoản tổ chức). Với hộ kinh doanh, mã số HKD = số định danh chủ hộ. Chỉ chữ số."},

    # --- Giấy ủy quyền (khi nộp thay chủ cơ sở) ---
    {"name": "UyQuyen_BenUyQuyen_HoTen", "desc": "Họ tên bên ủy quyền (chủ cơ sở) trong Giấy ủy quyền."},
    {"name": "UyQuyen_BenUyQuyen_SoDinhDanh", "desc": "Số CCCD/CMND bên ủy quyền."},
    {"name": "UyQuyen_BenDuocUyQuyen_HoTen", "desc": "Họ tên bên được ủy quyền (người đi nộp thay)."},
    {"name": "UyQuyen_BenDuocUyQuyen_SoDinhDanh", "desc": "Số CCCD/CMND bên được ủy quyền."},
    {"name": "UyQuyen_BenDuocUyQuyen_NgayCap", "desc": "Ngày cấp giấy tờ bên được ủy quyền, dd/mm/yyyy."},
    {"name": "UyQuyen_BenDuocUyQuyen_NoiCap", "desc": "Nơi cấp giấy tờ bên được ủy quyền."},

    # --- Chủ hồ sơ = CƠ SỞ sản xuất, kinh doanh (Phần II & IV) ---
    {"name": "CoSo_Ten", "desc": "TÊN CƠ SỞ sản xuất, kinh doanh (pháp nhân) — GCN ĐKKD 'Tên hộ kinh doanh' "
        "/ Đơn 01a 'Cơ sở sản xuất, kinh doanh' / DS tập huấn 'Tên cơ sở'. Vd 'HỘ KINH DOANH SALMON MOON'. "
        "KHÁC tên người ở CCCD."},
    {"name": "CoSo_MaSo", "desc": "Mã số hộ kinh doanh / mã số doanh nghiệp / MST của cơ sở — GCN ĐKKD. "
        "Chỉ chữ số. (HKD: mã số HKD trùng số định danh chủ hộ.)"},
    {"name": "CoSo_LoaiChuThe", "desc": '"Tổ chức" nếu cơ sở là hộ kinh doanh/công ty/HTX/doanh nghiệp; '
        '"Cá nhân" nếu là một cá nhân đứng tên. Đa số là hộ kinh doanh → "Tổ chức".'},
    {"name": "CoSo_NguoiDaiDien", "desc": "Họ tên chủ cơ sở / người đại diện — GCN ĐKKD mục 6 (chủ hộ KD) / "
        "Đơn 01a (đại diện cơ sở, ký tên). Dùng khi cơ sở là cá nhân/chủ hộ."},
    {"name": "CoSo_SoDinhDanhChuCoSo", "desc": "Số định danh/CCCD của chủ cơ sở/chủ hộ — GCN ĐKKD mục 6. "
        "Chỉ chữ số."},
    {"name": "CoSo_DienThoai", "desc": "Điện thoại cơ sở — GCN ĐKKD / Đơn 01a / TM 02a. Chỉ chữ số."},
    {"name": "CoSo_DiaChi", "desc": "ĐỊA CHỈ TRỤ SỞ/địa điểm CƠ SỞ SXKD, object {quocGia,tinh,xa,diaChi,"
        "fullText}. GCN ĐKKD 'Trụ sở hộ kinh doanh' / Đơn 01a 'Địa điểm tại' / TM 02a 'Địa chỉ cơ sở sản "
        "xuất'. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường. KHÁC nơi thường trú cá nhân."},
    {"name": "CoSo_NganhNghe", "desc": "Ngành nghề/mặt hàng sản xuất, kinh doanh (TÊN SẢN PHẨM, không phải "
        "mã ngành) — Đơn 01a 'Ngành nghề (tên sản phẩm)' / GCN ĐKKD mục 3 tên ngành / TM 02a 'Mặt hàng sản "
        "xuất'. Vd 'Sản xuất các loại bánh mặn, ngọt'."},

    # --- Đơn đề nghị Mẫu 01a (Phần III & V) ---
    {"name": "Don_DiaDanh", "desc": "Nơi lập đơn (chỉ ĐỊA DANH, không ngày) — dòng '…, ngày … tháng … năm' "
        "trên Đơn 01a. Vd 'Hải Châu'."},
    {"name": "Don_NgayLap", "desc": "Ngày lập đơn, dd/mm/yyyy — dòng địa danh/ký trên Đơn 01a."},
    {"name": "Don_KinhGui", "desc": "Cơ quan kính gửi trên Đơn 01a. Vd 'UBND Phường Hải Châu'."},
    {"name": "Don_LoaiHinh", "desc": 'Loại hình cơ sở người viết đơn TÍCH (× trên Đơn 01a): "san_xuat" '
        '(Cơ sở sản xuất) / "kinh_doanh" (Cơ sở kinh doanh) / "vua_sx_vua_kd" (Cơ sở vừa sản xuất vừa kinh '
        'doanh) / "chuoi" (Chuỗi cơ sở kinh doanh thực phẩm). Đọc đúng ô đã đánh dấu.'},
    {"name": "Don_TenChuoi", "desc": "Tên cơ sở của chuỗi (chỉ khi loại hình = chuỗi) — Đơn 01a dòng '(tên "
        "cơ sở)' dưới 4 ô vuông. Bỏ nếu không phải chuỗi."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Applicant_NgaySinh",
    "Applicant_NgayCap",
    "UyQuyen_BenDuocUyQuyen_NgayCap",
    "Don_NgayLap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Applicant_NoiCuTru", "CoSo_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Field-key CHUẨN từ HTML thật.
# province/address/phoneNumber TRÙNG Phần I/IV → mapper gắn occurrence (0/1). UI_COMP_BY_NAME chỉ khai comp.
UI_COMP_BY_NAME = {
    # ----- Phần I: TÀI KHOẢN NỘP HỒ SƠ (occurrence 0 cho key trùng) -----
    "data[fullname]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",       # phường/xã TÀI KHOẢN (key riêng).
    "data[taxCode]": "dom-input",
    "data[email]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[birthday]": "dom-date",
    "data[address]": "dom-input",
    "data[noidungyeucaugiaiquyet]": "dom-input",
    # ----- Phần II: CHỦ HỒ SƠ (cơ sở) -----
    "data[isOwnerDossier]": "dom-checkbox",
    "data[ownerFullname]": "dom-input",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownertaxCode]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerAddress]": "dom-input",
    # ----- Phần III: ĐƠN ĐỀ NGHỊ (header) -----
    "data[noiLapDon]": "dom-input",
    "data[ngayLap]": "dom-date",
    "data[KinhGui]": "dom-input",
    # ----- Phần IV: CƠ SỞ SXKD (occurrence 1 cho key trùng) -----
    "data[organization]": "dom-input",
    "data[village]": "dom-select",        # phường/xã CƠ SỞ (key riêng, KHÁC district).
    "data[fax]": "dom-input",
    "data[nganhNghe]": "dom-input",
    # ----- Phần V: LOẠI HÌNH CƠ SỞ (4 checkbox độc lập) -----
    "data[CoSoSanXuatChon]": "dom-checkbox",
    "data[CoSoKinhDoanh]": "dom-checkbox",
    "data[CoSoKinhDoanh1]": "dom-checkbox",   # ⚠ = VỪA sản xuất VỪA kinh doanh (đặt tên nhầm trên form).
    "data[ChuoiCoSo]": "dom-checkbox",
    "data[tencoso11]": "dom-input",
    "data[DinhKem]": "dom-input",             # textarea liệt kê hồ sơ gửi kèm.
}
