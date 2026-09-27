"""Compact schema "[Bắc Ninh] Tách thửa đất/hợp thửa đất" (Đơn Mẫu số 21).

LLM trả FACT nguồn từ CCCD chủ đất + Đơn đề nghị + GCN (sổ đỏ) + Bản vẽ tách thửa (Mẫu 22).
UI field điền vào e-form Bắc Ninh do `mapper.enrich` suy ra tất định:
  - Thân đơn: ô `element_<id>` khớp theo NHÃN (title) → name = CỐT NHÃN, comp bn-*.
  - Người nhận kết quả: field tên CỐ ĐỊNH `nhanTaiNha*` → name = ĐÚNG NAME, comp bn-*.

LƯU Ý trùng NHÃN: Phần II (tách) và Phần III (hợp) dùng chung nhiều title ("loại đất", "địa chỉ
thửa đất", "Giấy chứng nhận: số vào sổ cấp GCN", "ngày cấp GCN"). Ta CHỈ điền nhánh TÁCH; FE khớp
phần tử DOM ĐẦU TIÊN (tách đứng trước hợp) nên các nhãn trùng rơi đúng vào ô tách.
"""

FIELDS: list[dict] = [
    # --- Người sử dụng đất (chủ đất) ---
    {"name": "Cccd_HoTen",
     "desc": "Họ và tên NGƯỜI SỬ DỤNG ĐẤT (chủ đất đứng đơn). Lấy từ CCCD, hoặc mục 1.a của đơn, hoặc "
             "'Người sử dụng đất' trên GCN. KHÔNG lấy người được ủy quyền/người nộp thay."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số CCCD/định danh của chủ đất (12 chữ số). Từ CCCD hoặc mục 1.b của đơn."},
    {"name": "Nguoi_DiaChiThuongTru",
     "desc": "Địa chỉ thường trú của chủ đất (mục 1.c của đơn / Nơi thường trú CCCD). CHUỖI MỘT DÒNG, "
             "giữ ĐỦ thôn/tổ dân phố + phường/xã + tỉnh. KHÔNG trả object."},
    {"name": "Don_KinhGui",
     "desc": 'Cơ quan nhận đơn ở dòng "Kính gửi:" (thường là Chi nhánh Văn phòng đăng ký đất đai …).'},

    # --- Thửa đất GỐC đề nghị tách (mục 2.a) — nguồn GCN/đơn/bản vẽ ---
    {"name": "Thua_So", "desc": "Số thửa đất GỐC (thửa đang xin tách). Từ GCN 'Thửa đất số' / mục 2.a của đơn."},
    {"name": "Thua_ToBanDo", "desc": "Số tờ bản đồ của thửa gốc. Từ GCN 'Tờ bản đồ số'."},
    {"name": "Thua_DienTich", "desc": "Diện tích thửa gốc (m2, giữ nguyên cách ghi số). Từ GCN 'Diện tích'."},
    {"name": "Thua_LoaiDat",
     "desc": "Loại đất thửa gốc, chép NGUYÊN VĂN theo GCN (vd 'Đất ở tại đô thị (ODT)' hoặc mã 'ODT')."},
    {"name": "Thua_DiaChi",
     "desc": "Địa chỉ THỬA ĐẤT (vị trí thửa, KHÁC địa chỉ thường trú của chủ). Từ GCN 'Địa chỉ'. CHUỖI MỘT DÒNG."},
    {"name": "Gcn_SoVaoSo",
     "desc": "Số phát hành GCN + số vào sổ cấp GCN (vd 'AA 05419774, số vào sổ CX 714'). Từ GCN."},
    {"name": "Gcn_NgayCap", "desc": "Ngày cấp GCN (dd/mm/yyyy). Từ GCN 'ngày … tháng … năm'."},
    {"name": "ThuaMoi_DienTich1", "desc": "Diện tích thửa MỚI thứ nhất sau tách (m2). Từ đơn/bản vẽ tách thửa."},
    {"name": "ThuaMoi_DienTich2",
     "desc": "Diện tích thửa MỚI thứ hai (và các thửa tiếp theo) sau tách (m2). Từ đơn/bản vẽ tách thửa. Bỏ nếu chỉ tách 1."},

    # --- Lý do / giấy tờ kèm / đề nghị cấp GCN (mục 3,4,5) ---
    {"name": "Don_LyDo", "desc": "Lý do tách/hợp thửa (mục 3 của đơn), vd 'Để chuyển nhượng', 'Chia tài sản'. Bỏ nếu trống."},
    {"name": "Don_GiayToKem", "desc": "Danh sách giấy tờ nộp kèm liệt kê ở mục 4 của đơn. Chép nguyên văn. Bỏ nếu trống."},
    {"name": "Don_DeNghiCapGCN", "desc": "Nội dung mục 5 'Đề nghị cấp Giấy chứng nhận' trên đơn. Chép nguyên văn. Bỏ nếu trống."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["Gcn_NgayCap"] = "x-date"

# ---- UI: ô thân đơn — khớp theo NHÃN (title). Nhãn trùng Phần II/III → FE lấy DOM đầu (tách). ----
L_KINHGUI = "Kính gửi"
L_TEN = "a) Tên"
L_GIAYTO = "b) Giấy tờ nhân thân/ pháp nhân số"  # title có khoảng trắng sau "nhân/"
L_DIACHI_CT = "Địa chỉ thường trú chi tiết"       # startsWith "…chi tiết của chủ hồ sơ"
# Địa chỉ chủ đất TÁCH 3 cấp: Tỉnh/Xã là <select> select2 (title RỖNG) → khớp theo CLASS ổn định
# eform-element-TinhThuongTru / eform-element-XaThuongTru (FE findSelectForField theo class). Xã
# cascade theo Tỉnh (FE điền bất đồng bộ). Ô "Địa chỉ chi tiết" chỉ nhận phần tổ/xóm/số nhà.
S_TINH_DON = "TinhThuongTru"
S_XA_DON = "XaThuongTru"
# Phần II — Tách thửa:
L_THUA_SO = "a) Tách thửa đất số"
L_TOBANDO = ", tờ bản đồ số"                       # có dấu phẩy đầu → riêng của tách (hợp là "tờ bản đồ số")
L_DIENTICH = ", diện tích"                          # có dấu phẩy đầu → riêng của tách
L_LOAIDAT = "loại đất"                              # trùng hợp → DOM đầu = tách
L_DIACHITHUA = "địa chỉ thửa đất"                   # trùng hợp → DOM đầu = tách
L_SOVAOSO = "Giấy chứng nhận: số vào sổ cấp GCN"    # trùng hợp → DOM đầu = tách
L_NGAYCAP = "ngày cấp GCN"                          # trùng hợp → DOM đầu = tách
L_THUAMOI1 = "Thửa thứ nhất: diện tích"
L_THUAMOI2 = "Thửa thứ hai: diện tích"              # textarea
# Phần IV:
L_LYDO = "3. Lý do tách, hợp thửa đất"
L_GIAYTOKEM = "4. Giấy tờ nộp kèm theo đơn này gồm có"
L_DENGHIGCN = "5. Đề nghị cấp Giấy chứng nhận"

# ---- UI: người nhận kết quả — khớp theo NAME cố định ----
N_HOTEN = "nhanTaiNhahoTen"
N_CCCD = "nhanTaiNhasoCCCD"
N_SDT = "nhanTaiNhasoDienThoai"
N_DIACHI = "nhanTaiNhadiaChi"
# Nhận KQ cũng tách Tỉnh/Xã là select (khớp theo NAME cố định); Xã cascade theo Tỉnh.
N_TINH = "nhanTaiNhatinhThanhId"
N_XA = "nhanTaiNhaphuongXaId"

_LABELS = [
    L_KINHGUI, L_TEN, L_GIAYTO, L_DIACHI_CT,
    L_THUA_SO, L_TOBANDO, L_DIENTICH, L_LOAIDAT, L_DIACHITHUA, L_SOVAOSO, L_NGAYCAP,
    L_THUAMOI1, L_THUAMOI2, L_LYDO, L_GIAYTOKEM, L_DENGHIGCN,
    N_HOTEN, N_CCCD, N_SDT, N_DIACHI,
]
UI_COMP_BY_NAME = {name: "bn-input" for name in _LABELS}
# Các ô địa chỉ Tỉnh/Xã là <select> → comp bn-select.
for _s in (S_TINH_DON, S_XA_DON, N_TINH, N_XA):
    UI_COMP_BY_NAME[_s] = "bn-select"
