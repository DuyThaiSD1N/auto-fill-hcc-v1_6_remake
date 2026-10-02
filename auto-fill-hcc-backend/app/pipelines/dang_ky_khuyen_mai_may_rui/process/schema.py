"""Compact schema cho "Đăng ký hoạt động khuyến mại đối với chương trình khuyến mại mang tính may rủi thực
hiện trên địa bàn 01 tỉnh, thành phố trực thuộc Trung ương" (mã 2.000004) — cổng DVC Bộ Công Thương
dichvucong-tthc.moit.gov.vn, dùng chung cho Sở Công Thương mọi tỉnh.

Bước 1 là HAI form Form.io trên cùng trang: form tài khoản/chủ hồ sơ và tờ khai Mẫu 02 ĐP.
⚠ Tờ khai dùng lại 7 field-key của khối tài khoản: data[fullname], data[phoneNumber], data[province],
data[district], data[address], data[taxCode], data[email] → mapper gắn OCCURRENCE 0 (tài khoản) / 1 (tờ khai).

Nguồn: Đăng ký thực hiện khuyến mại (Mẫu 02 ĐP) + Thể lệ (Mẫu 03 ĐP) + CCCD người nộp (nếu có). Bản scan
hay xếp lẫn trang giữa hai văn bản (phần cuối Mẫu 02 nằm trong tệp Thể lệ và ngược lại).
"""

_DK = "Đăng ký thực hiện khuyến mại (Mẫu số 02 ĐP)"
_TL = "Thể lệ chương trình khuyến mại (Mẫu số 03 ĐP)"

