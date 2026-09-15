"""Compact schema "[Bắc Ninh] Đăng ký biến động QSDĐ" (maThuTuc 1.115468).

Nguồn = BÊN NHẬN chuyển quyền (Bên B) = CHỦ HỒ SƠ = NGƯỜI ỦY QUYỀN. TÁCH 2 bộ trường theo `purpose`
(runner chọn TRƯỚC khi gọi LLM để mỗi lần trích gọn, không lẫn):

- FIELDS_UYQUYEN (purpose="authorized_person", nút "Điền thông tin người ủy quyền", khối doiTuongKhac*):
  CHỈ nhân thân 1 người = chủ hồ sơ chính. Không cần đồng sử dụng/nghiệp vụ.
- FIELDS_DON (purpose="registration_form", Đơn Mẫu 18, element_*): chủ hồ sơ + người đồng sử dụng (GỘP
  vào ô Tên/Giấy tờ) + nội dung nghiệp vụ.

CHUNG 6 trường nhân thân (_PERSON): HoTen/SoDinhDanh/NgaySinh/ThuongTru/DienThoai/Email.
"""

# --- 6 trường nhân thân CHUNG (chủ hồ sơ chính) ---
_PERSON: list[dict] = [
    {"name": "ChuHoSo_HoTen",
     "desc": 'Họ tên NGƯỜI CHÍNH của bên nhận chuyển quyền (Bên B). Nếu 2 người đồng nhận (vợ chồng) thì '
             'đây là người đứng đầu (vd người chồng). Ưu tiên CCCD, rồi "Bên B" hợp đồng / mục I đơn. '
             'TUYỆT ĐỐI KHÔNG lấy bên chuyển/bên tặng cho (Bên A), không lấy người ĐƯỢC ủy quyền.'},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/định danh của chủ hồ sơ chính, chỉ chữ số (ưu tiên 12 số)."},
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh chủ hồ sơ chính, dd/mm/yyyy (ưu tiên CCCD ghi đủ ngày)."},
    {"name": "ChuHoSo_ThuongTru",
     "desc": "Nơi thường trú chủ hồ sơ chính, object {quocGia,tinh,xa,diaChi}. tinh=tên tỉnh/thành, "
             "xa=phường/xã, diaChi=số nhà/khu/thôn. ⚠ ƯU TIÊN địa chỉ ghi trên ĐƠN Mẫu 18 (mục I '- Địa "
             "chỉ') và các Tờ khai thuế; CHỈ khi đơn/tờ khai không có mới lấy Hợp đồng rồi CCCD. KHÔNG mặc "
             "nhiên lấy 'Nơi cư trú' trên CCCD (có thể là nơi cũ)."},
    {"name": "ChuHoSo_DienThoai", "desc": "SĐT liên hệ chủ hồ sơ (thường ghi tay ở Đơn Mẫu 18). Chỉ chữ số."},
    {"name": "ChuHoSo_Email", "desc": "Email chủ hồ sơ nếu giấy tờ có; thường không có → bỏ."},
]

# --- Riêng ỦY QUYỀN: khối có ô giới tính + ngày cấp + nơi cấp riêng ---
_UYQUYEN_EXTRA: list[dict] = [
    {"name": "ChuHoSo_GioiTinh", "desc": 'Giới tính chủ hồ sơ chính: "Nam"/"Nữ" — CCCD/giấy khai sinh.'},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD chủ hồ sơ chính, dd/mm/yyyy. Bỏ nếu không có."},
    {"name": "ChuHoSo_NoiCap",
     "desc": 'Nơi cấp CCCD chủ hồ sơ. Thẻ căn cước mới in "BỘ CÔNG AN" → "Bộ Công an"; CMND cũ "Cục Cảnh '
             'sát QLHC về TTXH". Bỏ nếu không có.'},
]

