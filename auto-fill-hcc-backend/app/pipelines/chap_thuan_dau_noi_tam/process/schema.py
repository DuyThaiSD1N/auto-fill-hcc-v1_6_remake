"""Compact schema cho "Chấp thuận vị trí đấu nối tạm vào đường bộ đang khai thác" — cổng DVC Bộ Xây dựng
dvc.moc.gov.vn (Form.io). TẤT CẢ field-key PHẲNG data[...] (không lồng panel).

HAI vai:
- Phần I  NGƯỜI NỘP (flat data[...]): người trực tiếp đăng nhập & nộp trực tuyến (thường là cá nhân/nhân
  viên nộp thay). Nguồn: CCCD người nộp + tài khoản (formContext). Hỗ trợ cả Cá nhân/Tổ chức.
- Phần II NỘI DUNG ĐƠN (flat data[...]): Chủ hồ sơ/ĐƠN VỊ đề nghị đấu nối tạm + nội dung Đơn đề nghị (khác
  người nộp). Nguồn: Đơn đề nghị (Mẫu Mucb) + Công văn/Hồ sơ thiết kế.
Đính kèm: 3 dòng attp-row (HĐ thi công/chủ trương, Văn bản đề nghị, Hồ sơ thiết kế bản vẽ).
"""

# Hai lựa chọn cố định của ô "Chọn trường hợp" (data[truongHop]) — khớp NGUYÊN VĂN option trên form.
TRUONG_HOP = {
    "1": "Làm đường công vụ phục vụ vận chuyển, khai thác vật liệu và vận chuyển thiết bị thi công xây "
         "dựng công trình",
    "2": "Phục vụ nhiệm vụ quốc phòng, an ninh, phòng chống thiên tai, đê điều",
}

# --- Người nộp hồ sơ (Phần I) ---
_NOP_FIELDS = [
    ("LoaiDoiTuong", '"Cá nhân" nếu người nộp là một người (có CCCD); "Tổ chức" nếu nộp danh nghĩa cơ '
        'quan/doanh nghiệp (có MST). Mặc định "Cá nhân".'),
    ("HoTen", "Họ và tên NGƯỜI NỘP HỒ SƠ — CHỈ lấy từ THẺ CCCD/CMND của người nộp. ⚠ KHÔNG lấy tên người "
        "ký/đại diện/liên hệ ghi trong Đơn đề nghị hay công văn (những tên đó thuộc Phần II). Nếu KHÔNG có "
        "thẻ CCCD người nộp thì BỎ TRỐNG. IN HOA."),
    ("TenToChuc", "Tên cơ quan/tổ chức NGƯỜI NỘP khi người nộp là TỔ CHỨC. Cá nhân → bỏ."),
    ("MaSoThue", "Mã số thuế NGƯỜI NỘP khi là TỔ CHỨC. Chỉ chữ số. Cá nhân → bỏ."),
    ("NgaySinh", "Ngày sinh NGƯỜI NỘP, dd/mm/yyyy — CCCD người nộp."),
    ("GioiTinh", 'Giới tính NGƯỜI NỘP: "Nam"/"Nữ" — CCCD người nộp.'),
    ("SoDinhDanh", "Số CCCD/định danh NGƯỜI NỘP (nếu Tổ chức thì là MST). Chỉ chữ số."),
    ("NgayCap", "Ngày cấp CCCD NGƯỜI NỘP, dd/mm/yyyy."),
    ("NoiCap", 'Nơi cấp CCCD NGƯỜI NỘP. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → '
        '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ căn cước mới → "Bộ Công an".'),
    ("ThuongTru", "NƠI CƯ TRÚ NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. tinh='Tỉnh/Thành phố …'; "
        "xa=phường/xã; diaChi=số nhà/đường/thôn (KHÔNG kèm phường/xã/tỉnh)."),
    ("DienThoai", "Số điện thoại NGƯỜI NỘP. Chỉ chữ số. Thường không có trên CCCD."),
    ("Email", "Email NGƯỜI NỘP nếu có; thường không có → bỏ."),
]

FIELDS: list[dict] = [{"name": f"NguoiNop_{n}", "desc": d} for n, d in _NOP_FIELDS]

