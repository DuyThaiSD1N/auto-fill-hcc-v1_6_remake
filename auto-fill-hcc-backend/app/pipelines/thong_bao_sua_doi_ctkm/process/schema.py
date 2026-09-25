"""Compact schema cho "Thông báo sửa đổi, bổ sung nội dung chương trình khuyến mại" (mã 2.001474) — cổng
DVC Bộ Công Thương dichvucong-tthc.moit.gov.vn, dùng chung cho Sở Công Thương mọi tỉnh.

Bước 1 là HAI form Form.io trên cùng trang: form tài khoản/chủ hồ sơ và form tờ khai Mẫu 06.
⚠ Tờ khai dùng lại 5 field-key của khối tài khoản: data[fullname], data[phoneNumber], data[province],
data[email], data[address] → mapper gắn OCCURRENCE 0 (tài khoản) / 1 (tờ khai). Phường/xã thì KEY KHÁC:
data[district] (tài khoản) / data[village] (trụ sở trên tờ khai).

Nguồn: Thông báo sửa đổi, bổ sung nội dung CTKM (Mẫu 06) + CCCD người nộp (nếu có).
"""

_TB = "Thông báo sửa đổi, bổ sung nội dung chương trình khuyến mại (Mẫu 06)"

FIELDS: list[dict] = [
    # --- Người nộp = chủ tài khoản đăng nhập; CHỈ lấy từ CCCD ---
    {"name": "NguoiNop_HoTen", "desc": "Họ tên trên CCCD/thẻ căn cước có trong hồ sơ. IN HOA. KHÔNG lấy người "
        f"liên hệ hay người ký trên {_TB}."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/định danh cá nhân in trên CÙNG thẻ căn cước đó. Chỉ chữ số."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh in trên CÙNG thẻ căn cước đó, dd/mm/yyyy."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp in ở mặt sau CÙNG thẻ căn cước đó, dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCuTru", "desc": "Nơi thường trú / nơi cư trú in trên CÙNG thẻ căn cước đó, object "
        "{quocGia,tinh,xa,diaChi}; diaChi chỉ phần số nhà/thôn/đường, KHÔNG kèm phường/xã/tỉnh."},

    # --- Thương nhân thực hiện khuyến mại = CHỦ HỒ SƠ (đầu Thông báo) ---
    {"name": "ThuongNhan_Ten", "desc": f"Tên doanh nghiệp ở dòng 'Tên thương nhân:' trên {_TB}, chép đúng "
        "chữ hoa/thường như dòng đó. CHỈ khi văn bản không có dòng này mới lấy tên đơn vị ở góc trái trên."},
    {"name": "ThuongNhan_MaSoThue", "desc": f"'Mã số thuế' trên {_TB}. Chép NGUYÊN VĂN chữ số đọc được; "
        "KHÔNG tự bù chữ số bị thiếu/che."},
    {"name": "ThuongNhan_DiaChi", "desc": f"'Địa chỉ trụ sở chính' trên {_TB}, object {{quocGia,tinh,xa,"
        "diaChi,fullText}}. fullText = nguyên dòng địa chỉ; tinh='Tỉnh/Thành phố …'; xa=phường/xã; "
        "diaChi=số nhà/tòa nhà/đường (KHÔNG kèm phường/xã/tỉnh)."},
    {"name": "ThuongNhan_DienThoai", "desc": f"'Điện thoại' ở dòng thông tin thương nhân trên {_TB} "
        "(KHÔNG phải điện thoại người liên hệ). Chỉ chữ số, không tự bù số."},
    {"name": "ThuongNhan_Fax", "desc": f"'Fax' trên {_TB}. Chỉ chữ số."},
    {"name": "ThuongNhan_Email", "desc": f"Email thương nhân nếu IN trên {_TB}; không in thì bỏ."},
    {"name": "ThuongNhan_NguoiLienHe", "desc": f"Họ tên ở mục 'Người liên hệ' trên {_TB}."},
    {"name": "ThuongNhan_DienThoaiLienHe", "desc": "'Điện thoại' in CÙNG dòng 'Người liên hệ'. Chỉ chữ số."},

    # --- Đầu văn bản Thông báo ---
    {"name": "ThongBao_So", "desc": f"Số văn bản ('Số: …') của {_TB}, góc trái dưới tên thương nhân. Chép "
        "nguyên văn phần sau 'Số:'."},
    {"name": "ThongBao_NgayLap", "desc": f"Ngày ở dòng '<địa danh>, ngày … tháng … năm …' đầu {_TB}, "
        "dd/mm/yyyy."},
    {"name": "ThongBao_KinhGui", "desc": f"Nơi nhận ở dòng 'Kính gửi:' của {_TB}, chép nguyên văn, bỏ chữ "
        "'Kính gửi:'."},

    # --- Thông báo thực hiện khuyến mại GỐC mà văn bản này sửa đổi ---
    {"name": "ThongBaoGoc_So", "desc": "Số văn bản ở câu 'Căn cứ Thông báo thực hiện khuyến mại số … ngày …' "
        "(văn bản GỐC đang được sửa đổi, KHÔNG phải số của chính Thông báo sửa đổi này)."},
    {"name": "ThongBaoGoc_Ngay", "desc": "Ngày ở CÙNG câu 'Căn cứ Thông báo thực hiện khuyến mại số … ngày …', "
        "dd/mm/yyyy."},

    # --- Chương trình khuyến mại ---
    {"name": "CTKM_Ten", "desc": "'Tên chương trình khuyến mại', chép nguyên văn, không kèm dấu ngoặc kép."},
    {"name": "CTKM_NgayBatDauSuaDoi", "desc": "Ngày bắt đầu thực hiện NỘI DUNG SỬA ĐỔI, BỔ SUNG (mục 'Thời "
        "gian bắt đầu thực hiện nội dung sửa đổi, bổ sung'), dd/mm/yyyy. KHÔNG lấy ngày bắt đầu/kết thúc "
        "của cả chương trình khuyến mại. Văn bản không ghi rõ thì bỏ."},
    {"name": "CTKM_LyDoDieuChinh", "desc": "Nội dung mục 'Lý do điều chỉnh', chép nguyên văn."},
    {"name": "CTKM_CamKet", "desc": "Các gạch đầu dòng cam kết ở cuối văn bản ('… cam kết:'), chép nguyên văn, "
        "mỗi cam kết một dòng (ngăn cách bằng xuống dòng)."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("NguoiNop_NgaySinh", "NguoiNop_NgayCap", "ThongBao_NgayLap", "ThongBaoGoc_Ngay",
              "CTKM_NgayBatDauSuaDoi"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("NguoiNop_NoiCuTru", "ThuongNhan_DiaChi"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

# ---- UI Form.io (data[...]) — field-key lấy từ DOM thật. Key trùng giữa 2 form → mapper gắn occurrence.
UI_COMP_BY_NAME = {
    # --- Khối TÀI KHOẢN NỘP HỒ SƠ (occurrence 0 cho key trùng) ---
    "data[fullname]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[birthday]": "dom-date",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[email]": "dom-input",
    "data[noidungyeucaugiaiquyet]": "dom-input",
    # --- Khối CHỦ HỒ SƠ = thương nhân ---
    "data[isOwnerDossier]": "dom-checkbox",
    "data[ownerFullname]": "dom-input",
    "data[ownertaxCode]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerAddress]": "dom-input",
    # --- Tờ khai Mẫu 06: đầu đơn ---
    "data[registerNumber]": "dom-input",
    "data[tinhThanhPhoNopDon]": "dom-select",
    "data[ngayNopDon]": "dom-date",
    "data[kinhGui]": "dom-input",
    # --- Tờ khai: thông tin doanh nghiệp (fullname/province/address/phoneNumber/email occurrence 1) ---
    "data[village]": "dom-select",
    "data[fax]": "dom-input",
    "data[contactPerson]": "dom-input",
    "data[phone]": "dom-input",
    "data[registerNumberSubmitted]": "dom-input",
    "data[submissionDate]": "dom-date",
    # --- Tờ khai: chương trình khuyến mại ---
    "data[promotionName]": "dom-input",
    "data[startDate]": "dom-date",
    "data[lyDoDieuChinh]": "dom-input",
    "data[CamKetKhac]": "dom-input",
}
