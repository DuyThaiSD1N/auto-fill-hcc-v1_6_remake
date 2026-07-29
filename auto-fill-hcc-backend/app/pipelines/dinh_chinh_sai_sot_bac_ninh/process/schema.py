"""Compact schema cho "[Bắc Ninh] Đính chính GCN đã cấp lần đầu có sai sót".

LLM chỉ trả FACT nguồn từ CCCD người yêu cầu + Đơn đăng ký biến động (Mẫu số 18).
UI field điền vào e-form Bắc Ninh được `mapper.enrich` suy ra tất định.

KHÁC contract laichau (dinh_chinh_sai_sot): ô trên e-form Bắc Ninh là
`element_<id>` khớp theo NHÃN (thuộc tính title). Do đó UI field ở đây đặt `name`
= CỐT NHÃN, comp `bn-*` để engine `fill-bacninh.js` khớp theo nhãn.
"""

FIELDS: list[dict] = [
    # CCCD/CMND người nộp hồ sơ (người sử dụng đất đứng đơn).
    {"name": "Cccd_HoTen", "desc": "Họ và tên người nộp hồ sơ (người đứng đơn) — lấy từ CCCD hoặc mục a) Tên của Đơn."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD/CMND của người đứng đơn; có thể đọc từ MRZ mặt sau hoặc dòng 'CCCD số' trong Đơn."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp CCCD/CMND (mặt sau), dd/mm/yyyy. Chỉ có nếu upload CCCD."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND (mặt sau). "CỤC TRƯỞNG CỤC CẢNH SÁT..." → '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi '
             '"BỘ CÔNG AN" → "Bộ Công an". Chỉ có nếu upload CCCD.'},

    # Địa chỉ người đứng đơn — CHUỖI 1 DÒNG (NGOẠI LỆ quy tắc địa chỉ chung, xem prompt).
    {"name": "Don_DiaChi",
     "desc": "Địa chỉ người đứng đơn — CHUỖI MỘT DÒNG (string), chép NGUYÊN VĂN dòng 'c) Địa chỉ' "
             "của Đơn Mẫu 18. PHẢI giữ ĐỦ tổ dân phố/thôn + phường/xã + tỉnh "
             '(vd "TDP Bùi Xá, phường Song Liễu, tỉnh Bắc Ninh"). KHÔNG trả object, KHÔNG bỏ phường/xã.'},

    # Đơn đăng ký biến động đất đai (Mẫu số 18) — do công dân tự khai.
    {"name": "Don_KinhGui",
     "desc": 'Cơ quan nhận đơn ghi ở dòng "Kính gửi:" đầu Đơn Mẫu 18 '
             '(vd "UBND phường Song Liễu, tỉnh Bắc Ninh"). Bỏ ký hiệu chú thích "(1)" ở cuối.'},
    {"name": "Don_DienThoai", "desc": "Số điện thoại liên hệ ghi trên Đơn Mẫu 18 (mục d) nếu có. Chỉ chữ số."},
    {"name": "Don_NoiDungBienDong",
     "desc": 'Nội dung biến động/đính chính ghi ở mục 2 của Đơn Mẫu số 18, NGUYÊN VĂN '
             '(vd "Đính chính mục đích sử dụng đất"). Không tự bịa.'},
    {"name": "Don_GiayTo2",
     "desc": 'Giấy tờ liên quan (2) liệt kê ở mục 3 Đơn Mẫu 18 (dòng "(2) ..."), vd "CCCD". '
             "Bỏ nếu trống. KHÔNG lấy dòng (1) Giấy chứng nhận đã cấp (dòng in sẵn)."},
    {"name": "Don_GiayTo3",
     "desc": 'Giấy tờ liên quan (3) liệt kê ở mục 3 Đơn Mẫu 18 (dòng "(3) ..."). Bỏ nếu trống.'},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["Cccd_NgayCap"] = "x-date"

# ---- UI fields (điền vào e-form Bắc Ninh) — khớp theo NHÃN (title đã fold) ----
# name = cốt nhãn của <label class="eform-element-label" title="...">.
UI_LABEL_KINHGUI = "Kính gửi"
UI_LABEL_TEN = "a) Tên"
UI_LABEL_GIAYTO = "b) Giấy tờ nhân thân/pháp nhân"
UI_LABEL_DIACHI = "c) Địa chỉ"
UI_LABEL_DIENTHOAI = "d) Điện thoại liên hệ"
UI_LABEL_NOIDUNG = "2. Nội dung biến động"
# Mục 3 giấy tờ liên quan: nhãn ô chỉ là "(2)"/"(3)" → engine khớp CHÍNH XÁC (exact) để không
# dính nhầm hậu tố "(2):" của các nhãn khác (a) Tên(2), c) Địa chỉ(2)...).
UI_LABEL_GIAYTO2 = "(2)"
UI_LABEL_GIAYTO3 = "(3)"

# comp: bn-input (input text), bn-textarea (ô nhiều dòng). FE điền theo NHÃN.
UI_COMP_BY_NAME = {
    UI_LABEL_KINHGUI: "bn-input",
    UI_LABEL_TEN: "bn-input",
    UI_LABEL_GIAYTO: "bn-input",
    UI_LABEL_DIACHI: "bn-input",
    UI_LABEL_DIENTHOAI: "bn-input",
    UI_LABEL_NOIDUNG: "bn-textarea",
    UI_LABEL_GIAYTO2: "bn-input",
    UI_LABEL_GIAYTO3: "bn-input",
}