# --- Riêng ĐƠN: mã số thuế + người đồng sử dụng (gộp) + nội dung nghiệp vụ ---
_DON_EXTRA: list[dict] = [
    {"name": "ChuHoSo_MaSoThue",
     "desc": "Mã số thuế chủ hồ sơ (nếu tờ khai thuế có ghi; thường = số định danh cá nhân). Chỉ chữ số."},
    {"name": "DongSuDung_HoTen",
     "desc": "Họ tên NGƯỜI THỨ HAI đồng nhận chuyển quyền (vd vợ/chồng của chủ hồ sơ chính), nếu hợp đồng/"
             "đơn ghi 2 người nhận. Không có người thứ hai → bỏ."},
    {"name": "DongSuDung_SoDinhDanh", "desc": "Số CCCD/định danh người đồng nhận thứ hai, chỉ chữ số."},
    {"name": "DongSuDung_NgaySinh", "desc": "Ngày sinh người đồng nhận thứ hai, dd/mm/yyyy (hoặc năm sinh)."},
    {"name": "Don_KinhGui",
     "desc": 'Dòng "Kính gửi:" đầu đơn (vd "Chi nhánh Văn phòng đăng ký đất đai liên phường …"). Bỏ ký hiệu cuối.'},
    {"name": "Don_LoaiGiaoDich",
     "desc": 'Loại giao dịch: "chuyển đổi"/"chuyển nhượng"/"tặng cho"/"thừa kế"/"góp vốn"/"cho thuê"/"mua bán '
             'nhà ở có thời hạn". Suy từ TÊN hợp đồng. Không rõ → bỏ (mapper mặc định "chuyển nhượng").'},
    {"name": "Don_TenHopDong",
     "desc": "Mục IV(2): tên loại + số công chứng CỦA HỢP ĐỒNG/VĂN BẢN CHUYỂN QUYỀN, chép đúng theo tiêu đề "
             "và số công chứng ghi trên hợp đồng của hồ sơ. Chỉ điền khi hồ sơ CÓ hợp đồng."},
    {"name": "Don_GiayToKem",
     "desc": "Mục IV(3): CHỈ các GIẤY TỜ TÙY THÂN/HỘ TỊCH nộp kèm (CCCD, Giấy CN kết hôn, Trích lục khai "
             "sinh, Giấy ủy quyền, Biên bản bàn giao…), ghép chuỗi ngăn '; '. ⚠ TUYỆT ĐỐI KHÔNG đưa hợp đồng "
             "chuyển quyền vào đây (nó ở mục IV(2)). Không có → bỏ."},
    {"name": "Don_TranhChap",
     "desc": "Mục V.2 tình trạng tranh chấp đất: CHÉP theo cam đoan trong Hợp đồng (điều cam đoan về việc "
             "thửa đất có/không có tranh chấp). Bỏ nếu hồ sơ không nêu."},
    {"name": "Don_RanhGioi",
     "desc": "Mục V.3 sự thay đổi ranh giới so với GCN: CHỈ điền khi biên bản/GCN nói RÕ về việc có/không "
             "thay đổi ranh giới so với GCN. Biên bản chỉ 'nhận đúng ranh giới/mốc giới' mà KHÔNG nói thẳng "
             "'so với GCN' → BỎ (không suy luận)."},
    {"name": "Don_MienGiam",
     "desc": "Mục III đối tượng/lý do miễn giảm nghĩa vụ tài chính: lấy ở Tờ khai lệ phí trước bạ (dòng 'Tài "
             "sản thuộc diện được miễn lệ phí trước bạ (lý do)') và/hoặc quan hệ hộ tịch chứng minh miễn giảm. "
             "Bỏ nếu hồ sơ không nêu."},
]

FIELDS_UYQUYEN: list[dict] = _PERSON + _UYQUYEN_EXTRA
FIELDS_DON: list[dict] = _PERSON + _DON_EXTRA

ALLOWED_UYQUYEN = {f["name"] for f in FIELDS_UYQUYEN}
ALLOWED_DON = {f["name"] for f in FIELDS_DON}
ALIASES: dict[str, list[str]] = {}

_DATE_FIELDS = {"ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "DongSuDung_NgaySinh"}


def _comp_map(fields: list[dict]) -> dict[str, str]:
    out = {f["name"]: "x-input" for f in fields}
    for name in out:
        if name in _DATE_FIELDS:
            out[name] = "x-date"
        elif name == "ChuHoSo_ThuongTru":
            out[name] = "x-select-area"
    return out


COMPACT_COMP_UYQUYEN = _comp_map(FIELDS_UYQUYEN)
COMPACT_COMP_DON = _comp_map(FIELDS_DON)

# ---- UI đơn Mẫu 18 (element_*) — khớp CLASS eform-element-<Key>. name = KEY. ----
K_KINHGUI = "KinhGui"
K_TEN = "Ten2"
K_GIAYTO = "GiayToNhanThanphapNhan"
K_DIACHI = "DiaChi"
K_MST = "MaSoThueNeuCo"
K_DIENTHOAI = "DienThoaiLienHeNeuCo"
K_EMAIL = "HopThuDienTuNeuCo"
K_NOIDUNG = "IINoiDungBienDong3"
K_MIENGIAM = "IIIThongTinVeDoiTuongDuocMienGiamNghiaVuTaiChinhVe"
K_GIAYTOKEM2 = "2"
K_GIAYTOKEM3 = "3"
K_TRANHCHAP = "2TinhTrangTranhChapDatDai"
K_RANHGIOI = "3SuThayDoiRanhGioiSoVoiRanhGioiDuocCapGiayChungNha"

UI_COMP_BY_NAME = {
    K_KINHGUI: "bn-input", K_TEN: "bn-input", K_GIAYTO: "bn-input", K_DIACHI: "bn-input",
    K_MST: "bn-input", K_DIENTHOAI: "bn-input", K_EMAIL: "bn-input", K_NOIDUNG: "bn-input",
    K_MIENGIAM: "bn-input", K_GIAYTOKEM2: "bn-input", K_GIAYTOKEM3: "bn-input",
    K_TRANHCHAP: "bn-input", K_RANHGIOI: "bn-input",
}
