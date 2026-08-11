"""Compact schema cho "Cấp giấy phép chặt hạ, dịch chuyển cây xanh" — cổng DVC Bộ Xây dựng dvc.moc.gov.vn
(Form.io). CÙNG cổng/engine với #63 liên vận (field-key lồng data[panel][...]).

Cấu trúc 5 phần khai:
- Phần I  Người nộp hồ sơ : field-key PHẲNG data[...] (CCCD người nộp / tài khoản). Như #103.
- Phần II Chủ hồ sơ + đơn : field-key LỒNG data[panel][...] (CCCD/Tờ khai Mẫu 01/GCN QSDĐ của người đề nghị).
- Phần III Bảng kê cây xanh: DATAGRID data[panel][tbantest][N][...] — nhiều cây (x-array).
- Phần IV-V Lý do/ký      : data[panel][lyDoChat/viTriMoi/TinTTTe/TDTTK/kyTen].
Nút "Sao chép thông tin người nộp" là BUTTON → bỏ qua, điền Phần II trực tiếp.
"""

_MAX_CAY = 12  # số dòng cây tối đa (đủ cho bảng kê thực tế).

# --- Người nộp hồ sơ (Phần I) ---
_NOP_FIELDS = [
    ("HoTen", "Họ và tên NGƯỜI NỘP HỒ SƠ (tài khoản nộp; có thể khác chủ hồ sơ). Từ CCCD người nộp. IN HOA."),
    ("NgaySinh", "Ngày sinh NGƯỜI NỘP, dd/mm/yyyy — CCCD người nộp."),
    ("GioiTinh", 'Giới tính NGƯỜI NỘP: "Nam"/"Nữ" — CCCD người nộp.'),
    ("SoDinhDanh", "Số CCCD/định danh NGƯỜI NỘP. Chỉ chữ số. Ưu tiên 12 chữ số."),
    ("NgayCap", "Ngày cấp CCCD NGƯỜI NỘP, dd/mm/yyyy."),
    ("NoiCap", 'Nơi cấp/cơ quan cấp CCCD NGƯỜI NỘP. "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT '
        'TỰ XÃ HỘI" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ căn cước mới ghi "BỘ CÔNG AN" '
        '→ "Bộ Công an".'),
    ("ThuongTru", "NƠI THƯỜNG TRÚ NGƯỜI NỘP, object {quocGia,tinh,xa,diaChi}. tinh='Tỉnh/Thành phố …', "
        "xa=phường/xã, diaChi=số nhà/đường/tổ (KHÔNG kèm phường/xã/tỉnh)."),
    ("DienThoai", "Số điện thoại NGƯỜI NỘP. Chỉ chữ số. Thường không có trên CCCD."),
    ("Email", "Email NGƯỜI NỘP nếu có; thường không có → bỏ."),
]

FIELDS: list[dict] = [{"name": f"NguoiNop_{n}", "desc": d} for n, d in _NOP_FIELDS]

# --- Chủ hồ sơ + nội dung đơn (Phần II) ---
FIELDS += [
    {"name": "ToKhai_KinhGui", "desc": "Nơi nhận đơn — mục 'Kính gửi' của Tờ khai/Đơn Mẫu 01 (vd 'Sở Xây "
        "dựng thành phố Đà Nẵng'). Chép nguyên văn."},
    {"name": "ChuHoSo_LoaiChuThe", "desc": '"Tổ chức" nếu chủ hồ sơ (người đề nghị) là công ty/cơ quan (có '
        '"Người đại diện", "Chức vụ"); "Cá nhân" nếu là một người.'},
    {"name": "ChuHoSo_Ten", "desc": "Tên tổ chức/cá nhân chủ hồ sơ (người đề nghị cấp phép). CÁ NHÂN: họ "
        "tên; TỔ CHỨC: tên tổ chức. Lấy ở Đơn Mẫu 01 mục 'Tên tổ chức/cá nhân' / CCCD / GCN QSDĐ (chủ sử "
        "dụng đất)."},
    {"name": "ChuHoSo_NguoiDaiDien", "desc": "Người đại diện — Đơn Mẫu 01 mục 'Người đại diện của tổ chức'. "
        "LẤY nếu đơn CÓ ghi (2 mục Người đại diện + Chức vụ BẮT BUỘC trên form, thường có ngay cả khi chủ "
        "hồ sơ là cá nhân — người đứng đại diện/nộp thay). Bỏ trống chỉ khi đơn thực sự để trống."},
    {"name": "ChuHoSo_ChucVu", "desc": "Chức vụ — Đơn Mẫu 01 mục 'Chức vụ'. LẤY nếu đơn CÓ ghi (kể cả khi "
        "chủ hồ sơ là cá nhân). Bỏ trống chỉ khi đơn để trống."},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/định danh chủ hồ sơ. Đơn Mẫu 01 'Số CCCD' / CCCD / GCN "
        "QSDĐ. Chỉ chữ số."},
    {"name": "ChuHoSo_DiaChi", "desc": "Địa chỉ chủ hồ sơ — MỘT chuỗi đầy đủ (số nhà, đường, phường, tỉnh). "
        "Đơn Mẫu 01 mục 'Địa chỉ' / CCCD (Nơi thường trú) / GCN QSDĐ (địa chỉ thửa đất). Chép nguyên văn."},
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại chủ hồ sơ. Đơn Mẫu 01 mục 'Điện thoại'. Chỉ chữ số."},
    {"name": "ChuHoSo_Fax", "desc": "Số Fax chủ hồ sơ nếu Đơn Mẫu 01 có mục 'Fax'. Chỉ chữ số (bỏ ngoặc/"
        "dấu). Dùng làm dự phòng cho số điện thoại khi điện thoại thiếu/không đủ số."},
]

