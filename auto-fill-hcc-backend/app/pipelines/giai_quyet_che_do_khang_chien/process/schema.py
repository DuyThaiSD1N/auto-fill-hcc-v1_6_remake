"""Schema vai trò cho thủ tục giải quyết chế độ người hoạt động kháng chiến.

- ``ChuHoSo_*``: cá nhân nhận mai táng phí/đại diện thân nhân tại Mục 2; nếu
  Mục 2 không có cá nhân thì là chính người đề nghị tại Mục 1.
- ``NguoiNop_*``: người thực tế nộp hồ sơ, chỉ trích từ tài liệu khớp mỏ neo UI.
- ``NguoiCoCong_*``: người hoạt động kháng chiến/người có công tại Mục 1,
  tách biệt khỏi chủ hồ sơ khi người đó đã chết.

Các field ``HDKC_*`` và ``HoSoDinhKem`` là dữ liệu nghiệp vụ, không dùng để suy
vai trò người nộp.
"""

FIELDS: list[dict] = [
    # Ưu tiên người nhận/đại diện tại Mục 2; chỉ dùng Mục 1 khi không có cá nhân ở Mục 2.
    {"name": "ChuHoSo_HoTen", "desc": "Họ tên chủ hồ sơ. Với Mẫu 12 lấy cá nhân nhận mai táng phí tại Mục 2a (hoặc người nhận trợ cấp tại Mục 3 nếu Mục 2a cùng người/thiếu); tuyệt đối không lấy người có công đã chết ở Mục 1. Với Mẫu 11 có đại diện thân nhân tại Mục 2 thì lấy người này; chỉ lấy người đề nghị tại Mục 1 khi Mục 2 không có cá nhân."},
    {"name": "ChuHoSo_NgaySinh", "desc": "Ngày sinh chủ hồ sơ, dd/mm/yyyy. Ưu tiên CCCD đúng người rồi Mục 2/3 Bản khai; Mẫu 11 lấy giấy tờ/Mục 1 đúng người."},
    {"name": "ChuHoSo_GioiTinh", "desc": 'Giới tính chủ hồ sơ, chỉ "Nam" hoặc "Nữ" theo giấy tờ đúng người.'},
    {"name": "ChuHoSo_SoDinhDanh", "desc": "Số CCCD/CMND chủ hồ sơ, chỉ chữ số; không lấy số của người có công đã chết."},
    {"name": "ChuHoSo_NgayCap", "desc": "Ngày cấp CCCD/CMND chủ hồ sơ, dd/mm/yyyy, phải đi cùng đúng số giấy tờ của chủ hồ sơ."},
    {"name": "ChuHoSo_NoiCap", "desc": "Nơi cấp CCCD/CMND chủ hồ sơ từ đúng giấy tờ; không lấy cơ quan cấp giấy của người có công đã chết."},
    {"name": "ChuHoSo_NoiCuTru", "desc": "Nơi thường trú chủ hồ sơ, object {quocGia,tinh,xa,diaChi}; Mẫu 12 ưu tiên Mục 2/3, CCCD chỉ bổ sung phần thiếu."},
    {"name": "ChuHoSo_QueQuan", "desc": "Quê quán chủ hồ sơ, object {quocGia,tinh,xa,diaChi}; ưu tiên CCCD đúng người."},
    {"name": "ChuHoSo_DienThoai", "desc": "Số điện thoại của chủ hồ sơ tại Mục 2/3; không lấy số của người có công đã chết."},
    {"name": "ChuHoSo_QuocTich", "desc": "Quốc tịch chủ hồ sơ khi giấy tờ đúng người ghi rõ."},
    {"name": "ChuHoSo_MoiQuanHe", "desc": "Mối quan hệ của chủ hồ sơ/người nhận mai táng phí với người có công đã chết, lấy đúng dòng Mục 2/3."},

    # Người nộp chỉ được trích từ tài liệu đã khớp mỏ neo UI.
    {"name": "NguoiNop_HoTen", "desc": "Họ tên người nộp, chỉ trả khi requester_context xác nhận tài liệu khớp UI."},
    {"name": "NguoiNop_NgaySinh", "desc": "Ngày sinh người nộp, dd/mm/yyyy, từ đúng tài liệu khớp UI."},
    {"name": "NguoiNop_GioiTinh", "desc": 'Giới tính người nộp, chỉ "Nam" hoặc "Nữ" theo đúng giấy tờ.'},
    {"name": "NguoiNop_SoDinhDanh", "desc": "Số CCCD/CMND người nộp; phải thuộc tài liệu đã khớp UI."},
    {"name": "NguoiNop_NgayCap", "desc": "Ngày cấp giấy tờ người nộp, dd/mm/yyyy, từ đúng tài liệu khớp UI."},
    {"name": "NguoiNop_NoiCap", "desc": "Nơi cấp giấy tờ người nộp từ đúng tài liệu khớp UI."},
    {"name": "NguoiNop_NoiCuTru", "desc": "Nơi cư trú người nộp, object {quocGia,tinh,xa,diaChi}, từ đúng tài liệu khớp UI."},
    {"name": "NguoiNop_DienThoai", "desc": "Số điện thoại người nộp nếu tài liệu đúng người ghi rõ."},
    {"name": "NguoiNop_Email", "desc": "Email người nộp nếu tài liệu đúng người ghi rõ."},

    # Người có công là dữ liệu nghiệp vụ Mục 1, không phải chủ hồ sơ khi đã chết.
    {"name": "NguoiCoCong_HoTen", "desc": "Họ tên người hoạt động kháng chiến/người có công tại Mục 1. Phải trả khi người tại Mục 1 khác chủ hồ sơ; với Mẫu 12 đây là người đã chết."},
    {"name": "NguoiCoCong_NgaySinh", "desc": "Ngày sinh người có công, dd/mm/yyyy; ưu tiên trích lục/CCCD đúng người rồi Mục 1."},
    {"name": "NguoiCoCong_GioiTinh", "desc": 'Giới tính người có công, chỉ "Nam" hoặc "Nữ".'},
    {"name": "NguoiCoCong_SoDinhDanh", "desc": "Số CCCD/CMND người có công, chỉ chữ số; không lấy số chủ hồ sơ ở Mục 2."},
    {"name": "NguoiCoCong_NgayCap", "desc": "Ngày cấp giấy tờ người có công, dd/mm/yyyy, đi cùng đúng số giấy tờ."},
    {"name": "NguoiCoCong_NoiCap", "desc": "Nơi cấp giấy tờ người có công từ đúng giấy tờ/trích lục."},
    {"name": "NguoiCoCong_QueQuan", "desc": "Quê quán người có công, object {quocGia,tinh,xa,diaChi}, lấy đúng Mục 1."},
    {"name": "NguoiCoCong_NoiCuTru", "desc": "Nơi thường trú người có công, object {quocGia,tinh,xa,diaChi}, lấy đúng Mục 1/trích lục."},
    {"name": "NguoiCoCong_QuocTich", "desc": "Quốc tịch người có công khi giấy tờ ghi rõ."},
    {"name": "NguoiCoCong_NgayMat", "desc": "Ngày người hoạt động kháng chiến/người có công chết, dd/mm/yyyy, lấy từ Bản khai Mẫu 12 hoặc trích lục khai tử."},

    # Dữ liệu nghiệp vụ Mẫu 11/Mẫu 12.
    {"name": "HDKC_CheDo", "desc": "Nội dung chế độ đề nghị giải quyết, chép theo tiêu đề Bản khai."},
    {"name": "HDKC_BiDanh", "desc": "Bí danh chủ hồ sơ tại Mục 1 Bản khai; bỏ nếu trống."},
    {"name": "HDKC_QuaTrinh", "desc": "Quá trình tham gia hoạt động kháng chiến: thời gian, đơn vị, cấp bậc/chức vụ; tóm tắt một dòng từ Bản khai/Sổ BHXH."},
    {"name": "HDKC_ThanhTich", "desc": "Thành tích giúp đỡ cách mạng nếu Bản khai ghi rõ."},
    {"name": "HDKC_DuocTang", "desc": "Hình thức khen thưởng, số và ngày quyết định nếu giấy tờ ghi rõ."},
    {"name": "HoSoDinhKem", "desc": "Danh sách giấy tờ kèm theo, mỗi item {tenGiayTo,loaiBan}; giữ thứ tự và bỏ item trống."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "ChuHoSo_NgaySinh",
    "ChuHoSo_NgayCap",
    "NguoiNop_NgaySinh",
    "NguoiNop_NgayCap",
    "NguoiCoCong_NgaySinh",
    "NguoiCoCong_NgayCap",
    "NguoiCoCong_NgayMat",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "ChuHoSo_NoiCuTru",
    "ChuHoSo_QueQuan",
    "NguoiNop_NoiCuTru",
    "NguoiCoCong_QueQuan",
    "NguoiCoCong_NoiCuTru",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"
COMPACT_COMP_BY_NAME["HoSoDinhKem"] = "x-array"

UI_COMP_BY_NAME = {
    # Người nộp hồ sơ, occurrence 0 với các key được dùng lại ở Mục 1/Mục 2.
    "data[chonDoiTuong]": "dom-select",
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
    "data[email]": "dom-input",
    "data[isOwnerDossierCheck]": "dom-checkbox",

    # Chủ hồ sơ.
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

    # Hồ sơ kèm theo.
    "data[hoSoDinhKem][0][textField1]": "dom-input",
    "data[hoSoDinhKem][0][textField2]": "dom-input",

    # Mục 1: người hoạt động kháng chiến/người có công.
    "data[CheDo]": "dom-input",
    "data[biDanh]": "dom-input",
    "data[identityAgency]": "dom-select",
    "data[quaTrinh]": "dom-input",
    "data[thanhTich]": "dom-input",
    "data[duocTang]": "dom-input",

    # Mục 2: đại diện thân nhân hưởng trợ cấp.
    "data[fullname1]": "dom-input",
    "data[birthday1]": "dom-date",
    "data[gender1]": "dom-select",
    "data[identityNumber1]": "dom-input",
    "data[identityDate1]": "dom-date",
    "data[identityAgency1]": "dom-select",
    "data[province1]": "dom-select",
    "data[district1]": "dom-select",
    "data[address1]": "dom-input",
    "data[province2]": "dom-select",
    "data[district2]": "dom-select",
    "data[address2]": "dom-input",
    "data[moiQH]": "dom-input",
    "data[ngayMat]": "dom-date",
}
