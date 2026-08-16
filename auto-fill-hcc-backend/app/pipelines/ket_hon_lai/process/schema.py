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

    # Lần đăng ký kết hôn TRƯỚC ĐÂY. Chỉ đọc từ tờ khai đăng ký lại hoặc giấy CN kết hôn cũ.
    {"name": "KetHonCu_So",
     "desc": "Số Giấy chứng nhận kết hôn/Số đăng ký kết hôn trước đây. Chỉ lấy khi GIẤY CHỨNG NHẬN KẾT HÔN cũ "
             "hoặc TỜ KHAI ĐĂNG KÝ LẠI KẾT HÔN ghi rõ giá trị; ưu tiên giấy chứng nhận cũ. Không lấy số/quyển/ngày từ giấy khai sinh, "
             "CCCD hay giấy tờ khác. Dòng nhãn có chỗ trống hoặc OCR không rõ thì bỏ field."},
    {"name": "KetHonCu_QuyenSo",
     "desc": "Quyển số đăng ký kết hôn trước đây. Chỉ lấy giá trị ghi rõ ngay sau nhãn 'Quyển số' trên giấy chứng nhận "
             "kết hôn cũ hoặc tờ khai đăng ký lại; ưu tiên giấy chứng nhận cũ. Không tự tính từ số đăng ký. Trống/không rõ thì bỏ field."},
    {"name": "KetHonCu_NgayDangKy",
     "desc": "Ngày đăng ký kết hôn trước đây, dd/mm/yyyy. Ưu tiên ngày đăng ký trên GIẤY CHỨNG NHẬN KẾT HÔN cũ; "
             "nếu giấy cũ không rõ thì lấy dòng 'Đã đăng ký kết hôn tại ... ngày ... tháng ... năm ...' trên tờ khai đăng ký lại. "
             "Không lấy ngày đăng ký khai sinh, ngày cấp CCCD hoặc ngày lập tờ khai."},
    {"name": "KetHonCu_TinhDangKy",
     "desc": "Tỉnh/thành phố của cơ quan đăng ký kết hôn trước đây. Chỉ lấy từ cơ quan trên giấy chứng nhận kết hôn cũ "
             "hoặc mục 'Đã đăng ký kết hôn tại' trên tờ khai đăng ký lại; ưu tiên giấy chứng nhận cũ. Không rõ thì bỏ field."},
    {"name": "KetHonCu_XaDangKy",
     "desc": "Tên PHƯỜNG/XÃ/THỊ TRẤN đăng ký kết hôn trước đây, giữ tiền tố đơn vị và bỏ 'UBND'. Chỉ lấy từ cơ quan "
             "trên giấy chứng nhận kết hôn cũ hoặc mục 'Đã đăng ký kết hôn tại' trên tờ khai đăng ký lại; ưu tiên giấy "
             "chứng nhận cũ. Không lấy 'Nơi đăng ký' của giấy khai sinh; không rõ thì bỏ field."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("CccdNam_NgaySinh", "CccdNam_NgayCap", "CccdNu_NgaySinh", "CccdNu_NgayCap", "KetHonCu_NgayDangKy"):
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