# --- Bảng kê cây xanh (Phần III — datagrid) ---
FIELDS += [
    {"name": "BangKeCay", "desc": "MẢNG các cây xanh đề nghị chặt hạ/dịch chuyển (bảng kê trong Đơn Mẫu "
        "01). Mỗi phần tử: {loaiCay, viTri, chieuCao, duongKinh, moTa}. loaiCay=tên loại cây; viTri=vị trí "
        "cây; chieuCao (vd '12m'); duongKinh (vd '46cm'); moTa=mô tả tình trạng cây (vd 'Mục', 'nghiêng'). "
        "Trích ĐÚNG số dòng có trong bảng kê, giữ nguyên đơn vị."},
]

# --- Lý do & ký (Phần IV-V) ---
FIELDS += [
    {"name": "Don_LyDo", "desc": "Lý do cần chặt hạ/dịch chuyển/thay thế cây — Đơn Mẫu 01 mục 'Lý do'. Chép "
        "nguyên văn (vd cây bị mục, nguy cơ ngã đổ ảnh hưởng nhà ở)."},
    {"name": "Don_ViTriMoi", "desc": "Vị trí trồng cây tại vị trí mới sau dịch chuyển HOẶC phương án xử lý "
        "cây sau khi chặt hạ — Đơn Mẫu 01. Nếu chặt hạ không trồng lại, mẫu ghi 'Không'."},
    {"name": "Don_DiaDanh", "desc": "Địa danh nơi lập đơn — dòng '..., ngày … tháng … năm …' cuối Đơn (tên "
        "tỉnh/thành phố, vd 'Đà Nẵng')."},
    {"name": "Don_NgayLap", "desc": "Ngày lập/ký đơn — dòng ký cuối Đơn Mẫu 01, dd/mm/yyyy."},
    {"name": "Don_NguoiKy", "desc": "Họ tên người làm đơn/ký tên cuối Đơn Mẫu 01 (thường là chủ hồ sơ)."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["NguoiNop_NgaySinh"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_NgayCap"] = "x-date"
COMPACT_COMP_BY_NAME["NguoiNop_ThuongTru"] = "x-select-area"
COMPACT_COMP_BY_NAME["Don_NgayLap"] = "x-date"
COMPACT_COMP_BY_NAME["BangKeCay"] = "x-array"

# ---- UI Form.io fields (data[...]) — comp dom-*. Tên field-key lấy CHUẨN từ HTML thật.
UI_COMP_BY_NAME = {
    # ----- Phần I: NGƯỜI NỘP HỒ SƠ (flat data[...]) -----
    "data[chonDoiTuong]": "dom-select",
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[email]": "dom-input",
    "data[tenHoSo]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[phoneNumber]": "dom-input",
    "data[AuthorityApplicantPhoneNumber]": "dom-input",
    "data[nation]": "dom-select",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",

    # ----- Phần II: CHỦ HỒ SƠ + nội dung đơn (nested data[panel][...]) -----
    "data[panel][kinhGui]": "dom-input",
    "data[panel][organization]": "dom-input",
    "data[panel][nguoiDaiDien]": "dom-input",
    "data[panel][chucVu]": "dom-input",
    "data[panel][identityNumber]": "dom-input",
    "data[panel][address]": "dom-input",
    "data[panel][phoneNumber]": "dom-input",

    # ----- Phần IV-V: lý do / phương án / ký -----
    "data[panel][lyDoChat]": "dom-input",
    "data[panel][viTriMoi]": "dom-input",
    "data[panel][TinTTTe]": "dom-select",
    "data[panel][TDTTK]": "dom-date",
    "data[panel][kyTen]": "dom-input",
}

# ----- Phần III: DATAGRID bảng kê cây xanh (data[panel][tbantest][i][...]) -----
for _i in range(_MAX_CAY):
    for _col in ("stt", "loaiCay", "viTri", "chieuCao", "duongKinh", "motaTinhTrang"):
        UI_COMP_BY_NAME[f"data[panel][tbantest][{_i}][{_col}]"] = "dom-input"
