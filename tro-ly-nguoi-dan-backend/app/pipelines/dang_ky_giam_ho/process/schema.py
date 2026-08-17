"""Compact schema for "Đăng ký giám hộ".

The LLM returns source facts only. UI field names and duplicated identity
fields are derived in Python from the iframe eForm DOM.
"""

FIELDS: list[dict] = [
    # I. Người yêu cầu đăng ký giám hộ.
    {"name": "Requester_FullName", "desc": "Họ tên người yêu cầu đăng ký giám hộ."},
    {"name": "Requester_IdNumber", "desc": "Số định danh/CCCD/CMND của người yêu cầu."},
    {"name": "Requester_IdIssueDate", "desc": "Ngày cấp giấy tờ tùy thân người yêu cầu, dd/mm/yyyy."},
    {"name": "Requester_IdIssuePlace", "desc": "Nơi cấp giấy tờ tùy thân người yêu cầu."},
    {"name": "Requester_ResidenceDomestic", "desc": "Nơi cư trú người yêu cầu, object {quocGia,tinh,xa,diaChi}; tinh/xa giữ loại đơn vị nếu giấy ghi."},

    # II. Người giám hộ.
    {"name": "Guardian_FullName", "desc": "Họ tên người giám hộ."},
    {"name": "Guardian_BirthDate", "desc": "Ngày sinh người giám hộ, dd/mm/yyyy."},
    {"name": "Guardian_Gender", "desc": 'Giới tính người giám hộ: "Nam" hoặc "Nữ".'},
    {"name": "Guardian_Ethnicity", "desc": "Dân tộc người giám hộ nếu giấy ghi rõ."},
    {"name": "Guardian_Nationality", "desc": "Quốc tịch người giám hộ nếu giấy ghi rõ hoặc khác Việt Nam."},
    {"name": "Guardian_IdNumber", "desc": "Số định danh/CCCD/CMND người giám hộ."},
    {"name": "Guardian_IdIssueDate", "desc": "Ngày cấp giấy tờ tùy thân người giám hộ, dd/mm/yyyy."},
    {"name": "Guardian_IdIssuePlace", "desc": "Nơi cấp giấy tờ tùy thân người giám hộ."},
    {"name": "Guardian_ResidenceDomestic", "desc": "Nơi cư trú người giám hộ, object {quocGia,tinh,xa,diaChi}; tinh/xa giữ loại đơn vị nếu giấy ghi."},

    # III. Người được giám hộ.
    {"name": "Ward_FullName", "desc": "Họ tên người được giám hộ."},
    {"name": "Ward_BirthDate", "desc": "Ngày sinh người được giám hộ, dd/mm/yyyy."},
    {"name": "Ward_Gender", "desc": 'Giới tính người được giám hộ: "Nam" hoặc "Nữ".'},
    {"name": "Ward_Ethnicity", "desc": "Dân tộc người được giám hộ."},
    {"name": "Ward_Nationality", "desc": "Quốc tịch người được giám hộ nếu giấy ghi rõ hoặc khác Việt Nam."},
    {"name": "Ward_IdNumber", "desc": "Số định danh cá nhân/CCCD/CMND người được giám hộ nếu có."},
    {"name": "Ward_IdIssueDate", "desc": "Ngày cấp giấy tờ tùy thân người được giám hộ, dd/mm/yyyy; chỉ trả nếu có."},
    {"name": "Ward_IdIssuePlace", "desc": "Nơi cấp giấy tờ tùy thân người được giám hộ; chỉ trả nếu có."},
    {"name": "Ward_ResidenceDomestic", "desc": "Nơi cư trú người được giám hộ, object {quocGia,tinh,xa,diaChi}; ưu tiên tờ khai."},
    {"name": "Ward_BirthCertificateNumber", "desc": "Số giấy khai sinh/bản khai sinh của người được giám hộ, ví dụ 234."},
    {"name": "Ward_BirthCertificateIssueDate", "desc": "Ngày cấp/ngày đăng ký giấy khai sinh của người được giám hộ, dd/mm/yyyy."},
    {"name": "Ward_BirthCertificateIssuePlace", "desc": "Cơ quan cấp/nơi đăng ký giấy khai sinh của người được giám hộ."},
    {"name": "Ward_BirthCertificateInfo", "desc": "Thông tin giấy khai sinh nếu đọc được, ví dụ số, nơi đăng ký, ngày đăng ký."},

    # IV. Nội dung đăng ký.
    {"name": "Registration_Agency", "desc": "Cơ quan kính gửi/cơ quan đăng ký giám hộ nếu tờ khai ghi rõ."},
    {"name": "Registration_RelationshipType", "desc": "Loại/quan hệ giám hộ nếu tờ khai ghi rõ."},
    {"name": "Registration_Reason", "desc": "Lý do đăng ký giám hộ."},
    {"name": "CopyRequest_WantsCopy", "desc": '"Có" nếu tờ khai tích đề nghị cấp bản sao, "Không" nếu tích không.'},
    {"name": "CopyRequest_Quantity", "desc": "Số lượng bản sao đề nghị cấp, chỉ trả số nếu tờ khai ghi rõ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Requester_IdIssueDate",
    "Guardian_BirthDate",
    "Guardian_IdIssueDate",
    "Ward_BirthDate",
    "Ward_IdIssueDate",
    "Ward_BirthCertificateIssueDate",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "Requester_ResidenceDomestic",
    "Guardian_ResidenceDomestic",
    "Ward_ResidenceDomestic",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # I. Người yêu cầu.
    "HoVaTenC": "x-input",
    "SoDinhDanhC": "x-input",
    "LoaiGiayToDinhDanhC": "x-select",
    "NgayCapDDC": "x-date",
    "NoiCapDDC": "x-input",
    "TT_SoNhaToDanPhoC": "x-input",
    "TT_TinhThanhC": "x-select",
    "TT_PhuongXaC": "x-select",

    # II. Người giám hộ.
    "hotenA": "x-input",
    "ngaysinhA": "x-date",
    "gioitinhA": "x-select",
    "dantocA": "x-select",
    "quoctichA": "x-select",
    "sodinhdanhA": "x-input",
    "loaigiaytoA": "x-select",
    "sodinhdanhA1": "x-input",
    "ngaycapA": "x-date",
    "noicapA": "x-input",
    "cutru1": "x-select",
    "noicutruA": "x-input",
    "tinhA": "x-select",
    "xaA": "x-select",

    # III. Người được giám hộ.
    "hotenB": "x-input",
    "ngaysinhB": "x-date",
    "gioitinhB": "x-select",
    "dantocB": "x-select",
    "quoctichB": "x-select",
    "sodinhdanhB": "x-input",
    "loaigiaytoB": "x-select",
    "sodinhdanhB1": "x-input",
    "ngaycapB": "x-date",
    "noicapB": "x-input",
    "cutru2": "x-select",
    "noicutruB": "x-input",
    "TinhB": "x-select",
    "XaB": "x-select",

    # IV. Nội dung đăng ký.
    "lydo": "x-input",
    "CapBanSao": "x-radio",
    "soluong": "raw",
}
