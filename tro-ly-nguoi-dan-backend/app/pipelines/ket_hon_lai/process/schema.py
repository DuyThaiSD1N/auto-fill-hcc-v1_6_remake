"""Compact schema cho "Đăng ký lại kết hôn".

LLM chỉ trả sự thật OCR: cặp CCCD nam/nữ + metadata hồ sơ gốc (giấy CN kết hôn cũ).
Tên field UI, field trùng lặp và các mặc định tất định được suy trong Python (mapper).
"""

FIELDS: list[dict] = [
    # CCCD/CMND bên nam (chồng).
    {"name": "CccdNam_HoTen", "desc": "Họ tên trên CCCD/CMND có giới tính Nam (nếu thiếu CCCD nam thì lấy 'Chồng' trên giấy CN kết hôn)."},
    {"name": "CccdNam_SoDinhDanh", "desc": "Số định danh/CCCD bên nam, 12 số; đọc MRZ mặt sau hoặc 'Số thẻ căn cước công dân' của chồng trên giấy CN kết hôn."},
    {"name": "CccdNam_NgaySinh", "desc": "Ngày sinh bên nam, dd/mm/yyyy."},
    {"name": "CccdNam_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân bên nam, dd/mm/yyyy."},
    {"name": "CccdNam_NoiCap",
     "desc": 'Nơi cấp giấy tờ tùy thân bên nam. Thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → trả "Bộ Công an"; '
             'chip cũ ghi "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "CccdNam_DanToc", "desc": "Dân tộc BÊN NAM. CCCD chip thường không ghi → lấy từ giấy CN kết hôn/tờ khai, đối chiếu đúng người. Không có thì để trống."},
    {"name": "CccdNam_QuocTich", "desc": "Quốc tịch bên nam chỉ trả nếu giấy tờ ghi rõ hoặc khác Việt Nam."},
    {"name": "CccdNam_NoiCuTru_TrongNuoc", "desc": "Nơi cư trú bên nam, object {quocGia,tinh,xa,diaChi}."},

    # CCCD/CMND bên nữ (vợ).
    {"name": "CccdNu_HoTen", "desc": "Họ tên trên CCCD/CMND có giới tính Nữ (nếu thiếu CCCD nữ thì lấy 'Vợ' trên giấy CN kết hôn)."},
    {"name": "CccdNu_SoDinhDanh", "desc": "Số định danh/CCCD bên nữ, 12 số; đọc MRZ mặt sau hoặc 'Số thẻ căn cước công dân' của vợ trên giấy CN kết hôn."},
    {"name": "CccdNu_NgaySinh", "desc": "Ngày sinh bên nữ, dd/mm/yyyy."},
    {"name": "CccdNu_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân bên nữ, dd/mm/yyyy."},
    {"name": "CccdNu_NoiCap",
     "desc": 'Nơi cấp giấy tờ tùy thân bên nữ. Thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" → trả "Bộ Công an"; '
             'chip cũ ghi "CỤC TRƯỞNG CỤC CẢNH SÁT..." → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "CccdNu_DanToc", "desc": "Dân tộc BÊN NỮ. CCCD chip thường không ghi → lấy từ giấy CN kết hôn/tờ khai, đối chiếu đúng người. Không có thì để trống."},
    {"name": "CccdNu_QuocTich", "desc": "Quốc tịch bên nữ chỉ trả nếu giấy tờ ghi rõ hoặc khác Việt Nam."},
    {"name": "CccdNu_NoiCuTru_TrongNuoc", "desc": "Nơi cư trú bên nữ, object {quocGia,tinh,xa,diaChi}."},

    # Hồ sơ gốc: lần đăng ký kết hôn TRƯỚC ĐÂY (từ giấy CN kết hôn cũ bản sao).
    {"name": "HoTich_So",
     "desc": 'Số đăng ký kết hôn trước đây — thường ở GÓC TRÊN giấy CN kết hôn, dạng "NN/YYYY" (vd 40/2026) hoặc "NN".'},
    {"name": "HoTich_NgayDangKy", "desc": "Ngày đăng ký kết hôn trước đây, dd/mm/yyyy."},
    {"name": "HoTich_TinhDangKy", "desc": "Tỉnh/thành phố của cơ quan đăng ký kết hôn trước đây (để lọc dropdown), vd Lai Châu."},
    {"name": "HoTich_XaDangKy",
     "desc": "Tên đơn vị hành chính PHƯỜNG/XÃ/THỊ TRẤN nơi đăng ký kết hôn trước đây, GIỮ tiền tố loại đơn vị. "
             "Nơi đăng ký thường ghi 'UBND phường/xã <X>, tỉnh <Y>' → trả '<Phường/Xã> <X>' "
             "(BỎ 'UBND' và phần ', tỉnh <Y>'). Vd 'UBND phường Đoàn Kết, tỉnh Lai Châu' → 'Phường Đoàn Kết'."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("CccdNam_NgaySinh", "CccdNam_NgayCap", "CccdNu_NgaySinh", "CccdNu_NgayCap", "HoTich_NgayDangKy"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("CccdNam_NoiCuTru_TrongNuoc", "CccdNu_NoiCuTru_TrongNuoc"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Bên nam (chồng).
    "HoTenBenNam": "x-input",
    "SoDinhDanh_BenNam": "x-input",
    "SoGiayToDinhDanh_BenNam": "x-input",
    "LoaiGiayToDinhDanh_BenNam": "x-select",
    "NgaySinhBenNam": "x-date",
    "NgayCapDD_BenNam": "x-date",
    "NoiCapDD_BenNam": "x-input",
    "DanTocBenNam": "x-select",
    "QuocTichBenNam": "x-select",
    "LoaiCuTru_BenNam": "x-select",
    "NoiCuTru_BenNam": "x-radio",
    "NoiCuTru_BenNam_TrongNuoc": "x-select-area",
    "SoLanKetHon_BenNam": "x-input-number",
    "LoaiTinhTrangHonNhan_BenNam": "x-select",
    # Bên nữ (vợ).
    "HoTenBenNu": "x-input",
    "SoDinhDanh_BenNu": "x-input",
    "SoGiayToDinhDanh_BenNu": "x-input",
    "LoaiGiayToDinhDanh_BenNu": "x-select",
    "NgaySinhBenNu": "x-date",
    "NgayCapDD_BenNu": "x-date",
    "NoiCapDD_BenNu": "x-input",
    "DanTocBenNu": "x-select",
    "QuocTichBenNu": "x-select",
    "LoaiCuTru_BenNu": "x-select",
    "NoiCuTru_BenNu": "x-radio",
    "NoiCuTru_BenNu_TrongNuoc": "x-select-area",
    "SoLanKetHon_BenNu": "x-input-number",
    "LoaiTinhTrangHonNhan_BenNu": "x-select",
    # Hồ sơ gốc (đăng ký lại).
    "loaiDangKy": "x-radio",
    "soDangKyTruocDay": "x-input",
    "quyenDangKyTruocDay": "x-input",
    "ngayDangKyTruocDay": "x-date",
    "noiDangKyTruocDay_filter": "x-select",  # dropdown tỉnh/thành (lọc trước)
    "noiDangKyTruocDay": "x-select",          # dropdown đơn vị (load theo filter)
    # Khác.
    "CapBanSao": "x-radio",
    # SoLuong: ô số lượng bản sao (input trần, hiện khi chọn "Có").
    "SoLuong": "raw",
}
