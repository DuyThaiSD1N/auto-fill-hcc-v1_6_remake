"""Compact schema for "Xác định mức độ khuyết tật".

The LLM returns OCR-derived facts only. The mapper derives Form.io DOM actions
for requester/owner, disabled person, representative, disability type and
activity-level radios.
"""

FIELDS: list[dict] = [
    # CCCD/CMND của chủ hồ sơ/người nộp.
    {"name": "Cccd_HoTen", "desc": "Họ tên trên CCCD/CMND của chủ hồ sơ/người nộp."},
    {"name": "Cccd_SoDinhDanh", "desc": "Số định danh/CCCD/CMND; có thể đọc từ MRZ mặt sau."},
    {"name": "Cccd_NgaySinh", "desc": "Ngày sinh trên CCCD/CMND, dd/mm/yyyy."},
    {"name": "Cccd_GioiTinh", "desc": 'Giới tính trên CCCD/CMND: "Nam" hoặc "Nữ".'},
    {"name": "Cccd_NgayCap",
     "desc": "Ngày cấp CCCD/CMND, dd/mm/yyyy. Bắt buộc cố đọc từ mặt sau nếu có."},
    {"name": "Cccd_NoiCap",
     "desc": 'Nơi cấp CCCD/CMND. Nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT..." '
             'thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội".'},
    {"name": "Cccd_NoiCuTru",
     "desc": "Nơi thường trú/cư trú trên CCCD, object {quocGia,tinh,xa,diaChi}."},

    # Đơn đề nghị.
    {"name": "DeNghi_NoiDung",
     "desc": 'Nội dung đề nghị trong đơn: "xac_dinh" nếu chọn Xác định mức độ và cấp giấy; '
             '"xac_dinh_lai" nếu chọn Xác định lại mức độ và cấp giấy/cấp đổi/cấp lại.'},

    # Người khuyết tật.
    {"name": "Nkt_HoTen", "desc": "Họ tên người được xác định mức độ khuyết tật."},
    {"name": "Nkt_NgaySinh", "desc": "Ngày sinh người khuyết tật, dd/mm/yyyy; bổ sung từ hồ sơ bệnh án/trích lục nếu đơn thiếu."},
    {"name": "Nkt_SoDinhDanh", "desc": "Số định danh/CCCD của người khuyết tật nếu có; bổ sung từ hồ sơ bệnh án/trích lục nếu đơn để trống."},
    {"name": "Nkt_GioiTinh", "desc": 'Giới tính người khuyết tật: "Nam" hoặc "Nữ".'},
    {"name": "Nkt_ThuongTru", "desc": "Hộ khẩu thường trú người khuyết tật, object {quocGia,tinh,xa,diaChi}."},
    {"name": "Nkt_NoiOHienNay", "desc": "Nơi ở hiện nay người khuyết tật, object {quocGia,tinh,xa,diaChi}."},

    # Người đại diện hợp pháp.
    {"name": "Ndd_HoTen", "desc": "Họ tên người đại diện hợp pháp trên đơn đề nghị."},
    {"name": "Ndd_SoDinhDanh", "desc": "Số CMND/CCCD của người đại diện hợp pháp."},
    {"name": "Ndd_QuanHe", "desc": 'Quan hệ với người khuyết tật, trả theo nhãn gốc nếu có: "bố đẻ", "mẹ đẻ", "cha", "mẹ"...'},
    {"name": "Ndd_SoDienThoai", "desc": "Số điện thoại người đại diện hợp pháp, số di động VN nếu có."},
    {"name": "Ndd_NoiCuTru", "desc": "Địa chỉ thường trú/nơi ở người đại diện, object {quocGia,tinh,xa,diaChi}."},

    # Bảng dạng khuyết tật.
    {"name": "KhuyetTat_BangDanhDau",
     "desc": 'Bảng "Thông tin về dạng khuyết tật" đọc THEO TỪNG DÒNG. Object: key là số dòng in trên '
             'đơn ("1","1.1",...,"6","6.3"), value là "co" nếu dấu X/✓ nằm ở cột "Có", "khong" nếu dấu '
             'nằm ở cột "Không", "" nếu dòng để trống hoặc KHÔNG chắc dấu thuộc cột nào. Trả ĐỦ mọi dòng '
             'đọc được, kể cả dòng "khong" — đây là nguồn chính, không được chỉ liệt kê dòng "co".'},
    {"name": "KhuyetTat_DanhMuc",
     "desc": 'Danh sách nhóm khuyết tật được tích "Có": array mã "kt1".."kt6" tương ứng vận động, nghe nói, nhìn, thần kinh tâm thần, trí tuệ, khác.'},
    {"name": "KhuyetTat_ChiTiet",
     "desc": 'Danh sách mục con được tích "Có": array mã dạng "kt5_1", "kt5_3"... Chỉ trả mục thấy được đánh dấu rõ trên đơn.'},

    # Bảng mức độ thực hiện hoạt động.
    {"name": "MucDo_HoatDong",
     "desc": 'Object ánh xạ số dòng "1".."10" sang một trong "THD", "CTG", "KTHD", "KXD" theo ô được đánh dấu trong bảng mức độ hoạt động.'},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in ("Cccd_NgaySinh", "Cccd_NgayCap", "Nkt_NgaySinh"):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in ("Cccd_NoiCuTru", "Nkt_ThuongTru", "Nkt_NoiOHienNay", "Ndd_NoiCuTru"):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
for _name in ("KhuyetTat_BangDanhDau", "KhuyetTat_DanhMuc", "KhuyetTat_ChiTiet", "MucDo_HoatDong"):
    COMPACT_COMP_BY_NAME[_name] = "raw"

UI_COMP_BY_NAME = {
    # Người nộp/chủ hồ sơ.
    "data[isOwnerDossierCheck]": "dom-checkbox",
    "data[fullname]": "dom-input",
    "data[birthday]": "dom-date",
    "data[gender]": "dom-select",
    "data[identityNumber]": "dom-input",
    "data[identityDate]": "dom-date",
    "data[idIssuePlace]": "dom-input",
    "data[province]": "dom-select",
    "data[district]": "dom-select",
    "data[address]": "dom-input",
    "data[phoneNumber]": "dom-input",

    # Chủ hồ sơ chỉ dùng khi về sau có ca người nộp khác chủ hồ sơ.
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

    # Nội dung đề nghị.
    "data[chonNoiDungDeNghi][]": "dom-checkbox",

    # Người khuyết tật.
    "data[NktHoTen]": "dom-input",
    "data[NktNgaySinh]": "dom-date",
    "data[NktSoDinhdanh]": "dom-input",
    "data[NktGioiTinh]": "dom-select",
    "data[NktMaTinh]": "dom-select",
    "data[NktMaXa]": "dom-select",
    "data[NktDiachi]": "dom-input",
    "data[NktNOHTMaTinh]": "dom-select",
    "data[NktNOHTMaXa]": "dom-select",
    "data[NktNOHTDiaChi]": "dom-input",

    # Người đại diện hợp pháp.
    "data[NddHoTen]": "dom-input",
    "data[NddSoDinhdanh]": "dom-input",
    "data[NddQuanheNkt]": "dom-select",
    "data[NddSodienthoai]": "dom-input",
    "data[NddMaTinh]": "dom-select",
    "data[NddMaXa]": "dom-select",
    "data[NddDiachi]": "dom-input",
}

DISABILITY_RADIO_FIELDS = {
    "kt1": "data[khuyetTat1Obj][khuyetTatRadio]",
    "kt1_1": "data[khuyetTat1Obj][khuyetTatRadio1]",
    "kt1_2": "data[khuyetTat1Obj][khuyetTatRadio2]",
    "kt1_3": "data[khuyetTat1Obj][khuyetTatRadio3]",
    "kt1_4": "data[khuyetTat1Obj][khuyetTatRadio4]",
    "kt1_5": "data[khuyetTat1Obj][khuyetTatRadio5]",
    "kt1_6": "data[khuyetTat1Obj][khuyetTatRadio6]",
    "kt2": "data[khuyetTat2Obj][khuyetTatRadio]",
    "kt2_1": "data[khuyetTat2Obj][khuyetTatRadio1]",
    "kt2_2": "data[khuyetTat2Obj][khuyetTatRadio2]",
    "kt2_3": "data[khuyetTat2Obj][khuyetTatRadio3]",
    "kt2_4": "data[khuyetTat2Obj][khuyetTatRadio4]",
    "kt2_5": "data[khuyetTat2Obj][khuyetTatRadio5]",
    "kt2_6": "data[khuyetTat2Obj][khuyetTatRadio6]",
    "kt3": "data[khuyetTat3Obj][khuyetTatRadio]",
    "kt3_1": "data[khuyetTat3Obj][khuyetTatRadio1]",
    "kt3_2": "data[khuyetTat3Obj][khuyetTatRadio2]",
    "kt3_3": "data[khuyetTat3Obj][khuyetTatRadio3]",
    "kt3_4": "data[khuyetTat3Obj][khuyetTatRadio4]",
    "kt3_5": "data[khuyetTat3Obj][khuyetTatRadio5]",
    "kt3_6": "data[khuyetTat3Obj][khuyetTatRadio6]",
    "kt3_7": "data[khuyetTat3Obj][khuyetTatRadio7]",
    "kt4": "data[khuyetTat4Obj][khuyetTatRadio]",
    "kt4_1": "data[khuyetTat4Obj][khuyetTatRadio1]",
    "kt4_2": "data[khuyetTat4Obj][khuyetTatRadio2]",
    "kt4_3": "data[khuyetTat4Obj][khuyetTatRadio3]",
    "kt4_4": "data[khuyetTat4Obj][khuyetTatRadio4]",
    "kt4_5": "data[khuyetTat4Obj][khuyetTatRadio5]",
    "kt5": "data[khuyetTat5Obj][khuyetTatRadio]",
    "kt5_1": "data[khuyetTat5Obj][khuyetTatRadio1]",
    "kt5_2": "data[khuyetTat5Obj][khuyetTatRadio2]",
    "kt5_3": "data[khuyetTat5Obj][khuyetTatRadio3]",
    "kt5_4": "data[khuyetTat5Obj][khuyetTatRadio4]",
    "kt6": "data[khuyetTat6Obj][khuyetTatRadio]",
    "kt6_1": "data[khuyetTat6Obj][khuyetTatRadio1]",
    "kt6_2": "data[khuyetTat6Obj][khuyetTatRadio2]",
    "kt6_3": "data[khuyetTat6Obj][khuyetTatRadio3]",
}

# Số dòng con của từng nhóm trong bảng "dạng khuyết tật" (Mẫu số 01) — dùng để suy nhóm cha ⇄ dòng con.
DISABILITY_GROUP_CHILDREN = {"kt1": 6, "kt2": 6, "kt3": 7, "kt4": 5, "kt5": 4, "kt6": 3}

MUC_DO_RADIO_FIELDS = {
    "1": "data[mucDoKhuyetTatObj][mucDoRadio1]",
    "2": "data[mucDoKhuyetTatObj][mucDoRadio2]",
    "3": "data[mucDoKhuyetTatObj][mucDoRadio3]",
    "4": "data[mucDoKhuyetTatObj][mucDoRadio4]",
    "5": "data[mucDoKhuyetTatObj][mucDoRadio5]",
    "6": "data[mucDoKhuyetTatObj][mucDoRadio6]",
    "7": "data[mucDoKhuyetTatObj][mucDoRadio7]",
    "8": "data[mucDoKhuyetTatObj][mucDoRadio8]",
    "9": "data[mucDoKhuyetTatObj][mucDoRadio9]",
    "10": "data[mucDoKhuyetTatObj][mucDoRadio10]",
}

UI_COMP_BY_NAME.update({name: "dom-radio" for name in DISABILITY_RADIO_FIELDS.values()})
UI_COMP_BY_NAME.update({name: "dom-radio" for name in MUC_DO_RADIO_FIELDS.values()})
