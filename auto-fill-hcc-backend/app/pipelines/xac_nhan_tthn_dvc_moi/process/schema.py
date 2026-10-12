"""Schema cấp Giấy xác nhận tình trạng hôn nhân trên Cổng DVC quốc gia bản mới (dichvucong.gov.vn/nop-ho-so, SurveyJS).

Tên câu hỏi + mã choice lấy từ formJson của cổng (mẫu "ThongTinNguoiNopXacNhanTtHonNhanGopCatalog"). Mỗi câu hỏi tên
`<tên>__<mã mẫu>` → backend chỉ gửi phần trước `__`, extension khớp theo tiền tố.

Khối THÔNG TIN NGƯỜI NỘP do cổng đổ từ tài khoản định danh và khóa (trừ số điện thoại) → chỉ trích số điện thoại và
quan hệ. Khối NGƯỜI ĐƯỢC CẤP: ba ô họ tên + ngày sinh + số định danh mang cờ `lookup` — cổng tra CSDL dân cư rồi tự đổ
và khóa giới tính, dân tộc, quốc tịch, giấy tờ → không trích các ô đó.

Field gửi extension (engine chung content/surveyjs-main.js): {name, comp, value, code?, default?, lookup?}.
"""

FIELDS: list[dict] = [
    {"name": "NguoiDuocCap_HoTen",
     "desc": "Họ, chữ đệm, tên của NGƯỜI ĐƯỢC CẤP Giấy XNTTHN (đúng người ở <nguoi_duoc_cap>)."},
    {"name": "NguoiDuocCap_NgaySinh", "desc": "Ngày sinh người được cấp, dd/mm/yyyy."},
    {"name": "NguoiDuocCap_SoDinhDanh",
     "desc": "Số định danh cá nhân (đúng 12 chữ số) của người được cấp. Số 9 chữ số là CMND → không trả ở đây."},
    {"name": "NguoiDuocCap_NoiCuTru",
     "desc": "Nơi cư trú hiện tại của người được cấp, object {quocGia,tinh,xa,diaChi[,huyen]}."},
    {"name": "NguoiNop_SoDienThoai",
     "desc": "Số điện thoại của NGƯỜI NỘP (khối <nguoi_nop>) ghi trên giấy tờ, chỉ khi số ghi cạnh tên / chữ ký của "
             "CHÍNH người đó. Không lấy số của người khác, cơ quan, cán bộ xác nhận. Không có → bỏ."},
    {"name": "NguoiYeuCau_HoTen", "desc": "Họ tên người yêu cầu ở khối ĐẦU tờ khai (trước câu 'Đề nghị cấp...')."},
    {"name": "NguoiYeuCau_SoDinhDanh", "desc": "Số giấy tờ tùy thân của người yêu cầu trên tờ khai."},
    {"name": "NguoiYeuCau_QuanHe",
     "desc": "Dòng 'Quan hệ với người được cấp Giấy xác nhận tình trạng hôn nhân' trên tờ khai, chép đúng chữ."},
    {"name": "TinhTrangHonNhan",
     "desc": 'MÃ tình trạng hôn nhân theo dòng "Tình trạng hôn nhân" trên TỜ KHAI: co_vo_chong | chua_ket_hon | '
             'ly_hon | goa | khoang_thoi_gian | khac — xem <tinh_trang_hon_nhan>.'},
    {"name": "TinhTrangHonNhan_NoiDung",
     "desc": 'Chỉ khi TinhTrangHonNhan = "khac": nội dung dòng tình trạng hôn nhân trên tờ khai, chép đúng chữ.'},
    {"name": "Marriage_SpouseName", "desc": "Họ tên vợ/chồng HIỆN TẠI của người được cấp."},
    {"name": "Marriage_Number", "desc": "Số giấy chứng nhận kết hôn hiện tại."},
    {"name": "Marriage_Date", "desc": "Ngày cấp/đăng ký giấy chứng nhận kết hôn hiện tại, dd/mm/yyyy."},
    {"name": "Marriage_Agency", "desc": "Cơ quan cấp giấy chứng nhận kết hôn hiện tại."},
    {"name": "BanAn_Number",
     "desc": "Số bản án/quyết định ly hôn đọc từ CHÍNH VĂN BẢN của Tòa án kèm trong hồ sơ; không có văn bản → bỏ."},
    {"name": "BanAn_Date",
     "desc": "Ngày ban hành bản án/quyết định ly hôn, dd/mm/yyyy; chỉ từ chính văn bản như BanAn_Number."},
    {"name": "BanAn_Agency", "desc": "Tòa án ban hành bản án/quyết định ly hôn; chỉ từ chính văn bản như BanAn_Number."},
    {"name": "DivorceDecision_Number",
     "desc": "Số bản án/quyết định ly hôn GHI TRÊN dòng tình trạng hôn nhân của TỜ KHAI / giấy XNTTHN cũ (không "
             "lấy từ văn bản bản án — văn bản đó là BanAn_*)."},
    {"name": "DivorceDecision_Date",
     "desc": "Ngày bản án/quyết định ly hôn ghi trên tờ khai, dd/mm/yyyy; nguồn như DivorceDecision_Number."},
    {"name": "DivorceDecision_Agency",
     "desc": "Cơ quan ban hành bản án/quyết định ly hôn ghi trên tờ khai; nguồn như DivorceDecision_Number."},
    {"name": "DeathCert_Number",
     "desc": "Số giấy chứng tử / trích lục khai tử / bản án tuyên bố chết của VỢ/CHỒNG đã chết — xem <giay_khai_tu>."},
    {"name": "DeathCert_Date", "desc": "Ngày cấp giấy chứng tử / trích lục khai tử đó, dd/mm/yyyy."},
    {"name": "DeathCert_Agency", "desc": "Cơ quan cấp giấy chứng tử / trích lục khai tử đó."},
    {"name": "Period_TuNgay",
     "desc": "Mốc BẮT ĐẦU khoảng thời gian xin xác nhận chưa đăng ký kết hôn (\"Từ ngày ...\"), dd/mm/yyyy."},
    {"name": "Period_DenNgay",
     "desc": "Mốc KẾT THÚC khoảng thời gian đó (\"đến ngày ...\"), dd/mm/yyyy."},
    {"name": "KetHonVoi_HoTen",
     "desc": "Chỉ khi mục đích là đăng ký kết hôn ở nước ngoài / tại cơ quan đại diện: họ tên NGƯỜI DỰ ĐỊNH KẾT HÔN."},
    {"name": "KetHonVoi_NgaySinh", "desc": "Ngày sinh người dự định kết hôn, dd/mm/yyyy."},
    {"name": "KetHonVoi_QuocTich", "desc": "Quốc tịch người dự định kết hôn."},
    {"name": "KetHonVoi_LoaiGiayTo", "desc": "Loại giấy tờ tùy thân của người dự định kết hôn (Hộ chiếu, Căn cước...)."},
    {"name": "KetHonVoi_SoGiayTo", "desc": "Số giấy tờ tùy thân của người dự định kết hôn."},
    {"name": "KetHonVoi_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân của người dự định kết hôn, dd/mm/yyyy."},
    {"name": "KetHonVoi_CoQuanCap", "desc": "Cơ quan cấp giấy tờ tùy thân của người dự định kết hôn."},
    {"name": "KetHonVoi_DiaChi", "desc": "Nơi cư trú của người dự định kết hôn, chép đúng chữ."},
    {"name": "KetHonVoi_NoiDuDinh", "desc": "Nơi dự định đăng ký kết hôn (cơ quan / thành phố), chép đúng chữ."},
    {"name": "KetHonVoi_QuocGia", "desc": "Quốc gia nơi dự định đăng ký kết hôn."},
    {"name": "SoLuongBanSao",
     "desc": "Số bản sao Giấy XNTTHN đề nghị cấp: số nguyên; tờ khai ghi không cần → 0; không khai → bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NguoiDuocCap_NgaySinh", "Marriage_Date", "BanAn_Date", "DivorceDecision_Date", "DeathCert_Date",
              "Period_TuNgay", "Period_DenNgay", "KetHonVoi_NgaySinh", "KetHonVoi_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
COMPACT_COMP_BY_NAME["NguoiDuocCap_NoiCuTru"] = "x-select-area"

UI_COMP_BY_NAME = {
    # Người nộp: khối khóa theo tài khoản, chỉ số điện thoại + quan hệ để mở.
    "citizenPhone": "sjs-text",
    "citizenQuanhevoinguoiduoccapGiayxacnhantinhtranghonnhan": "sjs-radio",
    "citizenField13": "sjs-text",  # Mối quan hệ khác — hiện khi quan hệ = Khác
    # NGƯỜI ĐƯỢC CẤP — ba ô tra cứu CSDL dân cư đi đầu.
    "citizenNDKHochudemtenngdccap": "sjs-text",
    "citizenNDKNgaythangnamsinh": "sjs-date",
    "citizenNDKSoDinhDanh": "sjs-text",
    "citizenNDKLoaicutru": "sjs-dropdown",
    "citizenNDKnoicutru": "sjs-radio",
    # Cụm địa chỉ thường trú trong nước (radio = Trong nước, loại cư trú = Thường trú); quốc gia cổng mặc định VN.
    "citizenNDKTinh_ThTru": "sjs-dropdown",
    "citizenNDKXa_ThTru": "sjs-dropdown",
    "citizenNDKDiaChi_ThTru": "sjs-text",
    "citizenNDKQG_Khac": "sjs-dropdown",
    "citizenNDKDiachi_Khac": "sjs-text",
    # Tình trạng hôn nhân + vùng chi tiết hiện theo từng option.
    "citizenTinhtranghonnhan": "sjs-dropdown",
    "citizenHovatencuavochongnguoicoyeucauxacnhantinhtranghonnhan": "sjs-text",  # =2 họ tên vợ/chồng
    "citizenField40": "sjs-text",  # =2 số giấy chứng nhận kết hôn
    "citizenField41": "sjs-date",  # =2 ngày cấp
    "citizenField42": "sjs-text",  # =2 cơ quan cấp
    "citizenSoBananQuyetdinhlyhon": "sjs-text",  # =3
    "citizenField46": "sjs-date",  # =3 ngày cấp bản án
    "citizenField47": "sjs-text",  # =3 cơ quan cấp bản án
    "citizenSogiaychungtuTrichluckhaituBanan": "sjs-text",  # =4
    "citizenField50": "sjs-date",  # =4 ngày cấp
    "citizenField51": "sjs-text",  # =4 cơ quan cấp
    "citizenField531": "sjs-text",  # =5 họ tên vợ/chồng
    "citizenField53": "sjs-text",  # =5 cơ quan cấp giấy chứng nhận kết hôn
    "citizenField54": "sjs-text",  # =5 số giấy chứng nhận kết hôn
    "citizenField55": "sjs-date",  # =5 ngày cấp
    "citizenField56": "sjs-date",  # =5 mốc bắt đầu
    "citizenField57": "sjs-date",  # =5 mốc kết thúc
    "citizenField59": "sjs-text",  # =6 nội dung tình trạng hôn nhân
    # Mục đích sử dụng + vùng chi tiết.
    "citizenField60": "sjs-dropdown",
    "citizenField69": "sjs-text",  # Nhập mục đích — mục đích khác
    "citizenHochudemtendaiienncngoai": "sjs-text",  # mục đích 1/2: người dự định kết hôn
    "citizenDaidienngaysinh": "sjs-date",
    "citizenDaidienquoctich": "sjs-dropdown",
    "citizenDaidiengiaytotuythan": "sjs-dropdown",
    "citizenDaidiensogiayto": "sjs-text",
    "citizenDaidienngaycap": "sjs-date",
    "citizenDaidiencoquancap": "sjs-text",
    "citizenDaidiendiachi": "sjs-text",
    "citizenNoidudinhdangkykethon": "sjs-text",
    "citizenDaidienquocgia": "sjs-dropdown",
    # Bắt buộc, cổng ghi "điền 0 nếu không cần".
    "citizenField70": "sjs-text",
}

# Danh mục tĩnh trong formJson: {choice value: nhãn}. Mã tình trạng hôn nhân KHÁC eForm cũ (1 = chưa đăng ký,
# 2 = đang có vợ/chồng).
QUAN_HE = {"1": "Bản thân", "2": "Khác"}
LOAI_CU_TRU = {"1": "Thường trú", "2": "Tạm trú", "3": "Nơi ở hiện tại"}
NOI_CU_TRU = {"1": "Trong nước", "2": "Khác"}
TINH_TRANG = {
    "1": "Hiện tại chưa đăng ký kết hôn với ai",
    "2": "Hiện tại đang có vợ/chồng",
    "3": "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng đã ly hôn; hiện tại chưa đăng ký kết hôn với ai",
    "4": "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng vợ/chồng đã chết; hiện tại chưa đăng ký kết hôn với ai",
    "5": "Từ ngày… tháng… năm… đến ngày… tháng… năm … chưa đăng ký kết hôn với ai; hiện tại đang có vợ/chồng",
    "6": "Khác - nếu không thuộc các trường hợp ở trên",
}
MUC_DICH = {
    "1": "Để đăng ký kết hôn tại Cơ quan đại diện Việt Nam ở nước ngoài",
    "2": "Để đăng ký kết hôn tại cơ quan có thẩm quyền của nước ngoài",
    "3": "Sử dụng vào mục đích khác",
}
LOAI_GIAY_TO = {
    "2": "Chứng minh nhân dân",
    "3": "Giấy chứng minh sĩ quan quân đội nhân dân Việt Nam",
    "4": "Giấy chứng minh công an nhân dân",
    "5": "Căn cước công dân",
    "6": "Hộ chiếu",
    "7": "Sổ hộ khẩu",
    "8": "Các loại giấy tờ tùy thân khác",
    "9": "Thẻ căn cước",
    "10": "Giấy chứng nhận căn cước",
}
