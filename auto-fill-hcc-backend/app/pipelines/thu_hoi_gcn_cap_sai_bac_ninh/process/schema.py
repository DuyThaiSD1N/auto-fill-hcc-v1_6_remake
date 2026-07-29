"""Compact schema cho "[Bắc Ninh] Thu hồi GCN cấp sai & cấp lại".

Đơn ngắn (5 ô) + người nhận. Nguồn: CCCD chủ hồ sơ, GCN QSDĐ (tên chủ sử dụng dạng "Hộ ông…"),
Biên bản họp gia đình (= văn bản kiến nghị).
"""

FIELDS: list[dict] = [
    {"name": "Cccd_HoTen",
     "desc": "Họ tên người kiến nghị/chủ hồ sơ, vd \"Nguyễn Kim Ánh\". ƯU TIÊN nguồn có DẤU CHUẨN: "
             "CCCD > Biên bản họp gia đình. KHÔNG lấy tên từ GCN/sổ đỏ cũ (OCR hay sai dấu)."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD của chủ hồ sơ (từ CCCD hoặc dòng CCCD số trên đơn/biên bản)."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp CCCD (mặt sau), dd/mm/yyyy. Bỏ nếu không có."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp CCCD. "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính về trật tự '
             'xã hội"; thẻ căn cước mới ghi "BỘ CÔNG AN" → "Bộ Công an". Bỏ nếu không có.'},
    {"name": "TenChuSuDungDat",
     "desc": 'Tên chủ sử dụng đất cho ô "a) Tên", dạng "Hộ ông …"/"Hộ bà …" (vd "Hộ ông Nguyễn Kim Ánh"). '
             'ƯU TIÊN lấy từ Biên bản họp gia đình (cụm "chủ sử dụng đất, hộ ông/bà: …") hoặc CCCD — '
             'nguồn có DẤU CHUẨN. KHÔNG lấy tên từ GCN/sổ đỏ cũ nếu OCR sai dấu (vd "Anh" thay vì "Ánh"). '
             "Nếu không rõ ông/bà thì bỏ tiền tố, chỉ trả họ tên chuẩn."},
    {"name": "Don_KinhGui",
     "desc": 'Cơ quan nhận đơn (dòng "Kính gửi:" hoặc "đề nghị UBND …" trong biên bản), vd "UBND phường Song Liễu".'},
    {"name": "Don_DiaChi",
     "desc": "Địa chỉ thường trú của chủ hồ sơ — CHUỖI MỘT DÒNG, giữ đủ tổ/thôn + phường/xã + tỉnh. KHÔNG object."},
    {"name": "Don_DienThoai", "desc": "Số điện thoại (thường không có trên giấy tờ → bỏ). Chỉ chữ số."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["Cccd_NgayCap"] = "x-date"

# ---- UI thân đơn (khớp NHÃN) ----
L_KINHGUI = "Kính gửi"
L_TEN = "a) Tên"
L_GIAYTO = "b) Giấy tờ nhân thân/pháp nhân"
L_DIACHI = "c) Địa chỉ"
L_DIENTHOAI = "d) Số điện thoại"

# ---- Người nhận (khớp NAME) ----
N_HOTEN = "nhanTaiNhahoTen"
N_CCCD = "nhanTaiNhasoCCCD"
N_SDT = "nhanTaiNhasoDienThoai"
N_DIACHI = "nhanTaiNhadiaChi"

UI_COMP_BY_NAME = {
    L_KINHGUI: "bn-input", L_TEN: "bn-input", L_GIAYTO: "bn-input", L_DIACHI: "bn-input",
    L_DIENTHOAI: "bn-input",
    N_HOTEN: "bn-input", N_CCCD: "bn-input", N_SDT: "bn-input", N_DIACHI: "bn-input",
}
