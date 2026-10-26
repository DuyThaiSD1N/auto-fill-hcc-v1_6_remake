"""Compact schema for "Đăng ký khai sinh".

The LLM returns only OCR-derived facts. UI defaults, name splitting, duplicate
fields, and form-specific components are derived in Python.
"""

FIELDS: list[dict] = [
    # Child facts from GIAY CHUNG SINH.
    {"name": "Gcs_HoTenCon", "desc": 'HỌ TÊN ĐẦY ĐỦ của ĐỨA TRẺ, CHỈ lấy giá trị được ghi rõ ngay tại trường "Dự định đặt tên con là". Bỏ các ký hiệu ngăn cách "/", "\\", "-", "_", "." ở ĐẦU giá trị rồi lấy họ tên còn lại; chỉ BỎ field khi TOÀN BỘ phần sau nhãn là rỗng/ký hiệu ngăn cách hoặc ghi "chưa đặt tên". Tuyệt đối không lấy tên mẹ/NND, tên trên CCCD hoặc giấy ra viện thay tên trẻ.'},
    {"name": "Gcs_NgaySinhCon", "desc": "Ngày sinh con trên giấy chứng sinh, dd/mm/yyyy. Nếu là GIẤY CAM ĐOAN: lấy ngày ở cụm 'Vào hồi ... ngày D tháng M năm Y' (ngày SINH, KHÔNG phải ngày làm giấy)."},
    {"name": "Gcs_GioiTinhCon", "desc": 'Giới tính con: "Nam" hoặc "Nữ". Nếu là GIẤY CAM ĐOAN: ô được đánh dấu ở "sinh ra 1 bé Trai/Gái" (Trai→Nam, Gái→Nữ).'},
    {"name": "Gcs_DanTocCon", "desc": "Dân tộc con trên giấy chứng sinh. Trả NGUYÊN VĂN giá trị đọc được, KỂ CẢ khi không nhận ra tên dân tộc (vd 'Cil', 'Cill' vẫn phải trả)."},
    {"name": "Gcs_NoiSinh", "desc": "Nơi sinh con lấy Ở DÒNG 'Tại:' trên GIẤY CHỨNG SINH (BẮT BUỘC khi có giấy chứng sinh, KHÔNG bỏ trống), object {tinh,xa,chiTietDuoiXa}; chiTietDuoiXa là TÊN ĐẦY ĐỦ cơ sở y tế (bệnh viện tuyến tỉnh kèm tên tỉnh). Chỉ trả xa khi OCR hoặc nguồn xác định đúng xã/phường của cơ sở; không lấy xã từ ví dụ của tỉnh khác. Nếu có tờ khai thì nơi sinh ưu tiên Tk_NoiSinh (xem mục B)."},
    {"name": "Tk_QueQuanCon", "desc": "QUÊ QUÁN của CON (người được khai sinh) lấy Ở DÒNG 'Quê quán' trong TỜ KHAI ĐĂNG KÝ KHAI SINH, object {tinh,xa,chiTietDuoiXa} (tách địa chỉ theo mục F). CHỈ có khi hồ sơ có tờ khai đăng ký khai sinh ghi rõ quê quán con; không có thì để trống."},
    {"name": "Tk_NoiSinh", "desc": "Nơi sinh con lấy Ở DÒNG 'Nơi sinh' trong TỜ KHAI ĐĂNG KÝ KHAI SINH (nếu có), object {tinh,xa,chiTietDuoiXa}. Trích NGUYÊN VĂN kể cả số nhà/đường/phố (vd chiTietDuoiXa='Bệnh viện Đa khoa Lâm Đồng, số 01 Phạm Ngọc Thạch'). CHỈ khi có tờ khai; không thì để trống. Nơi sinh điền vào form ưu tiên field này hơn Gcs_NoiSinh."},
    {"name": "Tk_HoTenCon", "desc": "Họ tên đầy đủ của người được khai sinh (con) lấy từ TỜ KHAI ĐĂNG KÝ KHAI SINH, dòng 'Họ, chữ đệm và tên khai sinh' hoặc 'Tên khai sinh'. CHỈ trả khi tờ khai ghi rõ; KHÔNG lấy từ giấy chứng sinh."},
    {"name": "Tk_NgaySinhCon", "desc": "Ngày sinh của người được khai sinh lấy từ TỜ KHAI ĐĂNG KÝ KHAI SINH, dd/mm/yyyy. CHỈ trả khi tờ khai ghi rõ."},
    {"name": "Tk_GioiTinhCon", "desc": 'Giới tính người được khai sinh lấy từ TỜ KHAI ĐĂNG KÝ KHAI SINH: "Nam" hoặc "Nữ". CHỈ trả khi tờ khai ghi rõ.'},
    {"name": "Tk_DanTocCon", "desc": "Dân tộc người được khai sinh lấy từ TỜ KHAI ĐĂNG KÝ KHAI SINH, dòng 'Dân tộc' trong khối thông tin người được khai sinh (KHÔNG phải dân tộc cha/mẹ). CHỈ trả khi tờ khai ghi rõ dân tộc của chính đứa trẻ. Trả NGUYÊN VĂN giá trị đọc được, KỂ CẢ khi không nhận ra tên dân tộc (vd 'Cil', 'Cill' vẫn phải trả)."},
    {"name": "Tk_NoiCuTruCha", "desc": "NƠI CƯ TRÚ của CHA/BỐ ĐẺ lấy Ở DÒNG 'Nơi cư trú' trong KHỐI THÔNG TIN CHA của TỜ KHAI ĐĂNG KÝ KHAI SINH, object {tinh,xa,chiTietDuoiXa} (tách theo mục F). CHỈ trả khi hồ sơ có tờ khai ghi rõ; KHÔNG lấy nơi cư trú của mẹ/người yêu cầu/con. Nơi cư trú cha điền vào form ưu tiên field này trước CCCD."},
    {"name": "Tk_NoiCuTruMe", "desc": "NƠI CƯ TRÚ của MẸ lấy Ở DÒNG 'Nơi cư trú' trong KHỐI THÔNG TIN MẸ của TỜ KHAI ĐĂNG KÝ KHAI SINH, object {tinh,xa,chiTietDuoiXa} (tách theo mục F). CHỈ trả khi hồ sơ có tờ khai ghi rõ; KHÔNG lấy nơi cư trú của cha/người yêu cầu/con. Nơi cư trú mẹ điền vào form ưu tiên field này trước CCCD."},

    # Thông tin bố theo VAI TRÒ trong hồ sơ, không đồng nghĩa dữ liệu chỉ đến từ CCCD nam.
    {"name": "ThongTinBo_HoTen", "desc": "Họ tên BỐ/CHA: ưu tiên giấy chứng sinh (khối cha) > giấy kết hôn (chồng/bên nam) > giấy khai sinh bản sao của con khác (khối cha) > CCCD/CMND của bố."},
    {"name": "ThongTinBo_SoDinhDanh", "desc": "Số định danh cha: ưu tiên giấy chứng sinh > giấy kết hôn > giấy khai sinh > CCCD/CMND được đối chiếu là của đúng người bố (12 số, có thể đọc từ MRZ)."},
    {"name": "ThongTinBo_NgaySinh", "desc": "Ngày sinh cha: ưu tiên giấy chứng sinh > giấy kết hôn > giấy khai sinh > CCCD/CMND được đối chiếu là của đúng người bố (dd/mm/yyyy, có thể chỉ năm sinh)."},
    {"name": "ThongTinBo_DanToc", "desc": "Dân tộc CHA/BỐ ĐẺ: hai nguồn chính theo thứ tự ưu tiên là (1) TỜ KHAI ĐĂNG KÝ KHAI SINH — dòng 'Dân tộc' trong khối thông tin bố đẻ/cha/người cha; (2) GIẤY CHỨNG NHẬN KẾT HÔN — dòng 'Dân tộc' thuộc khối chồng/bên nam. Có một trong hai giấy tờ thì BẮT BUỘC soát đúng khối của cha; đọc được giá trị không rỗng thì bắt buộc trả ThongTinBo_DanToc dù cha đã có CCCD hoặc tên dân tộc ít gặp. Chỉ khi cả hai nguồn chính không có/không ghi/không đọc được mới xét giấy chứng sinh hoặc giấy khai sinh có khối cha. Không lấy dân tộc mẹ/vợ hay của con."},
    {"name": "ThongTinBo_QuocTich", "desc": "Quốc tịch cha: chỉ trả nếu giấy tờ ghi rõ hoặc khác Việt Nam."},
    {"name": "ThongTinBo_QueQuan", "desc": "Quê quán/nguyên quán cha object {tinh,xa,chiTietDuoiXa}: lấy từ CCCD cũ (dòng 'Quê quán'). Thẻ căn cước mới KHÔNG có quê quán → để trống."},
    {"name": "ThongTinBo_NoiDangKyKhaiSinh", "desc": "Nơi đăng ký khai sinh cha trên thẻ CĂN CƯỚC mới (dòng 'Nơi đăng ký khai sinh'), object {tinh,xa,chiTietDuoiXa}. CHỈ khi thẻ CÓ dòng này."},
    {"name": "ThongTinBo_NoiCuTru", "desc": "Nơi cư trú cha object {tinh,xa,chiTietDuoiXa} NGOÀI tờ khai (tờ khai → Tk_NoiCuTruCha): ưu tiên CCCD/CMND được đối chiếu là của đúng người bố (dòng 'Nơi thường trú'/'Nơi cư trú') > giấy chứng sinh > giấy kết hôn > giấy khai sinh."},

    # Thông tin mẹ theo VAI TRÒ trong hồ sơ — ưu tiên giấy chứng sinh.
    {"name": "ThongTinMe_HoTen", "desc": "Họ tên MẸ: ưu tiên giấy chứng sinh (khối mẹ) > giấy khai sinh bản sao (khối mẹ) > giấy kết hôn (bên nữ) > CCCD/CMND được đối chiếu là của đúng người mẹ."},
    {"name": "ThongTinMe_SoDinhDanh", "desc": "Số định danh mẹ: ưu tiên giấy chứng sinh (Số ĐDCN/Hộ chiếu) > giấy khai sinh > giấy kết hôn > CCCD/CMND được đối chiếu là của đúng người mẹ (12 số, có thể đọc từ MRZ)."},
    {"name": "ThongTinMe_NgaySinh", "desc": "Ngày sinh mẹ: ưu tiên giấy chứng sinh (có thể chỉ năm sinh) > giấy khai sinh > giấy kết hôn > CCCD/CMND được đối chiếu là của đúng người mẹ (dd/mm/yyyy)."},
    {"name": "ThongTinMe_DanToc", "desc": "Dân tộc MẸ: BẮT BUỘC trích khi một trong các nguồn ghi rõ, theo đúng ưu tiên: (1) GIẤY CHỨNG SINH — dòng 'Dân tộc' trong khối thông tin mẹ, gần họ tên/ngày sinh/số ĐDCN của mẹ; (2) GIẤY CHỨNG NHẬN KẾT HÔN — dòng 'Dân tộc' thuộc khối vợ/bên nữ; (3) TỜ KHAI ĐĂNG KÝ KHAI SINH — dòng 'Dân tộc' thuộc khối người mẹ. Có nguồn ưu tiên cao hơn thì không thay bằng nguồn thấp hơn. Đọc được giá trị thì phải trả field dù cách ghi ít gặp; chỉ bỏ khi cả ba nguồn đều không ghi. CCCD thường không in dân tộc."},
    {"name": "ThongTinMe_QuocTich", "desc": "Quốc tịch mẹ: chỉ trả nếu giấy tờ ghi rõ hoặc khác Việt Nam."},
    {"name": "ThongTinMe_QueQuan", "desc": "Quê quán/nguyên quán MẸ object {tinh,xa,chiTietDuoiXa}: BẮT BUỘC trích khi CCCD cũ của đúng người mẹ có dòng 'Quê quán / Place of origin:' (OCR có thể chỉ còn 'Quê quán:'). , không dùng nơi cư trú mẹ thay quê quán. Nếu dòng quê quán chỉ ghi cấp huyện và tỉnh mà không có xã/phường thì không được coi tên huyện là xa, nhưng VẪN PHẢI trả field với phần xác định chắc chắn, tối thiểu là tinh; không được bỏ toàn bộ field."},
    {"name": "ThongTinMe_NoiCuTru", "desc": "Nơi cư trú mẹ object {tinh,xa,chiTietDuoiXa} NGOÀI tờ khai (tờ khai → Tk_NoiCuTruMe): ưu tiên CCCD/CMND được đối chiếu là của đúng người mẹ (dòng 'Nơi thường trú'/'Nơi cư trú') > giấy chứng sinh (dòng 'Nơi đăng ký thường trú' khối mẹ) > giấy kết hôn > giấy khai sinh. chiTietDuoiXa chỉ là bản/tổ/thôn/số nhà, không phải tên phường/xã."},
    {"name": "Gcs_NoiThuongTruMe", "desc": "Dòng 'Nơi đăng ký thường trú'/'Nơi thường trú'/'Nơi cư trú' trong KHỐI MẸ của GIẤY CHỨNG SINH, object {tinh,xa,chiTietDuoiXa} (tách theo mục F). BẮT BUỘC trả khi giấy chứng sinh có dòng này, kể cả khi đã trả ThongTinMe_NoiCuTru. Không có tỉnh thì suy từ thành phố/xã ghi trên dòng."},

    # Marriage certificate facts from GIẤY CHỨNG NHẬN KẾT HÔN của cha mẹ (nếu có).
    {"name": "GcnKetHon_So", "desc": 'Số giấy chứng nhận kết hôn trong GIẤY CHỨNG NHẬN KẾT HÔN của cha mẹ, ở mục "Số:", vd "119/2026".'},
    {"name": "GcnKetHon_QuyenSo", "desc": "Quyển số trong GIẤY CHỨNG NHẬN KẾT HÔN của cha mẹ nếu ghi riêng, ở mục 'Quyển số: ...'. Nếu không có không cần ghi vào"},
    {"name": "GcnKetHon_NgayCap", "desc": "Ngày đăng ký/cấp giấy chứng nhận kết hôn trong GIẤY CHỨNG NHẬN KẾT HÔN của cha mẹ, dd/mm/yyyy."},
    {"name": "GcnKetHon_NoiCap", "desc": "Nơi đăng ký/cấp giấy chứng nhận kết hôn (tên cơ quan) trong GIẤY CHỨNG NHẬN KẾT HÔN của cha mẹ, nếu có phải ghi rõ."},
    # Hai bên ghi trên GIẤY CHỨNG NHẬN KẾT HÔN — chép NGUYÊN theo giấy, mapper tự đối chiếu (trùng số giấy tờ
    # hoặc trùng họ tên) với cha/mẹ để bù ô còn thiếu (vd giấy chứng sinh chỉ ghi năm sinh mẹ).
    {"name": "GcnKetHon_Vo_HoTen", "desc": "Họ tên VỢ (bên nữ) trên GIẤY CHỨNG NHẬN KẾT HÔN. CHỈ lấy từ giấy kết hôn, BẮT BUỘC trả khi hồ sơ có giấy kết hôn."},
    {"name": "GcnKetHon_Vo_NgaySinh", "desc": "Ngày, tháng, năm sinh của VỢ trên GIẤY CHỨNG NHẬN KẾT HÔN, dd/mm/yyyy (vd '7/5/1990' → '07/05/1990'). CHỈ lấy từ giấy kết hôn."},
    {"name": "GcnKetHon_Vo_SoGiayTo", "desc": "Số giấy tờ tùy thân của VỢ ghi trên GIẤY CHỨNG NHẬN KẾT HÔN (CMND/CCCD/số định danh/chứng minh quân đội), chép nguyên số, GIỮ chữ cái nếu có (vd chứng minh quân đội '33A021121427'), bỏ khoảng trắng/dấu chấm. CHỈ lấy từ giấy kết hôn."},
    {"name": "GcnKetHon_Vo_DanToc", "desc": "Dân tộc của VỢ trên GIẤY CHỨNG NHẬN KẾT HÔN."},
    {"name": "GcnKetHon_Chong_HoTen", "desc": "Họ tên CHỒNG (bên nam) trên GIẤY CHỨNG NHẬN KẾT HÔN. CHỈ lấy từ giấy kết hôn, BẮT BUỘC trả khi hồ sơ có giấy kết hôn."},
    {"name": "GcnKetHon_Chong_NgaySinh", "desc": "Ngày, tháng, năm sinh của CHỒNG trên GIẤY CHỨNG NHẬN KẾT HÔN, dd/mm/yyyy. CHỈ lấy từ giấy kết hôn."},
    {"name": "GcnKetHon_Chong_SoGiayTo", "desc": "Số giấy tờ tùy thân của CHỒNG ghi trên GIẤY CHỨNG NHẬN KẾT HÔN (CMND/CCCD/số định danh/chứng minh quân đội), chép nguyên số, GIỮ chữ cái nếu có (vd chứng minh quân đội '33A021121427'), bỏ khoảng trắng/dấu chấm. CHỈ lấy từ giấy kết hôn."},
    {"name": "GcnKetHon_Chong_DanToc", "desc": "Dân tộc của CHỒNG trên GIẤY CHỨNG NHẬN KẾT HÔN."},
    # Cùng thông tin nhưng chép từ dòng in sẵn trên TỜ KHAI (hồ sơ hay không kèm giấy kết hôn thật).
    {"name": "Tk_GcnKetHon_So", "desc": 'Số giấy chứng nhận kết hôn ghi trên dòng "Thông tin về Giấy chứng nhận kết hôn của cha, mẹ trẻ" của TỜ KHAI (mục G).'},
    {"name": "Tk_GcnKetHon_QuyenSo", "desc": "Quyển số ghi trên dòng đó của TỜ KHAI; để chấm/trống → bỏ."},
    {"name": "Tk_GcnKetHon_NgayCap", "desc": "Ngày đăng ký kết hôn ghi trên dòng đó của TỜ KHAI, dd/mm/yyyy."},
    {"name": "Tk_GcnKetHon_NoiCap", "desc": "Nơi đăng ký kết hôn (tên cơ quan) ghi trên dòng đó của TỜ KHAI."},

    # Số điện thoại liên hệ (nếu giấy tờ có ghi).
    {"name": "LienHe_SoDienThoai", "desc": "Số điện thoại liên hệ đọc được trên giấy tờ; số di động VN 10 số bắt đầu bằng 0."},

    # Người ký TỜ KHAI ĐĂNG KÝ KHAI SINH — dùng để xác định số điện thoại trên giấy là của ai.
    {"name": "Tk_NguoiYeuCau_HoTen", "desc": "Họ tên NGƯỜI YÊU CẦU ở ĐẦU TỜ KHAI ĐĂNG KÝ KHAI SINH, dòng 'Họ, chữ đệm, tên người yêu cầu' (người ký cuối tờ khai). KHÔNG lấy tên con/cha/mẹ ở các khối bên dưới, cũng KHÔNG lấy người kê khai trên CT01. Chỉ trả khi có tờ khai đăng ký khai sinh ghi rõ."},
    {"name": "Tk_NguoiYeuCau_SoGiayTo", "desc": "Số giấy tờ tùy thân (CCCD/số định danh/CMND) của NGƯỜI YÊU CẦU ở dòng 'Giấy tờ tùy thân' ĐẦU TỜ KHAI ĐĂNG KÝ KHAI SINH. Chỉ trả khi tờ khai ghi rõ."},
    {"name": "Tk_NguoiYeuCau_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân của NGƯỜI YÊU CẦU ghi trên dòng 'Giấy tờ tùy thân' của TỜ KHAI ĐĂNG KÝ KHAI SINH, dd/mm/yyyy. Chỉ trả khi tờ khai ghi rõ."},
    {"name": "Tk_NguoiYeuCau_NoiCap", "desc": "Nơi cấp giấy tờ tùy thân của NGƯỜI YÊU CẦU ghi trên dòng 'Giấy tờ tùy thân' của TỜ KHAI ĐĂNG KÝ KHAI SINH (tên cơ quan). Chỉ trả khi tờ khai ghi rõ."},
    {"name": "Tk_NguoiYeuCau_NoiCuTru", "desc": "Dòng 'Nơi cư trú' của NGƯỜI YÊU CẦU ở ĐẦU TỜ KHAI ĐĂNG KÝ KHAI SINH (ngay dưới họ tên người yêu cầu), object {tinh,xa,chiTietDuoiXa} (tách theo mục F). KHÔNG lấy nơi cư trú trong khối cha/mẹ/con. Chỉ trả khi tờ khai ghi rõ."},

    # Ngày cấp / nơi cấp in trên CCCD/Căn cước của cha, mẹ — bù khối "Thông tin người yêu cầu" khi người
    # đăng nhập là cha/mẹ mà cổng không đổ sẵn.
    {"name": "ThongTinBo_NgayCapCccd", "desc": "Ngày cấp CCCD/Căn cước của đúng người CHA: dòng 'Ngày, tháng, năm / Date, month, year' (mặt sau CCCD gắn chip, cạnh chữ ký Cục trưởng) hoặc 'Ngày cấp' của thẻ Căn cước, dd/mm/yyyy. TUYỆT ĐỐI KHÔNG lấy 'Có giá trị đến' (ngày hết hạn) hay ngày sinh."},
    {"name": "ThongTinBo_NoiCapCccd", "desc": "Cơ quan cấp in trên CCCD/Căn cước của đúng người CHA (vd 'Cục Cảnh sát quản lý hành chính về trật tự xã hội', 'Bộ Công an'). Chỉ trả khi thẻ in rõ."},
    {"name": "ThongTinMe_NgayCapCccd", "desc": "Ngày cấp CCCD/Căn cước của đúng người MẸ: dòng 'Ngày, tháng, năm / Date, month, year' (mặt sau CCCD gắn chip) hoặc 'Ngày cấp' của thẻ Căn cước, dd/mm/yyyy. TUYỆT ĐỐI KHÔNG lấy 'Có giá trị đến' hay ngày sinh."},
    {"name": "ThongTinMe_NoiCapCccd", "desc": "Cơ quan cấp in trên CCCD/Căn cước của đúng người MẸ. Chỉ trả khi thẻ in rõ."},

    # CCCD/Căn cước của một người lớn KHÔNG phải cha/mẹ (ông bà, người giám hộ, người đi nộp hồ sơ...).
    {"name": "NguoiKhac_HoTen", "desc": "Họ tên trên CCCD/CMND/Căn cước của một người lớn KHÔNG phải cha, KHÔNG phải mẹ của trẻ (thường là người đi làm thủ tục: ông/bà, người giám hộ...). Chỉ trả khi hồ sơ có thẻ của người thứ ba như vậy."},
    {"name": "NguoiKhac_SoDinhDanh", "desc": "Số định danh (12 số) trên thẻ của người thứ ba nói ở NguoiKhac_HoTen; có thể đọc từ MRZ."},
    {"name": "NguoiKhac_GioiTinh", "desc": 'Giới tính trên thẻ của người thứ ba: "Nam" hoặc "Nữ".'},
    {"name": "NguoiKhac_NgayCapCccd", "desc": "Ngày cấp thẻ của người thứ ba (dòng 'Ngày, tháng, năm / Date, month, year' mặt sau CCCD gắn chip hoặc 'Ngày cấp'), dd/mm/yyyy. KHÔNG lấy 'Có giá trị đến'."},
    {"name": "NguoiKhac_NoiCapCccd", "desc": "Cơ quan cấp in trên thẻ của người thứ ba. Chỉ trả khi thẻ in rõ."},
    {"name": "NguoiKhac_NoiCuTru", "desc": "Nơi thường trú/nơi cư trú trên thẻ của người thứ ba, object {tinh,xa,chiTietDuoiXa} (tách theo mục F)."},

    # Số lượng bản sao trên tờ khai đăng ký khai sinh; không có số lượng thật thì không trả.
    {"name": "CopyRequest_Quantity",
     "desc": "Số lượng bản sao ghi thật ở mục 'Đề nghị cấp bản sao' trên TỜ KHAI ĐĂNG KÝ KHAI SINH, "
             "trả số nguyên dương (ví dụ '...3... bản' -> 3). Không có số lượng thì bỏ field; "
             "không tự mặc định."},

    # Tờ khai thay đổi thông tin cư trú (mẫu CT01) — CHỈ khi hồ sơ có tài liệu này (xem mục J).
    {"name": "Ct01_ChuHoHoTen", "desc": "Họ tên CHỦ HỘ trên TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ (CT01), mục 7 'Họ, chữ đệm và tên chủ hộ'. KHÔNG lấy mục 1 (người kê khai/đứa trẻ). Chỉ trả khi có giấy CT01."},
    {"name": "Ct01_ChuHoSoDinhDanh", "desc": "Số định danh cá nhân của CHỦ HỘ trên CT01, mục 9, 12 số. KHÔNG nhầm với số định danh người kê khai (mục 4)."},
    {"name": "Ct01_QuanHeVoiChuHo", "desc": "Mối quan hệ của người được khai sinh với chủ hộ trên CT01, mục 8 (vd 'Con đẻ', 'Cháu ngoại', 'Cháu nội')."},
    {"name": "Ct01_NoiDeNghiDktt", "desc": "Địa chỉ nơi đề nghị đăng ký thường trú ghi trong mục 'Nội dung đề nghị' của CT01, object {tinh,xa,chiTietDuoiXa} (tách theo mục F: chiTietDuoiXa = số nhà/đường/thôn/tổ ĐỨNG TRƯỚC phường/xã). Chỉ trả khi có giấy CT01."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "text" for name in ALLOWED}
for _name in ("Gcs_NgaySinhCon", "ThongTinBo_NgaySinh", "ThongTinMe_NgaySinh", "GcnKetHon_NgayCap", "Tk_GcnKetHon_NgayCap", "Tk_NgaySinhCon",
              "GcnKetHon_Vo_NgaySinh", "GcnKetHon_Chong_NgaySinh", "Tk_NguoiYeuCau_NgayCap",
              "ThongTinBo_NgayCapCccd", "ThongTinMe_NgayCapCccd", "NguoiKhac_NgayCapCccd"):
    COMPACT_COMP_BY_NAME[_name] = "date"
for _name in ("Gcs_NoiSinh", "Tk_NoiSinh", "Tk_QueQuanCon", "ThongTinBo_QueQuan", "ThongTinBo_NoiDangKyKhaiSinh", "ThongTinBo_NoiCuTru", "ThongTinMe_QueQuan", "ThongTinMe_NoiCuTru", "Gcs_NoiThuongTruMe", "Tk_NoiCuTruCha", "Tk_NoiCuTruMe", "Ct01_NoiDeNghiDktt",
              "Tk_NguoiYeuCau_NoiCuTru", "NguoiKhac_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "diachi"

UI_COMP_BY_NAME = {
    # Child.
    "Ho": "text",
    "ChuDem": "text",
    "Ten": "text",
    "NgaySinh": "date",
    "GioiTinh": "select",
    "MaDanToc": "select",
    "DantocKhac": "text",
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
    "MeDantocKhac": "text",
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
    "ChaDantocKhac": "text",
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
    # Chủ hộ CT01 là bố/mẹ → người xác nhận và chủ sở hữu chỗ ở là chính người đó (1 = bố, 2 = mẹ).
    "LoaiThanNhanXacNhan": "radio",
    "LoaiChuSoHuuChoO": "radio",
    "DkttChuHo": "text",
    "DkttChuhoSoGiayTo": "text",
    "DkttMaQuanHe": "select",
    # Nơi đề nghị đăng ký thường trú: Tỉnh/Phường readonly (cổng tự đổ theo cơ quan) → chỉ gửi diaChi.
    "DkttDiaChi": "diachi",
    # Người yêu cầu. SĐT chỉ điền khi người đăng nhập đúng là người ký tờ khai → comp riêng để
    # extension tự so tên với ô NycHoTen readonly mà cổng đổ sẵn.
    "NycSdt": "sdt-nguoiyeucau",
    # Đề nghị cấp bản sao trên form liên thông Angular.
    "CapBanSao": "radio",
    "BanSaoSoLuong": "raw",
    # Quan hệ người yêu cầu với trẻ: extension tự so khớp CCCD/tên người đăng nhập (cổng điền
    # sẵn trên form) với cha/mẹ để chọn Cha/Mẹ; khác cả hai → "Người giám hộ/đại diện hợp pháp".
    "NycQuanHe": "quanhe-auto",
    # Bù ô còn TRỐNG của khối người yêu cầu (giới tính, ngày/nơi cấp, nơi cư trú). Value là danh sách
    # người có trong giấy tờ; extension chọn người trùng CCCD/tên với ô readonly cổng đổ sẵn, ô cổng đã
    # có giá trị thì giữ nguyên.
    "NycBuThieu": "nyc-bu-thieu",
    # Thông tin cấp thẻ BHYT. CskcbbdMa là ng-select (danh sách theo tỉnh tài khoản) — chỉ mapper
    # điền theo cấu hình tài khoản (4 phường Đà Lạt).
    "NguoiGiamHo": "select",
    "CskcbbdMa": "select",
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
