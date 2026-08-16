"""Compact schema for "Đăng ký khai sinh".

The LLM returns only OCR-derived facts. UI defaults, name splitting, duplicate
fields, and form-specific components are derived in Python.
"""

FIELDS: list[dict] = [
    # Child facts from GIAY CHUNG SINH.
    {"name": "Gcs_HoTenCon", "desc": 'HỌ TÊN ĐẦY ĐỦ của ĐỨA TRẺ, CHỈ lấy giá trị được ghi rõ ngay tại trường "Dự định đặt tên con là". Nếu trường này trống hoặc chỉ có "/", "-", dấu gạch/điểm, "chưa đặt tên" thì BỎ field. Tuyệt đối không lấy tên mẹ/NND, tên trên CCCD hoặc giấy ra viện thay tên trẻ.'},
    {"name": "Gcs_NgaySinhCon", "desc": "Ngày sinh con trên giấy chứng sinh, dd/mm/yyyy. Nếu là GIẤY CAM ĐOAN: lấy ngày ở cụm 'Vào hồi ... ngày D tháng M năm Y' (ngày SINH, KHÔNG phải ngày làm giấy)."},
    {"name": "Gcs_GioiTinhCon", "desc": 'Giới tính con: "Nam" hoặc "Nữ". Nếu là GIẤY CAM ĐOAN: ô được đánh dấu ở "sinh ra 1 bé Trai/Gái" (Trai→Nam, Gái→Nữ).'},
    {"name": "Gcs_DanTocCon", "desc": "Dân tộc con trên giấy chứng sinh. Trả NGUYÊN VĂN giá trị đọc được, KỂ CẢ khi không nhận ra tên dân tộc (vd 'Cil', 'Cill' vẫn phải trả)."},
    {"name": "Gcs_NoiSinh", "desc": "Nơi sinh con lấy Ở DÒNG 'Tại:' trên GIẤY CHỨNG SINH (BẮT BUỘC khi có giấy chứng sinh, KHÔNG bỏ trống), object {tinh,xa,diaChi}; diaChi là TÊN ĐẦY ĐỦ cơ sở y tế (bệnh viện tuyến tỉnh kèm tên tỉnh). Chỉ trả xa khi OCR hoặc nguồn xác định đúng xã/phường của cơ sở; không lấy xã từ ví dụ của tỉnh khác. Nếu có tờ khai thì nơi sinh ưu tiên Tk_NoiSinh (xem mục B)."},
    {"name": "Tk_QueQuanCon", "desc": "QUÊ QUÁN của CON (người được khai sinh) lấy Ở DÒNG 'Quê quán' trong TỜ KHAI ĐĂNG KÝ KHAI SINH, object {tinh,xa,diaChi} (tách địa chỉ theo mục F). CHỈ có khi hồ sơ có tờ khai đăng ký khai sinh ghi rõ quê quán con; không có thì để trống."},
    {"name": "Tk_NoiSinh", "desc": "Nơi sinh con lấy Ở DÒNG 'Nơi sinh' trong TỜ KHAI ĐĂNG KÝ KHAI SINH (nếu có), object {tinh,xa,diaChi}. Trích NGUYÊN VĂN kể cả số nhà/đường/phố (vd diaChi='Bệnh viện Đa khoa Lâm Đồng, số 01 Phạm Ngọc Thạch'). CHỈ khi có tờ khai; không thì để trống. Nơi sinh điền vào form ưu tiên field này hơn Gcs_NoiSinh."},
    {"name": "Tk_HoTenCon", "desc": "Họ tên đầy đủ của người được khai sinh (con) lấy từ TỜ KHAI ĐĂNG KÝ KHAI SINH, dòng 'Họ, chữ đệm và tên khai sinh' hoặc 'Tên khai sinh'. CHỈ trả khi tờ khai ghi rõ; KHÔNG lấy từ giấy chứng sinh."},
    {"name": "Tk_NgaySinhCon", "desc": "Ngày sinh của người được khai sinh lấy từ TỜ KHAI ĐĂNG KÝ KHAI SINH, dd/mm/yyyy. CHỈ trả khi tờ khai ghi rõ."},
    {"name": "Tk_GioiTinhCon", "desc": 'Giới tính người được khai sinh lấy từ TỜ KHAI ĐĂNG KÝ KHAI SINH: "Nam" hoặc "Nữ". CHỈ trả khi tờ khai ghi rõ.'},
    {"name": "Tk_DanTocCon", "desc": "Dân tộc người được khai sinh lấy từ TỜ KHAI ĐĂNG KÝ KHAI SINH, dòng 'Dân tộc' trong khối thông tin người được khai sinh (KHÔNG phải dân tộc cha/mẹ). CHỈ trả khi tờ khai ghi rõ dân tộc của chính đứa trẻ. Trả NGUYÊN VĂN giá trị đọc được, KỂ CẢ khi không nhận ra tên dân tộc (vd 'Cil', 'Cill' vẫn phải trả)."},

    # Father facts - ưu tiên giấy chứng sinh/khai sinh/kết hôn, fallback CCCD Nam.
    {"name": "CccdNam_HoTen", "desc": "Họ tên CHA: ưu tiên giấy chứng sinh (khối cha) > giấy kết hôn (chồng/bên nam) > giấy khai sinh bản sao của con khác (khối cha) > CCCD/CMND Nam."},
    {"name": "CccdNam_SoDinhDanh", "desc": "Số định danh cha: ưu tiên giấy chứng sinh > giấy kết hôn > giấy khai sinh > CCCD Nam (12 số, có thể đọc từ MRZ)."},
    {"name": "CccdNam_NgaySinh", "desc": "Ngày sinh cha: ưu tiên giấy chứng sinh > giấy kết hôn > giấy khai sinh > CCCD Nam (dd/mm/yyyy, có thể chỉ năm sinh)."},
    {"name": "CccdNam_DanToc", "desc": "Dân tộc CHA: BẮT BUỘC lấy từ giấy chứng sinh (khối cha) hoặc giấy kết hôn (chồng) hoặc giấy khai sinh (khối cha) hoặc tờ khai khai sinh (khối cha), KỂ CẢ khi cha đã có CCCD. Trả NGUYÊN VĂN giá trị đọc được, KỂ CẢ khi không nhận ra tên dân tộc (vd 'Cil', 'Cill' vẫn phải trả). CCCD thường không in dân tộc."},
    {"name": "CccdNam_QuocTich", "desc": "Quốc tịch cha: chỉ trả nếu giấy tờ ghi rõ hoặc khác Việt Nam."},
    {"name": "CccdNam_QueQuan", "desc": "Quê quán/nguyên quán cha object {tinh,xa,diaChi}: lấy từ CCCD cũ (dòng 'Quê quán'). Thẻ căn cước mới KHÔNG có quê quán → để trống."},
    {"name": "CccdNam_NoiDangKyKhaiSinh", "desc": "Nơi đăng ký khai sinh cha trên thẻ CĂN CƯỚC mới (dòng 'Nơi đăng ký khai sinh'), object {tinh,xa,diaChi}. CHỈ khi thẻ CÓ dòng này."},
    {"name": "CccdNam_NoiCuTru", "desc": "Nơi cư trú cha object {tinh,xa,diaChi}: ưu tiên giấy chứng sinh > giấy kết hôn > giấy khai sinh > CCCD Nam."},

    # Mother facts - ƯU TIÊN GIẤY CHỨNG SINH.
    {"name": "CccdNu_HoTen", "desc": "Họ tên MẸ: ưu tiên giấy chứng sinh (khối mẹ) > giấy khai sinh bản sao (khối mẹ) > giấy kết hôn (bên nữ) > CCCD/CMND Nữ."},
    {"name": "CccdNu_SoDinhDanh", "desc": "Số định danh mẹ: ưu tiên giấy chứng sinh (Số ĐDCN/Hộ chiếu) > giấy khai sinh > giấy kết hôn > CCCD Nữ (12 số, có thể đọc từ MRZ)."},
    {"name": "CccdNu_NgaySinh", "desc": "Ngày sinh mẹ: ưu tiên giấy chứng sinh (có thể chỉ năm sinh) > giấy khai sinh > giấy kết hôn > CCCD Nữ (dd/mm/yyyy)."},
    {"name": "CccdNu_QueQuan", "desc": "Quê quán/nguyên quán MẸ object {tinh,xa,diaChi}: lấy từ CCCD/CMND cũ (dòng 'Quê quán / Place of origin'). Thẻ căn cước mới KHÔNG có quê quán → để trống. Dùng cho quê quán con khi áp dụng ngoại lệ Lâm Đồng."},
    {"name": "CccdNu_NoiDangKyKhaiSinh", "desc": "Nơi đăng ký khai sinh MẸ trên thẻ CĂN CƯỚC mới (dòng 'Nơi đăng ký khai sinh'), object {tinh,xa,diaChi}. CHỈ khi thẻ CÓ dòng này."},
    {"name": "CccdNu_DanToc", "desc": "Dân tộc mẹ: BẮT BUỘC lấy từ giấy chứng sinh (dòng 'Dân tộc' khối mẹ) hoặc giấy khai sinh (khối mẹ) hoặc giấy kết hôn. Trả NGUYÊN VĂN giá trị đọc được, KỂ CẢ khi không nhận ra tên dân tộc (vd 'Cil', 'Cill' vẫn phải trả). CCCD thường không in dân tộc."},
    {"name": "CccdNu_QuocTich", "desc": "Quốc tịch mẹ: chỉ trả nếu giấy tờ ghi rõ hoặc khác Việt Nam."},
    {"name": "CccdNu_NoiCuTru", "desc": "Nơi cư trú mẹ object {tinh,xa,diaChi}: ưu tiên giấy kết hôn > giấy chứng sinh > giấy khai sinh > CCCD Nữ. diaChi chỉ là bản/tổ/thôn/số nhà, không phải tên phường/xã."},

    # Marriage certificate facts from GIẤY CHỨNG NHẬN KẾT HÔN của cha mẹ (nếu có).
    {"name": "GcnKetHon_So", "desc": 'Số giấy chứng nhận kết hôn trong GIẤY CHỨNG NHẬN KẾT HÔN của cha mẹ, ở mục "Số:", vd "119/2026".'},
    {"name": "GcnKetHon_QuyenSo", "desc": "Quyển số trong GIẤY CHỨNG NHẬN KẾT HÔN của cha mẹ nếu ghi riêng, ở mục 'Quyển số: ...'. Nếu không có không cần ghi vào"},
    {"name": "GcnKetHon_NgayCap", "desc": "Ngày đăng ký/cấp giấy chứng nhận kết hôn trong GIẤY CHỨNG NHẬN KẾT HÔN của cha mẹ, dd/mm/yyyy."},
    {"name": "GcnKetHon_NoiCap", "desc": "Nơi đăng ký/cấp giấy chứng nhận kết hôn (tên cơ quan) trong GIẤY CHỨNG NHẬN KẾT HÔN của cha mẹ, nếu có phải ghi rõ."},

    # Số điện thoại liên hệ (nếu giấy tờ có ghi).
    {"name": "LienHe_SoDienThoai", "desc": "Số điện thoại liên hệ đọc được trên giấy tờ; số di động VN 10 số bắt đầu bằng 0."},

    # Số lượng bản sao trên tờ khai đăng ký khai sinh; không có số lượng thật thì không trả.
    {"name": "CopyRequest_Quantity",
     "desc": "Số lượng bản sao ghi thật ở mục 'Đề nghị cấp bản sao' trên TỜ KHAI ĐĂNG KÝ KHAI SINH, "
             "trả số nguyên dương (ví dụ '...3... bản' -> 3). Không có số lượng thì bỏ field; "
             "không tự mặc định."},

    # Tờ khai thay đổi thông tin cư trú (mẫu CT01) — CHỈ khi hồ sơ có tài liệu này (xem mục J).
    {"name": "Ct01_ChuHoHoTen", "desc": "Họ tên CHỦ HỘ trên TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ (CT01), mục 7 'Họ, chữ đệm và tên chủ hộ'. KHÔNG lấy mục 1 (người kê khai/đứa trẻ). Chỉ trả khi có giấy CT01."},
    {"name": "Ct01_ChuHoSoDinhDanh", "desc": "Số định danh cá nhân của CHỦ HỘ trên CT01, mục 9, 12 số. KHÔNG nhầm với số định danh người kê khai (mục 4)."},
    {"name": "Ct01_QuanHeVoiChuHo", "desc": "Mối quan hệ của người được khai sinh với chủ hộ trên CT01, mục 8 (vd 'Con đẻ', 'Cháu ngoại', 'Cháu nội')."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "text" for name in ALLOWED}
for _name in ("Gcs_NgaySinhCon", "CccdNam_NgaySinh", "CccdNu_NgaySinh", "GcnKetHon_NgayCap", "Tk_NgaySinhCon"):
    COMPACT_COMP_BY_NAME[_name] = "date"
for _name in ("Gcs_NoiSinh", "Tk_NoiSinh", "Tk_QueQuanCon",
              "CccdNam_QueQuan", "CccdNam_NoiDangKyKhaiSinh", "CccdNam_NoiCuTru",
              "CccdNu_QueQuan", "CccdNu_NoiDangKyKhaiSinh", "CccdNu_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "diachi"

UI_COMP_BY_NAME = {
    # Child.
    "Ho": "text",
    "ChuDem": "text",
    "Ten": "text",
    "NgaySinh": "date",
    "GioiTinh": "select",
    "MaDanToc": "select",
    "MaQuocTich": "select",
    "NsMaQuocGia": "select",
    "NsDiaChi": "diachi",
    "QqMaQuocGia": "select",
    "QqDiaChi": "diachi",
    # Mother.
    "MeHo": "text",
    "MeChuDem": "text",
    "MeTen": "text",
    "MeNgaySinh": "date",
    "MeSoGiayTo": "text",
    "MeMaDanToc": "select",
    "MeMaQuocTich": "select",
    "MeLoaiCuTru": "select",
    "MeMaQuocGia": "select",
    "MeDiaChi": "diachi",
    # Father (form cũ tách 3 ô; form liên thông gộp 1 ô ChaHoTen).
    "ChaHo": "text",
    "ChaChuDem": "text",
    "ChaTen": "text",
    "ChaHoTen": "text",
    "ChaNgaySinh": "date",
    "ChaSoGiayTo": "text",
    "ChaMaDanToc": "select",
    "ChaMaQuocTich": "select",
    "ChaLoaiCuTru": "select",
    "ChaMaQuocGia": "select",
    "ChaDiaChi": "diachi",
    # Giấy chứng nhận kết hôn của cha mẹ (app-input → text, kể cả Ngày cấp).
    "GiayCNKHSo": "text",
    "GiayCNKHQuyenSo": "text",
    "GiayCNKHNgayCap": "text",
    "GiayCNKHNoiCap": "text",
    # Đăng ký thường trú — nhánh XÁC NHẬN BẰNG TỜ KHAI GIẤY (CT01). Mapper chỉ bật khi có CT01.
    "LoaiXacNhanVNeID": "radio",
    "DkttIsTtBo": "checkbox",
    "DkttIsTtMe": "checkbox",
    "DkttChuHo": "text",
    "DkttChuhoSoGiayTo": "text",
    "DkttMaQuanHe": "select",
    # Người yêu cầu.
    "NycSdt": "text",
    # Đề nghị cấp bản sao trên form liên thông Angular.
    "CapBanSao": "radio",
    "BanSaoSoLuong": "raw",
    # Quan hệ người yêu cầu với trẻ: extension tự so khớp CCCD/tên người đăng nhập (cổng điền
    # sẵn trên form) với cha/mẹ để chọn Cha/Mẹ; khác cả hai → "Người giám hộ/đại diện hợp pháp".
    "NycQuanHe": "quanhe-auto",
}

STATIC_DEFAULTS: list[dict] = [
    # KHÔNG mặc định NycQuanHe="Cha": khai "người yêu cầu = cha" khiến cổng tự copy người
    # đăng nhập vào khối cha, đè dữ liệu cha từ giấy tờ. Để trống cho người dùng tự chọn.
    # default=True → extension đánh dấu VIỀN VÀNG (giá trị mặc định, không phải từ giấy tờ).
    # Mục đăng ký thường trú: CHỈ điền khi có tờ khai CT01 (xem mapper).
    # Không mặc định VNeID vì nhiều nơi dùng mẫu hệ (bà/mẹ là chủ hộ), bỏ mặc định tránh sai.
    {"name": "NguoiGiamHo", "comp": "select", "value": "Thông tin cha", "default": True},
]

# Field ĐÁNG rà soát bbox (name → nhãn). Đọc từ giấy chứng sinh/tờ khai + CCCD cha/mẹ. Tên con/mẹ
# tách Họ/Chữ đệm/Tên (đúng ô form); cha dùng ô gộp ChaHoTen. Địa chỉ (comp "diachi") tách
# tỉnh/xã/địa chỉ ở service. BỎ QUA: quốc tịch, quốc gia, loại cư trú, các mục ĐKTT mặc định.
REVIEW_FIELDS = {
    # Con (họ tên gộp qua REVIEW_NAME_GROUPS)
    "NgaySinh": "Ngày sinh con",
    "GioiTinh": "Giới tính con",
    "MaDanToc": "Dân tộc con",
    "NsDiaChi": "Nơi sinh con",
    # Mẹ (họ tên gộp qua REVIEW_NAME_GROUPS)
    "MeNgaySinh": "Ngày sinh mẹ",
    "MeSoGiayTo": "Số định danh mẹ",
    "MeMaDanToc": "Dân tộc mẹ",
    "MeDiaChi": "Nơi cư trú mẹ",
    # Cha (họ tên gộp qua REVIEW_NAME_GROUPS — form liên thông dùng 3 ô tách ChaHo/ChaChuDem/ChaTen)
    "ChaNgaySinh": "Ngày sinh cha",
    "ChaSoGiayTo": "Số định danh cha",
    "ChaMaDanToc": "Dân tộc cha",
    "ChaDiaChi": "Nơi cư trú cha",
    # Giấy chứng nhận kết hôn của cha, mẹ (nếu có)
    "GiayCNKHSo": "Số giấy chứng nhận kết hôn",
    "GiayCNKHNgayCap": "Ngày cấp giấy chứng nhận kết hôn",
    "GiayCNKHNoiCap": "Nơi cấp giấy chứng nhận kết hôn",
}

# Gộp ô Họ/Chữ đệm/Tên (con, mẹ, cha) thành 1 mục rà "họ tên đầy đủ". NEO vào ô TÊN (dưới cùng
# trong 3 ô) để panel không che mất ô Chữ đệm/Tên phía trên. Cha dùng 3 ô tách (không có ChaHoTen).
REVIEW_NAME_GROUPS = [
    {"parts": ["Ho", "ChuDem", "Ten"], "label": "Họ tên con", "anchor": "Ten"},
    {"parts": ["MeHo", "MeChuDem", "MeTen"], "label": "Họ tên mẹ", "anchor": "MeTen"},
    {"parts": ["ChaHo", "ChaChuDem", "ChaTen"], "label": "Họ tên cha", "anchor": "ChaTen"},
]
