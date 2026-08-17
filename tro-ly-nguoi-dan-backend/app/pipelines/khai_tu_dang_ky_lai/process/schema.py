"""Compact schema for "Đăng ký lại khai tử".

The LLM returns only role/source facts. UI defaults, duplicated identity fields,
and web-component names are derived in Python.
"""

FIELDS: list[dict] = [
    # Người yêu cầu trong hồ sơ/tờ khai.
    {"name": "Requester_FullName", "desc": "Họ tên người yêu cầu đăng ký lại khai tử."},
    {"name": "Requester_IdNumber", "desc": "Số định danh/CCCD/CMND của người yêu cầu."},
    {"name": "Requester_IdIssueDate", "desc": "Ngày cấp giấy tờ tùy thân người yêu cầu, dd/mm/yyyy."},
    {"name": "Requester_IdIssuePlace", "desc": "Nơi cấp giấy tờ tùy thân người yêu cầu."},
    {"name": "Requester_ResidenceDomestic", "desc": "Nơi cư trú người yêu cầu, object {quocGia,tinh,xa,diaChi}; xa bắt buộc nếu giấy có."},
    {"name": "Requester_Relationship", "desc": "Quan hệ của người yêu cầu với người đã chết."},

    # Người được đăng ký lại khai tử.
    {"name": "Deceased_FullName", "desc": "Họ tên người được đăng ký lại khai tử/người đã chết."},
    {"name": "Deceased_BirthDate", "desc": "Ngày sinh người đã chết, dd/mm/yyyy; nếu chỉ có năm thì trả yyyy."},
    {"name": "Deceased_Gender", "desc": 'Giới tính người đã chết: "Nam" hoặc "Nữ".'},
    {"name": "Deceased_Ethnicity", "desc": "Dân tộc người đã chết."},
    {"name": "Deceased_Nationality", "desc": "Quốc tịch người đã chết nếu giấy ghi rõ hoặc khác Việt Nam."},
    {"name": "Deceased_IdNumber", "desc": "Số định danh/CCCD/CMND người đã chết nếu có."},
    {"name": "Deceased_IdIssueDate", "desc": "Ngày cấp giấy tờ tùy thân người đã chết, dd/mm/yyyy."},
    {"name": "Deceased_IdIssuePlace", "desc": "Nơi cấp giấy tờ tùy thân người đã chết."},
    {"name": "Deceased_ResidenceDomestic", "desc": "Nơi cư trú cuối cùng của người đã chết, object {quocGia,tinh,xa,diaChi}; xa bắt buộc nếu giấy có."},
    {"name": "Deceased_DeathDate", "desc": 'Ngày chết, dd/mm/yyyy; lấy từ "Đã chết vào lúc"/"Tử vong lúc".'},
    {"name": "Deceased_DeathTime", "desc": 'Giờ chết dạng "HH:mm"; ví dụ "09 giờ 40 phút" -> "09:40".'},
    {"name": "Deceased_DeathPlaceDomestic", "desc": "Nơi chết, object {quocGia,tinh,xa,diaChi}; xa bắt buộc nếu giấy có."},
    {"name": "Deceased_DeathCause", "desc": "Nguyên nhân chết."},

    # Giấy báo tử/giấy tờ thay thế.
    {"name": "DeathNotice_Type", "desc": "Loại giấy tờ báo tử/giấy tờ thay thế nếu giấy ghi rõ."},
    {"name": "DeathNotice_Number", "desc": "Số giấy báo tử/giấy tờ thay thế; chỉ trả nếu có giá trị thật."},
    {"name": "DeathNotice_IssueDate", "desc": "Ngày cấp/lập giấy báo tử/giấy tờ thay thế, dd/mm/yyyy; chỉ trả nếu có."},
    {"name": "DeathNotice_IssueAgency", "desc": "Cơ quan/cơ sở cấp giấy báo tử/giấy tờ thay thế; chỉ trả nếu có."},

    # Thông tin đăng ký khai tử trước đây.
    {"name": "PreviousDeathRegistration_AgencyProvince", "desc": "Tỉnh/thành phố của cơ quan đăng ký khai tử trước đây."},
    {"name": "PreviousDeathRegistration_AgencyCommune", "desc": "Xã/phường/thị trấn hoặc tên cơ quan đăng ký khai tử trước đây."},
    {"name": "PreviousDeathRegistration_Number", "desc": "Số đăng ký khai tử trước đây; chỉ trả nếu chắc chắn là số đăng ký cũ."},
    {"name": "PreviousDeathRegistration_BookNumber", "desc": "Quyển số đăng ký khai tử trước đây; chỉ trả nếu giấy ghi rõ."},
    {"name": "PreviousDeathRegistration_Date", "desc": "Ngày đăng ký khai tử trước đây, dd/mm/yyyy; chỉ trả nếu giấy ghi rõ."},

    # Đề nghị cấp bản sao.
    {"name": "CopyRequest_WantsCopy", "desc": '"Có" nếu tờ khai tích đề nghị cấp bản sao, "Không" nếu tích không.'},
    {"name": "CopyRequest_Quantity", "desc": "Số lượng bản sao đề nghị cấp, chỉ trả số nếu tờ khai ghi rõ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Requester_IdIssueDate",
    "Deceased_BirthDate",
    "Deceased_IdIssueDate",
    "Deceased_DeathDate",
    "DeathNotice_IssueDate",
    "PreviousDeathRegistration_Date",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "Requester_ResidenceDomestic",
    "Deceased_ResidenceDomestic",
    "Deceased_DeathPlaceDomestic",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # Người yêu cầu.
    "HoVaTenC": "x-input",
    "SoDinhDanhC": "x-input",
    "SoGiayToDinhDanhC": "x-input",
    "LoaiGiayToDinhDanhC": "x-select",
    "NgayCapDDC": "x-date",
    "NoiCapDDC": "x-input",
    "nycLoaiCuTru": "x-select",
    "nycNoiCuTru": "x-radio",
    "nycNoiCuTru_TrongNuoc": "x-select-area",
    "QuanHe": "x-input",
    # Đăng ký lại.
    "loaiDangKy": "x-radio",
    "coQuanDKTruocDay_filter": "x-select",
    "coQuanDKTruocDay": "x-select",
    "soDKTruocDay": "x-input",
    "quyenSoDKTruocDay": "x-input",
    "ngayDKTruocDay": "x-date-text",
    # Người được đăng ký lại khai tử.
    "HoTen": "x-input",
    "NgaySinh": "x-input",
    "GioiTinh": "x-select",
    "nktDanToc": "x-select",
    "nktQuocTich": "x-select",
    "SoDinhDanh": "x-input",
    "SoGiayToDinhDanh": "x-input",
    "LoaiGiayToDinhDanh": "x-select",
    "NgayCapDD": "x-date",
    "NoiCapDD": "x-input",
    "nktLoaiCuTru": "x-select",
    "nktNoiCuTru": "x-radio",
    "nktNoiCuTru_TrongNuoc": "x-select-area",
    "NgayMat": "x-date-text",
    "GioMat": "raw",
    "PhutMat": "raw",
    "nktNoiChet": "x-radio",
    "nktNoiChet_TrongNuoc": "x-select-area",
    "NguyenNhanMat": "x-input",
    # Giấy báo tử/giấy tờ thay thế.
    "gbtLoai": "x-select-default",
    "gbtSo": "x-input",
    "gbtNgay": "x-date",
    "gbtCoQuanCap": "x-input",
    # Bản sao.
    "CapBanSao": "x-radio",
    "SoLuong": "raw",
}

