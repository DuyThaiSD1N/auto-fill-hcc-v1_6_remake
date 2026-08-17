"""Field đích cho thủ tục "Đăng ký lại khai sinh" — FORM CŨ (web-component x-*).

Tái dùng đúng tên field + comp của mapping cũ. Người yêu cầu = CHA. Con + đăng ký trước đây
lấy từ GIẤY KHAI SINH CŨ (GKS). Comp: x-input | x-select | x-date | x-date-text | x-radio |
x-select-area | x-select-default.
"""

FIELDS: list[dict] = [
    # ===== I. Người yêu cầu = CHA (suffix C) =====
    {"name": "HoVaTenC", "comp": "x-input", "desc": "Họ tên người yêu cầu = họ tên CHA."},
    {"name": "SoDinhDanhC", "comp": "x-input", "desc": "Số định danh người yêu cầu = số định danh CHA."},
    {"name": "SoGiayToDinhDanhC", "comp": "x-input", "desc": "Số giấy tờ người yêu cầu = số định danh CHA."},
    {"name": "LoaiGiayToDinhDanhC", "comp": "x-select", "desc": 'Loại giấy tờ người yêu cầu. Mặc định "Căn cước công dân".'},
    {"name": "NgayCapDDC", "comp": "x-date", "desc": "Ngày cấp CCCD của CHA (dd/mm/yyyy)."},
    {"name": "NoiCapDDC", "comp": "x-input", "desc": "Nơi cấp CCCD của CHA."},
    {"name": "nycLoaiCuTru", "comp": "x-select", "desc": 'Loại cư trú người yêu cầu. Mặc định "Thường trú".'},
    {"name": "nycNoiCuTru", "comp": "x-radio", "desc": 'Nơi cư trú người yêu cầu trong/ngoài nước. Trong nước → "1".'},
    {"name": "nycNoiCuTru_TrongNuoc", "comp": "x-select-area", "desc": "Địa chỉ cư trú người yêu cầu (theo CCCD cha)."},

    # ===== Cha (suffix Cha) =====
    {"name": "HoTenChaKS", "comp": "x-input", "desc": "Họ tên cha."},
    {"name": "SoDinhDanhCha", "comp": "x-input", "desc": "Số định danh cha (12 số; có thể đọc từ MRZ mặt sau)."},
    {"name": "SoGiayToDinhDanhCha", "comp": "x-input", "desc": "Số giấy tờ cha = số định danh cha."},
    {"name": "LoaiGiayToDinhDanhCha", "comp": "x-select", "desc": 'Loại giấy tờ cha. Mặc định "Căn cước công dân".'},
    {"name": "NgayCapDDCha", "comp": "x-date", "desc": "Ngày cấp CCCD cha."},
    {"name": "NoiCapDDCha", "comp": "x-input", "desc": "Nơi cấp CCCD cha."},
    {"name": "NamSinhChaKS", "comp": "x-date-text", "desc": "Ngày sinh cha (dd/mm/yyyy)."},
    {"name": "DanTocChaKS", "comp": "x-select", "desc": "Dân tộc cha — CHỈ nếu CCCD/giấy tờ ghi rõ; không có → để trống (không bịa)."},
    {"name": "QuocTichChaKS", "comp": "x-select", "desc": 'Quốc tịch cha. Mặc định "Việt Nam".'},
    {"name": "ChaLoaiCuTru", "comp": "x-select", "desc": 'Loại cư trú cha. Mặc định "Thường trú".'},
    {"name": "ChaNoiCuTru", "comp": "x-radio", "desc": 'Nơi cư trú cha. Trong nước → "1".'},
    {"name": "ChaNoiCuTru_TrongNuoc", "comp": "x-select-area", "desc": "Địa chỉ cư trú cha."},

    # ===== Mẹ (suffix Me) =====
    {"name": "HoTenMeKS", "comp": "x-input", "desc": "Họ tên mẹ."},
    {"name": "SoDinhDanhMe", "comp": "x-input", "desc": "Số định danh mẹ (12 số; có thể đọc từ MRZ mặt sau)."},
    {"name": "SoGiayToDinhDanhMe", "comp": "x-input", "desc": "Số giấy tờ mẹ = số định danh mẹ."},
    {"name": "LoaiGiayToDinhDanhMe", "comp": "x-select", "desc": 'Loại giấy tờ mẹ. Mặc định "Căn cước công dân".'},
    {"name": "NgayCapDDMe", "comp": "x-date", "desc": "Ngày cấp CCCD mẹ."},
    {"name": "NoiCapDDMe", "comp": "x-input", "desc": "Nơi cấp CCCD mẹ."},
    {"name": "NamSinhMeKS", "comp": "x-date-text", "desc": "Ngày sinh mẹ (dd/mm/yyyy)."},
    {"name": "DanTocMeKS", "comp": "x-select", "desc": "Dân tộc mẹ — CHỈ nếu CCCD/giấy tờ ghi rõ; không có → để trống (không bịa)."},
    {"name": "QuocTichMeKS", "comp": "x-select", "desc": 'Quốc tịch mẹ. Mặc định "Việt Nam".'},
    {"name": "MeLoaiCuTru", "comp": "x-select", "desc": 'Loại cư trú mẹ. Mặc định "Thường trú".'},
    {"name": "MeNoiCuTru", "comp": "x-radio", "desc": 'Nơi cư trú mẹ. Trong nước → "1".'},
    {"name": "MeNoiCuTru_TrongNuoc", "comp": "x-select-area", "desc": "Địa chỉ cư trú mẹ."},

    # ===== II. Người được khai sinh (CON) — từ GIẤY KHAI SINH CŨ =====
    {"name": "HoTenKS", "comp": "x-input", "desc": "Họ tên đầy đủ của con (trên giấy khai sinh cũ)."},
    {"name": "NgaySinhChon", "comp": "x-date", "desc": "Ngày sinh con (dd/mm/yyyy)."},
    {"name": "GioiTinhKS", "comp": "x-select", "desc": 'Giới tính con: "Nam"/"Nữ".'},
    {"name": "DanTocKS", "comp": "x-select", "desc": "Dân tộc con."},
    {"name": "QuocTichKS", "comp": "x-select", "desc": 'Quốc tịch con. Mặc định "Việt Nam".'},
    {"name": "nksNoiSinh", "comp": "x-radio", "desc": 'Nơi sinh con trong/ngoài nước. Trong nước → "1".'},
    {"name": "nksNoiSinh_TrongNuoc", "comp": "x-select-area", "desc": "Nơi sinh của con (trên giấy khai sinh cũ)."},
    {"name": "nksQueQuan", "comp": "x-radio", "desc": 'Quê quán con trong/ngoài nước. Trong nước → "1".'},
    {"name": "nksQueQuan_TrongNuoc", "comp": "x-select-area", "desc": "Quê quán con (trên giấy khai sinh cũ)."},

    # ===== Thông tin đăng ký khai sinh TRƯỚC ĐÂY (trên GKS cũ) =====
    {"name": "coQuanDKTruocDay_filter", "comp": "x-select",
     "desc": "Tỉnh/Thành phố của cơ quan đăng ký khai sinh trước đây = phần TỈNH trong "
             "'Nơi đăng ký khai sinh' trên giấy khai sinh cũ (vd 'Lai Châu')."},
    {"name": "soDKTruocDay", "comp": "x-input", "desc": "Số đăng ký khai sinh trước đây."},
    {"name": "quyenSoDKTruocDay", "comp": "x-input", "desc": "Quyển số đăng ký khai sinh trước đây."},
    {"name": "ngayDKTruocDay", "comp": "x-date-text", "desc": "Ngày đăng ký khai sinh trước đây (dd/mm/yyyy)."},
]

