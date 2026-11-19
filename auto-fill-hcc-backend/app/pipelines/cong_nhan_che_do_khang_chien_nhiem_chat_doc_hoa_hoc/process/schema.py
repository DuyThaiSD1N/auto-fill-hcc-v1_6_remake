"""Compact schema cho "Công nhận và giải quyết chế độ ưu đãi người hoạt động kháng chiến bị nhiễm chất độc hóa học"
(1.010816) — cổng Bộ Nội vụ (Form.io).

Hồ sơ: Bản khai Mẫu số 09 (Phụ lục I NĐ 131/2021/NĐ-CP) + CCCD + giấy tờ ghi nhận thời gian tham gia kháng chiến (giấy
X Y Z, quyết định phục viên / xuất ngũ, lý lịch, giấy xác nhận phiên hiệu Mẫu 37…) + giấy tờ ghi nhận mắc bệnh (bản tóm
tắt hồ sơ bệnh án) hoặc giấy xác nhận có vợ/chồng nhưng không có con đẻ.

Hai vai:
- ChuHoSo_*  : NGƯỜI HOẠT ĐỘNG KHÁNG CHIẾN ở Mục 1 Bản khai (luôn còn sống, tự khai) = chủ hồ sơ + người khai Mục 1.
- NguoiNop_* : người nộp = tài khoản đăng nhập, chỉ khi khác chủ hồ sơ và có CCCD khớp tài khoản.
"""

_AREA = "object {quocGia,tinh,xa,chiTietDuoiXa}"

