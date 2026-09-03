"""Compact schema cho "Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất"
— cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn (Form.io, Sở Nông nghiệp và Môi trường).

CÙNG contact-block với chuyen_muc_dich/tach_hop_thua/#75 (1 panel thongTinChung, data[...] người nộp/chủ
hồ sơ Y HỆT, có data[organization]/data[taxCode] cho tổ chức). KHÁC #135-137: KHÔNG có panel thửa đất.

Phần I là 1 panel chứa HAI vai:
- ChuHoSo_*  : CHỦ HỒ SƠ = người sử dụng đất/chủ sở hữu đứng tên Giấy chứng nhận đề nghị CẤP ĐỔI (đứng tên
               GCN / Đơn đăng ký biến động Mẫu 18). Có thể CÁ NHÂN (kể cả ĐỒNG SỞ HỮU vợ+chồng) / TỔ CHỨC.
- NguoiNop_* : NGƯỜI NỘP HỒ SƠ = người trực tiếp thao tác nộp (có thể được ỦY QUYỀN). Tự nộp thì = ChuHoSo.

⚠ Form KHÔNG có ô riêng cho SỐ Giấy chứng nhận → số GCN cần cấp đổi (GCN_So) được mapper ghép vào
data[noidungyeucaugiaiquyet].
"""

# --- Chủ hồ sơ (subject = người đứng tên GCN đề nghị cấp đổi) ---
FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Tổ chức" nếu chủ hồ sơ là công ty/doanh nghiệp/HTX/cơ quan '
        '(tên có "Công ty", "Doanh nghiệp", "HTX", "Hợp tác xã"); "Cá nhân" nếu là một người/hộ gia đình. '
        'Chủ hồ sơ là người sử dụng đất/chủ sở hữu ĐỨNG TÊN Giấy chứng nhận đề nghị cấp đổi.'},
    {"name": "ChuHoSo_HoTen", "desc": "Tên CHỦ HỒ SƠ — nếu CÁ NHÂN: họ và tên (IN HOA); nếu ĐỒNG SỞ HỮU "
        "vợ/chồng (Giấy chứng nhận ghi 'Ông: … và Bà: …' hoặc Đơn Mẫu 18 ghi 2 người) → GHI ĐỦ CẢ HAI TÊN "
        "vào một chuỗi, dạng 'NGUYỄN VĂN A và TRẦN THỊ B'. Nếu TỔ CHỨC: tên đầy đủ tổ chức. Lấy ở mục I "
        "'Người sử dụng đất' trên Giấy chứng nhận, Đơn đăng ký biến động Mẫu 18 (mục 1a Tên), hoặc GCN ĐKDN."},
    {"name": "ChuHoSo_DiaChi", "desc": "Địa chỉ THƯỜNG TRÚ/nơi ở của CHỦ HỒ SƠ, object {quocGia,tinh,xa,"
        "diaChi}. Lấy ở Đơn Mẫu 18 (mục 1c 'Địa chỉ'), địa chỉ người sử dụng đất trên Giấy chứng nhận, hoặc "
        "Nơi thường trú trên CCCD chủ hồ sơ. ⚠ KHÔNG lấy 'địa chỉ thửa đất' (vị trí lô đất) làm địa chỉ "
        "người. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/tổ/thôn."},
]

# --- Nghiệp vụ cấp đổi: số GCN + nội dung/lý do biến động (ghép vào 'Nội dung yêu cầu giải quyết') ---
FIELDS += [
    {"name": "GCN_So", "desc": "SỐ Giấy chứng nhận cần CẤP ĐỔI — số phát hành GCN (vd 'BA 685616') và số "
        "vào sổ cấp GCN nếu có. Lấy ở Bản gốc Giấy chứng nhận đã cấp / Trang "
        "bổ sung GCN. Ghi dạng 'BA 685616 (số vào sổ CH 00131)'. ⚠ Nếu hồ sơ có NHIỀU Giấy chứng nhận (vd "
        "GCN của cá nhân và GCN của tổ chức) → lấy GCN CỦA CHỦ HỒ SƠ: số GCN mà tên người sử dụng đất/chủ "
        "sở hữu trên GCN KHỚP với ChuHoSo_HoTen, và khớp số GCN nêu trong mục 'Nội dung biến động' của Đơn "
        "Mẫu 18 của chủ hồ sơ. KHÔNG bịa nếu không đọc được."},
    {"name": "NoiDungBienDong", "desc": "Nội dung/lý do BIẾN ĐỘNG (cấp đổi) — mục 2 'Nội dung biến động' "
        "của Đơn đăng ký biến động đất đai Mẫu số 18. Vd: cấp đổi do Giấy chứng nhận cũ rách/hư hỏng/ố "
        "nhòe; do chỉnh lý biến động ranh giới/diện tích sau đo đạc; do thay đổi địa chỉ thường trú; do dồn "
        "nhiều Giấy chứng nhận thành một... CHÉP ĐẦY ĐỦ nội dung mục 2, KHÔNG tóm tắt. Không có thì bỏ trống."},
]

