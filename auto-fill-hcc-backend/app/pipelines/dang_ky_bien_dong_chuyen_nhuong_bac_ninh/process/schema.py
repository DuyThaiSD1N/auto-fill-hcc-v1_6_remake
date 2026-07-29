"""Compact schema "[Bắc Ninh] Đăng ký biến động QSDĐ (chuyển nhượng/thừa kế/tặng cho/góp vốn)".

LLM trả FACT nguồn của BÊN NHẬN chuyển quyền (Bên B) từ CCCD + Đơn ĐK biến động + Hợp đồng.
UI field điền vào e-form Bắc Ninh do `mapper.enrich` suy ra tất định:
  - Thân đơn (Phần II): ô `element_<id>` khớp theo NHÃN (title) → name = CỐT NHÃN, comp bn-*.
  - Người nhận kết quả (Phần IV): field tên CỐ ĐỊNH `nhanTaiNha*` → name = ĐÚNG NAME, comp bn-*.
Engine `fill-bacninh.js` thử khớp theo NAME trước, không có thì khớp theo NHÃN (startsWith/includes).
"""

FIELDS: list[dict] = [
    {"name": "Cccd_HoTen",
     "desc": 'Họ và tên BÊN NHẬN chuyển quyền (Bên B: bên mua/được tặng cho/thừa kế/nhận góp vốn), '
             'vd "Nguyễn Xuân Khang". Lấy từ CCCD của bên nhận, hoặc mục I của đơn, hoặc "Bên B" trong '
             'hợp đồng. TUYỆT ĐỐI KHÔNG lấy bên chuyển nhượng/bên bán/bên tặng cho (Bên A).'},
    {"name": "Cccd_SoDinhDanh",
     "desc": "Số định danh/CCCD của bên nhận (Bên B). Từ CCCD hoặc dòng \"CCCD số/Căn cước công dân số\" của Bên B."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp CCCD của bên nhận, dd/mm/yyyy. Bỏ nếu không có."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp CCCD bên nhận. "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính về '
             'trật tự xã hội"; thẻ mới ghi "BỘ CÔNG AN" → "Bộ Công an". CCCD gắn chip không in nơi cấp '
             "trên mặt thẻ → lấy từ đơn/hợp đồng. Bỏ nếu không có."},
    {"name": "Don_KinhGui",
     "desc": 'Nơi nhận ở dòng "Kính gửi:" đầu đơn (thường là "Chi nhánh Văn phòng đăng ký đất đai …"). '
             'Bỏ ký hiệu chú thích ở cuối.'},
    {"name": "Don_DiaChi",
     "desc": "Địa chỉ thường trú của bên nhận (Bên B) — mục I của đơn / Nơi thường trú CCCD / địa chỉ "
             "Bên B trong hợp đồng. CHUỖI MỘT DÒNG, giữ ĐỦ thôn/tổ dân phố + phường/xã + tỉnh. KHÔNG object."},
    {"name": "Don_DienThoai", "desc": "Số điện thoại liên hệ của bên nhận (thường không có → bỏ). Chỉ chữ số."},
    {"name": "Don_LoaiGiaoDich",
     "desc": 'Loại giao dịch biến động, MỘT trong: "chuyển nhượng", "tặng cho", "thừa kế", "góp vốn". '
             'Suy từ TÊN hợp đồng/văn bản (vd "HỢP ĐỒNG CHUYỂN NHƯỢNG QUYỀN SỬ DỤNG ĐẤT" → "chuyển nhượng"; '
             '"HỢP ĐỒNG TẶNG CHO…" → "tặng cho"; "VĂN BẢN KHAI NHẬN/PHÂN CHIA DI SẢN THỪA KẾ" → "thừa kế"). '
             'Không rõ thì bỏ (mapper mặc định "chuyển nhượng").'},
    {"name": "Don_TenHopDong",
     "desc": 'Tên đầy đủ của hợp đồng/văn bản chuyển quyền (vd "Hợp đồng chuyển nhượng quyền sử dụng đất"). '
             'Lấy từ tiêu đề trang đầu hợp đồng. Bỏ nếu không có.'},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["Cccd_NgayCap"] = "x-date"

# ---- UI: ô thân đơn (Phần II) — khớp theo NHÃN (title). name = cốt nhãn (startsWith/exact). ----
# element_69738 title "a) Tên(2):" · 69739 "b) Giấy tờ nhân thân/pháp nhân(2):" · 69740 "c) Địa chỉ(2):"
# 69741 "d) Điện thoại liên hệ (nếu có):" (number) · 69743 "2. Nội dung biến động(3):" · 69747 "(3)"
L_KINHGUI = "Kính gửi"
L_TEN = "a) Tên"
L_GIAYTO = "b) Giấy tờ nhân thân/pháp nhân"
L_DIACHI = "c) Địa chỉ"
L_DIENTHOAI = "d) Điện thoại liên hệ"
L_NOIDUNG = "2. Nội dung biến động"
L_GIAYTOKEM3 = "(3)"

# ---- UI: người nhận kết quả (Phần IV) — khớp theo NAME cố định của cổng ----
N_HOTEN = "nhanTaiNhahoTen"
N_CCCD = "nhanTaiNhasoCCCD"
N_SDT = "nhanTaiNhasoDienThoai"
N_DIACHI = "nhanTaiNhadiaChi"

UI_COMP_BY_NAME = {
    L_KINHGUI: "bn-input", L_TEN: "bn-input", L_GIAYTO: "bn-input", L_DIACHI: "bn-input",
    L_DIENTHOAI: "bn-input", L_NOIDUNG: "bn-input", L_GIAYTOKEM3: "bn-input",
    N_HOTEN: "bn-input", N_CCCD: "bn-input", N_SDT: "bn-input", N_DIACHI: "bn-input",
}