FIELDS: list[dict] = [
    # --- Người nộp = chủ tài khoản đăng nhập; CHỈ lấy từ thẻ CCCD ---
    {"name": "NguoiNop_HoTen", "desc": "Họ tên trên thẻ CCCD/căn cước có trong hồ sơ. IN HOA. KHÔNG lấy người "
        f"liên hệ, người ký trên {_DK}, hay họ tên khách hàng trên phiếu bốc thăm."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh cá nhân in trên CÙNG thẻ căn cước đó. Chỉ chữ số."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh in trên CÙNG thẻ căn cước đó, dd/mm/yyyy."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp in ở mặt sau CÙNG thẻ căn cước đó, dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCuTru", "desc": "Nơi thường trú / nơi cư trú in trên CÙNG thẻ căn cước đó, object "
        "{quocGia,tinh,xa,diaChi}; diaChi chỉ phần số nhà/thôn/đường, KHÔNG kèm phường/xã/tỉnh."},

    # --- Thương nhân thực hiện khuyến mại = CHỦ HỒ SƠ (phần đầu Mẫu 02) ---
    {"name": "ThuongNhan_Ten", "desc": f"Tên thương nhân ở dòng 'Tên thương nhân:' trên {_DK} (vd 'Hộ kinh doanh "
        "…', 'Công ty …'), chép đúng chữ hoa/thường như dòng đó. CHỈ khi không có dòng này mới lấy tên đơn vị "
        "ở góc trái trên."},
    {"name": "ThuongNhan_MaSoThue", "desc": f"'Mã số thuế' / 'Mã số doanh nghiệp' trên {_DK}; nếu Đơn không ghi "
        "thì lấy 'MST' trên con dấu cạnh chữ ký. Chép NGUYÊN VĂN chữ số đọc được; KHÔNG tự bù chữ số thiếu."},
    {"name": "ThuongNhan_SoCanCuoc", "desc": f"'Số căn cước' / 'Số CCCD' in ở phần thông tin thương nhân trên {_DK} "
        "(hộ kinh doanh ghi số căn cước của chủ hộ). Không in thì BỎ. KHÔNG lấy từ phiếu bốc thăm."},
    {"name": "ThuongNhan_DiaChi", "desc": f"'Địa chỉ trụ sở chính' trên {_DK}, object {{quocGia,tinh,xa,diaChi,"
        "fullText}}. fullText = nguyên dòng địa chỉ; tinh='Tỉnh/Thành phố …'; xa=phường/xã; diaChi=số nhà/thôn/"
        "đường (KHÔNG kèm phường/xã/tỉnh). KHÔNG lấy địa chỉ khắc trên con dấu (thường là địa danh cũ)."},
    {"name": "ThuongNhan_DienThoai", "desc": f"'Điện thoại' ở dòng thông tin thương nhân trên {_DK} (KHÔNG phải "
        "điện thoại người liên hệ). Chép nguyên chữ số đọc được, không tự bù số."},
    {"name": "ThuongNhan_Fax", "desc": f"'Fax' trên {_DK}. Chỉ chữ số; để chấm '....' thì BỎ."},
    {"name": "ThuongNhan_Email", "desc": f"Email thương nhân nếu IN trên {_DK}; để chấm hoặc không in thì BỎ."},
    {"name": "ThuongNhan_NguoiLienHe", "desc": f"Họ tên ở mục 'Người liên hệ' trên {_DK} (phần đầu Đơn hoặc mục "
        "'Đầu mối giải đáp thắc mắc')."},
    {"name": "ThuongNhan_DienThoaiLienHe", "desc": "'Điện thoại' in CÙNG dòng 'Người liên hệ' (hoặc 'Số điện thoại' "
        "ở mục Đầu mối giải đáp thắc mắc). Chép nguyên chữ số."},
    {"name": "ThuongNhan_DaiDien", "desc": f"Họ tên NGƯỜI KÝ dưới khối 'ĐẠI DIỆN CỦA …' cuối {_DK} (hoặc cuối "
        f"{_TL} nếu trang ký của Mẫu 02 nằm ở đó). Chép họ tên người, bỏ chức danh; KHÔNG lấy chữ trên con dấu "
        "(tên cửa hàng, địa chỉ, ĐT, MST)."},

    # --- Đầu văn bản Mẫu 02 ---
    {"name": "Don_So", "desc": f"Số văn bản ('Số: …') góc trái của {_DK}, chép nguyên văn phần sau 'Số:'. Đơn "
        f"không ghi thì lấy số công văn ở dòng '(Kèm theo công văn số … ngày …)' của {_TL}."},
    {"name": "Don_NgayLap", "desc": f"Ngày ở dòng '<địa danh>, ngày … tháng … năm …' đầu {_DK}, dd/mm/yyyy."},
    {"name": "Don_DiaDanh", "desc": "Địa danh ở đầu CÙNG dòng '<địa danh>, ngày … tháng … năm …', chép nguyên "
        "văn phần trước dấu phẩy, KHÔNG kèm chữ 'ngày'."},
    {"name": "Don_KinhGui", "desc": f"Nơi nhận ở dòng 'Kính gửi:' của {_DK}, chép nguyên văn, bỏ chữ 'Kính gửi:'."},

    # --- Chương trình khuyến mại (mục 1–8 Mẫu 02; Thể lệ chỉ bổ khuyết mục Đơn bỏ trống) ---
    {"name": "CTKM_Ten", "desc": "'Tên chương trình khuyến mại', chép nguyên văn, BỎ dấu ngoặc kép bao ngoài."},
    {"name": "CTKM_TuNgay", "desc": "Ngày BẮT ĐẦU ở mục 'Thời gian khuyến mại' ('từ … ngày X đến … ngày Y' → X), "
        "dd/mm/yyyy, bỏ giờ."},
    {"name": "CTKM_DenNgay", "desc": "Ngày KẾT THÚC ở mục 'Thời gian khuyến mại' (→ Y), dd/mm/yyyy, bỏ giờ. KHÔNG "
        "lấy thời gian xác định trúng thưởng / trao thưởng."},
    {"name": "CTKM_HangHoaKhuyenMai", "desc": f"Mục 'Hàng hóa, dịch vụ được khuyến mại' trên {_DK} (hàng khách phải MUA), chép "
        "nguyên văn, bỏ ngoặc đơn bao ngoài cả câu."},
    {"name": "CTKM_SoLuongHangHoa", "desc": "Mục 'Số lượng hàng hóa, dịch vụ được khuyến mại (nếu có)'. Để chấm "
        "'....' hoặc bỏ trống thì BỎ."},
    {"name": "CTKM_HangHoaDungKhuyenMai", "desc": f"Mục 'Hàng hóa, dịch vụ dùng để khuyến mại' trên {_DK} (giải thưởng/quà), "
        "chép nguyên văn kể cả số lượng; nhiều dòng thì nối bằng '; '."},
    {"name": "CTKM_DiaBan", "desc": f"Mục 'Địa bàn (phạm vi) khuyến mại' trên {_DK}, chép nguyên văn; Thể lệ ghi "
        "khác cách diễn đạt thì vẫn theo Đơn."},
    {"name": "CTKM_HinhThuc", "desc": f"Mục 'Hình thức khuyến mại' trên {_DK}, chép nguyên văn."},
    {"name": "CTKM_KhachHang", "desc": "Mục 'Khách hàng của chương trình khuyến mại (đối tượng được hưởng khuyến "
        "mại)', chép nguyên văn phần nội dung (kể cả phần bị ngắt sang trang sau)."},
    {"name": "CTKM_TongGiaTri", "desc": "Mục 'Tổng giá trị giải thưởng' (Mẫu 02 mục 8, hoặc Thể lệ), chép số tiền "
        "kèm đơn vị và phần '(Bằng chữ: …)' nếu có."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NguoiNop_NgaySinh", "NguoiNop_NgayCap", "Don_NgayLap", "CTKM_TuNgay", "CTKM_DenNgay"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("NguoiNop_NoiCuTru", "ThuongNhan_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# ---- UI Form.io (data[...]) — field-key lấy từ DOM thật. Key trùng giữa 2 form → mapper gắn occurrence.
UI_COMP_BY_NAME = {
    # --- Khối TÀI KHOẢN NỘP HỒ SƠ (occurrence 0 cho key trùng) ---
    "data[fullname]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[province]": "dom-select",
    "data[taxCode]": "dom-input",
    "data[email]": "dom-input",
    "data[district]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[birthday]": "dom-date",
    "data[address]": "dom-input",
    "data[noidungyeucaugiaiquyet]": "dom-input",
    # --- Khối CHỦ HỒ SƠ = thương nhân ---
    "data[isOwnerDossier]": "dom-checkbox",
    "data[ownerFullname]": "dom-input",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownertaxCode]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerAddress]": "dom-input",
    # --- Tờ khai Mẫu 02 ĐP: đầu đơn ---
    "data[soDon]": "dom-input",
    "data[tinhThanhPhoNopDon]": "dom-select",
    "data[ngayNopDon]": "dom-date",
    "data[kinhGui]": "dom-input",
    # --- Tờ khai: thông tin doanh nghiệp (7 key trùng → occurrence 1) ---
    "data[fax]": "dom-input",
    "data[fullname1]": "dom-input",          # nhãn "Người liên hệ:" (panel Người đại diện theo pháp luật)
    "data[phoneNumber1]": "dom-input",
    # --- Tờ khai: chương trình khuyến mại (mục 9 chỉ là chữ tĩnh, không có ô) ---
    "data[tenkm]": "dom-input",
    "data[ngayvb1]": "dom-date",             # "2. Thời gian khuyến mại" — CHỈ MỘT ô ngày
    "data[hhkm]": "dom-input",
    "data[slhh]": "dom-input",
    "data[dvkm]": "dom-input",
    "data[pvkm]": "dom-input",
    "data[htkm]": "dom-input",
    "data[khkm]": "dom-input",
    "data[tgtkm]": "dom-input",
    "data[daiDienPhapLuat]": "dom-input",
}
