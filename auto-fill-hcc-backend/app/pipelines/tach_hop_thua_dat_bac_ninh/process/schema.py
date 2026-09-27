"""Compact schema "[Bắc Ninh] Tách thửa đất/hợp thửa đất" (Đơn Mẫu số 22).

LLM trả FACT nguồn từ CCCD chủ đất + Đơn đề nghị + GCN (sổ đỏ) + Bản vẽ tách thửa (Mẫu 22a).
UI field điền vào e-form Bắc Ninh do `mapper.enrich` suy ra tất định:
  - Thân đơn: ô `element_<id>` khớp theo CLASS `eform-element-<Key>` → name = KEY, comp bn-*.
  - Người nhận kết quả: field tên CỐ ĐỊNH `nhanTaiNha*` → name = ĐÚNG NAME, comp bn-*.

LƯU Ý trùng CLASS: Phần 2.1 (tách) và 2.2 (hợp) dùng chung class ToBanDoSo/DienTich/LoaiDat/
DiaChiThuaDat/GiayChungNhanSoVaoSoCapGCN/NgayCapGCN. Ta CHỈ điền nhánh TÁCH; FE lấy phần tử DOM ĐẦU
TIÊN (2.1 đứng trước 2.2) nên các key trùng rơi đúng vào ô tách.
"""

