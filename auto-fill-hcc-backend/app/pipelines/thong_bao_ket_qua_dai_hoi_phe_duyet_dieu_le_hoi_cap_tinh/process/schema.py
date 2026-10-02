"""Compact schema cho "Thông báo kết quả đại hội và phê duyệt đổi tên hội, phê duyệt điều lệ hội (cấp tỉnh)" (mã
1.012943) — cổng DVCQG (Form.io).

Hồ sơ mẫu: Tờ trình báo cáo kết quả đại hội (kính gửi Sở Nội vụ) + Danh sách BCH kèm tờ trình + Nghị quyết đại hội +
Báo cáo tổng kết nhiệm kỳ (kèm báo cáo kinh phí, phụ lục thi đua) + Biên bản bầu cử + Danh sách BCH / Ban thường vụ /
Chủ tịch, Phó Chủ tịch / Ban kiểm tra + Biên bản họp BCH lần thứ nhất. Hồ sơ thường KHÔNG có CCCD nào.

HAI vai:
- NguoiNop_* : NGƯỜI NỘP = tài khoản đăng nhập. Họ tên, ngày sinh, số định danh cổng tự đổ (ô khoá) → chỉ lấy giới
               tính, ngày cấp, nơi cấp, nơi thường trú từ CCCD KHỚP tài khoản.
- ChuHoSo_*  : người đại diện hội ký "TM. Ban chấp hành" — CHỈ lấy từ thẻ CCCD của chính người đó. Cổng mặc định tích
               "Người nộp hồ sơ là chủ hồ sơ" (Phần II chép từ Phần I); không có CCCD người ký thì giữ nguyên.

Phần IV là mẫu khai "Văn bản báo cáo kết quả đại hội": tên hội, số văn bản, ngày đại hội, loại đại hội, nhiệm kỳ, địa
điểm, nội dung đã thông qua (toàn văn phần Quyết nghị), datagrid hồ sơ gửi kèm, người ký TM. BCH.
"""

