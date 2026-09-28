"""Compact schema cho "Thủ tục báo cáo tổ chức đại hội thành lập, đại hội nhiệm kỳ, đại hội bất thường của hội (cấp
tỉnh)" (mã 1.012942) — cổng DVCQG (Form.io).

Hồ sơ mẫu (đại hội nhiệm kỳ): Công văn báo cáo tổ chức đại hội (kính gửi Sở Nội vụ) + Đề án nhân sự + Dự kiến danh
sách BCH + các văn bản cử cán bộ / ý kiến đồng ý + Dự thảo báo cáo tổng kết, báo cáo chính trị, báo cáo kiểm điểm
BCH / Ban kiểm tra + Dự thảo Nghị quyết đại hội + Dự thảo Điều lệ sửa đổi + Sơ yếu lý lịch + Phiếu LLTP số 1.

HAI vai:
- NguoiNop_* : NGƯỜI NỘP = tài khoản đăng nhập. Họ tên, ngày sinh, số định danh cổng tự đổ (ô khoá) → chỉ lấy giới
               tính, ngày cấp, nơi cấp, nơi thường trú từ CCCD KHỚP tài khoản.
- ChuHoSo_*  : CHỦ HỒ SƠ = nhân sự dự kiến làm Chủ tịch hội — người có Sơ yếu lý lịch / Phiếu LLTP số 1 trong hồ sơ.

Form chỉ có Phần I (người nộp), Phần II (chủ hồ sơ + ghi chú) và datagrid "Hồ sơ kèm theo gồm" — không có mẫu đơn.
"""

