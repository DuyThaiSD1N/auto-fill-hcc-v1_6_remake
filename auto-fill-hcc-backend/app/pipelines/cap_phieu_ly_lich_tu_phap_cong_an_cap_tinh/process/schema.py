"""Schema trích xuất cho "Cấp Phiếu lý lịch tư pháp" (3.000333, Công an cấp tỉnh) trên Cổng DVC quốc gia mới.

Biểu mẫu SurveyJS có radio "Loại tờ khai": Cá nhân (tài khoản = người yêu cầu cấp phiếu, khối nhân thân cổng đổ từ
CSDLQG về dân cư) / Khai hộ (tài khoản = người được ủy quyền hoặc cha mẹ người chưa thành niên, người khai nhập tay
khối người yêu cầu). LLM trả dữ kiện của NGƯỜI YÊU CẦU CẤP PHIẾU (NYC_*) và của NGƯỜI KHAI trên tờ khai mẫu ủy quyền
(NguoiKhai_*); mapper chọn biến thể theo tài khoản rồi phát đúng bộ ô (Mapping_LLTP_3.000333, 2 sheet).
"""

FIELDS: list[dict] = [
    {"name": "ToKhai_UyQuyen",
     "desc": 'true khi hồ sơ có TỜ KHAI mẫu dùng cho trường hợp ỦY QUYỀN / cha, mẹ của người chưa thành niên (có mục '
             '"Được sự ủy quyền" hoặc "PHẦN KHAI VỀ NGƯỜI ỦY QUYỀN HOẶC NGƯỜI CHƯA THÀNH NIÊN"); tờ khai cá nhân tự '
             'yêu cầu → false; không có tờ khai → bỏ.'},
    # Người khai trên tờ khai mẫu ủy quyền ("1. Tên tôi là") = người được ủy quyền / cha mẹ đi nộp.
    {"name": "NguoiKhai_HoTen", "desc": 'Tờ khai mẫu ủy quyền: họ tên sau "Tên tôi là" (người khai). Tờ khai cá nhân → bỏ.'},
    {"name": "NguoiKhai_SoGiayTo", "desc": "Số CMND/CCCD/hộ chiếu của người khai (tờ khai mẫu ủy quyền)."},
    {"name": "NguoiKhai_SoDienThoai", "desc": "Số điện thoại của người khai (mục 6 phần đầu tờ khai mẫu ủy quyền)."},
    {"name": "NguoiKhai_QuanHe",
     "desc": 'Dòng "Mối quan hệ với người ủy quyền" của tờ khai mẫu ủy quyền, chép đúng chữ (vd "Cha", "Mẹ", "Con").'},
    # Người yêu cầu cấp Phiếu (chủ hồ sơ, người được cấp phiếu).
    {"name": "NYC_HoTen", "desc": "Họ, chữ đệm, tên của NGƯỜI YÊU CẦU CẤP PHIẾU (người được cấp phiếu)."},
    {"name": "NYC_TenGoiKhac", "desc": 'Tên gọi khác của người yêu cầu; tờ khai ghi "Không" / để trống → bỏ.'},
    {"name": "NYC_GioiTinh", "desc": 'Giới tính người yêu cầu: "Nam" hoặc "Nữ".'},
    {"name": "NYC_NgaySinh", "desc": "Ngày sinh người yêu cầu, dd/mm/yyyy."},
    {"name": "NYC_NoiSinh",
     "desc": 'Nơi đăng ký khai sinh của người yêu cầu, object {quocGia,tinh,xa,chiTietDuoiXa[,huyen]}: ưu tiên dòng '
             '"Nơi đăng ký khai sinh / Place of birth" của thẻ căn cước, không có thì "Nơi sinh" của tờ khai.'},
    {"name": "NYC_QuocTich", "desc": "Quốc tịch người yêu cầu nếu giấy tờ ghi."},
    {"name": "NYC_DanToc", "desc": "Dân tộc người yêu cầu nếu giấy tờ ghi (thẻ căn cước mẫu mới không in → theo tờ khai)."},
    {"name": "NYC_LoaiGiayTo",
     "desc": "Loại giấy tờ tùy thân CỦA CHÍNH người yêu cầu: Căn cước, Căn cước công dân, CMND, Hộ chiếu..."},
    {"name": "NYC_SoGiayTo", "desc": "Số giấy tờ tùy thân của người yêu cầu (số định danh 12 số / CMND / hộ chiếu)."},
    {"name": "NYC_NgayCap", "desc": "Ngày cấp giấy tờ tùy thân của người yêu cầu, dd/mm/yyyy."},
    {"name": "NYC_NoiCap", "desc": "Cơ quan cấp giấy tờ tùy thân của người yêu cầu, chép đúng chữ trên giấy."},
    {"name": "NYC_NoiThuongTru",
     "desc": "Nơi thường trú của người yêu cầu, object {quocGia,tinh,xa,chiTietDuoiXa[,huyen]} (tờ khai mục Nơi thường "
             "trú; không có thì dòng Nơi cư trú của thẻ căn cước)."},
    {"name": "NYC_NoiTamTru",
     "desc": "Nơi tạm trú của người yêu cầu, object {quocGia,tinh,xa,chiTietDuoiXa[,huyen]}; chỉ khi tờ khai ghi."},
    {"name": "NYC_SoDienThoai", "desc": "Số điện thoại của người yêu cầu (mục Số điện thoại/e-mail của phần người yêu cầu)."},
    {"name": "NYC_Email", "desc": "Email của người yêu cầu nếu tờ khai ghi."},
    {"name": "NYC_HoTenCha", "desc": "Họ tên CHA của người yêu cầu (bảng CHA, MẸ, VỢ/CHỒNG của tờ khai)."},
    {"name": "NYC_HoTenMe", "desc": "Họ tên MẸ của người yêu cầu (bảng CHA, MẸ, VỢ/CHỒNG của tờ khai)."},
    {"name": "NYC_HoTenVoChong", "desc": "Họ tên VỢ/CHỒNG của người yêu cầu (bảng của tờ khai); để trống → bỏ."},
    {"name": "LoaiPhieu",
     "desc": 'Số Phiếu lý lịch tư pháp tờ khai YÊU CẦU RÕ: "1" hoặc "2" (ô đánh dấu / dòng ghi số phiếu). Tiêu đề in '
             'sẵn của mẫu tờ khai KHÔNG phải căn cứ. Không ghi rõ → bỏ.'},
    {"name": "YeuCauCDNCV",
     "desc": 'Dòng "Yêu cầu xác nhận về nội dung cấm đảm nhiệm chức vụ, thành lập, quản lý doanh nghiệp, hợp tác xã": '
             '"Có" hoặc "Không" theo ô được đánh dấu; không đánh dấu → bỏ.'},
    {"name": "SoLuongPhieu", "desc": "Số lượng Phiếu lý lịch tư pháp yêu cầu cấp: số nguyên; không ghi → bỏ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NYC_NgaySinh", "NYC_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("NYC_NoiSinh", "NYC_NoiThuongTru", "NYC_NoiTamTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# Ô SurveyJS: name = phần trước hậu tố "__<số>" của data-name (extension khớp theo tiền tố). Ô cổng khoá (readonly,
# đổ từ tài khoản / CSDLQG) không phát.
UI_COMP_BY_NAME = {
    "citizenLoaiToKhai": "sjs-radio",                      # 1 = Cá nhân, 2 = Khai hộ
    # ── Biến thể Cá nhân: khối người nộp = người yêu cầu (phần lớn khoá) ──
    "citizenField18": "sjs-dropdown",                       # Loại giấy tờ (sửa được)
    "citizenTenGoiKhac_NYC": "sjs-text",
    "citizenDateOfBirth": "sjs-date",                       # Ngày sinh (sửa được)
    "citizenCauhoi1": "sjs-dropdown",                       # Nơi tạm trú: Tỉnh/thành phố
    "citizenField33": "sjs-dropdown",                       # Nơi tạm trú: Phường/Xã
    "citizenDiaChiCuThe": "sjs-text",                       # Nơi tạm trú: Số nhà, đường phố
    "citizenHoVaTenVoChong_NYC": "sjs-text",
    "citizenPhone": "sjs-text",
    "citizenEmail": "sjs-text",
    # ── Biến thể Khai hộ: khối người được ủy quyền (tài khoản, phần lớn khoá) ──
    "citizenSoDienThoai_NYC_UyQuyen": "sjs-text",
    "citizenMoiQuanHe_NYC_NguoiUyQuyen": "sjs-dropdown",
    # ── Biến thể Khai hộ: khối người yêu cầu cấp phiếu (người khai nhập tay) ──
    "citizenLoaiGiayTo_NguoiUyQuyen": "sjs-dropdown",
    "citizenSoGiayTo_NguoiUyQuyen": "sjs-text",
    "citizenNgayCap_NguoiUyQuyen": "sjs-date",
    "citizenNoiCap_NguoiUyQuyen": "sjs-text",
    "citizenHoVaTen_NguoiUyQuyen": "sjs-text",
    "citizenField32": "sjs-text",                           # Tên gọi khác
    "citizenNgaySinh_NguoiUyQuyen": "sjs-date",
    "citizenGioiTinh_NguoiUyQuyen": "sjs-dropdown",
    # Panel động "NƠI ĐĂNG KÝ KHAI SINH": chỉ ô Quốc gia có tên trong mapping; Tỉnh/Xã hiện sau khi chọn Quốc gia, tên
    # ô khác khuôn biến thể Cá nhân (chạy thật 24/11: NoiSinhDangKy_MaTinh_NguoiUyQuyen không có) → cụm sjs-area dò theo
    # nhãn ngay sau ô Quốc gia.
    "NoiSinhDangKy_QuocGia_NguoiUyQuyen": "sjs-dropdown",
    "NoiSinhDangKy_NguoiUyQuyen": "sjs-area",
    "QuocTich_NguoiUyQuyen": "sjs-dropdown",
    "citizenDanToc_NguoiUyQuyen": "sjs-dropdown",
    "citizenNoiThuongTru_MaTinh_NguoiUyQuyen": "sjs-dropdown",
    "citizenNoiThuongTru_MaXa_NguoiUyQuyen": "sjs-dropdown",
    "citizenNoiThuongTru_DiaChiChiTiet_NguoiUyQuyen": "sjs-text",
    "citizenNoiTamTru_MaTinh_NguoiUyQuyen": "sjs-dropdown",
    "citizenNoiTamTru_MaXa_NguoiUyQuyen": "sjs-dropdown",
    "citizenNoiTamTru_DiaChiChiTiet_NguoiUyQuyen": "sjs-text",
    "citizenHoTenCha_NguoiUyQuyen": "sjs-text",
    "citizenHoVaTenMe_NguoiUyQuyen": "sjs-text",
    "citizenHoVaTenVoChong_NguoiUyQuyen": "sjs-text",
    "citizenSoDienThoai_NguoiUyQuyen": "sjs-text",
    "citizenEmail_NguoiUyQuyen": "sjs-text",
    # ── Thông tin yêu cầu cấp phiếu (chung hai biến thể) ──
    "citizenLoaiPhieu": "sjs-dropdown",
    "YeuCauCDNCV": "sjs-dropdown",
}