# --- Người nộp hồ sơ (người thao tác nộp; có thể được ủy quyền) ---
FIELDS += [
    {"name": "NguoiNop_LoaiDoiTuong", "desc": '"Tổ chức" nếu người nộp là tổ chức; "Cá nhân" nếu là một '
        'người. Đa số người nộp là CÁ NHÂN (kể cả khi được tổ chức ủy quyền).'},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP HỒ SƠ. Nếu có Giấy ủy quyền: lấy BÊN ĐƯỢC ỦY "
        "QUYỀN (Ông/Bà được ủy quyền / 'Tôi tên là'). Nếu KHÔNG có ủy quyền (tự nộp): người nộp CHÍNH LÀ "
        "chủ hồ sơ (nếu chủ hồ sơ là đồng sở hữu vợ+chồng thì lấy người đứng đơn/ký đơn). IN HOA như CCCD."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh NGƯỜI NỘP (cá nhân), dd/mm/yyyy — CCCD / Giấy ủy quyền. "
        "Giấy tờ đất thường chỉ ghi NĂM sinh → ưu tiên ngày/tháng đầy đủ từ CCCD."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính NGƯỜI NỘP: "Nam"/"Nữ" — CCCD, hoặc suy từ danh xưng '
        'Ông/Bà trong Đơn Mẫu 18 / Giấy ủy quyền.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND/định danh cá nhân NGƯỜI NỘP. Đọc CCCD hoặc Giấy "
        "ủy quyền ('Căn cước công dân số'). Chỉ chữ số. Ưu tiên 12 chữ số của CCCD (GCN cũ có thể ghi CMND "
        "9 số → vẫn ưu tiên CCCD 12 số hiện hành)."},
    {"name": "NguoiNop_MaSoThue", "desc": "Mã số thuế / mã số doanh nghiệp NGƯỜI NỘP (CHỈ khi người nộp là "
        "TỔ CHỨC). Lấy ở GCN đăng ký doanh nghiệp. Chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD NGƯỜI NỘP, dd/mm/yyyy — mặt sau CCCD / Giấy ủy "
        "quyền. ⚠ Phân biệt với 'ngày cấp GCN' (không lấy nhầm)."},
    {"name": "NguoiNop_NoiCap", "desc": 'Cơ quan cấp CCCD NGƯỜI NỘP — GHI ĐẦY ĐỦ, KHÔNG viết tắt. Giấy tờ '
        'hay ghi tắt "CCSQLHC TTXH" / "CCS QLHC về TTXH" / "Cục CSQLHC" → PHẢI ghi thành "Cục Cảnh sát quản '
        'lý hành chính về trật tự xã hội". Thẻ căn cước mới ghi "Bộ Công an".'},
    {"name": "NguoiNop_DiaChi", "desc": "Địa chỉ THƯỜNG TRÚ của CHÍNH NGƯỜI NỘP, object {quocGia,tinh,xa,"
        "diaChi}. Lấy ở CCCD người nộp (Nơi thường trú), Đơn Mẫu 18 (mục 1c) hoặc Giấy ủy quyền. Tự nộp và "
        "không có giấy tờ riêng → BỎ TRỐNG (mapper tự dùng ChuHoSo_DiaChi). ⚠ KHÔNG lấy địa chỉ thửa đất, "
        "trụ sở tổ chức, hay tỉnh của thửa đất làm địa chỉ người nộp. tinh='Tỉnh/Thành phố …', xa=phường/"
        "xã, diaChi=số nhà/đường/tổ/thôn."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại NGƯỜI NỘP — Đơn Mẫu 18 mục 1d 'Điện thoại liên "
        "hệ' hoặc CCCD. Chỉ chữ số."},
    {"name": "NguoiNop_Email", "desc": "Email NGƯỜI NỘP — Đơn Mẫu 18 mục 1d 'Hộp thư điện tử' nếu có; "
        "thường không có → bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["ChuHoSo_DiaChi"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Contact block Y HỆT chuyen_muc_dich (KHÔNG panel thửa).
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
