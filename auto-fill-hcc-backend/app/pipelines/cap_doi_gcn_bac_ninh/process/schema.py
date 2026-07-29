"""Compact schema cho "[Bắc Ninh] Cấp đổi Giấy chứng nhận QSDĐ, QSH tài sản gắn liền với đất".

LLM chỉ trả FACT nguồn từ CCCD người yêu cầu + Đơn đăng ký biến động (Mẫu số 18). UI field
điền vào e-form Bắc Ninh được `mapper.enrich` suy ra tất định.

Cấu trúc = ĐƠN Mẫu 18 (giống dinh_chinh_sai_sot_bac_ninh) + khối NGƯỜI NHẬN KẾT QUẢ (giống
thu_hoi_gcn_cap_sai_bac_ninh). Ô đơn khớp theo NHÃN (title đã fold); ô người nhận khớp theo NAME.
"""

FIELDS: list[dict] = [
    # CCCD/CMND người nộp hồ sơ (người sử dụng đất đứng đơn = người nhận kết quả khi tự nộp).
    {"name": "Cccd_HoTen", "desc": "Họ và tên người nộp hồ sơ (người sử dụng đất đứng đơn) — lấy từ CCCD "
        "hoặc mục a) Tên của Đơn Mẫu 18. Ghi như trên Giấy chứng nhận đã cấp."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD/CMND của người đứng đơn; đọc mặt trước, MRZ mặt "
        "sau, hoặc dòng 'CCCD số' trong Đơn."},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp CCCD/CMND (mặt sau), dd/mm/yyyy. Chỉ có nếu upload CCCD."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND (mặt sau). "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành '
             'chính về trật tự xã hội"; thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → "Bộ Công an". Chỉ có nếu upload CCCD.'},

    # Địa chỉ người đứng đơn — CHUỖI 1 DÒNG (NGOẠI LỆ quy tắc địa chỉ chung, xem prompt).
    {"name": "Don_DiaChi",
     "desc": "Địa chỉ người đứng đơn — CHUỖI MỘT DÒNG (string), chép NGUYÊN VĂN dòng 'c) Địa chỉ' của Đơn "
             "Mẫu 18. PHẢI giữ ĐỦ tổ dân phố/thôn + phường/xã + tỉnh "
             '(vd "Bản Nậm Dòn, xã Nậm Hàng, tỉnh Lai Châu"). KHÔNG trả object, KHÔNG bỏ phường/xã.'},

    # Đơn đăng ký biến động đất đai (Mẫu số 18) — do công dân tự khai.
    {"name": "Don_KinhGui",
     "desc": 'Cơ quan nhận đơn ghi ở dòng "Kính gửi:" đầu Đơn Mẫu 18 (vd "Chi nhánh VP ĐKĐĐ ..."). '
             'Bỏ ký hiệu chú thích "(1)" ở cuối.'},
    {"name": "Don_DienThoai", "desc": "Số điện thoại liên hệ ghi trên Đơn Mẫu 18 (mục d) nếu có. Chỉ chữ số; "
        "không lấy số điện thoại bàn."},
    {"name": "Don_NoiDungBienDong",
     "desc": 'Nội dung biến động ghi ở mục 2 của Đơn Mẫu số 18, NGUYÊN VĂN — với thủ tục này thường là '
             '"Cấp đổi giấy chứng nhận quyền sử dụng đất". Không tự bịa.'},
    {"name": "Don_GiayTo2",
     "desc": 'Giấy tờ liên quan (2) liệt kê ở mục 3 Đơn Mẫu 18 (dòng "(2) ..."). Bỏ nếu trống. KHÔNG lấy '
             "dòng (1) Giấy chứng nhận đã cấp (dòng in sẵn)."},
    {"name": "Don_GiayTo3",
     "desc": 'Giấy tờ liên quan (3) liệt kê ở mục 3 Đơn Mẫu 18 (dòng "(3) ..."). Bỏ nếu trống.'},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["Cccd_NgayCap"] = "x-date"

# ---- UI thân đơn (khớp NHÃN — title đã fold) ----
L_KINHGUI = "Kính gửi"
L_TEN = "a) Tên"
L_GIAYTO = "b) Giấy tờ nhân thân/pháp nhân"
L_DIACHI = "c) Địa chỉ"
L_DIENTHOAI = "d) Điện thoại liên hệ"
L_NOIDUNG = "2. Nội dung biến động"
# Mục 3 giấy tờ liên quan: nhãn ô chỉ là "(2)"/"(3)" → engine khớp CHÍNH XÁC (exact) để không dính
# nhầm hậu tố "(2):" của các nhãn khác.
L_GIAYTO2 = "(2)"
L_GIAYTO3 = "(3)"

# ---- Người nhận kết quả (khớp NAME — id DOM là _org_bn_hoso_noptructuyen_<name>) ----
N_HOTEN = "nhanTaiNhahoTen"
N_CCCD = "nhanTaiNhasoCCCD"
N_SDT = "nhanTaiNhasoDienThoai"
N_DIACHI = "nhanTaiNhadiaChi"

# comp: bn-input (input text), bn-textarea (ô nhiều dòng). FE điền theo NHÃN/NAME.
UI_COMP_BY_NAME = {
    L_KINHGUI: "bn-input",
    L_TEN: "bn-input",
    L_GIAYTO: "bn-input",
    L_DIACHI: "bn-input",
    L_DIENTHOAI: "bn-input",
    L_NOIDUNG: "bn-textarea",
    L_GIAYTO2: "bn-input",
    L_GIAYTO3: "bn-input",
    N_HOTEN: "bn-input",
    N_CCCD: "bn-input",
    N_SDT: "bn-input",
    N_DIACHI: "bn-input",
}
