"""Compact schema cho "Đăng ký biến động QSDĐ (chuyển đổi/chuyển nhượng/thừa kế/tặng cho/góp vốn/cho
thuê...)" — cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn (Form.io). CÙNG cổng/engine với #95
(dang_ky_bien_phap_bao_dam_qsdd).

Phần I là 1 panel "thongTinChung" chứa HAI vai:
- ChuHoSo_*  : CHỦ HỒ SƠ = người sử dụng đất/chủ tài sản đăng ký biến động (bên nhận chuyển nhượng/thừa
               kế/tặng cho...). Có thể CÁ NHÂN / TỔ CHỨC. Mẫu = Công ty CP Đầu tư KCN Hòa Cẩm (tổ chức).
- NguoiNop_* : NGƯỜI NỘP HỒ SƠ = người trực tiếp thao tác nộp (có thể là người được ỦY QUYỀN). Mẫu =
               Ông Võ Văn Cảnh (cá nhân, ủy quyền). Khi tự nộp thì NguoiNop = ChuHoSo.
Bên chuyển nhượng (bên bán) KHÔNG lên form (chỉ ở giấy đính kèm).
"""

# --- Chủ hồ sơ (subject = chủ đất/tài sản đăng ký biến động) ---
FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Tổ chức" nếu chủ hồ sơ là công ty/doanh nghiệp/HTX/cơ quan '
        '(tên có "Công ty", "Doanh nghiệp", "HTX", "Hợp tác xã"); "Cá nhân" nếu là một người. Chủ hồ sơ là '
        'BÊN NHẬN chuyển nhượng/thừa kế/tặng cho/góp vốn (bên B) trên Hợp đồng, hoặc chủ đứng tên đăng ký.'},
    {"name": "ChuHoSo_HoTen", "desc": "Tên CHỦ HỒ SƠ — nếu CÁ NHÂN: họ và tên (IN HOA); nếu TỔ CHỨC: tên "
        "đầy đủ tổ chức. Lấy ở Hợp đồng chuyển nhượng/tặng cho (bên NHẬN), Giấy chứng nhận ĐKKD, hoặc Đơn "
        "Mẫu 18 (người đăng ký biến động)."},
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
    {"name": "NguoiNop_NoiCap", "desc": 'Cơ quan cấp CCCD NGƯỜI NỘP. "Cục Cảnh sát quản lý hành chính về '
        'trật tự xã hội"; thẻ căn cước mới "Bộ Công an".'},
    {"name": "NguoiNop_DiaChi", "desc": "Địa chỉ thường trú NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. Lấy "
        "ở CCCD (Nơi thường trú) / Hợp đồng ủy quyền. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/"
        "đường/thôn (KHÔNG kèm phường/xã/tỉnh)."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại NGƯỜI NỘP. Chỉ chữ số. Thường không có trên giấy tờ."},
    {"name": "NguoiNop_Email", "desc": "Email NGƯỜI NỘP nếu giấy tờ có; thường không có → bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_DiaChi"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên field-key lấy CHUẨN từ HTML thật. 1 panel thongTinChung.
UI_COMP_BY_NAME = {
    # Chủ hồ sơ.
    "data[ownerFullname]": "dom-input",       # Họ tên chủ hồ sơ (person hoặc tên tổ chức).
    "data[isOwnerDossier]": "dom-checkbox",   # "Chủ hồ sơ cũng là người nộp" — bỏ tích khi ủy quyền.
    "data[organization]": "dom-input",        # Tên cơ quan/tổ chức (khi chủ hồ sơ là tổ chức).
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
    "data[noidungyeucaugiaiquyet]": "dom-input",  # textarea nội dung yêu cầu (ghép từ tên chủ hồ sơ).
    "data[taxCode]": "dom-input",             # Mã định danh tổ chức (khi NGƯỜI NỘP là tổ chức).
    "data[chonDoiTuong]": "dom-select",       # Loại NGƯỜI NỘP: Cá nhân/Tổ chức.
    "data[hinhThucNop]": "dom-select",        # Hình thức nộp (mặc định Trực tuyến).
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
}
