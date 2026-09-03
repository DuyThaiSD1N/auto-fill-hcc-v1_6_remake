"""Compact schema cho "Xóa đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất"
— cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn (Form.io).

CÙNG contact-block với cap_doi_gcn/chuyen_muc_dich (1 panel, data[...] người nộp/chủ hồ sơ Y HỆT +
data[organization]/data[taxCode] cho tổ chức). KHÔNG có panel thửa đất.

Phần I là 1 panel chứa HAI vai:
- ChuHoSo_*  : CHỦ HỒ SƠ = BÊN BẢO ĐẢM / chủ tài sản được GIẢI CHẤP (người/tổ chức đứng tên Giấy chứng nhận
               tài sản bảo đảm, đề nghị xóa đăng ký). Có thể CÁ NHÂN / TỔ CHỨC.
- NguoiNop_* : NGƯỜI NỘP HỒ SƠ = người trực tiếp thao tác nộp (thường được ỦY QUYỀN). Tự nộp thì = ChuHoSo.

⚠ Form KHÔNG có ô riêng cho số Giấy chứng nhận → số GCN tài sản bảo đảm (GCN_So) được mapper ghép vào
data[noidungyeucaugiaiquyet].
"""

# --- Chủ hồ sơ (subject = bên bảo đảm/chủ tài sản được giải chấp) ---
FIELDS: list[dict] = [
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Tổ chức" nếu chủ hồ sơ là công ty/doanh nghiệp/HTX/cơ quan/tổ '
        'chức tín dụng (tên có "Công ty", "Doanh nghiệp", "HTX", "Ngân hàng"); "Cá nhân" nếu là một người. '
        'Chủ hồ sơ là BÊN BẢO ĐẢM/chủ tài sản được giải chấp (đứng tên Giấy chứng nhận tài sản bảo đảm).'},
    {"name": "ChuHoSo_HoTen", "desc": "Tên CHỦ HỒ SƠ — nếu CÁ NHÂN: họ và tên (IN HOA). Nếu TỔ CHỨC: tên "
        "đầy đủ tổ chức (bên bảo đảm, vd 'Công ty TNHH ... '). Lấy ở Phiếu yêu cầu xóa đăng ký (Mẫu 03a — "
        "bên bảo đảm), Giấy chứng nhận (người sử dụng đất/chủ tài sản), hoặc Giấy ủy quyền (bên ủy quyền là "
        "chủ tài sản). KHÔNG lấy tên BÊN NHẬN BẢO ĐẢM (ngân hàng)."},
    {"name": "ChuHoSo_DiaChi", "desc": "Địa chỉ THƯỜNG TRÚ/trụ sở của CHỦ HỒ SƠ (bên bảo đảm), object "
        "{quocGia,tinh,xa,diaChi}. Lấy ở Phiếu yêu cầu Mẫu 03a / Giấy ủy quyền (địa chỉ bên ủy quyền) / địa "
        "chỉ trên Giấy chứng nhận. ⚠ KHÔNG lấy 'địa chỉ thửa đất' (vị trí lô đất) làm địa chỉ người. "
        "tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường/tổ/thôn."},
]

# --- Nghiệp vụ: số GCN + nội dung yêu cầu xóa (ghép vào 'Nội dung yêu cầu giải quyết') ---
FIELDS += [
    {"name": "GCN_So", "desc": "SỐ Giấy chứng nhận của TÀI SẢN BẢO ĐẢM (tài sản được giải chấp) — số phát "
        "hành GCN (vd 'BA 685616') và số vào sổ cấp GCN nếu có. Lấy ở Phiếu yêu cầu Mẫu 03a (mục tài sản "
        "bảo đảm/giấy tờ kèm theo) hoặc Bản gốc Giấy chứng nhận. Ghi dạng 'BA 685616 (số vào sổ CH 00131)'. "
        "KHÔNG bịa nếu không đọc được."},
    {"name": "NoiDungYeuCau", "desc": "Nội dung yêu cầu XÓA đăng ký biện pháp bảo đảm — chép nội dung mục "
        "yêu cầu của Phiếu yêu cầu xóa đăng ký (Mẫu số 03a): mô tả biện pháp bảo đảm/hợp đồng thế chấp cần "
        "xóa (số hợp đồng thế chấp, ngày, bên nhận bảo đảm là ngân hàng nào, số đăng ký biện pháp bảo đảm/"
        "hồ sơ số). CHÉP ĐẦY ĐỦ, KHÔNG tóm tắt. ĐÂY là nội dung yêu cầu — KHÔNG đặt tên/CCCD chủ hồ sơ ở "
        "đầu. Không có thì bỏ trống."},
]

