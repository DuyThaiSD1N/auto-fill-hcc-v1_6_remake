"""Compact schema for "Đăng ký kết hôn".

The LLM returns OCR-derived facts from identity documents and the marriage
declaration. UI field names, duplicate identity fields, and deterministic
values are derived in Python.
"""

FIELDS: list[dict] = [
    # CCCD/CMND bên nam.
    {"name": "CccdNam_HoTen", "desc": "Họ tên trên CCCD/CMND có giới tính Nam."},
    {"name": "CccdNam_SoDinhDanh", "desc": "Số định danh/CCCD bên nam, đúng 12 số; CHỈ đọc ở MẶT TRƯỚC CCCD/CMND, từ dãy số ngay sau nhãn 'Số / No.'. TUYỆT ĐỐI không đọc, ghép hoặc suy ra từ MRZ/IDVNM ở mặt sau. Nếu không có mặt trước hoặc mặt trước không đọc rõ đủ 12 số thì bỏ field."},
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
    {"name": "CccdNam_NoiCuTru_TrongNuoc", "desc": "Địa chỉ cư trú CHỈ lấy từ CCCD/CMND của bên nam, object {quocGia,tinh,xa,diaChi}; xa BẮT BUỘC giữ tên loại đơn vị đầy đủ: P/P. → Phường, X/X. → Xã, TT/TT. → Thị trấn; không trả dạng viết tắt. tinh chỉ chứa tên tỉnh/thành phố đầy đủ."},
    {"name": "CccdNam_SoLanKetHon", "desc": "Số lần kết hôn của BÊN NAM — CHỈ lấy nếu tờ khai có mục 'Kết hôn lần thứ mấy'/'Số lần kết hôn' ghi rõ số ở cột nam. Trả SỐ NGUYÊN (vd '1', '2'). Không có thì bỏ qua."},
    {"name": "CccdNam_TinhTrangHonNhan", "desc": "Mã tình trạng hôn nhân BÊN NAM. Với bản án/quyết định ly hôn, chỉ trả mã 3 khi họ tên đương sự khớp CHÍNH XÁC sau chuẩn hóa dấu/hoa-thường/khoảng trắng với CccdNam_HoTen, hoặc văn bản có đúng số CCCD của người nam. Không fuzzy tên; lệch bất kỳ chữ nào mà không có CCCD khớp thì bỏ field. Mã: 1=đang có vợ/chồng; 2=chưa đăng ký; 3=đã ly hôn, hiện tại chưa đăng ký; 4=vợ/chồng đã chết; 5=chưa đăng ký trong một khoảng thời gian nhưng hiện đang có vợ/chồng; 6=khác. Chỉ trả mã số."},
    {"name": "CccdNam_BanAnLyHon_So",
     "desc": "Số bản án/quyết định ly hôn của BÊN NAM. CHỈ lấy khi văn bản ly hôn thật xác định đúng "
             "người này là đương sự, cùng điều kiện đối chiếu tên/CCCD như CccdNam_TinhTrangHonNhan mã 3. "
             "Tính cả bản án/quyết định KHÔNG CÔNG NHẬN QUAN HỆ VỢ CHỒNG và HỦY VIỆC KẾT HÔN TRÁI PHÁP "
             "LUẬT — tiêu đề không có chữ \"ly hôn\" vẫn là văn bản ly hôn của đương sự trong đó. Số "
             "dạng \"Bản án số: 06/2020/HNGĐ - ST\" trả thành \"06/2020/HNGĐ-ST\". "
             "Không khớp đúng người hoặc không có văn bản thì bỏ field; TUYỆT ĐỐI không mượn văn bản "
             "của bên kia."},
    {"name": "CccdNam_BanAnLyHon_Ngay",
     "desc": "Ngày cấp/ban hành bản án/quyết định ly hôn của BÊN NAM, dd/mm/yyyy. Cùng điều kiện đối "
             "chiếu như CccdNam_BanAnLyHon_So."},
    {"name": "CccdNam_BanAnLyHon_CoQuan",
     "desc": "Cơ quan ban hành/cấp bản án/quyết định ly hôn của BÊN NAM (vd 'Tòa án nhân dân huyện An Lão, "
             "thành phố Hải Phòng'), đọc ở góc trên của CHÍNH văn bản đã khớp tên người này. Cùng điều kiện "
             "đối chiếu như CccdNam_BanAnLyHon_So."},
    {"name": "CccdNam_BanAnLyHon_DuongSu",
     "desc": "Họ tên ĐẦY ĐỦ của TẤT CẢ đương sự ghi trong CHÍNH văn bản ly hôn đã gán cho BÊN NAM, nối bằng "
             "'; ' (vd 'Nguyễn Hoàng Hải Thanh; Lưu Hùng Nguyên'); bỏ xưng hô ông/bà/anh/chị và năm sinh. "
             "BẮT BUỘC trả kèm khi có CccdNam_BanAnLyHon_So — hệ thống dùng để kiểm tra chéo, nếu họ tên "
             "bên NAM không nằm trong danh sách này thì toàn bộ phần ly hôn của bên NAM bị loại bỏ."},

    # CCCD/CMND bên nữ.
    {"name": "CccdNu_HoTen", "desc": "Họ tên trên CCCD/CMND có giới tính Nữ."},
    {"name": "CccdNu_SoDinhDanh", "desc": "Số định danh/CCCD bên nữ, đúng 12 số; CHỈ đọc ở MẶT TRƯỚC CCCD/CMND, từ dãy số ngay sau nhãn 'Số / No.'. TUYỆT ĐỐI không đọc, ghép hoặc suy ra từ MRZ/IDVNM ở mặt sau. Nếu không có mặt trước hoặc mặt trước không đọc rõ đủ 12 số thì bỏ field."},
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
    {"name": "CccdNu_NoiCuTru_TrongNuoc", "desc": "Địa chỉ cư trú CHỈ lấy từ CCCD/CMND của bên nữ, object {quocGia,tinh,xa,diaChi}; xa BẮT BUỘC giữ tên loại đơn vị đầy đủ: P/P. → Phường, X/X. → Xã, TT/TT. → Thị trấn; không trả dạng viết tắt. tinh chỉ chứa tên tỉnh/thành phố đầy đủ."},
    {"name": "CccdNu_SoLanKetHon", "desc": "Số lần kết hôn của BÊN NỮ — CHỈ lấy nếu tờ khai có mục 'Kết hôn lần thứ mấy'/'Số lần kết hôn' ghi rõ số ở cột nữ. Trả SỐ NGUYÊN (vd '1', '2'). Không có thì bỏ qua."},
    {"name": "CccdNu_TinhTrangHonNhan", "desc": "Mã tình trạng hôn nhân BÊN NỮ. Với bản án/quyết định ly hôn, chỉ trả mã 3 khi họ tên đương sự khớp CHÍNH XÁC sau chuẩn hóa dấu/hoa-thường/khoảng trắng với CccdNu_HoTen, hoặc văn bản có đúng số CCCD của người nữ. Không fuzzy tên; lệch bất kỳ chữ nào mà không có CCCD khớp thì bỏ field. Mã: 1=đang có vợ/chồng; 2=chưa đăng ký; 3=đã ly hôn, hiện tại chưa đăng ký; 4=vợ/chồng đã chết; 5=chưa đăng ký trong một khoảng thời gian nhưng hiện đang có vợ/chồng; 6=khác. Chỉ trả mã số."},
    {"name": "CccdNu_BanAnLyHon_So",
     "desc": "Số bản án/quyết định ly hôn của BÊN NỮ. CHỈ lấy khi văn bản ly hôn thật xác định đúng "
             "người này là đương sự, cùng điều kiện đối chiếu tên/CCCD như CccdNu_TinhTrangHonNhan mã 3. "
             "Tính cả bản án/quyết định KHÔNG CÔNG NHẬN QUAN HỆ VỢ CHỒNG và HỦY VIỆC KẾT HÔN TRÁI PHÁP "
             "LUẬT — tiêu đề không có chữ \"ly hôn\" vẫn là văn bản ly hôn của đương sự trong đó. Số "
             "dạng \"Bản án số: 06/2020/HNGĐ - ST\" trả thành \"06/2020/HNGĐ-ST\". "
             "Không khớp đúng người hoặc không có văn bản thì bỏ field; TUYỆT ĐỐI không mượn văn bản "
             "của bên kia."},
    {"name": "CccdNu_BanAnLyHon_Ngay",
     "desc": "Ngày cấp/ban hành bản án/quyết định ly hôn của BÊN NỮ, dd/mm/yyyy. Cùng điều kiện đối "
             "chiếu như CccdNu_BanAnLyHon_So."},
    {"name": "CccdNu_BanAnLyHon_CoQuan",
     "desc": "Cơ quan ban hành/cấp bản án/quyết định ly hôn của BÊN NỮ (vd 'Tòa án nhân dân huyện An Lão, "
             "thành phố Hải Phòng'), đọc ở góc trên của CHÍNH văn bản đã khớp tên người này. Cùng điều kiện "
             "đối chiếu như CccdNu_BanAnLyHon_So."},
    {"name": "CccdNu_BanAnLyHon_DuongSu",
     "desc": "Họ tên ĐẦY ĐỦ của TẤT CẢ đương sự ghi trong CHÍNH văn bản ly hôn đã gán cho BÊN NỮ, nối bằng "
             "'; ' (vd 'Nguyễn Hoàng Hải Thanh; Lưu Hùng Nguyên'); bỏ xưng hô ông/bà/anh/chị và năm sinh. "
             "BẮT BUỘC trả kèm khi có CccdNu_BanAnLyHon_So — hệ thống dùng để kiểm tra chéo, nếu họ tên "
             "bên NỮ không nằm trong danh sách này thì toàn bộ phần ly hôn của bên NỮ bị loại bỏ."},

    # Tách nguồn tờ khai khỏi CCCD để mapper ưu tiên tất định, không phụ thuộc LLM tự chọn nguồn.
    {"name": "ToKhaiNam_NoiCuTru_TrongNuoc",
     "desc": "Nơi cư trú ở đúng cột BÊN NAM của TỜ KHAI ĐĂNG KÝ KẾT HÔN, "
             "object {quocGia,tinh,xa,diaChi}. CHỈ lấy từ tờ khai; không lấy CCCD, giấy xác nhận "
             "tình trạng hôn nhân, giấy phép lái xe hoặc giấy tờ phụ. tinh chỉ chứa tên tỉnh/thành phố đầy đủ; "
             "xa phải mở rộng P/P. thành Phường, X/X. thành Xã, TT/TT. thành Thị trấn."},
    {"name": "ToKhaiNu_NoiCuTru_TrongNuoc",
     "desc": "Nơi cư trú ở đúng cột BÊN NỮ của TỜ KHAI ĐĂNG KÝ KẾT HÔN, "
             "object {quocGia,tinh,xa,diaChi}. CHỈ lấy từ tờ khai; không lấy CCCD, giấy xác nhận "
             "tình trạng hôn nhân, giấy phép lái xe hoặc giấy tờ phụ. tinh chỉ chứa tên tỉnh/thành phố đầy đủ; "
             "xa phải mở rộng P/P. thành Phường, X/X. thành Xã, TT/TT. thành Thị trấn."},

    # Nhân thân ghi ở cột BÊN NAM của TỜ KHAI — CHỈ là nguồn DỰ PHÒNG khi thiếu CCCD/không đọc được trên thẻ.
    {"name": "ToKhaiNam_HoTen",
     "desc": "Họ tên ở đúng cột BÊN NAM của TỜ KHAI ĐĂNG KÝ KẾT HÔN. CHỈ lấy từ tờ khai, không lấy CCCD."},
    {"name": "ToKhaiNam_NgaySinh",
     "desc": "Ngày sinh ở đúng cột BÊN NAM của TỜ KHAI ĐĂNG KÝ KẾT HÔN, dd/mm/yyyy."},
    {"name": "ToKhaiNam_SoDinhDanh",
     "desc": "Số định danh/giấy tờ tùy thân ở đúng cột BÊN NAM của TỜ KHAI ĐĂNG KÝ KẾT HÔN."},
    {"name": "ToKhaiNam_NgayCap",
     "desc": "Ngày cấp giấy tờ tùy thân ở đúng cột BÊN NAM của TỜ KHAI ĐĂNG KÝ KẾT HÔN, dd/mm/yyyy."},
    {"name": "ToKhaiNam_NoiCap",
     "desc": "Nơi cấp giấy tờ tùy thân ở đúng cột BÊN NAM của TỜ KHAI ĐĂNG KÝ KẾT HÔN."},
    # Nhân thân ghi ở cột BÊN NỮ của TỜ KHAI — CHỈ là nguồn DỰ PHÒNG khi thiếu CCCD/không đọc được trên thẻ.
    {"name": "ToKhaiNu_HoTen",
     "desc": "Họ tên ở đúng cột BÊN NỮ của TỜ KHAI ĐĂNG KÝ KẾT HÔN. CHỈ lấy từ tờ khai, không lấy CCCD."},
    {"name": "ToKhaiNu_NgaySinh",
     "desc": "Ngày sinh ở đúng cột BÊN NỮ của TỜ KHAI ĐĂNG KÝ KẾT HÔN, dd/mm/yyyy."},
    {"name": "ToKhaiNu_SoDinhDanh",
     "desc": "Số định danh/giấy tờ tùy thân ở đúng cột BÊN NỮ của TỜ KHAI ĐĂNG KÝ KẾT HÔN."},
    {"name": "ToKhaiNu_NgayCap",
     "desc": "Ngày cấp giấy tờ tùy thân ở đúng cột BÊN NỮ của TỜ KHAI ĐĂNG KÝ KẾT HÔN, dd/mm/yyyy."},
    {"name": "ToKhaiNu_NoiCap",
     "desc": "Nơi cấp giấy tờ tùy thân ở đúng cột BÊN NỮ của TỜ KHAI ĐĂNG KÝ KẾT HÔN."},
    {"name": "ToKhaiNam_DanToc",
     "desc": "Dân tộc ở đúng cột BÊN NAM của TỜ KHAI ĐĂNG KÝ KẾT HÔN, chép NGUYÊN VĂN chữ trên tờ khai "
             "(kể cả tên nhóm địa phương như K'Ho, Cil, Chil). Python tự chuẩn hóa về option. Tờ khai không ghi thì bỏ."},
    {"name": "ToKhaiNu_DanToc",
     "desc": "Dân tộc ở đúng cột BÊN NỮ của TỜ KHAI ĐĂNG KÝ KẾT HÔN, chép NGUYÊN VĂN chữ trên tờ khai "
             "(kể cả tên nhóm địa phương như K'Ho, Cil, Chil). Python tự chuẩn hóa về option. Tờ khai không ghi thì bỏ."},

    # Loại đăng ký chỉ lấy khi tờ khai ghi rõ; không có thì bỏ, không tác động radio trên cổng.
    {"name": "ToKhai_LoaiDangKy",
     "desc": 'Loại đăng ký ghi trên TỜ KHAI ĐĂNG KÝ KẾT HÔN nếu tờ khai có mục "Loại đăng ký" '
             'được tích/ghi rõ (vd "Đăng ký lần đầu", "Đăng ký lại"). Trả đúng nhãn được chọn. '
             "Không có mục này hoặc không tích ô nào thì BỎ QUA field, không tự mặc định."},

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
    "CccdNam_BanAnLyHon_Ngay",
    "CccdNu_BanAnLyHon_Ngay",
    "ToKhaiNam_NgaySinh",
    "ToKhaiNam_NgayCap",
    "ToKhaiNu_NgaySinh",
    "ToKhaiNu_NgayCap",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "CccdNam_TinhTrangHonNhan",
    "CccdNu_TinhTrangHonNhan",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select"
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
    # Ô ghi tay khi dropdown dân tộc chọn "Khác" (tên ngoài danh sách, vd nhóm địa phương "Cill").
    "DanTocKhacBenNam": "x-select-area",
    "QuocTichBenNam": "x-select",
    "LoaiCuTru_BenNam": "x-select",
    "NoiCuTru_BenNam": "x-radio",
    "NoiCuTru_BenNam_TrongNuoc": "x-select-area",
    "NoiCuTru_BenNam_NuocNgoai": "x-select-area",
    "SoLanKetHon_BenNam": "raw",
    "LoaiTinhTrangHonNhan_BenNam": "x-select",
    # Widget động khi chọn "Đã ly hôn": tên thật lấy từ DOM cổng dịch vụ công (name="TTHN_LyHonBenNam"),
    # chứa 3 ô con Số bản án -> Ngày cấp -> Cơ quan cấp theo thứ tự (input name="BenNam_SoBanAn"...).
    "TTHN_LyHonBenNam": "x-select-area",
    # Bên nữ.
    "HoTenBenNu": "x-input",
    "SoDinhDanh_BenNu": "x-input",
    "SoGiayToDinhDanh_BenNu": "x-input",
    "LoaiGiayToDinhDanh_BenNu": "x-select",
    "NgaySinhBenNu": "x-date",
    "NgayCapDD_BenNu": "x-date",
    "NoiCapDD_BenNu": "x-input",
    "DanTocBenNu": "x-select",
    "DanTocKhacBenNu": "x-select-area",
    "QuocTichBenNu": "x-select",
    "LoaiCuTru_BenNu": "x-select",
    "NoiCuTru_BenNu": "x-radio",
    "NoiCuTru_BenNu_TrongNuoc": "x-select-area",
    "NoiCuTru_BenNu_NuocNgoai": "x-select-area",
    "SoLanKetHon_BenNu": "raw",
    "LoaiTinhTrangHonNhan_BenNu": "x-select",
    "TTHN_LyHonBenNu": "x-select-area",  # tương tự TTHN_LyHonBenNam nhưng cho bên nữ
    "loaiDangKy": "x-radio",
    "CapBanSao": "x-radio",
    "SoLuong": "raw",
}

# Tên DOM ô "dân tộc khác" chưa đối chiếu được trên cổng → gửi kèm các biến thể đặt tên của eForm;
# extension còn tìm theo ô dropdown gốc (otherOf) nếu không tên nào khớp.
UI_ALIASES = {
    "DanTocKhacBenNam": ["DanTocBenNamKhac", "DanTocKhac_BenNam", "DanTocBenNam_Khac"],
    "DanTocKhacBenNu": ["DanTocBenNuKhac", "DanTocKhac_BenNu", "DanTocBenNu_Khac"],
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