FIELDS: list[dict] = [
    # --- Người sử dụng đất (chủ đất) ---
    {"name": "Cccd_HoTen",
     "desc": "Họ và tên NGƯỜI SỬ DỤNG ĐẤT (chủ đất đứng đơn). Lấy từ CCCD, hoặc mục 1.1 của đơn, hoặc "
             "'Người sử dụng đất' trên GCN. KHÔNG lấy người được ủy quyền/người nộp thay."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số CCCD/định danh của chủ đất (12 chữ số). Từ CCCD hoặc mục 1.2 của đơn."},
    {"name": "Nguoi_DiaChiThuongTru",
     "desc": "Địa chỉ của chủ đất: ƯU TIÊN mục 1.3 'Địa chỉ' của đơn tách thửa; chỉ khi đơn để trống mới lấy "
             "'Nơi thường trú' trên CCCD. KHÔNG ghép hai nguồn (CCCD cũ có thể còn thôn/huyện trước sáp nhập). "
             "CHUỖI MỘT DÒNG, "
             "giữ ĐỦ thôn/tổ dân phố + phường/xã + tỉnh. KHÔNG trả object."},
    {"name": "Nguoi_DienThoai", "desc": "Số điện thoại liên hệ của chủ đất (mục 1.4 của đơn). Bỏ nếu không ghi."},
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
    {"name": "ThuaMoi_SoThua",
     "desc": "Số thửa mới sau khi tách, lấy từ cụm 'thành … thửa' ở mục tách thửa của đơn/bản vẽ. Chỉ ghi số "
             "đúng như trên giấy (vd '02')."},
    {"name": "ThuaMoi_DienTich1", "desc": "Diện tích thửa MỚI thứ nhất sau tách (m2). Từ đơn/bản vẽ tách thửa."},
    {"name": "ThuaMoi_LoaiDat1", "desc": "Loại đất thửa MỚI thứ nhất sau tách, chép nguyên văn (vd 'ODT'). Từ đơn/bản vẽ."},
    {"name": "ThuaMoi_DienTich2",
     "desc": "Diện tích thửa MỚI thứ hai sau tách (m2). Từ đơn/bản vẽ tách thửa. Bỏ nếu chỉ tách 1."},
    {"name": "ThuaMoi_LoaiDat2",
     "desc": "Loại đất thửa MỚI thứ hai sau tách, chép nguyên văn (vd 'ODT'). Từ đơn/bản vẽ. Bỏ nếu chỉ tách 1."},
    {"name": "ThuaMoi_Khac",
     "desc": "Các thửa MỚI từ thứ BA trở đi, MỘT DÒNG, mỗi thửa dạng 'Thửa thứ ba: diện tích 114,0 m², loại "
             "đất ODT' ngăn bằng '; '. Bỏ nếu tách không quá 2 thửa."},

    # --- Lý do / giấy tờ kèm / đề nghị cấp GCN (mục 3,4,5) ---
    {"name": "Don_LyDo", "desc": "Lý do tách/hợp thửa (mục 3 của đơn), vd 'Để chuyển nhượng', 'Chia tài sản'. Bỏ nếu trống."},
    {"name": "Don_GiayToKem",
     "desc": "Giấy tờ nộp kèm KHÁC ghi ở mục 4 của đơn, NGOÀI dòng in sẵn 'Giấy chứng nhận và Bản vẽ tách "
             "thửa đất, hợp thửa đất…'. Chép nguyên văn. Bỏ nếu không có."},
    {"name": "Don_DeNghiCapGCN",
     "desc": "Phần người viết đơn ghi sau '5. Đề nghị cấp Giấy chứng nhận:' (vd 'Không thay đổi người sử dụng "
             "đất'). Chép nguyên văn, BỎ chú thích in sẵn trong ngoặc '(ghi có hoặc không thay đổi…)'. Bỏ nếu trống."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
COMPACT_COMP_BY_NAME["Gcn_NgayCap"] = "x-date"

# ---- UI: ô thân đơn — khớp theo CLASS `eform-element-<Key>` (ổn định hơn title: cổng đổi nhãn
# "a) Tên" → "1.1. Tên", ", tờ bản đồ số" → "tờ bản đồ số"…). Key trùng 2.1/2.2 → FE lấy DOM đầu (tách). ----
L_KINHGUI = "KinhGui"                               # title "kính"
L_TEN = "11Ten"                                     # 1.1. Tên
L_GIAYTO = "12GiayToNhanThanphapNhanSo2"            # 1.2. Giấy tờ nhân thân/pháp nhân số(2)
L_DIACHI = "13DiaChi"                               # 1.3. Địa chỉ — MỘT ô text, không còn select Tỉnh/Xã
L_DIENTHOAI = "14DienThoaiLienHeNeuCo"              # 1.4. Điện thoại liên hệ (nếu có)
# Phần 2.1 — Tách thửa:
L_THUA_SO = "21TachThuaDatSo"                       # 2.1. Tách thửa đất số
L_TOBANDO = "ToBanDoSo"                             # trùng 2.2 → DOM đầu = tách
L_DIENTICH = "DienTich"                             # trùng 2.2 → DOM đầu = tách
L_LOAIDAT = "LoaiDat"                               # trùng thửa mới + 2.2 → DOM đầu = thửa gốc
L_DIACHITHUA = "DiaChiThuaDat"                      # trùng 2.2 → DOM đầu = tách
L_SOVAOSO = "GiayChungNhanSoVaoSoCapGCN"            # trùng 2.2 → DOM đầu = tách
L_NGAYCAP = "NgayCapGCN"                            # trùng 2.2 → DOM đầu = tách
L_THANH = "Thanh"                                   # "thành … thửa" (số thửa mới)
L_THUAMOI1 = "ThuaThuNhatDienTich"                  # Thửa thứ nhất: diện tích
L_THUAMOI2 = "ThuaThuHaiDienTich"                   # Thửa thứ hai: diện tích
# Loại đất thửa mới cũng mang class LoaiDat (trùng thửa gốc) → "Neo>Key": FE lấy ô LoaiDat ĐẦU TIÊN
# đứng SAU ô diện tích của thửa đó, không phụ thuộc thứ tự đếm.
L_THUAMOI1_LOAIDAT = "ThuaThuNhatDienTich>LoaiDat"
L_THUAMOI2_LOAIDAT = "ThuaThuHaiDienTich>LoaiDat"
L_THUAMOI_KHAC = "LietKeCacThuaDatTachThua"         # "(Liệt kê các thửa đất tách thửa)" — thửa thứ 3+
# Phần 3–5:
L_LYDO = "3LyDoTachHopThuaDat"
# Mục 4 không còn ô "Giấy tờ nộp kèm…": chỉ còn ô sau dòng in sẵn "- Giấy chứng nhận và Bản vẽ…"
# (class bị cổng cắt cụt ở "CacThuaDa").
L_GIAYTOKEM = "GiayChungNhanVaBanVeTachThuaDatHopThuaDatCacThuaDa"
L_DENGHIGCN = "5DeNghiCapGiayChungNhan"

# ---- UI: người nhận kết quả — khớp theo NAME cố định ----
N_HOTEN = "nhanTaiNhahoTen"
N_CCCD = "nhanTaiNhasoCCCD"
N_SDT = "nhanTaiNhasoDienThoai"
N_DIACHI = "nhanTaiNhadiaChi"
# Nhận KQ cũng tách Tỉnh/Xã là select (khớp theo NAME cố định); Xã cascade theo Tỉnh.
N_TINH = "nhanTaiNhatinhThanhId"
N_XA = "nhanTaiNhaphuongXaId"

_LABELS = [
    L_KINHGUI, L_TEN, L_GIAYTO, L_DIACHI, L_DIENTHOAI,
    L_THUA_SO, L_TOBANDO, L_DIENTICH, L_LOAIDAT, L_DIACHITHUA, L_SOVAOSO, L_NGAYCAP,
    L_THANH, L_THUAMOI1, L_THUAMOI1_LOAIDAT, L_THUAMOI2, L_THUAMOI2_LOAIDAT, L_THUAMOI_KHAC, L_LYDO, L_GIAYTOKEM, L_DENGHIGCN,
    N_HOTEN, N_CCCD, N_SDT, N_DIACHI,
]
UI_COMP_BY_NAME = {name: "bn-input" for name in _LABELS}
# Ô Tỉnh/Xã người nhận kết quả là <select> → comp bn-select.
for _s in (N_TINH, N_XA):
    UI_COMP_BY_NAME[_s] = "bn-select"
