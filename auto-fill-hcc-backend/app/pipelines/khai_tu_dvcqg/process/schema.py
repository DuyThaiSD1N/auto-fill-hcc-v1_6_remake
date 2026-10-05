"""Schema khai tử trên Cổng DVC quốc gia bản mới (dichvucong.gov.vn/nop-ho-so, React + SurveyJS).

Tên câu hỏi + mã choice lấy từ formJson của cổng (mẫu "ThongTinNguoiNopKhaiTuGopVer2Catalog", version 19). Mỗi
câu hỏi tên `<tên>__<mã mẫu>` → backend chỉ gửi phần trước `__`, extension khớp theo tiền tố.

Khối THÔNG TIN NGƯỜI NỘP do cổng đổ từ tài khoản định danh và khóa → không trích. LLM trả dữ kiện của NGƯỜI
MẤT (đúng người đã chốt ở bước phân vai), giấy báo tử / giấy tờ thay thế, dòng người yêu cầu + quan hệ trên tờ
khai (để đối chiếu với tài khoản) và yêu cầu cấp bản sao.

Field gửi extension (engine chung content/surveyjs-main.js): {name, comp, value, code?, default?, lookup?, radio?}
- code: mã option tĩnh trong formJson → extension khớp mã trước, nhãn sau.
- Ba ô họ tên + số định danh + ngày sinh người mất mang cờ `lookup`: cổng tra CSDL dân cư rồi tự đổ + khóa
  giới tính, dân tộc, quốc tịch, giấy tờ, nơi cư trú → extension chờ cổng tra, không ghi đè ô cổng đã đổ.
"""

