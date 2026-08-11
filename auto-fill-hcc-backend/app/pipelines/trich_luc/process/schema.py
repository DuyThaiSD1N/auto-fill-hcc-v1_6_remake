"""Compact schema for "Cấp bản sao Giấy khai sinh, bản sao Trích lục hộ tịch".

The LLM returns only OCR-derived facts. UI defaults, duplicate identity fields,
and form-specific components are derived in Python.
"""

FIELDS: list[dict] = [
    # CCCD/CMND RIÊNG của NGƯỜI YÊU CẦU, phải khớp mỏ neo formContext khi mỏ neo có mặt.
    {"name": "Nyc_HoTen", "desc": "Họ tên trên CCCD/CMND của người yêu cầu."},
    {"name": "Nyc_SoDinhDanh",
     "desc": "Số định danh/CCCD/CMND của người yêu cầu; có thể đọc từ MRZ mặt sau."},
    {"name": "Nyc_NgaySinh", "desc": "Ngày sinh trên CCCD/CMND của người yêu cầu, dd/mm/yyyy."},
    {"name": "Nyc_GioiTinh", "desc": 'Giới tính người yêu cầu trên CCCD/CMND: "Nam" hoặc "Nữ".'},
    {"name": "Nyc_NgayCap", "desc": "Ngày cấp CCCD/CMND của người yêu cầu, dd/mm/yyyy."},
    {"name": "Nyc_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND của người yêu cầu từ mặt sau. Thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" '
             'thì trả "Bộ Công an"; CCCD cũ có "CỤC TRƯỞNG CỤC CẢNH SÁT..." thì trả '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "Nyc_NoiCuTru",
     "desc": "Địa chỉ cư trú/thường trú trên CCCD của người yêu cầu, "
             "object {quocGia,tinh,xa,diaChi}. Với chuỗi 3 cấp hành chính "
             "'[chi tiết], [xã], [huyện], [tỉnh]': xa là cụm [xã] ngay sau chi tiết; "
             "bỏ cụm [huyện] dù OCR không ghi chữ 'huyện'."},

    {"name": "NguoiDuocCap_HoTen",
     "desc": 'Họ tên người được cấp bản sao từ tài liệu bổ trợ. GIẤY CHỨNG SINH lấy ở "Dự định đặt tên con"; '
             'TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ (CT01) lấy người tại mục 1. Không lấy mẹ, chủ hộ, người ký.'},
    {"name": "NguoiDuocCap_NgaySinh",
     "desc": 'Ngày sinh người được cấp bản sao từ tài liệu bổ trợ, dd/mm/yyyy. GIẤY CHỨNG SINH lấy ngày sinh '
             'trong câu "Đã sinh con ... ngày ..."; CT01 lấy mục 2.'},
    {"name": "NguoiDuocCap_GioiTinh",
     "desc": 'Giới tính người được cấp bản sao từ tài liệu bổ trợ: "Nam" hoặc "Nữ". GIẤY CHỨNG SINH lấy '
             '"Giới tính của con"; CT01 lấy mục 3.'},

    # Giấy tờ hộ tịch đã đăng ký trước đây: khai sinh/kết hôn/khai tử.
    {"name": "HoTich_LoaiSuKien",
     "desc": 'Loại sự kiện hộ tịch của giấy tờ chính: "birth", "marriage" hoặc "death".'},
    {"name": "HoTich_TenGiayTo",
     "desc": "Tên giấy tờ hộ tịch theo OCR, ví dụ Giấy khai sinh, Giấy chứng nhận kết hôn, Trích lục khai tử."},
    {"name": "HoTich_HoTenNguoiDuocDangKy",
     "desc": "Họ tên người được đăng ký trong giấy tờ hộ tịch; riêng giấy kết hôn lấy người chồng/bên nam."},
    {"name": "HoTich_NgaySinh", "desc": "Ngày sinh người được đăng ký nếu giấy tờ có ghi, dd/mm/yyyy."},
    {"name": "HoTich_GioiTinh", "desc": 'Giới tính người được đăng ký nếu giấy tờ có ghi: "Nam" hoặc "Nữ".'},
    {"name": "HoTich_DanToc",
     "desc": 'Dân tộc người được đăng ký nếu giấy tờ có ghi; giữ nguyên tên trên giấy tờ, kể cả tên '
             'không có trong danh sách chọn. Không tự đổi thành "Khác".'},
    {"name": "HoTich_QuocTich", "desc": "Quốc tịch người được đăng ký nếu giấy tờ có ghi hoặc khác Việt Nam."},
    {"name": "HoTich_SoDinhDanh", "desc": "Số định danh cá nhân của người được đăng ký nếu giấy tờ có ghi."},
    {"name": "HoTich_LoaiGiayToTuyThan",
     "desc": "Loại giấy tờ tùy thân của người được đăng ký. Với TỜ KHAI CẤP BẢN SAO lấy trong block "
             "sau 'cho người có tên dưới đây"},
    {"name": "HoTich_SoGiayToTuyThan",
     "desc": "Số giấy tờ tùy thân của người được đăng ký. Với TỜ KHAI CẤP BẢN SAO lấy trong block "
             "sau 'cho người có tên dưới đây"},
    {"name": "HoTich_NgayCapGiayToTuyThan",
     "desc": "Ngày cấp giấy tờ tùy thân của người được đăng ký, dd/mm/yyyy. Với TỜ KHAI CẤP BẢN SAO "
             "lấy trong block sau 'cho người có tên dưới đây'. Với TRÍCH LỤC KHAI TỬ, "
             "lấy ngày cấp trong dòng giấy tờ tùy thân của NGƯỜI CHẾT, không lấy của người đi khai tử; "},
    {"name": "HoTich_NoiCapGiayToTuyThan",
     "desc": 'Cơ quan cấp giấy tờ tùy thân của người được đăng ký. Với TỜ KHAI CẤP BẢN SAO lấy trong '
             'block sau "cho người có tên dưới đây". Với TRÍCH LỤC KHAI TỬ, lấy cơ quan '
             'trong dòng giấy tờ tùy thân của NGƯỜI CHẾT; "Cục CS QLHC về trật tự xã hội" chuẩn hóa '
             'thành "Cục Cảnh sát quản lý hành chính về trật tự xã hội", không lấy của người đi khai tử; '
             "riêng giấy kết hôn lấy của chồng/bên nam."},

    # CCCD/CMND RIÊNG của CHÍNH người được đăng ký, tách biệt hoàn toàn với Nyc_*.
    {"name": "ChuThe_HoTen", "desc": "Họ tên trên CCCD/CMND của chính người được đăng ký."},
    {"name": "ChuThe_SoDinhDanh",
     "desc": "Số định danh/CCCD/CMND của chính người được đăng ký; có thể đọc từ MRZ mặt sau."},
    {"name": "ChuThe_NgaySinh",
     "desc": "Ngày sinh trên CCCD/CMND của chính người được đăng ký, dd/mm/yyyy."},
    {"name": "ChuThe_GioiTinh",
     "desc": 'Giới tính người được đăng ký trên CCCD/CMND: "Nam" hoặc "Nữ".'},
    {"name": "ChuThe_QuocTich", "desc": "Quốc tịch trên CCCD/CMND của chính người được đăng ký."},
    {"name": "ChuThe_LoaiGiayTo",
     "desc": "Loại giấy tờ của chính người được đăng ký: Căn cước, Căn cước công dân, CMND hoặc Hộ chiếu."},
    {"name": "ChuThe_NgayCap",
     "desc": "Ngày cấp CCCD/CMND của chính người được đăng ký, dd/mm/yyyy; đọc từ mặt sau."},
    {"name": "ChuThe_NoiCap",
     "desc": 'Nơi cấp giấy tờ của chính người được đăng ký. Thẻ CĂN CƯỚC mới ghi "BỘ CÔNG AN" '
             'thì trả "Bộ Công an"; CCCD cũ trả '
             '"Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "ChuThe_NoiCuTru",
     "desc": "Địa chỉ cư trú/thường trú trên CCCD của chính người được đăng ký, "
             "object {quocGia,tinh,xa,diaChi}. Với chuỗi 3 cấp hành chính "
             "'[chi tiết], [xã], [huyện], [tỉnh]': xa là cụm [xã] ngay sau chi tiết; "
             "bỏ cụm [huyện] dù OCR không ghi chữ 'huyện'."},

    {"name": "HoTich_NoiCuTru",
     "desc": "Nơi cư trú của người được đăng ký nếu giấy tờ có ghi, object {quocGia,tinh,xa,diaChi}; "
             "với TỜ KHAI CẤP BẢN SAO, bắt buộc lấy dòng 'Nơi cư trú' trong block sau "
             "'cho người có tên dưới đây', không lấy nơi cư trú của người yêu cầu ở phần đầu; "
             "riêng giấy kết hôn lấy nơi cư trú của người chồng/bên nam."},
    {"name": "HoTich_CoQuanDangKy", "desc": "Cơ quan đã đăng ký sự kiện hộ tịch trước đây."},
    {"name": "HoTich_So",
     "desc": 'Số giấy tờ/số đăng ký/số trích lục của giấy tờ hộ tịch. BẮT BUỘC trả khi giấy tờ '
             'hộ tịch chính có dòng "Số:" ở phần đầu hoặc sát tiêu đề; nhận đầy đủ dạng số/năm.'},
    {"name": "HoTich_QuyenSo",
     "desc": "Quyển số đăng ký hộ tịch, CHỈ trả khi nhãn 'Quyển số'/'Quyển' có giá trị ghi rõ ngay sau nhãn. "
             "Không lấy 'số bộ', 'sổ bộ', 'bộ số', 'số hiệu' hoặc HoTich_So làm quyển số."},
    {"name": "HoTich_NgayDangKy",
     "desc": "Ngày đăng ký sự kiện hộ tịch trước đây, dd/mm/yyyy. Với TỜ KHAI, lấy D/M/Y trong block "
             "'Đã đăng ký tại ... ngày D tháng M năm Y số ...' kể cả khi bị xuống dòng; dấu chấm sau "
             "D/M là đường chấm của mẫu, không phải thiếu dữ liệu. Đủ D/M/Y thì BẮT BUỘC trả."},

    {"name": "CopyRequest_Quantity",
     "desc": "Số lượng bản sao được yêu cầu, chỉ trả số nguyên dương khi tờ khai/tài liệu yêu cầu ghi rõ. "
             "Trong cụm ngay trước từ 'bản', dấu chấm/phẩy xen giữa các chữ số là nhiễu OCR hoặc "
             "đường chấm điền: ghép các chữ số, bỏ số 0 ở đầu và không hiểu là số thập phân. "
             "Không tự mặc định là 3 hoặc bất kỳ số nào khác."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Nyc_NgaySinh", "Nyc_NgayCap", "ChuThe_NgaySinh", "ChuThe_NgayCap",
              "NguoiDuocCap_NgaySinh",
              "HoTich_NgaySinh", "HoTich_NgayDangKy",
              "HoTich_NgayCapGiayToTuyThan"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Nyc_NoiCuTru", "ChuThe_NoiCuTru", "HoTich_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Metadata để extension tự điền người yêu cầu
    "__requesterInfo": "raw",  # Thông tin người yêu cầu từ tờ khai/CCCD để extension tự điền đè lên VNeID
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
    "NDK_DanTocKhac": "x-select-area",
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
