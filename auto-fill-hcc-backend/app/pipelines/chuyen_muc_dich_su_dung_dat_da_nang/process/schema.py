"""Compact schema cho "Đăng ký biến động chuyển mục đích sử dụng đất không phải xin phép" — cổng DVC TP
Đà Nẵng dichvucong.danang.gov.vn (Form.io). CÙNG form/contact-block với #75 (dang_ky_bien_dong_dat_dai_da_nang)
— UI field-key data[...] Y HỆT (1 panel thongTinChung).

Phần I là 1 panel "thongTinChung" chứa HAI vai:
- ChuHoSo_*  : CHỦ HỒ SƠ = CHỦ ĐẤT/người sử dụng đất ĐỀ NGHỊ chuyển mục đích sử dụng đất (đứng tên GCN /
               Đơn đăng ký biến động). Có thể CÁ NHÂN / TỔ CHỨC.
- NguoiNop_* : NGƯỜI NỘP HỒ SƠ = người trực tiếp thao tác nộp (có thể là người được ỦY QUYỀN). Khi tự nộp
               thì NguoiNop = ChuHoSo.
KHÁC #75: KHÔNG có bên chuyển nhượng/bên nhận — chỉ MỘT chủ đất tự chuyển mục đích (không phải xin phép).
"""

# --- Chủ hồ sơ (subject = chủ đất đề nghị chuyển mục đích) ---
FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Tổ chức" nếu chủ hồ sơ là công ty/doanh nghiệp/HTX/cơ quan '
        '(tên có "Công ty", "Doanh nghiệp", "HTX", "Hợp tác xã"); "Cá nhân" nếu là một người. Chủ hồ sơ là '
        'CHỦ ĐẤT đề nghị chuyển mục đích sử dụng đất (người đứng tên Giấy chứng nhận / Đơn đăng ký biến động).'},
    {"name": "ChuHoSo_HoTen", "desc": "Tên CHỦ HỒ SƠ — nếu CÁ NHÂN: họ và tên (IN HOA); nếu TỔ CHỨC: tên "
        "đầy đủ tổ chức. Lấy ở Đơn đăng ký biến động (người sử dụng đất), Giấy chứng nhận QSDĐ (người đứng "
        "tên), hoặc Giấy chứng nhận ĐKKD."},
]

# --- Người nộp hồ sơ (người thao tác nộp; có thể được ủy quyền) ---
FIELDS += [
    {"name": "NguoiNop_LoaiDoiTuong", "desc": '"Tổ chức" nếu người nộp là tổ chức; "Cá nhân" nếu là một '
        'người. Đa số người nộp là CÁ NHÂN (kể cả khi được tổ chức ủy quyền).'},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP HỒ SƠ. Nếu có Hợp đồng ủy quyền: lấy BÊN ĐƯỢC "
        "ỦY QUYỀN (Bên B). Nếu KHÔNG có ủy quyền (tự nộp): người nộp CHÍNH LÀ chủ hồ sơ. IN HOA như CCCD."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh NGƯỜI NỘP (cá nhân), dd/mm/yyyy — CCCD / Hợp đồng ủy quyền."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính NGƯỜI NỘP: "Nam"/"Nữ" — CCCD, hoặc suy từ danh xưng '
        'Ông/Bà trong Hợp đồng ủy quyền.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND/định danh cá nhân NGƯỜI NỘP. Đọc CCCD hoặc Hợp "
        "đồng ủy quyền (Bên B 'Căn cước công dân số'). Chỉ chữ số. Ưu tiên 12 chữ số."},
    {"name": "NguoiNop_MaSoThue", "desc": "Mã số thuế / mã định danh tổ chức NGƯỜI NỘP (CHỈ khi người nộp "
        "là TỔ CHỨC). Chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD NGƯỜI NỘP, dd/mm/yyyy — mặt sau CCCD / Hợp đồng ủy quyền."},
    {"name": "NguoiNop_NoiCap", "desc": 'Cơ quan cấp CCCD NGƯỜI NỘP — GHI ĐẦY ĐỦ, KHÔNG viết tắt. Giấy tờ '
        'hay ghi tắt "CCSQLHC TTXH" / "CCSVLHC TTXH" / "CCS QLHC về TTXH" / "Cục CSQLHC" → PHẢI ghi thành '
        '"Cục Cảnh sát quản lý hành chính về trật tự xã hội". Thẻ căn cước mới ghi "Bộ Công an".'},
    {"name": "NguoiNop_DiaChi", "desc": "Địa chỉ THƯỜNG TRÚ của CHÍNH NGƯỜI NỘP, object {quocGia,tinh,xa,"
        "diaChi}. CHỈ lấy ở CCCD người nộp (Nơi thường trú) hoặc Hợp đồng ủy quyền (địa chỉ Bên được ủy "
        "quyền). ⚠ Giấy giới thiệu THƯỜNG KHÔNG có địa chỉ thường trú → nếu không có, BỎ TRỐNG toàn bộ "
        "(đừng đoán). TUYỆT ĐỐI KHÔNG lấy địa chỉ thửa đất, trụ sở tổ chức/ngân hàng, hay tỉnh của thửa đất "
        "làm địa chỉ người nộp. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/thôn."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại NGƯỜI NỘP. Chỉ chữ số. Thường không có trên giấy tờ."},
    {"name": "NguoiNop_Email", "desc": "Email NGƯỜI NỘP nếu giấy tờ có; thường không có → bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_DiaChi"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Y HỆT #75 (1 panel thongTinChung).
UI_COMP_BY_NAME = {
    # Chủ hồ sơ.
    "data[ownerFullname]": "dom-input",
    "data[isOwnerDossier]": "dom-checkbox",
    "data[organization]": "dom-input",
    # Người nộp hồ sơ.
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[note]": "dom-input",
    "data[noidungyeucaugiaiquyet]": "dom-input",
    "data[taxCode]": "dom-input",
    "data[chonDoiTuong]": "dom-select",
    "data[hinhThucNop]": "dom-select",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
}