EXTRA_RULES = """Đầu vào: CCCD/CMND của CHA, CCCD/CMND của MẸ, và GIẤY KHAI SINH CŨ/bản chính của con.

NGUỒN DỮ LIỆU (QUAN TRỌNG NHẤT):
- CHA = người trên CCCD giới tính "Nam"; MẸ = CCCD giới tính "Nữ". Dùng "Họ tên cha"/"Họ tên mẹ" \
trên giấy khai sinh cũ CHỈ để ĐỐI CHIẾU xác định CCCD nào là cha / CCCD nào là mẹ.
- Thông tin CHA và MẸ (họ tên, ngày sinh, số định danh, ngày cấp, nơi cấp, dân tộc, quốc tịch, nơi cư trú) \
BẮT BUỘC LẤY TỪ CCCD của cha/mẹ — TUYỆT ĐỐI KHÔNG lấy từ giấy khai sinh cũ. Mỗi nhóm field cha lấy TRỌN VẸN \
từ MỘT CCCD (cùng một người), nhóm mẹ từ MỘT CCCD; KHÔNG trộn số định danh của người này với tên người khác. \
Nếu không có CCCD khớp cha/mẹ → để TRỐNG nhóm đó (đừng lấy tên từ GKS).
- NGƯỜI YÊU CẦU MẶC ĐỊNH LÀ CHA: nhóm field hậu tố C (HoVaTenC, SoDinhDanhC, NgayCapDDC, NoiCapDDC, \
nycNoiCuTru_TrongNuoc...) lấy từ CHÍNH CCCD của CHA (trùng với nhóm Cha).
- CON (người được khai sinh) là TRẺ → thông tin con (HoTenKS, NgaySinhChon, GioiTinhKS, DanTocKS, \
nơi sinh, quê quán) CHỈ lấy từ GIẤY KHAI SINH CŨ.
- Khối "đăng ký trước đây" (soDKTruocDay, quyenSoDKTruocDay, ngayDKTruocDay) lấy từ thông tin đăng ký \
ghi trên giấy khai sinh cũ. coQuanDKTruocDay_filter = phần TỈNH trong "Nơi đăng ký khai sinh" \
(vd "UBND Xã ..., huyện ..., tỉnh Lai Châu" → "Lai Châu").

DÂN TỘC cha/mẹ (DanTocChaKS, DanTocMeKS): CCCD gắn chip KHÔNG in dân tộc. Chỉ điền nếu giấy tờ của \
cha/mẹ GHI RÕ dân tộc; nếu không có → ĐỂ TRỐNG (bỏ field). TUYỆT ĐỐI KHÔNG suy đoán/bịa (đừng tự điền \
"Tày"/"Kinh"...). KHÔNG lấy dân tộc của con (trên GKS) gán cho cha/mẹ.

Mặc định: mọi loại giấy tờ = "Căn cước công dân"; mọi *QuocTich* = "Việt Nam" nếu không ghi; \
mọi *LoaiCuTru = "Thường trú"; radio nơi cư trú/nơi sinh/quê quán ở Việt Nam = "1". \
(Dân tộc KHÔNG có giá trị mặc định — xem quy tắc trên.)
HoTenKS giữ NGUYÊN cả cụm (không tách). Giữ hoa/dấu OCR đọc được."""

ALLOWED = {f["name"]: f["comp"] for f in FIELDS}
ALIASES: dict = {}

# Field mặc định cố định (không phụ thuộc giấy tờ).
STATIC_DEFAULTS: list[dict] = [
    {"name": "QuanHe", "comp": "x-radio", "value": "ChaDe"},  # Người yêu cầu là cha
    {"name": "LoaiDangKy", "comp": "x-radio", "value": "2"},  # Đăng ký lại
    {"name": "nksLoaiKhaiSinh", "comp": "x-select-default", "value": "Đã xác định được cả cha lẫn mẹ"},
]
