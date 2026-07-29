"""Compact schema cho "Cung cấp thông tin quy hoạch đô thị và nông thôn" (cổng Bộ Xây dựng
dvc.moc.gov.vn — Form.io).

Form CHỈ có 1 khối "Thông tin người nộp hồ sơ" (Phần I). LLM chỉ trả FACT nguồn về NGƯỜI NỘP
(CCCD + Đơn đề nghị); `mapper.enrich` suy ra tất định các ô Form.io data[...].

CÙNG nền tảng/engine với dang_ky_dat_dai_lan_dau_lam_dong (comp dom-*), NHƯNG rút gọn còn MỘT
người: không có khối chủ hồ sơ / thửa đất / GCN (thửa đất nộp qua bản scan ở bước đính kèm).
"""

FIELDS: list[dict] = [
    # NGƯỜI NỘP HỒ SƠ = người sử dụng đất đứng đơn (tự nộp) hoặc người được ủy quyền (nộp thay).
    # Nguồn chính: CCCD người nộp + Đơn đề nghị cung cấp thông tin quy hoạch.
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên NGƯỜI NỘP HỒ SƠ. Lấy từ CCCD (Họ và tên) hoặc dòng "
        "'Tôi là/Tên tôi là' của Đơn đề nghị. Nếu <nguoi_nop_context> chỉ rõ tài liệu CCCD của người nộp "
        "thì lấy đúng người đó."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người nộp, dd/mm/yyyy — lấy từ CCCD hoặc dòng 'Ngày, "
        "tháng, năm sinh' của Đơn đề nghị."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người nộp: "Nam" hoặc "Nữ" (từ CCCD).'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số định danh/CCCD/CMND của người nộp; đọc mặt trước hoặc MRZ "
        "mặt sau CCCD, hoặc dòng 'Số CCCD/CMND' của Đơn đề nghị. Chỉ chữ số."},
    {"name": "NguoiNop_NgayCapCccd", "desc": "Ngày cấp CCCD/CMND (mặt sau), dd/mm/yyyy. Chỉ có nếu upload "
        "CCCD hoặc Đơn ghi 'Cấp ngày'."},
    {"name": "NguoiNop_NoiCapCccd",
     "desc": 'Nơi cấp CCCD/CMND (mặt sau). "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính '
             'về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an". Chỉ có nếu upload CCCD.'},
    {"name": "NguoiNop_ThuongTru",
     "desc": "Nơi thường trú của người nộp, object {quocGia,tinh,xa,diaChi}. ƯU TIÊN tên phường/xã MỚI ghi "
             "trong Đơn đề nghị (địa danh sau sáp nhập); nếu CCCD ghi tên CŨ mà Đơn ghi tên mới thì lấy theo "
             "Đơn. tinh = 'Tỉnh/Thành phố …', xa = phường/xã, diaChi = tổ dân phố/thôn/số nhà."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại liên hệ của người nộp — lấy trong Đơn đề nghị nếu "
        "có. Chỉ chữ số; không lấy số điện thoại bàn/cơ quan."},
    {"name": "NguoiNop_Email", "desc": "Hộp thư điện tử của người nộp ghi trong Đơn đề nghị nếu có; bỏ trống "
        "thì bỏ qua (CCCD không có email)."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCapCccd"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_ThuongTru"] = "x-select-area"

# ---- UI fields Form.io (data[...]) — comp dom-* cho engine fillFormStandard ----
# Chỉ Phần I "Thông tin người nộp hồ sơ". Bỏ data[tenHoSo] (ghi chú tự nhập) và
# data[AuthorityApplicantPhoneNumber] (điều kiện, chỉ khi ủy quyền).
UI_COMP_BY_NAME = {
    "data[chonDoiTuong]": "dom-select",   # Cá nhân / Tổ chức
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",       # Tỉnh/TP
    "data[district]": "dom-select",       # Phường/Xã (cấp 2/3 — trên form này 'district' giữ phường/xã)
    "data[address]": "dom-input",         # địa chỉ chi tiết
    "data[phoneNumber]": "dom-input",
}
