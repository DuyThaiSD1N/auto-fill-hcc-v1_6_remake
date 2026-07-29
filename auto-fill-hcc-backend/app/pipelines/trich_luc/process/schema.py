"""Compact schema for "Cấp bản sao Giấy khai sinh, bản sao Trích lục hộ tịch".

The LLM returns only OCR-derived facts. UI defaults, duplicate identity fields,
and form-specific components are derived in Python.
"""

FIELDS: list[dict] = [
    # CCCD/CMND đính kèm (có thể là của người yêu cầu HOẶC của người được đăng ký).
    {"name": "Cccd_HoTen", "desc": "Họ tên trên CCCD/CMND."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD/CMND; có thể đọc từ MRZ mặt sau."},
    {"name": "Cccd_NgaySinh", "desc": "Ngày sinh trên CCCD/CMND, dd/mm/yyyy."},
    {"name": "Cccd_GioiTinh", "desc": 'Giới tính trên CCCD/CMND: "Nam" hoặc "Nữ".'},
    {"name": "Cccd_NgayCap", "desc": "Ngày cấp CCCD/CMND, dd/mm/yyyy."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND từ mặt sau. Gần ngày cấp thường có '
             '"CỤC TRƯỞNG CỤC CẢNH SÁT..."; trả '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "Cccd_NoiCuTru", "desc": "Địa chỉ cư trú/thường trú trên CCCD, object {quocGia,tinh,xa,diaChi}."},

    # Giấy tờ hộ tịch đã đăng ký trước đây: khai sinh/kết hôn/khai tử.
    {"name": "HoTich_LoaiSuKien",
     "desc": 'Loại sự kiện hộ tịch của giấy tờ chính: "birth", "marriage" hoặc "death".'},
    {"name": "HoTich_TenGiayTo",
     "desc": "Tên giấy tờ hộ tịch theo OCR, ví dụ Giấy khai sinh, Giấy chứng nhận kết hôn, Trích lục khai tử."},
    {"name": "HoTich_HoTenNguoiDuocDangKy",
     "desc": "Họ tên người được đăng ký trong giấy tờ hộ tịch; riêng giấy kết hôn lấy người chồng/bên nam."},
    {"name": "HoTich_NgaySinh", "desc": "Ngày sinh người được đăng ký nếu giấy tờ có ghi, dd/mm/yyyy."},
    {"name": "HoTich_GioiTinh", "desc": 'Giới tính người được đăng ký nếu giấy tờ có ghi: "Nam" hoặc "Nữ".'},
    {"name": "HoTich_DanToc", "desc": "Dân tộc người được đăng ký nếu giấy tờ có ghi."},
    {"name": "HoTich_QuocTich", "desc": "Quốc tịch người được đăng ký nếu giấy tờ có ghi hoặc khác Việt Nam."},
    {"name": "HoTich_SoDinhDanh", "desc": "Số định danh cá nhân của người được đăng ký nếu giấy tờ có ghi."},
    {"name": "HoTich_LoaiGiayToTuyThan",
     "desc": "Loại giấy tờ tùy thân của người được đăng ký nếu giấy tờ hộ tịch có ghi; riêng giấy kết hôn lấy của chồng/bên nam."},
    {"name": "HoTich_SoGiayToTuyThan",
     "desc": "Số giấy tờ tùy thân của người được đăng ký nếu giấy tờ hộ tịch có ghi; riêng giấy kết hôn lấy của chồng/bên nam."},
    {"name": "HoTich_NgayCapGiayToTuyThan",
     "desc": "Ngày cấp giấy tờ tùy thân của người được đăng ký, dd/mm/yyyy; riêng giấy kết hôn lấy của chồng/bên nam."},
    {"name": "HoTich_NoiCapGiayToTuyThan",
     "desc": "Cơ quan cấp giấy tờ tùy thân của người được đăng ký; riêng giấy kết hôn lấy của chồng/bên nam."},

    # Giấy tờ tùy thân RIÊNG của CHÍNH người được đăng ký, lấy từ CCCD/Thẻ căn cước CỦA HỌ
    # (tách biệt CCCD người yêu cầu). Vd mẹ đi làm bản sao khai sinh cho con nhưng con ĐÃ có thẻ căn cước.
    {"name": "ChuThe_LoaiGiayToTuyThan",
     "desc": "Loại giấy tờ tùy thân (Căn cước công dân/Căn cước/CMND/Hộ chiếu) trên CCCD/thẻ căn cước CỦA CHÍNH người được đăng ký, khi hồ sơ có thẻ đó (tên/số định danh trùng người được đăng ký)."},
    {"name": "ChuThe_SoGiayToTuyThan",
     "desc": "Số CCCD/thẻ căn cước của CHÍNH người được đăng ký (trùng tên/số định danh của người được đăng ký)."},
    {"name": "ChuThe_NgayCapGiayToTuyThan",
     "desc": "Ngày cấp CCCD/thẻ căn cước của chính người được đăng ký, dd/mm/yyyy (đọc mặt sau/ngày cấp)."},
    {"name": "ChuThe_NoiCapGiayToTuyThan",
     "desc": 'Nơi cấp CCCD/thẻ căn cước của chính người được đăng ký. Thẻ CĂN CƯỚC mới ("BỘ CÔNG AN") → "Bộ Công an"; CCCD cũ → "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},

    {"name": "HoTich_NoiCuTru",
     "desc": "Nơi cư trú của người được đăng ký nếu giấy tờ có ghi, object {quocGia,tinh,xa,diaChi}; "
             "riêng giấy kết hôn lấy nơi cư trú của người chồng/bên nam. Địa chỉ ghi Phường 3, Đà Lạt, "
             "Lâm Đồng thì chuẩn hóa xa='Phường Xuân Hương'."},
    {"name": "HoTich_CoQuanDangKy", "desc": "Cơ quan đã đăng ký sự kiện hộ tịch trước đây."},
    {"name": "HoTich_So", "desc": "Số giấy tờ/số đăng ký/số trích lục của giấy tờ hộ tịch."},
    {"name": "HoTich_QuyenSo",
     "desc": "Quyển số đăng ký hộ tịch, CHỈ trả khi nhãn 'Quyển số'/'Quyển' có giá trị ghi rõ ngay sau nhãn. "
             "Không lấy 'số bộ', 'sổ bộ', 'bộ số', 'số hiệu' hoặc HoTich_So làm quyển số."},
    {"name": "HoTich_NgayDangKy", "desc": "Ngày đăng ký sự kiện hộ tịch trước đây, dd/mm/yyyy. Ưu tiên đọc ở TỜ KHAI (cụm 'Đã đăng ký tại ... ngày D tháng M năm Y số ...'), sau đó tới giấy khai sinh/trích lục. BẮT BUỘC điền nếu đọc được (xem field_rules)."},

    # Yêu cầu cấp bản sao trên tờ khai/tài liệu yêu cầu.
    {"name": "CopyRequest_Quantity",
     "desc": "Số lượng bản sao được yêu cầu, chỉ trả số nguyên dương khi tờ khai/tài liệu yêu cầu ghi rõ. "
             "Không tự mặc định là 3 hoặc bất kỳ số nào khác."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Cccd_NgaySinh", "Cccd_NgayCap", "HoTich_NgaySinh", "HoTich_NgayDangKy",
              "HoTich_NgayCapGiayToTuyThan", "ChuThe_NgayCapGiayToTuyThan"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd_NoiCuTru", "HoTich_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Người yêu cầu.
    "HoVaTenC": "x-input",
    "SoDinhDanhC": "x-input",
    "LoaiGiayToDinhDanhC": "x-select",
    # raw works for both a bare input and an input wrapped by x-input.
    "NYC_SoGiayToTuyThan": "raw",
    "NgayCapDDC": "x-date",
    "NoiCapDDC": "x-input",
    "NYC_LoaiCuTru": "x-select",
    "NYC_NoiCuTru": "x-radio",
    "NYC_NoiCuTru_TrongNuoc": "x-select-area",
    # Người được khai sinh.
    "NDK_HoVaTen": "x-input",
    "NDK_NgaySinh": "x-date-text",
    "NDK_GioiTinh": "x-select",
    "NDK_DanToc": "x-select",
    "NDK_QuocTich": "x-select",
    "NDK_SoDinhDanh": "x-input",
    "NDK_LoaiGiayToTuyThan": "x-select",
    "NDK_SoGiayToTuyThan": "x-input",
    "NDK_NgayCap": "x-date",
    "NDK_NoiCap": "x-input",
    "NDK_LoaiCuTru": "x-select",
    "NDK_NoiCuTru": "x-radio",
    "NDK_NoiCuTru_TrongNuoc": "x-select-area",
    # Hồ sơ đăng ký trước đây.
    "HoSo_LoaiYeuCau": "x-select",
    "HoSo_CoQuanDangKy": "x-input",
    "HoSo_TenGiayTo": "x-input",
    "HoSo_So": "x-input",
    "HoSo_QuyenSo": "x-input",
    "HoSo_NgayCapSo": "x-date",
    "PhuongThucNhanKQ": "x-radio",
    # Số lượng bản sao đọc từ tờ khai; form không có radio Có/Không.
    "SoLuong": "raw",
}

UI_ALIASES = {
    "HoVaTenC": ["NYC_HoVaTen"],
    "SoDinhDanhC": ["NYC_SoDinhDanh"],
    "LoaiGiayToDinhDanhC": ["NYC_LoaiGiayToTuyThan"],
    "NYC_SoGiayToTuyThan": ["SoGiayToDinhDanhC"],
    "NgayCapDDC": ["NYC_NgayCap"],
    "NoiCapDDC": ["NYC_NoiCap"],
}


# Field ĐÁNG rà soát bbox (name → nhãn). Đọc từ CCCD người yêu cầu + giấy tờ hộ tịch (khai sinh cũ...)
# của người được đăng ký. Địa chỉ x-select-area tách tỉnh/xã/địa chỉ ở service. BỎ QUA: quốc tịch,
# loại cư trú, radio và phương thức nhận.
REVIEW_FIELDS = {
    # Người được đăng ký (chủ thể hộ tịch)
    "NDK_HoVaTen": "Họ tên người được đăng ký",
    "NDK_NgaySinh": "Ngày sinh người được đăng ký",
    "NDK_GioiTinh": "Giới tính người được đăng ký",
    "NDK_DanToc": "Dân tộc người được đăng ký",
    "NDK_SoDinhDanh": "Số định danh người được đăng ký",
    "NDK_LoaiGiayToTuyThan": "Loại giấy tờ người được đăng ký",
    "NDK_SoGiayToTuyThan": "Số giấy tờ người được đăng ký",
    "NDK_NgayCap": "Ngày cấp CCCD người được đăng ký",
    "NDK_NoiCap": "Nơi cấp CCCD người được đăng ký",
    "NDK_NoiCuTru_TrongNuoc": "Nơi cư trú người được đăng ký",
    # Giấy tờ hộ tịch gốc (khai sinh cũ...)
    "HoSo_TenGiayTo": "Tên giấy tờ hộ tịch",
    "HoSo_CoQuanDangKy": "Cơ quan đăng ký",
    "HoSo_So": "Số",
    "HoSo_QuyenSo": "Quyển số",
    "HoSo_NgayCapSo": "Ngày đăng ký",
    # Người yêu cầu
    "HoVaTenC": "Họ tên người yêu cầu",
    "SoDinhDanhC": "Số định danh người yêu cầu",
    "LoaiGiayToDinhDanhC": "Loại giấy tờ người yêu cầu",
    "NYC_SoGiayToTuyThan": "Số giấy tờ người yêu cầu",
    "NgayCapDDC": "Ngày cấp CCCD người yêu cầu",
    "NoiCapDDC": "Nơi cấp CCCD người yêu cầu",
    "NYC_NoiCuTru_TrongNuoc": "Nơi cư trú người yêu cầu",
}
