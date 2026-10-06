"""Compact schema cho "Đăng ký, cấp GCN cho người nhận chuyển nhượng QSDĐ, quyền sở hữu nhà ở, công trình xây
dựng trong dự án bất động sản" — cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn (Form.io). UI field-key theo
file "Mapping_DKCapGCN_nhan_chuyen_nhuong_DuAnBDS_DaNang.xlsx" (Phần I, STT 1–20).

Phần I là 1 panel "Thông tin chung" chứa HAI vai:
- ChuHoSo_*  : CHỦ HỒ SƠ = BÊN NHẬN chuyển nhượng (người mua nhà/đất trong dự án); vợ chồng cùng nhận →
               người đứng tên ĐẦU TIÊN (form chỉ có một ô chủ hồ sơ).
- NguoiNop_* : NGƯỜI NỘP HỒ SƠ (tự nộp = chủ hồ sơ; ủy quyền = bên được ủy quyền kèm CCCD).
Bên CHUYỂN NHƯỢNG (chủ đầu tư dự án) KHÔNG lên form; ChuDauTu_Ten chỉ dùng để mapper chặn nhầm vai.
Ô "Nội dung yêu cầu giải quyết" cổng điền sẵn — mapping yêu cầu giữ nguyên nên schema không có field này.
"""

# --- Chủ hồ sơ (bên nhận chuyển nhượng) ---
FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Tổ chức" nếu BÊN NHẬN chuyển nhượng là công ty/doanh nghiệp/HTX/'
        'cơ quan; "Cá nhân" nếu là người (kể cả vợ chồng cùng nhận). Chủ hồ sơ là BÊN NHẬN / BÊN MUA, KHÔNG '
        'phải chủ đầu tư dự án (bên bán).'},
    {"name": "ChuHoSo_HoTen", "desc": "Tên CHỦ HỒ SƠ = BÊN NHẬN chuyển nhượng / BÊN MUA. CÁ NHÂN: họ và tên "
        "IN HOA, vợ chồng cùng nhận ('Ông … – Bà …', 'Cùng vợ là') → CHỈ người đứng tên ĐẦU TIÊN. TỔ CHỨC: tên "
        "đầy đủ. Lấy ở CCCD, Đơn Mẫu 18 do BÊN NHẬN ký (mục 1a 'Tên'), 'Bên mua' trên Hợp đồng mua bán. KHÔNG "
        "lấy tên chủ đầu tư dự án."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số định danh CHỦ HỒ SƠ (cùng người với ChuHoSo_HoTen). CÁ NHÂN: "
        "số CCCD (CCCD / Đơn Mẫu 18 mục 1b / Hợp đồng bên mua). TỔ CHỨC: mã số doanh nghiệp. CHỈ chữ số. "
        "KHÔNG lấy mã số doanh nghiệp của chủ đầu tư dự án."},
    {"name": "ChuHoSo_DiaChi", "desc": "Địa chỉ THƯỜNG TRÚ HIỆN HÀNH của CHỦ HỒ SƠ, object {quocGia,tinh,xa,"
        "diaChi}. Ưu tiên CCCD 'Nơi thường trú' → Giấy xác nhận cư trú CT07 'Nơi thường trú' → Đơn Mẫu 18 mục "
        "1c. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/thôn/tổ (KHÔNG kèm phường/xã/tỉnh)."},
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại CHỦ HỒ SƠ (Đơn Mẫu 18 mục 1d / Hợp đồng bên mua). "
        "Chép ĐÚNG như giấy tờ, kể cả đầu số quốc tế (00…, +…). Không có thì bỏ."},
    {"name": "ChuHoSo_Email", "desc": "Email CHỦ HỒ SƠ (Đơn Mẫu 18 mục 1d 'Hộp thư điện tử' / Hợp đồng bên "
        "mua). KHÔNG lấy email của chủ đầu tư. Không có thì bỏ."},
    {"name": "ChuDauTu_Ten", "desc": "Tên CHỦ ĐẦU TƯ dự án = BÊN BÁN / bên chuyển nhượng (công ty bất động "
        "sản, đứng tên Giấy chứng nhận đã cấp cho chủ đầu tư). Chỉ dùng đối chiếu, không lên form."},
]