FIELDS: list[dict] = [
    {"name": "TenHoi", "desc": "Tên hội tổ chức đại hội, viết CHUẨN đầy đủ như Điều lệ (vd 'Hội Cờ tướng tỉnh Bình "
        "An'), sửa lỗi OCR hiển nhiên, KHÔNG viết IN HOA toàn bộ, không dùng tên viết tắt (KHHGĐ → Kế hoạch hóa gia "
        "đình, TP → thành phố)."},
    {"name": "LoaiDaiHoi", "desc": 'Loại đại hội được báo cáo: "nhiệm kỳ" / "bất thường" / "thành lập". Nguồn: trích '
        'yếu "V/v tổ chức Đại hội ..." của văn bản báo cáo → Nghị quyết Ban chấp hành.'},
    {"name": "NhiemKy", "desc": "Nhiệm kỳ của đại hội, dạng 'yyyy-yyyy' (vd '2026-2031'). Đại hội bất thường / thành "
        "lập không ghi thì bỏ."},
    {"name": "TenDaiHoi", "desc": "Tên gọi đại hội như văn bản ghi, bỏ tên hội (vd 'Đại hội đại biểu lần thứ VII'). "
        "Không có thì bỏ."},
    {"name": "DanhMucHoSo", "desc": "Mảng giấy tờ CÓ trong bộ hồ sơ tải lên, mỗi phần tử một chuỗi 'Tên giấy tờ – "
        "Số: ..., ngày ...' (bỏ phần số/ngày nếu giấy không ghi). Thứ tự: Văn bản báo cáo → Nghị quyết BCH → Đề án "
        "nhân sự / Danh sách dự kiến BCH → Văn bản cử cán bộ / ý kiến đồng ý → Các dự thảo báo cáo → Dự thảo Nghị "
        "quyết đại hội → Dự thảo Điều lệ → Sơ yếu lý lịch / Phiếu LLTP. KHÔNG liệt kê CCCD/căn cước."},
    {"name": "ChuHoSo_HoTen", "desc": "Họ tên NHÂN SỰ DỰ KIẾN LÀM CHỦ TỊCH hội (người có Sơ yếu lý lịch / Phiếu LLTP "
        "số 1; Đề án / Danh sách dự kiến BCH: chức danh 'Chủ tịch'). Nguồn: CCCD → Phiếu LLTP mục 1 'Họ và tên' "
        "(KHÔNG lấy mục 'Tên gọi khác') → Sơ yếu lý lịch 'Họ và tên khai sinh'. Viết hoa chữ cái đầu mỗi từ."},
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh chủ hồ sơ, dd/mm/yyyy (CCCD → Phiếu LLTP → Sơ yếu lý lịch)."},
    {"name": "ChuHoSo_GioiTinh", "desc": 'Giới tính chủ hồ sơ: "Nam"/"Nữ" (CCCD → Phiếu LLTP → Sơ yếu lý lịch).'},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/thẻ căn cước của chủ hồ sơ (CCCD → Phiếu LLTP mục 8 → Sơ yếu lý "
        "lịch mục 'Số CMND/CCCD'). Chỉ chữ số. KHÔNG lấy số phiếu LLTP."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD của chủ hồ sơ (CCCD → Phiếu LLTP mục 8 'Cấp ngày ...'), "
        "dd/mm/yyyy. KHÔNG lấy ngày cấp phiếu LLTP, ngày xác nhận Sơ yếu lý lịch."},
    {"name": "ChuHoSo_NoiCap", "desc": "Nơi cấp CCCD của chủ hồ sơ, chép đúng (CCCD → Phiếu LLTP mục 8 'Nơi cấp'). "
        "KHÔNG lấy cơ quan cấp phiếu LLTP (Công an tỉnh/TP)."},
    {"name": "ChuHoSo_DiaChi", "desc": "Nơi thường trú của chủ hồ sơ (CCCD → Phiếu LLTP mục 9 → Sơ yếu lý lịch 'Nơi ở "
        "hiện nay'), object {quocGia,tinh,xa,diaChi}. diaChi = số nhà, đường, tổ/thôn (KHÔNG kèm phường/tỉnh)."},
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại của chủ hồ sơ (Sơ yếu lý lịch 'Điện thoại' → cột SĐT của "
        "Danh sách dự kiến BCH ở dòng người này). Không có thì bỏ."},
    {"name": "ChuHoSo_Email", "desc": "Email của CHÍNH chủ hồ sơ nếu giấy tờ ghi. KHÔNG lấy email của cán bộ được cử "
        "trong các công văn cử cán bộ."},
    {"name": "ChuHoSo_QuocTich", "desc": "Quốc tịch của chủ hồ sơ (vd 'Việt Nam')."},
    {"name": "NguoiNop_HoTen", "desc": "Họ và tên in trên thẻ CCCD của NGƯỜI NỘP (xem nguoi_nop_context) — không có "
        "thẻ đó thì bỏ."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số định danh 12 số trên CHÍNH thẻ CCCD người nộp."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính trên thẻ CCCD người nộp: "Nam"/"Nữ".'},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CHÍNH thẻ CCCD người nộp, dd/mm/yyyy. KHÔNG lấy ngày hết hạn."},
    {"name": "NguoiNop_NoiCap", "desc": "Cơ quan cấp thẻ CCCD người nộp, chép đúng như in trên thẻ. Thẻ không in thì "
        "bỏ."},
    {"name": "NguoiNop_DiaChi", "desc": "Nơi thường trú / nơi cư trú trên thẻ CCCD người nộp, object {quocGia,tinh,"
        "xa,diaChi}."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại của NGƯỜI NỘP nếu hồ sơ ghi cạnh đúng tên người đó (vd "
        "'Người liên hệ: ..., ĐT ...'). Không có thì bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_DiaChi", "NguoiNop_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
COMPACT_COMP_BY_NAME["DanhMucHoSo"] = "x-array"

# ---- UI Form.io fields (data[...]) — field-key lấy từ DOM thật (mapping 1.012942). data[fullname],
# data[birthday], data[identityNumber] cổng khoá; data[chonDoiTuong], data[chonDoiTuong1] mặc định "Cá nhân" → KHÔNG
# phát. data[email], data[fax], data[ownerFax] hồ sơ không có nguồn → bỏ.
UI_COMP_BY_NAME: dict[str, str] = {
    # Phần I — người nộp (ô không khoá).
    "data[gender]": "dom-select",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[isOwnerDossierCheck]": "dom-checkbox",
    # Phần II — chủ hồ sơ.
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerEmail]": "dom-input",
    "data[ownerNation]": "dom-select",
    "data[ghiChu]": "dom-input",
}

# Datagrid "Hồ sơ kèm theo gồm" — mỗi giấy tờ một dòng (FE tự bấm "Thêm dòng").
MAX_HO_SO_ROWS = 20
for _i in range(MAX_HO_SO_ROWS):
    UI_COMP_BY_NAME[f"data[hoSoDinhKem][{_i}][textField1]"] = "dom-input"
    UI_COMP_BY_NAME[f"data[hoSoDinhKem][{_i}][textField2]"] = "dom-input"