FIELDS: list[dict] = [
    {"name": "ChuHoSo_HoTen", "desc": "Họ và tên người hoạt động kháng chiến ở Mục 1 Bản khai Mẫu 09 (đối chiếu CCCD đúng "
        "người). Chép đúng dấu; KHÔNG lấy người nộp, KHÔNG lấy con đẻ ở Mục 2."},
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh người hoạt động kháng chiến, dd/mm/yyyy (\"3/7/1950\" → 03/07/1950). "
        "Ưu tiên CCCD đúng người, rồi Mục 1 Bản khai."},
    {"name": "ChuHoSo_GioiTinh", "desc": 'Giới tính người hoạt động kháng chiến: "Nam" hoặc "Nữ" (ô "Nam/Nữ" Mục 1, CCCD).'},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/CMND người hoạt động kháng chiến (\"CCCD số\" Mục 1, CCCD), chỉ chữ số."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD của người hoạt động kháng chiến, dd/mm/yyyy, đi cùng đúng số CCCD."},
    {"name": "ChuHoSo_NoiCap", "desc": "Nơi cấp CCCD của người hoạt động kháng chiến. Viết tắt kiểu \"Cục CS QLHC về TTXH\", "
        "\"Cục Csát QLý trật tự xã hội Bộ CA\" → \"Cục Cảnh sát quản lý hành chính về trật tự xã hội\"."},
    {"name": "ChuHoSo_QueQuan", "desc": f"Quê quán người hoạt động kháng chiến (Mục 1 \"Quê quán\", CCCD \"Quê quán\"), {_AREA}. "
        "Ghi xã/phường CŨ đúng như giấy, mapper tự đổi sang đơn vị hiện hành."},
    {"name": "ChuHoSo_NoiThuongTru", "desc": f"Nơi thường trú người hoạt động kháng chiến (Mục 1 \"Nơi thường trú\", CCCD), "
        f"{_AREA}. chiTietDuoiXa = số nhà, kiệt/hẻm, đường, tổ, thôn (vd \"K12/3 Lê Lợi\")."},
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại ở Mục 1 Bản khai, chỉ chữ số."},

    {"name": "NguoiNop_HoTen", "desc": "Họ tên người nộp — CHỈ trả theo nguoi_nop_context (thẻ CCCD khớp tài khoản)."},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD người nộp, từ đúng thẻ khớp tài khoản."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người nộp, dd/mm/yyyy, từ đúng thẻ khớp tài khoản."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người nộp "Nam"/"Nữ", từ đúng thẻ khớp tài khoản.'},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp CCCD người nộp, dd/mm/yyyy."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp CCCD người nộp."},
    {"name": "NguoiNop_NoiCuTru", "desc": f"Nơi cư trú / thường trú người nộp trên thẻ khớp tài khoản, {_AREA}."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại người nộp nếu giấy tờ đúng người ghi rõ."},

    {"name": "HDKC_TinhTrangSucKhoe", "desc": "Mục 1 \"Tình trạng bệnh tật, sức khỏe hiện nay\": chép đủ các bệnh, dị dạng, "
        "dị tật, ngăn bằng dấu phẩy, sửa chính tả rõ ràng (\"tiểu đường, cao huyết áp\"). Trường hợp vô sinh "
        "ghi \"có vợ hoặc có chồng nhưng không có con đẻ\"."},
    {"name": "HDKC_QuaTrinh", "desc": "Bảng \"Có quá trình hoạt động kháng chiến ở vùng quân đội Mỹ sử dụng chất độc hóa "
        "học\" Mục 1: MỖI giai đoạn một item {thoiGian, coQuan, diaBan} theo thứ tự trên giấy. BỎ dòng in sẵn \"Từ tháng "
        "... năm ... đến tháng ... năm ...\". Chữ viết xuống dòng trong cùng ô gộp vào cùng item."},
    {"name": "HDKC_ConDe", "desc": "Bảng Mục 2 \"Phần khai về con đẻ\" (con dị dạng, dị tật): mỗi người một item "
        "{hoTen, namSinh, giayTo, tinhTrang}; giayTo = số CCCD/CMND/GKS kèm ngày cấp, nơi cấp. Bảng trống thì trả []."},
    {"name": "HoSoDinhKem", "desc": "Danh sách giấy tờ THỰC CÓ trong hồ sơ, mỗi item {tenGiayTo, loaiBan}; Bản khai Mẫu 09 "
        "đứng đầu (\"Bản chính\"); giấy tờ chứng thực/photo ghi \"Bản sao\". Không liệt kê giấy không có."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("ChuHoSo_NgaySinh", "ChuHoSo_NgayCap", "NguoiNop_NgaySinh", "NguoiNop_NgayCap"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("ChuHoSo_QueQuan", "ChuHoSo_NoiThuongTru", "NguoiNop_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
for _name in ("HDKC_QuaTrinh", "HDKC_ConDe", "HoSoDinhKem"):
    COMPACT_COMP_BY_NAME[_name] = "x-array"

UI_COMP_BY_NAME: dict[str, str] = {
    # Phần I — người nộp (occurrence 0; họ tên / ngày sinh / CCCD cổng khoá theo tài khoản nên không phát).
    "data[gender]": "dom-select",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",
    "data[isOwnerDossierCheck]": "dom-checkbox",
    # Phần II — chủ hồ sơ = người hoạt động kháng chiến.
    "data[chonDoiTuong1]": "dom-select",
    "data[ownerFullname]": "dom-input",
    "data[ownerBirthday]": "dom-date",
    "data[ownerGender]": "dom-select",
    "data[ownerIdentityNumber]": "dom-input",
    "data[ownerIdentityDate]": "dom-date",
    "data[ownerIdIssuePlace]": "dom-input",
    "data[ownerProvince]": "dom-select",
    "data[ownerDistrict]": "dom-select",
    "data[ownerAddress]": "dom-input",
    "data[ownerPhoneNumber]": "dom-input",
    "data[ownerNation]": "dom-select",
    # Phần IV — eForm Bản khai Mẫu 09 Mục 1 (key trùng Phần I → occurrence 1).
    "data[fullname]": "dom-input",
    "data[identityNumber]": "dom-input",
    "data[birthday]": "dom-date",
    "data[identityAgency]": "dom-select",
    "data[village]": "dom-select",
    "data[province1]": "dom-select",
    "data[village1]": "dom-select",
    "data[address1]": "dom-input",
    "data[tinhTrang]": "dom-input",
}

# Datagrid (FE tự bấm "Thêm dòng" theo chỉ số lớn nhất).
MAX_HO_SO_ROWS = 10
MAX_QUA_TRINH_ROWS = 12
MAX_CON_DE_ROWS = 8
for _i in range(MAX_HO_SO_ROWS):
    UI_COMP_BY_NAME[f"data[hoSoDinhKem][{_i}][textField1]"] = "dom-input"
    UI_COMP_BY_NAME[f"data[hoSoDinhKem][{_i}][textField2]"] = "dom-input"
for _i in range(MAX_QUA_TRINH_ROWS):
    for _col in ("thoiGian", "coQuan", "diaBan"):
        UI_COMP_BY_NAME[f"data[quaTrinh][{_i}][{_col}]"] = "dom-input"
for _i in range(MAX_CON_DE_ROWS):
    for _col in ("hoTen", "namSinh", "giayTo", "tinhTrang"):
        UI_COMP_BY_NAME[f"data[conDe][{_i}][{_col}]"] = "dom-input"