# --- Người nộp hồ sơ (người thao tác nộp; thường được ủy quyền) ---
FIELDS += [
    {"name": "NguoiNop_LoaiDoiTuong", "desc": '"Tổ chức" nếu người nộp là tổ chức; "Cá nhân" nếu là một '
        'người. Đa số người nộp là CÁ NHÂN (kể cả khi được tổ chức ủy quyền).'},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP HỒ SƠ. Nếu có Giấy ủy quyền: lấy BÊN ĐƯỢC ỦY "
        "QUYỀN (Ông/Bà được ủy quyền). Nếu KHÔNG có ủy quyền (tự nộp): người nộp CHÍNH LÀ chủ hồ sơ (nếu "
        "chủ hồ sơ là tổ chức thì lấy người đại diện theo pháp luật ký đơn). IN HOA như CCCD."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh NGƯỜI NỘP (cá nhân), dd/mm/yyyy — CCCD / Giấy ủy quyền. "
        "Nếu giấy tờ chỉ ghi NĂM sinh (thiếu ngày/tháng) thì để trống, đừng bịa."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính NGƯỜI NỘP: "Nam"/"Nữ" — CCCD, hoặc suy từ danh xưng '
        'Ông/Bà trong Giấy ủy quyền.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND/định danh cá nhân NGƯỜI NỘP. Đọc CCCD hoặc Giấy "
        "ủy quyền ('CMND/Thẻ căn cước/Hộ chiếu số'). Chỉ chữ số. Ưu tiên 12 chữ số của CCCD."},
    {"name": "NguoiNop_MaSoThue", "desc": "Mã số thuế / mã số doanh nghiệp NGƯỜI NỘP (CHỈ khi người nộp là "
        "TỔ CHỨC). Chỉ chữ số."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD NGƯỜI NỘP, dd/mm/yyyy — mặt sau CCCD / Giấy ủy quyền "
        "('...cấp ngày ...')."},
    {"name": "NguoiNop_NoiCap", "desc": 'Cơ quan cấp CCCD NGƯỜI NỘP — GHI ĐẦY ĐỦ, KHÔNG viết tắt. Giấy tờ '
        'hay ghi tắt "Cục CSQLHC" / "CCS QLHC về TTXH" → PHẢI ghi thành "Cục Cảnh sát quản lý hành chính về '
        'trật tự xã hội". Thẻ căn cước mới ghi "Bộ Công an".'},
    {"name": "NguoiNop_DiaChi", "desc": "Địa chỉ THƯỜNG TRÚ của CHÍNH NGƯỜI NỘP, object {quocGia,tinh,xa,"
        "diaChi}. Lấy ở CCCD người nộp / Giấy ủy quyền (địa chỉ thường trú Bên được ủy quyền). Tự nộp và "
        "không có giấy tờ riêng → BỎ TRỐNG (mapper tự dùng ChuHoSo_DiaChi). ⚠ KHÔNG lấy địa chỉ thửa đất, "
        "trụ sở tổ chức, hay tỉnh của thửa đất làm địa chỉ người nộp. tinh='Tỉnh/Thành phố …', xa=phường/"
        "xã, diaChi=số nhà/đường/tổ/thôn."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại NGƯỜI NỘP. Chỉ chữ số. Thường không có trên giấy tờ."},
    {"name": "NguoiNop_Email", "desc": "Email NGƯỜI NỘP nếu giấy tờ có; thường không có → bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_DiaChi"] = "x-select-area"
COMPACT_COMP_BY_NAME["ChuHoSo_DiaChi"] = "x-select-area"

# ---- UI Form.io fields (data[...]) — comp dom-*. Contact block Y HỆT cap_doi_gcn (KHÔNG panel thửa).
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