FIELDS: list[dict] = [
    {"name": "TenHoi", "desc": "Tên hội, viết CHUẨN đầy đủ (vd 'Hội Cờ tướng tỉnh Bình An'), sửa lỗi OCR hiển nhiên, "
        "KHÔNG viết IN HOA toàn bộ, không viết tắt (CGC → Cựu giáo chức, TP → thành phố). Nguồn: Tờ trình / văn bản "
        "báo cáo → Nghị quyết đại hội → con dấu."},
    {"name": "SoVanBan", "desc": "Số, ký hiệu của VĂN BẢN BÁO CÁO KẾT QUẢ ĐẠI HỘI (Tờ trình) gửi Sở Nội vụ, vd "
        "'12/TTr-HCT'. Số viết tay ghép đúng thứ tự. KHÔNG lấy số của Báo cáo tổng kết hay số công văn được viện dẫn."},
    {"name": "NgayDaiHoi", "desc": "Ngày KHAI MẠC đại hội (ngày đầu tiên), dd/mm/yyyy. Đại hội 2 ngày '17 và 18 tháng 9' "
        "→ 17/09/yyyy. Ưu tiên Tờ trình → Biên bản bầu cử / Biên bản đại hội → Nghị quyết."},
    {"name": "LoaiDaiHoi", "desc": 'Loại đại hội: "nhiệm kỳ" / "bất thường" / "thành lập". Đại hội "lần thứ N, nhiệm '
        'kỳ yyyy-yyyy" (kể cả lần thứ I sau hợp nhất) → "nhiệm kỳ".'},
    {"name": "LanThu", "desc": "Số lần đại hội như văn bản ghi, chỉ phần số (vd 'I', 'VII'). Không ghi thì bỏ."},
    {"name": "NhiemKy", "desc": "Nhiệm kỳ dạng 'yyyy-yyyy' (vd '2026-2031')."},
    {"name": "DiaDiem", "desc": "Nơi tổ chức đại hội (hội trường, số nhà, đường, phường, tỉnh/thành phố). Ưu tiên "
        "Nghị quyết đại hội → Biên bản bầu cử → Biên bản đại hội."},
    {"name": "NoiDung", "desc": "TOÀN VĂN phần quyết nghị của Nghị quyết đại hội — chép NGUYÊN VĂN từ dòng 'QUYẾT "
        "NGHỊ' (hoặc 'I. ...' ngay sau) tới hết đoạn cuối trước khối chữ ký; giữ đánh số mục, giữ xuống dòng giữa các "
        "đoạn bằng \\n; KHÔNG tóm tắt, KHÔNG sửa số liệu; chỉ sửa lỗi OCR hiển nhiên. Không có Nghị quyết thì lấy "
        "các nội dung đại hội đã thông qua trong Tờ trình / Biên bản đại hội."},
    {"name": "NguoiKy_TMBCH", "desc": "Họ tên người ký 'TM. Ban chấp hành' / 'T/M Thường trực' trên văn bản báo cáo "
        "kết quả đại hội (Tờ trình) → Nghị quyết đại hội. Viết hoa chữ cái đầu mỗi từ."},
    {"name": "DanhMucHoSo", "desc": "Mảng giấy tờ GỬI KÈM văn bản báo cáo — có trong file tải lên, TRỪ chính Tờ trình "
        "/ văn bản báo cáo và CCCD. Mỗi phần tử một chuỗi bắt đầu bằng TÊN LOẠI văn bản ('Danh sách ...', 'Nghị quyết "
        "...', 'Báo cáo ...', 'Biên bản ...', 'Dự thảo Điều lệ ...'), kèm trích yếu, số/ngày nếu có. Theo thứ tự trong "
        "hồ sơ. Báo cáo kinh phí / phụ lục thống kê nằm trong Báo cáo tổng kết thì ghi chung một dòng."},
    {"name": "SaiLech", "desc": "Mảng chuỗi ngắn nêu chỗ các giấy tờ ghi LỆCH nhau về ngày đại hội, địa điểm, tên hội, "
        "nhiệm kỳ (vd 'Nghị quyết ghi tháng 8, Tờ trình ghi tháng 9'). Không có thì bỏ."},
    {"name": "ChuHoSo_HoTen", "desc": "Họ tên trên thẻ CCCD của NGƯỜI KÝ TM. Ban chấp hành (NguoiKy_TMBCH). CHỈ điền khi "
        "hồ sơ có thẻ CCCD của chính người đó; KHÔNG lấy từ danh sách nhân sự."},
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh trên thẻ CCCD người ký, dd/mm/yyyy."},
    {"name": "ChuHoSo_GioiTinh", "desc": 'Giới tính trên thẻ CCCD người ký: "Nam"/"Nữ".'},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số định danh 12 số trên thẻ CCCD người ký."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp thẻ CCCD người ký, dd/mm/yyyy. KHÔNG lấy ngày hết hạn."},
    {"name": "ChuHoSo_NoiCap", "desc": "Cơ quan cấp thẻ CCCD người ký, chép đúng như in trên thẻ."},
    {"name": "ChuHoSo_DiaChi", "desc": "Nơi thường trú / nơi cư trú trên thẻ CCCD người ký, object {quocGia,tinh,xa,"
        "diaChi}. diaChi = số nhà, đường, tổ/thôn (KHÔNG kèm phường/tỉnh)."},
    {"name": "ChuHoSo_QuocTich", "desc": "Quốc tịch trên thẻ CCCD người ký (vd 'Việt Nam')."},
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
for _name in ("NgayDaiHoi", "ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_DiaChi", "NguoiNop_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
for _name in ("DanhMucHoSo", "SaiLech"):
    COMPACT_COMP_BY_NAME[_name] = "x-array"

# ---- UI Form.io fields (data[...]) — field-key theo mapping 1.012943. data[fullname], data[birthday],
# data[identityNumber], data[chonDoiTuong], data[chonDoiTuong1] cổng khoá → KHÔNG phát. data[email], data[fax],
# data[ownerFax] hồ sơ không có nguồn → bỏ. data[Ngay] (cụm chữ ký) cổng để ẩn → bỏ.
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
    # Phần II — chủ hồ sơ (chỉ phát khi bỏ tích "Người nộp hồ sơ là chủ hồ sơ").
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    "data[ownerNation]": "dom-select",
    "data[ghiChu]": "dom-input",
    # Phần IV — mẫu khai văn bản báo cáo kết quả đại hội.
    "data[TenHoi]": "dom-input",
    "data[So]": "dom-input",
    "data[NgayTl]": "dom-date",
    "data[DaiHoiTl]": "dom-select",
    "data[NhiemKy]": "dom-input",
    "data[ToChucTai]": "dom-input",
    "data[NoiDung]": "dom-input",
    "data[TM.BCH]": "dom-input",
}

# Option của data[DaiHoiTl] (nhãn form ghi "Đại hội thành lập" nhưng danh mục chỉ có 2 lựa chọn này).
DAI_HOI_NHIEM_KY = "Đại hội nhiệm kỳ"
DAI_HOI_BAT_THUONG = "Đại hội bất thường"

# Hai datagrid cùng liệt kê giấy tờ (FE tự bấm "Thêm dòng"):
#   Phần III data[hoSoDinhKem][i] — Tên giấy tờ / Loại bản ("Bản chính").
#   Phần IV  data[HoSo][i]        — Tên giấy tờ / Loại giấy tờ ("Danh sách", "Nghị quyết", ...).
MAX_HO_SO_ROWS = 20
for _i in range(MAX_HO_SO_ROWS):
    for _grid in ("hoSoDinhKem", "HoSo"):
        UI_COMP_BY_NAME[f"data[{_grid}][{_i}][textField1]"] = "dom-input"
        UI_COMP_BY_NAME[f"data[{_grid}][{_i}][textField2]"] = "dom-input"
