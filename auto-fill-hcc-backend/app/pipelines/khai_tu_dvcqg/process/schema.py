"""Field thật của tờ khai đăng ký khai tử trên Cổng DVC quốc gia bản mới.

Trang dichvucong.gov.vn/nop-ho-so?formalityCaseId=...: React + SurveyJS. Nguồn: formJson của API
`configuring/formality/get-formality-form-by-citizen` (mẫu "ThongTinNguoiNopKhaiTuGopVer2Catalog",
version 19, crawl 2026-10-05). Mỗi câu hỏi có tên `<tên>__<mã mẫu>`, vd `citizenNDK_HoVaTen__1761724625529`.
Đuôi `__<mã>` là mã phiên bản mẫu nên backend CHỈ gửi phần tên trước `__`; extension khớp câu hỏi có
tên bằng `<tên>` hoặc bắt đầu bằng `<tên>__` (DOM: `[data-name]`). Không dùng id `sq_*` (đánh số lại mỗi
lần render).

Mỗi field gửi extension: {name, comp, value, code?, default?}
- value: NHÃN hiển thị (để khớp option trên DOM / cán bộ đọc);
- code: giá trị lưu trong model SurveyJS khi biết chắc (choice value tĩnh, ngày ISO) — extension ưu tiên
  `survey.setValue(tên đầy đủ, code)` để kích hoạt visibleIf/trigger của cổng.

Comp:
- "sv-text" / "sv-number": ô chữ / ô số.
- "sv-date": câu hỏi inputType=date (flatpickr). value "dd/mm/yyyy", code "yyyy-mm-dd".
- "sv-dropdown": dropdown SurveyJS. Có code khi danh mục tĩnh; tỉnh/xã nạp qua API của cổng
  (province-vn / ward list-by-citizen) nên chỉ có nhãn, phải chọn theo nhãn sau khi danh sách nạp.
- "sv-radio": radiogroup, code "1" = Trong nước, "2" = Khác.
- "sv-diachi": (tạm) cụm nơi chết — chờ phần formJson còn lại để tách tên ô thật.

THỨ TỰ quan trọng: họ tên + số định danh + ngày sinh người mất kích hoạt `get-citizen-by-code` của cổng;
tra được trong CSDL dân cư thì cổng tự đổ và KHÓA (isReadOnlyWhenFillForm) giới tính, dân tộc, quốc
tịch, giấy tờ, nơi cư trú. Mapper xếp ba ô đó đầu tiên; extension phải bỏ qua ô đã bị cổng khóa.

Khối "Thông tin người nộp" (citizenName, citizenIdentity, citizenField18, citizenNyc*...) và "Kính gửi"
(citizenField27, cổng tự lấy theo cơ quan) cổng tự điền → KHÔNG có trong bảng này.
"""

UI_COMP_BY_NAME = {
    # Người nộp: chỉ ô quan hệ là cổng để trống.
    "citizenmoiquanhe": "sv-text",
    # NGƯỜI ĐƯỢC ĐĂNG KÝ KHAI TỬ — ba ô tra cứu CSDL dân cư đi đầu.
    "citizenNDK_HoVaTen": "sv-text",
    "citizenNDK_SoDinhDanh": "sv-text",  # regex cổng: đúng 12 số
    "citizenNDK_NgaySinh": "sv-text",  # regex cổng: dd/mm/yyyy | mm/yyyy | yyyy
    "citizenGioitinh_NgdcKT": "sv-dropdown",
    "citizenDantoc_NgdcKT": "sv-dropdown",
    "citizenQuoctich_NgdcKT": "sv-dropdown",
    "citizenLoaiGiaytotuythan_NgdcKT": "sv-dropdown",
    "citizenSogiaytotuythan_NgdcKT": "sv-text",
    "citizenField19": "sv-date",  # Ngày cấp giấy tờ tùy thân
    "citizenNoicapgiaytotuythan_NgdcKT": "sv-text",
    "citizenField56": "sv-text",  # Ngày, tháng, năm chết — bắt buộc, cùng regex với ngày sinh
    "citizenGiomat": "sv-number",
    "citizenPhutmat": "sv-number",
    "citizenNDKLoaidangky": "sv-dropdown",
    "citizenNDKLoaicutru": "sv-dropdown",
    "citizenNDKnoicutru": "sv-radio",  # Nơi cư trú cuối cùng
    # Cụm địa chỉ hiện theo (radio, loại cư trú). Quốc gia của nhánh trong nước cổng khóa sẵn "VN".
    "citizenNDKTinh_Thtru": "sv-dropdown",
    "citizenNDKXa_Thtru": "sv-dropdown",
    "citizenNDKDiaChi_Thtru": "sv-text",
    "citizenNDKTinh_Tamtru": "sv-dropdown",
    "citizenNDKXa_Tamtru": "sv-dropdown",
    "citizenNDKDiachi_Tamtru": "sv-text",
    "citizenNDKTinh_Ohientai": "sv-dropdown",
    "citizenNDKXa_Ohientai": "sv-dropdown",
    "citizenNDKDiachi_Ohientai": "sv-text",
    "citizenNDKQG_Khac": "sv-dropdown",
    "citizenNDKDiaChi_Khac": "sv-text",
    "citizenNoichet": "sv-diachi",
    "citizenNguyennhanchet_NgdcKT": "sv-text",
    # Giấy báo tử.
    "citizenLoaigiaybaotu": "sv-dropdown",
    "citizenSogiaybaotu_NgdcKT": "sv-text",
    "citizenNgaythangnamcapgiaybaotu": "sv-date",
    "citizenCoquancapgiaybaotucochuthichneukhongcothidetrong": "sv-text",
    # Bắt buộc, cổng ghi "điền 0 nếu không cần".
    "citizenSoluongbansaonguoiyeucaudenghi": "sv-number",
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
