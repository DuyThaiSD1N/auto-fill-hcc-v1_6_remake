"""Compact schema for "Đăng ký kết hôn".

The LLM returns OCR-derived facts from identity documents and the marriage
declaration. UI field names, duplicate identity fields, and deterministic
values are derived in Python.
"""

FIELDS: list[dict] = [
    # CCCD/CMND bên nam.
    {"name": "CccdNam_HoTen", "desc": "Họ tên trên CCCD/CMND có giới tính Nam."},
    {"name": "CccdNam_SoDinhDanh", "desc": "Số định danh/CCCD bên nam, 12 số; có thể đọc từ MRZ mặt sau."},
    {"name": "CccdNam_NgaySinh", "desc": "Ngày sinh bên nam trên CCCD/CMND, dd/mm/yyyy."},
    {"name": "CccdNam_NgayCap", "desc": "Ngày cấp CCCD/CMND bên nam, dd/mm/yyyy."},
    {"name": "CccdNam_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND bên nam từ mặt sau. Gần ngày cấp thường có '
             '"CỤC TRƯỞNG CỤC CẢNH SÁT..."; trả '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "CccdNam_DanToc", "desc": "Dân tộc BÊN NAM. CHỈ trả khi OCR có nhãn 'Dân tộc' ghi trực tiếp giá trị của đúng người trong tờ khai/giấy tờ khác; CCCD/Căn cước không ghi dân tộc. Không suy từ họ tên, địa chỉ, quê quán hay vùng miền; thiếu nhãn thì bỏ field."},
    {"name": "CccdNam_QuocTich", "desc": "Quốc tịch bên nam chỉ trả nếu giấy tờ ghi rõ hoặc khác Việt Nam."},
    {"name": "CccdNam_LoaiGiayTo",
     "desc": "Loại giấy tờ tùy thân bên nam — CHỈ điền khi là giấy tờ NƯỚC NGOÀI "
             "(vd 'Chứng minh thư', 'Hộ chiếu', 'Identity Card'). "
             "CCCD/Căn cước Việt Nam → BỎ QUA field này."},
    {"name": "CccdNam_NoiCuTru_TrongNuoc", "desc": "Địa chỉ cư trú trên CCCD bên nam, object {quocGia,tinh,xa,diaChi}; xa (phường/xã) BẮT BUỘC khi giấy có, chỉ lấy TÊN."},
    {"name": "CccdNam_SoLanKetHon", "desc": "Số lần kết hôn của BÊN NAM — CHỈ lấy nếu tờ khai có mục 'Kết hôn lần thứ mấy'/'Số lần kết hôn' ghi rõ số ở cột nam. Trả SỐ NGUYÊN (vd '1', '2'). Không có thì bỏ qua."},

    # CCCD/CMND bên nữ.
    {"name": "CccdNu_HoTen", "desc": "Họ tên trên CCCD/CMND có giới tính Nữ."},
    {"name": "CccdNu_SoDinhDanh", "desc": "Số định danh/CCCD bên nữ, 12 số; có thể đọc từ MRZ mặt sau."},
    {"name": "CccdNu_NgaySinh", "desc": "Ngày sinh bên nữ trên CCCD/CMND, dd/mm/yyyy."},
    {"name": "CccdNu_NgayCap", "desc": "Ngày cấp CCCD/CMND bên nữ, dd/mm/yyyy."},
    {"name": "CccdNu_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND bên nữ từ mặt sau. Gần ngày cấp thường có '
             '"CỤC TRƯỞNG CỤC CẢNH SÁT..."; trả '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "CccdNu_DanToc", "desc": "Dân tộc BÊN NỮ. CHỈ trả khi OCR có nhãn 'Dân tộc' ghi trực tiếp giá trị của đúng người trong tờ khai/giấy tờ khác; CCCD/Căn cước không ghi dân tộc. Không suy từ họ tên, địa chỉ, quê quán hay vùng miền; thiếu nhãn thì bỏ field."},
    {"name": "CccdNu_QuocTich", "desc": "Quốc tịch bên nữ chỉ trả nếu giấy tờ ghi rõ hoặc khác Việt Nam."},
    {"name": "CccdNu_LoaiGiayTo",
     "desc": "Loại giấy tờ tùy thân bên nữ — CHỈ điền khi là giấy tờ NƯỚC NGOÀI "
             "(vd 'Chứng minh thư', 'Hộ chiếu', 'Identity Card'). "
             "CCCD/Căn cước Việt Nam → BỎ QUA field này."},
    {"name": "CccdNu_NoiCuTru_TrongNuoc", "desc": "Địa chỉ cư trú trên CCCD bên nữ, object {quocGia,tinh,xa,diaChi}; xa (phường/xã) BẮT BUỘC khi giấy có, chỉ lấy TÊN."},
    {"name": "CccdNu_SoLanKetHon", "desc": "Số lần kết hôn của BÊN NỮ — CHỈ lấy nếu tờ khai có mục 'Kết hôn lần thứ mấy'/'Số lần kết hôn' ghi rõ số ở cột nữ. Trả SỐ NGUYÊN (vd '1', '2'). Không có thì bỏ qua."},

    # Tách nguồn tờ khai khỏi CCCD để mapper ưu tiên tất định, không phụ thuộc LLM tự chọn nguồn.
    {"name": "ToKhaiNam_NoiCuTru_TrongNuoc",
     "desc": "Nơi cư trú ở đúng cột BÊN NAM của TỜ KHAI ĐĂNG KÝ KẾT HÔN, "
             "object {quocGia,tinh,xa,diaChi}. CHỈ lấy từ tờ khai; không lấy CCCD, giấy xác nhận "
             "tình trạng hôn nhân, giấy phép lái xe hoặc giấy tờ phụ."},
    {"name": "ToKhaiNu_NoiCuTru_TrongNuoc",
     "desc": "Nơi cư trú ở đúng cột BÊN NỮ của TỜ KHAI ĐĂNG KÝ KẾT HÔN, "
             "object {quocGia,tinh,xa,diaChi}. CHỈ lấy từ tờ khai; không lấy CCCD, giấy xác nhận "
             "tình trạng hôn nhân, giấy phép lái xe hoặc giấy tờ phụ."},

    # Yêu cầu cấp bản sao trên chính tờ khai đăng ký kết hôn, không đặt mặc định.
    {"name": "CopyRequest_WantsCopy",
     "desc": '"Có" nếu TỜ KHAI ĐĂNG KÝ KẾT HÔN tích/chọn Có ở mục đề nghị cấp bản sao; '
             '"Không" nếu tích/chọn Không. Nếu tờ khai ghi số lượng bản sao dương thì trả "Có" '
             "kể cả dấu tick không rõ. Không có dấu chọn và không có số lượng thì bỏ field."},
    {"name": "CopyRequest_Quantity",
     "desc": "Số lượng bản sao ghi thật trên TỜ KHAI ĐĂNG KÝ KẾT HÔN, trả số nguyên dương "
             "(ví dụ 02 bản -> 2). Field này chỉ là bằng chứng suy ra yêu cầu cấp bản sao; "
             "không tự mặc định số lượng."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "CccdNam_NgaySinh",
    "CccdNam_NgayCap",
    "CccdNu_NgaySinh",
    "CccdNu_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "CccdNam_NoiCuTru_TrongNuoc",
    "CccdNu_NoiCuTru_TrongNuoc",
    "ToKhaiNam_NoiCuTru_TrongNuoc",
    "ToKhaiNu_NoiCuTru_TrongNuoc",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Bên nam.
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
    "NoiCuTru_BenNam_NuocNgoai": "x-select-area",
    "SoLanKetHon_BenNam": "raw",
    "LoaiTinhTrangHonNhan_BenNam": "x-select",
    # Bên nữ.
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
    "NoiCuTru_BenNu_NuocNgoai": "x-select-area",
    "SoLanKetHon_BenNu": "raw",
    "LoaiTinhTrangHonNhan_BenNu": "x-select",
    # Chung cả form (radio ở cuối tờ khai) — option khớp theo suffix id: loaiDangKy-1 =
    # "Đăng ký lần đầu"; CapBanSao-YES/-NO = "Có"/"Không".
    "loaiDangKy": "x-radio",
    "CapBanSao": "x-radio",
    "SoLuong": "raw",
}

# Field ĐÁNG rà soát bbox (name → nhãn hiển thị). CHỈ các ô đọc TỪ GIẤY TỜ, có thể khoanh
# vùng trên ảnh: họ tên, số định danh, ngày sinh/cấp, và NƠI CƯ TRÚ (x-select-area → tách
# tỉnh/xã/địa chỉ ở service). BỎ QUA: loại giấy tờ, quốc tịch, loại cư trú, radio "nơi cư trú"=1,
# số lần kết hôn, tình trạng hôn nhân (giá trị suy diễn/hằng số, không nằm trên giấy tờ).
REVIEW_FIELDS = {
    # Bên nam
    "HoTenBenNam": "Họ tên chồng",
    "SoDinhDanh_BenNam": "Số định danh chồng",
    "LoaiGiayToDinhDanh_BenNam": "Loại giấy tờ chồng",
    "SoGiayToDinhDanh_BenNam": "Số giấy tờ chồng",
    "NgaySinhBenNam": "Ngày sinh chồng",
    "DanTocBenNam": "Dân tộc chồng",
    "NgayCapDD_BenNam": "Ngày cấp CCCD chồng",
    "NoiCapDD_BenNam": "Nơi cấp CCCD chồng",
    "NoiCuTru_BenNam_TrongNuoc": "Nơi cư trú chồng",
    "SoLanKetHon_BenNam": "Số lần kết hôn chồng",
    # Bên nữ
    "HoTenBenNu": "Họ tên vợ",
    "SoDinhDanh_BenNu": "Số định danh vợ",
    "LoaiGiayToDinhDanh_BenNu": "Loại giấy tờ vợ",
    "SoGiayToDinhDanh_BenNu": "Số giấy tờ vợ",
    "NgaySinhBenNu": "Ngày sinh vợ",
    "DanTocBenNu": "Dân tộc vợ",
    "NgayCapDD_BenNu": "Ngày cấp CCCD vợ",
    "NoiCapDD_BenNu": "Nơi cấp CCCD vợ",
    "NoiCuTru_BenNu_TrongNuoc": "Nơi cư trú vợ",
    "SoLanKetHon_BenNu": "Số lần kết hôn vợ",
}