# --- Người nộp hồ sơ (người thao tác nộp; có thể được ủy quyền) ---
FIELDS += [
    {"name": "NguoiNop_LoaiDoiTuong", "desc": '"Tổ chức" nếu người nộp là tổ chức; "Cá nhân" nếu là một '
        'người. Đa số người nộp là CÁ NHÂN (kể cả khi được tổ chức ủy quyền).'},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP HỒ SƠ (một CÁ NHÂN). CHỈ điền khi: có Hợp đồng/"
        "Giấy ủy quyền → BÊN ĐƯỢC ỦY QUYỀN (có CCCD); HOẶC chủ hồ sơ CÁ NHÂN tự nộp → = ChuHoSo_HoTen. Chủ hồ "
        "sơ TỔ CHỨC không có ủy quyền kèm CCCD → ĐỂ TRỐNG. IN HOA."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh NGƯỜI NỘP, dd/mm/yyyy — CCCD / Giấy xác nhận cư trú CT07 "
        "/ Giấy chứng nhận kết hôn / tờ khai thuế của CHÍNH người đó. Chỉ có năm sinh thì bỏ."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính NGƯỜI NỘP: "Nam"/"Nữ" — CCCD / CT07 của chính người '
        'nộp. Không có thì bỏ (mapper tự suy từ số định danh).'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh cá nhân của CHÍNH NGƯỜI NỘP (cùng người với "
        "NguoiNop_HoTen). Chỉ chữ số, ưu tiên 12 số. TUYỆT ĐỐI KHÔNG lấy CCCD của vợ/chồng, người đại diện "
        "chủ đầu tư hay người khác."},
    {"name": "NguoiNop_MaSoThue", "desc": "Mã số thuế / mã định danh tổ chức NGƯỜI NỘP (CHỈ khi người nộp "
        "là TỔ CHỨC). Chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CHÍNH CCCD của người nộp, dd/mm/yyyy — CCCD mặt sau / Hợp "
        "đồng mua bán ('… cấp ngày … tại …') / tờ khai thuế SDĐPNN phần II ô [31]. KHÔNG lấy ngày cấp giấy "
        "khác. Ô [08] phần I tờ khai thuế hay ghi nhầm số CCCD → bỏ qua ô đó."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp CCCD của NGƯỜI NỘP, chép ĐÚNG như giấy tờ ghi (CCCD / Hợp "
        "đồng mua bán '… tại …' / tờ khai thuế SDĐPNN ô [32]). Giấy tờ không ghi nơi cấp → BỎ TRỐNG, không "
        "suy đoán."},
    {"name": "NguoiNop_DiaChi", "desc": "Địa chỉ thường trú NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi} — CCCD "
        "/ CT07 / Hợp đồng ủy quyền. diaChi KHÔNG kèm phường/xã/tỉnh."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại NGƯỜI NỘP, chép đúng như giấy tờ. Thường không có."},
    {"name": "NguoiNop_Email", "desc": "Email NGƯỜI NỘP nếu giấy tờ có; thường không có → bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["ChuHoSo_DiaChi"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Field-key theo cột H của file mapping.
UI_COMP_BY_NAME = {
    "data[ownerFullname]": "dom-input",       # STT 1 — Họ và tên chủ hồ sơ.
    "data[isOwnerDossier]": "dom-checkbox",   # STT 2 — Chủ hồ sơ cũng là người nộp.
    "data[organization]": "dom-input",        # STT 3 — Tên cơ quan/doanh nghiệp (chỉ khi tổ chức).
    "data[fullname]": "dom-input",            # STT 4
    "data[birthday]": "dom-date",             # STT 5 — cổng điền sẵn ngày sinh tài khoản → phải ghi đè.
    "data[gender]": "dom-select",             # STT 6
    "data[email]": "dom-input",               # STT 7
    "data[phoneNumber]": "dom-input",         # STT 8
    "data[identityNumber]": "dom-input",      # STT 9
    "data[identityDate]": "dom-date",         # STT 10
    "data[identityAgency]": "dom-select",     # STT 11
    "data[taxCode]": "dom-input",             # STT 14 — Mã định danh tổ chức (chỉ khi tổ chức).
    "data[chonDoiTuong]": "dom-select",       # STT 15 — Cá nhân/Tổ chức.
    "data[province]": "dom-select",           # STT 18 — cổng mặc định "Thành phố Đà Nẵng" → phải đổi.
    "data[district]": "dom-select",           # STT 19
    "data[address]": "dom-input",             # STT 20
}
