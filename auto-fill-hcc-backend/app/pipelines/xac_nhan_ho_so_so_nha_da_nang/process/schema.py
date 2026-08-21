"""Compact schema cho "Thủ tục xác nhận hồ sơ cấp mới/cấp lại Giấy chứng nhận biển số nhà" — cổng DVC TP
Đà Nẵng dichvucong.danang.gov.vn (Form.io). CÙNG cổng/engine + field-key data[...] Y HỆT #110
(cap_gcn_so_nha_da_nang); chỉ khác tên thủ tục + đính kèm chỉ 1 dòng (Đơn đề nghị).

Phần I là 1 panel chứa HAI vai:
- ChuHoSo_*  : CHỦ HỒ SƠ = chủ sở hữu nhà đề nghị cấp GCN số nhà = người KÝ Đơn đề nghị. Thường CÁ NHÂN
               (mẫu = Bà LÊ NA); có thể TỔ CHỨC.
- NguoiNop_* : NGƯỜI NỘP HỒ SƠ = người trực tiếp thao tác nộp. Số nhà hầu như luôn TỰ NỘP → NguoiNop =
               ChuHoSo. Chỉ khi có Hợp đồng ủy quyền (nộp thay) thì NguoiNop KHÁC ChuHoSo.
Nhân thân (ngày sinh/CCCD/địa chỉ liên hệ) thuộc NGƯỜI NỘP; khi tự nộp chính là của chủ hồ sơ.
"""

# --- Chủ hồ sơ (chủ sở hữu nhà, người ký Đơn đề nghị cấp GCN số nhà) ---
FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Tổ chức" nếu chủ hồ sơ là công ty/doanh nghiệp/cơ quan '
        '(tên có "Công ty", "Doanh nghiệp", "HTX"); "Cá nhân" nếu là một người. Chủ hồ sơ là NGƯỜI KÝ Đơn '
        'đề nghị cấp giấy chứng nhận số nhà (chủ sở hữu nhà đề nghị cấp/cấp lại biển số nhà).'},
    {"name": "ChuHoSo_HoTen", "desc": "Tên CHỦ HỒ SƠ — nếu CÁ NHÂN: họ và tên IN HOA; nếu TỔ CHỨC: tên "
        "đầy đủ tổ chức. Lấy ở Đơn đề nghị cấp giấy chứng nhận số nhà (người đứng đơn/chủ sở hữu nhà), "
        "hoặc danh xưng chủ sở hữu trên Giấy chứng nhận QSDĐ."},
    {"name": "ChuHoSo_DiaChiXinCap", "desc": "Địa chỉ CÔNG TRÌNH/NHÀ đang đề nghị cấp số nhà (địa chỉ xin "
        "cấp biển số nhà) — ghi trong Đơn đề nghị ('đề nghị cấp giấy chứng nhận số nhà tại...'). Ví dụ dạng "
        "'5A Ngõ Chi Lan, phường Hải Châu, TP Đà Nẵng'. KHÁC địa chỉ thường trú/liên hệ của người nộp và "
        "KHÁC địa chỉ trên Giấy chứng nhận QSDĐ. Chữ viết tay có thể khó đọc — chỉ lấy khi đọc được, không bịa."},
]

# --- Người nộp hồ sơ (người thao tác nộp; có thể được ủy quyền) ---
FIELDS += [
    {"name": "NguoiNop_LoaiDoiTuong", "desc": '"Tổ chức" nếu người nộp là tổ chức; "Cá nhân" nếu là một '
        'người. Đa số người nộp là CÁ NHÂN.'},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP HỒ SƠ. Nếu có Hợp đồng ủy quyền (nộp thay): lấy "
        "BÊN ĐƯỢC ỦY QUYỀN (Bên B). Nếu KHÔNG có ủy quyền (tự nộp): người nộp CHÍNH LÀ chủ hồ sơ. IN HOA như CCCD."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh NGƯỜI NỘP (cá nhân), dd/mm/yyyy — CCCD / Đơn đề nghị."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính NGƯỜI NỘP: "Nam"/"Nữ" — CCCD; nếu không có nhãn giới '
        'tính thì SUY từ danh xưng "Ông"/"Bà" ghi trong Đơn đề nghị hoặc Giấy chứng nhận QSDĐ ("Bà" → Nữ, '
        '"Ông" → Nam). KHÔNG tự suy đoán nếu không có căn cứ.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND/định danh cá nhân NGƯỜI NỘP. Đọc CCCD, Đơn đề "
        "nghị, hoặc Giấy chứng nhận QSDĐ (nhiều nguồn thường thống nhất). Chỉ chữ số. Ưu tiên 12 chữ số."},
    {"name": "NguoiNop_MaSoThue", "desc": "Mã số thuế / mã định danh tổ chức NGƯỜI NỘP (CHỈ khi người nộp "
        "là TỔ CHỨC). Chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD NGƯỜI NỘP, dd/mm/yyyy — mặt sau CCCD / Đơn đề nghị."},
    {"name": "NguoiNop_NoiCap", "desc": 'Cơ quan cấp CCCD NGƯỜI NỘP. CCCD gắn chip cấp từ 2021: "Cục Cảnh '
        'sát quản lý hành chính về trật tự xã hội"; thẻ căn cước mới: "Bộ Công an".'},
    {"name": "NguoiNop_DiaChi", "desc": "Địa chỉ thường trú/LIÊN HỆ hiện tại của NGƯỜI NỘP, object "
        "{quocGia,tinh,xa,diaChi}. Lấy ở CCCD (Nơi thường trú) / Đơn đề nghị (địa chỉ hiện tại/tổ dân phố). "
        "tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/tổ dân phố (KHÔNG kèm phường/xã/tỉnh). "
        "ĐÂY LÀ ĐỊA CHỈ LIÊN HỆ — KHÁC địa chỉ xin cấp số nhà (ChuHoSo_DiaChiXinCap)."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại NGƯỜI NỘP (thường ghi tay dưới phần ký tên trên "
        "Đơn đề nghị). Chỉ chữ số."},
    {"name": "NguoiNop_Email", "desc": "Email NGƯỜI NỘP nếu giấy tờ có; thường không có → bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_DiaChi"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên field-key lấy CHUẨN từ HTML thật. 1 panel.
UI_COMP_BY_NAME = {
    # Chủ hồ sơ.
    "data[ownerFullname]": "dom-input",       # Họ tên chủ hồ sơ (chủ sở hữu nhà, hoặc tên tổ chức).
    "data[isOwnerDossier]": "dom-checkbox",   # "Chủ hồ sơ cũng là người nộp" — tick khi tự nộp, bỏ khi ủy quyền.
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
    "data[noidungyeucaugiaiquyet]": "dom-input",  # textarea nội dung yêu cầu (ghép từ tên chủ hồ sơ + địa chỉ xin cấp).
    "data[taxCode]": "dom-input",             # Mã định danh tổ chức (khi NGƯỜI NỘP là tổ chức).
    "data[chonDoiTuong]": "dom-select",       # Loại NGƯỜI NỘP: Cá nhân/Tổ chức.
    "data[hinhThucNop]": "dom-select",        # Hình thức nộp (mặc định Trực tuyến).
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
}