# --- Nội dung Đơn đề nghị (Phần II) ---
FIELDS += [
    {"name": "Don_TenToChuc", "desc": "Tên TỔ CHỨC/cá nhân ĐỀ NGHỊ đấu nối tạm (chủ hồ sơ/đơn vị đứng đơn — "
        "KHÁC người nộp trực tuyến). Đơn đề nghị: đơn vị đề nghị (mở đầu văn bản) / Hợp đồng: Chủ đầu tư "
        "(Bên A). Vd 'Ban Quản lý các dự án đầu tư cơ sở hạ tầng ưu tiên thành phố Đà Nẵng'."},
    {"name": "Don_NguoiDaiDien", "desc": "Người đại diện đứng/ký Đơn đề nghị (vd Phó Giám đốc ký thừa lệnh). "
        "LẤY THEO ĐƠN ĐỀ NGHỊ (văn bản gắn trực tiếp hồ sơ), không lấy theo hợp đồng nếu khác người."},
    {"name": "Don_DauNoiTamTu", "desc": "Điểm/vị trí NHÁNH TẠM nơi ĐẤU NỐI XUẤT PHÁT (đường công vụ, vệt "
        "cây xanh, lối tạm…) — đứng NGAY SAU chữ 'đấu nối (đường) tạm TỪ …' trong Đơn/Công văn. Vd 'vệt "
        "cây xanh cách ly (giữa đường Vành đai phía Tây 2 và KCN Hòa Khánh)'. KHÔNG phải con đường lớn "
        "đang khai thác (đó là Don_VaoDuong)."},
    {"name": "Don_VaoDuong", "desc": "TÊN CON ĐƯỜNG BỘ LỚN ĐANG KHAI THÁC được đấu nối VÀO (chính là 'đường "
        "bộ đang khai thác' trong tên thủ tục) — đứng NGAY SAU chữ 'vào (đường) …'. Vd 'Vành đai phía Tây "
        "2'. ⚠ Đừng đảo: 'từ' = nhánh tạm (Don_DauNoiTamTu), 'vào' = đường lớn đang khai thác (field này)."},
    {"name": "Don_TruongHop", "desc": 'Trường hợp đấu nối tạm — trả "1" nếu làm đường công vụ phục vụ vận '
        'chuyển/khai thác vật liệu/thiết bị thi công (đa số); "2" nếu phục vụ quốc phòng, an ninh, phòng '
        'chống thiên tai, đê điều. Suy từ mục đích nêu trong Đơn/Công văn.'},
    {"name": "Don_CamKet", "desc": "Nội dung cam kết khác trong Đơn (vd 'không đòi bồi thường khi cơ quan "
        "có thẩm quyền yêu cầu di chuyển hoặc cải tạo'). Chép đoạn cam kết cuối Đơn."},
    {"name": "Don_PhapLuat", "desc": "Căn cứ pháp luật nêu đầu Đơn (vd 'Luật Đường bộ ngày 27/6/2024; Nghị "
        "định số 165/2024/NĐ-CP ngày 26/12/2024'). Chép nguyên văn phần căn cứ."},
    {"name": "Don_NguoiKy", "desc": "Họ tên người ký, đóng dấu cuối Đơn đề nghị (thường trùng người đại diện)."},
]

# --- Chi tiết vị trí đấu nối (panel điều kiện hiện sau khi chọn 'Chọn trường hợp') ---
FIELDS += [
    {"name": "DauNoi_ViTri", "desc": "Vị trí CỤ THỂ điểm đấu nối tạm (ghi rõ lý trình, vị trí, bên phải/"
        "trái nếu có; số lượng vị trí). Vd '03 vị trí tại vệt cây xanh cách ly giữa đường Vành đai phía "
        "Tây 2 và KCN Hòa Khánh'. Nguồn: Đơn/Công văn."},
    {"name": "DauNoi_DiaBan", "desc": "Thuộc ĐỊA BÀN (phường/xã/khu vực nơi đấu nối). Vd 'phường Liên "
        "Chiểu' hoặc 'KCN Hòa Khánh'. Nguồn: Đơn/Công văn."},
    {"name": "DauNoi_MucDich", "desc": "Mục đích việc đấu nối tạm. Vd 'vận chuyển đất dôi dư (đất tầng "
        "mặt) từ dự án … nhằm cải tạo đất trồng trọt'. Nguồn: Đơn/Công văn."},
    {"name": "DauNoi_TuNgay", "desc": "TỪ NGÀY của thời gian đề nghị đấu nối tạm, dd/mm/yyyy — Đơn 'Thời "
        "gian đề nghị đấu nối tạm từ … đến …'."},
    {"name": "DauNoi_DenNgay", "desc": "ĐẾN NGÀY của thời gian đề nghị đấu nối tạm, dd/mm/yyyy."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_ThuongTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["DauNoi_TuNgay"] = "x-date"
COMPACT_COMP_BY_NAME["DauNoi_DenNgay"] = "x-date"

# ---- UI Form.io fields (data[...]) — comp dom-*. Field-key lấy CHUẨN từ HTML thật (fill.html). ----
UI_COMP_BY_NAME = {
    # ----- Phần I: NGƯỜI NỘP HỒ SƠ (flat) -----
    "data[chonDoiTuong]": "dom-select",
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[phoneNumber]": "dom-input",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[email]": "dom-input",

    # ----- Phần II: NỘI DUNG ĐƠN ĐỀ NGHỊ (flat) -----
    "data[tentochucanhan]": "dom-input",
    "data[nguoidaidien]": "dom-input",
    "data[veViecDeNghiDauNoiTamTu]": "dom-input",
    "data[vaoDuong]": "dom-input",
    "data[truongHop]": "dom-select",
    "data[cacCamKet]": "dom-input",
    "data[dauNoiTam]": "dom-input",
    "data[chuKy]": "dom-input",

    # ----- Panel điều kiện: TRƯỜNG HỢP (1) "Làm đường công vụ…" (lamDuong) -----
    # tuNgay/denNgay là ô datetime lưu ISO (Y-m-dTH:i:S) → comp dom-datetime (khác birthday dd/MM/yyyy).
    "data[viTriDauNoiTam]": "dom-input",
    "data[tenDuong]": "dom-input",
    "data[thuocDiaban]": "dom-input",
    "data[mucDichViecDauNoiTam]": "dom-input",
    "data[tuNgay]": "dom-datetime",
    "data[denNgay]": "dom-datetime",

    # ----- Panel điều kiện: TRƯỜNG HỢP (2) "Phục vụ quốc phòng, an ninh…" (phucVu) -----
    "data[Duong]": "dom-input",
    "data[diaBan]": "dom-input",
    "data[TuNgay]": "dom-datetime",
    "data[DenNgay]": "dom-datetime",
}