FIELDS: list[dict] = [
    {"name": "NguoiMat_HoTen", "desc": "Họ, chữ đệm, tên của NGƯỜI ĐƯỢC ĐĂNG KÝ KHAI TỬ (người đã chết)."},
    {"name": "NguoiMat_SoDinhDanh",
     "desc": "Số định danh cá nhân (đúng 12 chữ số) của người chết. Số 9 chữ số là CMND → không trả ở đây."},
    {"name": "NguoiMat_NgaySinh",
     "desc": "Ngày sinh người chết: dd/mm/yyyy; giấy chỉ ghi tháng/năm hoặc năm thì trả đúng mm/yyyy hoặc yyyy."},
    {"name": "NguoiMat_GioiTinh", "desc": 'Giới tính người chết: "Nam" hoặc "Nữ" — chỉ khi giấy ghi.'},
    {"name": "NguoiMat_DanToc", "desc": "Dân tộc người chết nếu giấy ghi."},
    {"name": "NguoiMat_QuocTich", "desc": "Quốc tịch người chết nếu giấy ghi."},
    {"name": "NguoiMat_LoaiGiayTo",
     "desc": "Loại giấy tờ tùy thân CỦA CHÍNH người chết: Căn cước, Căn cước công dân, CMND, Hộ chiếu..."},
    {"name": "NguoiMat_SoGiayTo", "desc": "Số giấy tờ tùy thân CỦA CHÍNH người chết."},
    {"name": "NguoiMat_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân của người chết, dd/mm/yyyy."},
    {"name": "NguoiMat_NoiCap",
     "desc": "Cơ quan cấp giấy tờ tùy thân của người chết, CHÉP ĐÚNG chữ trên giấy. Không ghi → bỏ."},
    {"name": "NguoiMat_NoiCuTru",
     "desc": "NƠI CƯ TRÚ CUỐI CÙNG của người chết, object {quocGia,tinh,xa,diaChi[,huyen]}."},
    {"name": "NguoiMat_NgayMat",
     "desc": 'Ngày chết ("Đã chết vào lúc ... ngày"): dd/mm/yyyy; chỉ có tháng/năm hoặc năm thì mm/yyyy hoặc yyyy.'},
    {"name": "NguoiMat_GioMat", "desc": 'Giờ chết "HH:mm" — chỉ khi đọc chắc cả giờ và phút.'},
    {"name": "NguoiMat_NoiChet",
     "desc": "Nơi chết theo nhãn 'Nơi chết'/'Nơi tử vong', object {quocGia,tinh,xa,diaChi[,huyen]}."},
    {"name": "NguoiMat_NguyenNhan", "desc": "Nguyên nhân chết nếu giấy ghi."},
    {"name": "Gbt_Loai",
     "desc": '"Giấy báo tử" khi hồ sơ có chính GIẤY BÁO TỬ; "Giấy tờ thay thế" khi dùng giấy tờ thay giấy báo tử '
             '(trích lục khai tử, biên bản xác minh, văn bản xác nhận...). Không có → bỏ.'},
    {"name": "Gbt_So",
     "desc": "Số hiệu ĐẦY ĐỦ của giấy báo tử / giấy tờ thay thế như in trên giấy (vd '01/UBND-GBT', số trích lục)."},
    {"name": "Gbt_NgayCap", "desc": "Ngày cấp giấy báo tử / giấy tờ thay thế, dd/mm/yyyy."},
    {"name": "Gbt_CoQuanCap", "desc": "Cơ quan cấp giấy báo tử / giấy tờ thay thế (letterhead hoặc khối ký)."},
    {"name": "NguoiYeuCau_HoTen", "desc": "Họ tên người yêu cầu ở khối TRÊN câu 'Đề nghị...' của tờ khai."},
    {"name": "NguoiYeuCau_SoDinhDanh", "desc": "Số giấy tờ tùy thân của người yêu cầu trên tờ khai."},
    {"name": "NguoiYeuCau_QuanHe",
     "desc": "Dòng 'Quan hệ với người đã chết' trên tờ khai, chép đúng chữ (vd 'Con', 'Vợ')."},
    {"name": "ToKhai_LoaiDangKy", "desc": "Nhãn 'Loại đăng ký' trên tờ khai / mẫu hộ tịch điện tử nếu ghi."},
    {"name": "SoLuongBanSao",
     "desc": "Số bản sao trích lục đề nghị cấp: số nguyên; tờ khai đánh dấu KHÔNG → 0; ô Có/Không đều trống → bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NguoiMat_NgayCap", "Gbt_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("NguoiMat_NoiCuTru", "NguoiMat_NoiChet"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Người nộp: chỉ ô quan hệ là cổng để trống.
    "citizenmoiquanhe": "sjs-text",
    # NGƯỜI ĐƯỢC ĐĂNG KÝ KHAI TỬ — ba ô tra cứu CSDL dân cư đi đầu.
    "citizenNDK_HoVaTen": "sjs-text",
    "citizenNDK_SoDinhDanh": "sjs-text",  # regex cổng: đúng 12 số
    "citizenNDK_NgaySinh": "sjs-text",  # regex cổng: dd/mm/yyyy | mm/yyyy | yyyy
    "citizenGioitinh_NgdcKT": "sjs-dropdown",
    "citizenDantoc_NgdcKT": "sjs-dropdown",
    "citizenQuoctich_NgdcKT": "sjs-dropdown",
    "citizenLoaiGiaytotuythan_NgdcKT": "sjs-dropdown",
    "citizenSogiaytotuythan_NgdcKT": "sjs-text",
    "citizenField19": "sjs-date",  # Ngày cấp giấy tờ tùy thân
    "citizenNoicapgiaytotuythan_NgdcKT": "sjs-text",
    "citizenField56": "sjs-text",  # Ngày, tháng, năm chết — bắt buộc, cùng regex với ngày sinh
    "citizenGiomat": "sjs-text",
    "citizenPhutmat": "sjs-text",
    "citizenNDKLoaidangky": "sjs-dropdown",
    "citizenNDKLoaicutru": "sjs-dropdown",
    "citizenNDKnoicutru": "sjs-radio",  # Nơi cư trú cuối cùng
    # Cụm địa chỉ hiện theo (radio, loại cư trú). Quốc gia của nhánh trong nước cổng khóa sẵn "VN".
    "citizenNDKTinh_Thtru": "sjs-dropdown",
    "citizenNDKXa_Thtru": "sjs-dropdown",
    "citizenNDKDiaChi_Thtru": "sjs-text",
    "citizenNDKTinh_Tamtru": "sjs-dropdown",
    "citizenNDKXa_Tamtru": "sjs-dropdown",
    "citizenNDKDiachi_Tamtru": "sjs-text",
    "citizenNDKTinh_Ohientai": "sjs-dropdown",
    "citizenNDKXa_Ohientai": "sjs-dropdown",
    "citizenNDKDiachi_Ohientai": "sjs-text",
    "citizenNDKQG_Khac": "sjs-dropdown",
    "citizenNDKDiaChi_Khac": "sjs-text",
    "citizenNoichet": "sjs-radio",  # Nơi chết: Trong nước / Khác
    "citizenNoichet_TrongNuoc": "sjs-area",
    "citizenNguyennhanchet_NgdcKT": "sjs-text",
    # Giấy báo tử.
    "citizenLoaigiaybaotu": "sjs-dropdown",
    "citizenSogiaybaotu_NgdcKT": "sjs-text",
    "citizenNgaythangnamcapgiaybaotu": "sjs-date",
    "citizenCoquancapgiaybaotucochuthichneukhongcothidetrong": "sjs-text",
    # Bắt buộc, cổng ghi "điền 0 nếu không cần".
    "citizenSoluongbansaonguoiyeucaudenghi": "sjs-text",
}

# Tên ô địa chỉ nơi cư trú cuối cùng theo mã loại cư trú (choice value của citizenNDKLoaicutru).
NDK_ADDRESS_FIELDS = {
    "1": ("citizenNDKTinh_Thtru", "citizenNDKXa_Thtru", "citizenNDKDiaChi_Thtru"),
    "2": ("citizenNDKTinh_Tamtru", "citizenNDKXa_Tamtru", "citizenNDKDiachi_Tamtru"),
    "3": ("citizenNDKTinh_Ohientai", "citizenNDKXa_Ohientai", "citizenNDKDiachi_Ohientai"),
}

# Danh mục tĩnh trong formJson: {choice value: nhãn}.
GIOI_TINH = {"1": "Nam", "2": "Nữ"}
LOAI_DANG_KY = {
    "1": "Đăng ký đúng hạn",
    "4": "Đăng ký quá hạn",
    "5": "Đăng ký khai tử cho người chết đã lâu",
}
LOAI_CU_TRU = {"1": "Thường trú", "2": "Tạm trú", "3": "Nơi ở hiện tại"}
NOI_CU_TRU = {"1": "Trong nước", "2": "Khác"}
QUOC_TICH = {"VN": "Việt Nam"}
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
DAN_TOC = {
    "01": "Kinh", "02": "Tày", "03": "Thái", "04": "Hoa", "05": "Khơ-me", "06": "Mường", "07": "Nùng",
    "08": "H'Mông", "09": "Dao", "10": "Gia-rai", "11": "Ngái", "12": "Ê-đê", "13": "Ba na",
    "14": "Xơ-Đăng", "15": "Sán Chay", "16": "Cơ-ho", "17": "Chăm", "18": "Sán Dìu", "19": "Hrê",
    "20": "Mnông", "21": "Ra-glai", "22": "Xtiêng", "23": "Bru-Vân Kiều", "24": "Thổ", "25": "Giáy",
    "26": "Cơ-tu", "27": "Giẻ Triêng", "28": "Mạ", "29": "Khơ-mú", "30": "Co", "31": "Tà-ôi",
    "32": "Chơ-ro", "33": "Kháng", "34": "Xinh-mun", "35": "Hà Nhì", "36": "Chu ru", "37": "Lào",
    "38": "La Chí", "39": "La Ha", "40": "Phù Lá", "41": "La Hủ", "42": "Lự", "43": "Lô Lô",
    "44": "Chứt", "45": "Mảng", "46": "Pà Thẻn", "47": "Cơ Lao", "48": "Cống", "49": "Bố Y",
    "50": "Si La", "51": "Pu Péo", "52": "Brâu", "53": "Ơ Đu", "54": "Rơ măm", "55": "Người nước ngoài",
    "56": "Không rõ",
}
