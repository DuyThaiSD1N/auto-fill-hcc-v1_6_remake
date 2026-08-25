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

    # NGƯỜI YÊU CẦU ghi trên TỜ KHAI (phần đầu, trước "cho người có tên dưới đây").
    # Đây là NGUỒN ƯU TIÊN cho khối người yêu cầu; Nyc_* (CCCD) chỉ bù field tờ khai không có.
    {"name": "TkNyc_HoTen",
     "desc": "Họ tên người yêu cầu ghi trên TỜ KHAI cấp bản sao (dòng 'Họ, chữ đệm, tên người yêu cầu' "
             "ở phần đầu). KHÔNG lấy tên người được cấp bản sao ở block 'cho người có tên dưới đây'."},
    {"name": "TkNyc_NoiCuTru",
     "desc": "Nơi cư trú của NGƯỜI YÊU CẦU ghi trên TỜ KHAI (dòng 'Nơi cư trú' ở phần đầu, TRƯỚC "
             "'cho người có tên dưới đây'), object {quocGia,tinh,xa,diaChi}; bỏ cấp huyện."},
    {"name": "TkNyc_LoaiGiayToTuyThan",
     "desc": "Loại giấy tờ tùy thân của NGƯỜI YÊU CẦU trên TỜ KHAI (Căn cước/Căn cước công dân/CMND/Hộ chiếu)."},
    {"name": "TkNyc_SoGiayToTuyThan",
     "desc": "Số giấy tờ tùy thân của NGƯỜI YÊU CẦU trên TỜ KHAI."},
    {"name": "TkNyc_NgayCapGiayToTuyThan",
     "desc": "Ngày cấp giấy tờ tùy thân của NGƯỜI YÊU CẦU trên TỜ KHAI, dd/mm/yyyy."},
    {"name": "TkNyc_NoiCapGiayToTuyThan",
     "desc": "Cơ quan cấp giấy tờ tùy thân của NGƯỜI YÊU CẦU trên TỜ KHAI."},

    {"name": "NguoiDuocCap_HoTen",
     "desc": 'Họ tên người được cấp bản sao từ tài liệu bổ trợ. GIẤY CHỨNG SINH lấy ở "Dự định đặt tên con"; '
             'TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ (CT01) lấy người tại mục 1. Không lấy mẹ, chủ hộ, người ký.'},
    {"name": "NguoiDuocCap_NgaySinh",
     "desc": 'Ngày sinh người được cấp bản sao từ tài liệu bổ trợ, dd/mm/yyyy. GIẤY CHỨNG SINH lấy ngày sinh '
             'trong câu "Đã sinh con ... ngày ..."; CT01 lấy mục 2.'},
    {"name": "NguoiDuocCap_GioiTinh",
     "desc": 'Giới tính người được cấp bản sao từ tài liệu bổ trợ: "Nam" hoặc "Nữ". GIẤY CHỨNG SINH lấy '
             '"Giới tính của con"; CT01 lấy mục 3.'},

    # TỜ KHAI CẤP BẢN SAO: tách nguồn riêng để Python khóa loại yêu cầu và chủ thể,
    # không cho một giấy hộ tịch khác loại nhưng cùng người ghi đè.
    {"name": "ToKhai_LoaiSuKien",
     "desc": 'Loại được yêu cầu tại mục (4) TỜ KHAI CẤP BẢN SAO: "birth", "marriage" hoặc "death". '
             "Chỉ phân loại đúng cụm ở mục (4), không nhìn loại của giấy hộ tịch đính kèm; giá trị phải "
             "khớp ToKhai_TenGiayTo."},
    {"name": "ToKhai_TenGiayTo",
     "desc": "Tên giấy được yêu cầu tại dòng 'Đề nghị cơ quan cấp bản sao trích lục (4)' trên TỜ KHAI."},
    {"name": "ToKhai_HoTenNguoiDuocCap",
     "desc": "Họ tên trong block sau 'cho người có tên dưới đây' trên TỜ KHAI CẤP BẢN SAO."},
    {"name": "ToKhai_NgaySinh", "desc": "Ngày sinh người được cấp trong TỜ KHAI, dd/mm/yyyy."},
    {"name": "ToKhai_GioiTinh", "desc": 'Giới tính người được cấp trong TỜ KHAI: "Nam" hoặc "Nữ".'},
    {"name": "ToKhai_DanToc", "desc": "Dân tộc người được cấp trong TỜ KHAI."},
    {"name": "ToKhai_QuocTich", "desc": "Quốc tịch người được cấp trong TỜ KHAI."},
    {"name": "ToKhai_SoDinhDanh",
     "desc": "Số định danh cá nhân trong block người được cấp trên TỜ KHAI. CHỈ trả khi số có đúng 12 "
             "chữ số; CMND 9 chữ số không phải số định danh và phải bỏ trường này. Nếu dòng 'Giấy tờ tùy thân' "
             "ghi đúng 12 chữ số thì vẫn trả, kể cả khi không có chữ CCCD/Căn cước hoặc trùng người yêu cầu."},
    {"name": "ToKhai_LoaiGiayToTuyThan",
     "desc": "Loại giấy tờ tùy thân trong block người được cấp trên TỜ KHAI: Căn cước, CCCD, CMND hoặc "
             "Hộ chiếu. Nếu chỉ có số thì 12 chữ số suy ra Căn cước, 9 chữ số suy ra CMND."},
    {"name": "ToKhai_SoGiayToTuyThan",
     "desc": "Số giấy tờ tùy thân trong block người được cấp trên TỜ KHAI."},
    {"name": "ToKhai_NgayCapGiayToTuyThan",
     "desc": "Ngày cấp giấy tờ tùy thân trong block người được cấp trên TỜ KHAI, dd/mm/yyyy."},
    {"name": "ToKhai_NoiCapGiayToTuyThan",
     "desc": "Cơ quan cấp giấy tờ tùy thân trong block người được cấp trên TỜ KHAI."},
    {"name": "ToKhai_NoiCuTru",
     "desc": "Nơi cư trú trong block người được cấp trên TỜ KHAI, object {quocGia,tinh,xa,diaChi}."},
    {"name": "ToKhai_CoQuanDangKy",
     "desc": "Cơ quan ở mục 'Đã đăng ký tại' trên TỜ KHAI CẤP BẢN SAO."},
    {"name": "ToKhai_So", "desc": "Số đăng ký ghi sau mục 'Đã đăng ký tại' trên TỜ KHAI."},
    {"name": "ToKhai_QuyenSo",
     "desc": "Quyển số trên TỜ KHAI, chỉ trả khi có giá trị thật sau nhãn; nhãn trống thì bỏ field."},
    {"name": "ToKhai_NgayDangKy",
     "desc": "Ngày đăng ký trong mục 'Đã đăng ký tại ... ngày D tháng M năm Y' trên TỜ KHAI, dd/mm/yyyy."},

    # Giấy tờ hộ tịch đã đăng ký trước đây: khai sinh/kết hôn/khai tử.
    {"name": "HoTich_LoaiSuKien",
     "desc": 'Loại của CHÍNH giấy hộ tịch đính kèm đang xét: "birth", "marriage" hoặc "death". '
             "Không lấy loại yêu cầu từ TỜ KHAI vào trường này."},
    {"name": "HoTich_TenGiayTo",
     "desc": "Tên của CHÍNH giấy hộ tịch đính kèm đang xét; không lấy tên giấy được yêu cầu trên TỜ KHAI."},
    {"name": "HoTich_HoTenNguoiDuocDangKy",
     "desc": "Họ tên người được đăng ký trong giấy tờ hộ tịch; riêng giấy kết hôn lấy người chồng/bên nam."},
    {"name": "HoTich_NgaySinh", "desc": "Ngày sinh người được đăng ký nếu giấy tờ có ghi, dd/mm/yyyy."},
    {"name": "HoTich_GioiTinh", "desc": 'Giới tính người được đăng ký nếu giấy tờ có ghi: "Nam" hoặc "Nữ".'},
    {"name": "HoTich_DanToc",
     "desc": 'Dân tộc người được đăng ký nếu giấy tờ có ghi; giữ nguyên tên trên giấy tờ, kể cả tên '
             'không có trong danh sách chọn. Không tự đổi thành "Khác".'},
    {"name": "HoTich_QuocTich", "desc": "Quốc tịch người được đăng ký nếu giấy tờ có ghi hoặc khác Việt Nam."},
    {"name": "HoTich_SoDinhDanh",
     "desc": "Số định danh cá nhân của người được đăng ký ghi trên CHÍNH giấy hộ tịch đính kèm; "
             "không lấy từ TỜ KHAI."},
    {"name": "HoTich_LoaiGiayToTuyThan",
     "desc": "Loại giấy tờ tùy thân của người được đăng ký ghi trên CHÍNH giấy hộ tịch đính kèm; "
             "không lấy từ TỜ KHAI."},
    {"name": "HoTich_SoGiayToTuyThan",
     "desc": "Số giấy tờ tùy thân của người được đăng ký ghi trên CHÍNH giấy hộ tịch đính kèm; "
             "không lấy từ TỜ KHAI."},
    {"name": "HoTich_NgayCapGiayToTuyThan",
     "desc": "Ngày cấp giấy tờ tùy thân của người được đăng ký trên CHÍNH giấy hộ tịch đính kèm, "
             "dd/mm/yyyy; không lấy từ TỜ KHAI. Với TRÍCH LỤC KHAI TỬ, lấy của NGƯỜI CHẾT."},
    {"name": "HoTich_NoiCapGiayToTuyThan",
     "desc": 'Cơ quan cấp giấy tờ tùy thân của người được đăng ký trên CHÍNH giấy hộ tịch đính kèm; '
             'không lấy từ TỜ KHAI. Với TRÍCH LỤC KHAI TỬ, lấy cơ quan '
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
     "desc": "Nơi cư trú của người được đăng ký trên CHÍNH giấy hộ tịch đính kèm, "
             "object {quocGia,tinh,xa,diaChi}; không lấy từ TỜ KHAI; "
             "riêng giấy kết hôn lấy nơi cư trú của người chồng/bên nam."},
    {"name": "HoTich_NguoiThan",
     "desc": "Những người thân của NGƯỜI ĐƯỢC ĐĂNG KÝ mà CHÍNH giấy hộ tịch đính kèm có ghi tên, "
             "array object {quanHe, hoTen, soGiayTo}. quanHe = ĐÚNG vai ghi trên giấy ở dạng danh từ "
             "quan hệ ('cha', 'mẹ', 'vợ', 'chồng'...), lấy từ chính nhãn của dòng đó; hoTen = họ tên "
             "đầy đủ của người đó; soGiayTo = số định danh/số giấy tờ tùy thân của người đó CHỈ khi "
             "giấy ghi rõ, không có thì bỏ. Lấy MỌI dòng người thân giấy có ghi. TUYỆT ĐỐI không suy "
             "quan hệ từ họ, tuổi hay địa chỉ; giấy không ghi vai thì bỏ dòng đó."},
    {"name": "HoTich_CoQuanDangKy",
     "desc": "Cơ quan đăng ký ghi trên CHÍNH giấy hộ tịch đính kèm; không lấy từ TỜ KHAI."},
    {"name": "HoTich_So",
     "desc": "Số giấy tờ/số đăng ký/số trích lục ghi trên CHÍNH giấy hộ tịch đính kèm; "
             "không lấy từ TỜ KHAI hoặc giấy khác."},
    {"name": "HoTich_QuyenSo",
     "desc": "Quyển số đăng ký hộ tịch, CHỈ trả khi nhãn 'Quyển số'/'Quyển' có giá trị ghi rõ ngay sau nhãn. "
             "Chỉ lấy trên CHÍNH giấy hộ tịch đính kèm, không lấy từ TỜ KHAI. "
             "Không lấy 'số bộ', 'sổ bộ', 'bộ số', 'số hiệu' hoặc HoTich_So làm quyển số."},
    {"name": "HoTich_NgayDangKy",
     "desc": "Ngày đăng ký ghi trên CHÍNH giấy hộ tịch đính kèm, dd/mm/yyyy; "
             "không lấy từ TỜ KHAI hoặc giấy khác."},

    {"name": "CopyRequest_Quantity",
     "desc": "Số lượng bản sao được yêu cầu, chỉ trả số nguyên dương khi tờ khai/tài liệu yêu cầu ghi rõ. "
             "Trong cụm ngay trước từ 'bản', dấu chấm/phẩy xen giữa các chữ số là nhiễu OCR hoặc "
             "đường chấm điền: ghép các chữ số, bỏ số 0 ở đầu và không hiểu là số thập phân. "
             "Không tự mặc định là 3 hoặc bất kỳ số nào khác."},
    {"name": "CopyRequest_QuanHe",
     "desc": "Quan hệ của NGƯỜI YÊU CẦU với người được cấp bản sao, đọc ở TỜ KHAI dòng "
             "'Quan hệ với người được cấp bản sao Trích lục hộ tịch: ...'. Trả đúng chữ ghi trên tờ khai "
             "(vd 'Mẹ đẻ', 'Bố đẻ', 'Bản thân', 'Con đẻ', 'Vợ', 'Chồng'). Không có dòng này thì bỏ qua."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Nyc_NgaySinh", "Nyc_NgayCap", "ChuThe_NgaySinh", "ChuThe_NgayCap",
              "NguoiDuocCap_NgaySinh",
              "ToKhai_NgaySinh", "ToKhai_NgayCapGiayToTuyThan", "ToKhai_NgayDangKy",
              "HoTich_NgaySinh", "HoTich_NgayDangKy",
              "HoTich_NgayCapGiayToTuyThan", "TkNyc_NgayCapGiayToTuyThan"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Nyc_NoiCuTru", "ChuThe_NoiCuTru", "HoTich_NoiCuTru", "TkNyc_NoiCuTru"):
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
    "NYC_QuanHe": "x-radio",
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
