"""Compact schema for "Đăng ký nhận cha, mẹ, con".

The LLM returns source facts only. UI eForm fields are derived in Python from
the actual iframe DOM where C=requester, A=father/mother, B=child.
"""

FIELDS: list[dict] = [
    # I. Người yêu cầu.
    {"name": "Requester_FullName", "desc": "Họ tên người yêu cầu đăng ký nhận cha, mẹ, con."},
    {"name": "Requester_BirthDate", "desc": "Ngày sinh người yêu cầu, dd/mm/yyyy nếu có."},
    {"name": "Requester_IdNumber", "desc": "Số định danh/CCCD/CMND người yêu cầu."},
    {"name": "Requester_IdIssueDate", "desc": "Ngày cấp giấy tờ tùy thân người yêu cầu, dd/mm/yyyy."},
    {"name": "Requester_IdIssuePlace", "desc": "Nơi cấp giấy tờ tùy thân người yêu cầu."},
    {"name": "Requester_ResidenceDomestic", "desc": "Nơi cư trú người yêu cầu, object {quocGia,tinh,xa,diaChi}; ưu tiên tờ khai."},
    {"name": "Requester_PhoneNumber", "desc": "Số điện thoại người yêu cầu nếu giấy tờ ghi rõ."},
    {"name": "Requester_Email", "desc": "Email người yêu cầu nếu giấy tờ ghi rõ."},
    {"name": "Requester_RelationshipToRecognized", "desc": "Quan hệ với người được nhận cha/mẹ/con: Cha, Mẹ, Con hoặc Khác; có thể đọc là Bố."},

    # II. Cha/mẹ.
    {"name": "Parent_FullName", "desc": "Họ tên cha/mẹ trong phần Thông tin về cha/mẹ."},
    {"name": "Parent_BirthDate", "desc": "Ngày sinh cha/mẹ, dd/mm/yyyy."},
    {"name": "Parent_Gender", "desc": 'Giới tính cha/mẹ: "Nam" hoặc "Nữ".'},
    {"name": "Parent_Ethnicity", "desc": "Dân tộc cha/mẹ."},
    {"name": "Parent_Nationality", "desc": "Quốc tịch cha/mẹ nếu giấy ghi rõ hoặc khác Việt Nam."},
    {"name": "Parent_IdNumber", "desc": "Số định danh/CCCD/CMND cha/mẹ."},
    {"name": "Parent_IdIssueDate", "desc": "Ngày cấp giấy tờ tùy thân cha/mẹ, dd/mm/yyyy."},
    {"name": "Parent_IdIssuePlace", "desc": "Nơi cấp giấy tờ tùy thân cha/mẹ."},
    {"name": "Parent_ResidenceDomestic", "desc": "Nơi cư trú cha/mẹ, object {quocGia,tinh,xa,diaChi}; ưu tiên tờ khai."},

    # III. Người con.
    {"name": "Child_FullName", "desc": "Họ tên người con."},
    {"name": "Child_BirthDate", "desc": "Ngày sinh người con, dd/mm/yyyy."},
    {"name": "Child_Gender", "desc": 'Giới tính người con: "Nam" hoặc "Nữ".'},
    {"name": "Child_Ethnicity", "desc": "Dân tộc người con."},
    {"name": "Child_Nationality", "desc": "Quốc tịch người con nếu giấy ghi rõ hoặc khác Việt Nam."},
    {"name": "Child_IdNumber", "desc": "Số định danh cá nhân/CCCD/CMND của người con nếu có."},
    {"name": "Child_IdIssueDate", "desc": "Ngày cấp giấy tờ tùy thân người con, dd/mm/yyyy nếu có."},
    {"name": "Child_IdIssuePlace", "desc": "Nơi cấp giấy tờ tùy thân người con nếu có."},
    {"name": "Child_ResidenceDomestic", "desc": "Nơi cư trú người con, object {quocGia,tinh,xa,diaChi}; ưu tiên tờ khai."},
    {"name": "Child_BirthDocumentType", "desc": "Loại giấy tờ khai sinh/sinh như Giấy khai sinh hoặc Giấy chứng sinh nếu có."},
    {"name": "Child_BirthDocumentNumber", "desc": "Số giấy khai sinh/giấy chứng sinh của người con nếu có."},
    {"name": "Child_BirthDocumentIssueDate", "desc": "Ngày cấp/ngày đăng ký giấy khai sinh/giấy chứng sinh, dd/mm/yyyy."},
    {"name": "Child_BirthDocumentIssuePlace", "desc": "Cơ quan cấp/nơi đăng ký giấy khai sinh/giấy chứng sinh."},
    {"name": "Child_BirthDocumentInfo", "desc": "Thông tin giấy khai sinh/giấy chứng sinh nếu đọc được, gồm số, nơi cấp, ngày cấp."},

    # IV. Nội dung đăng ký.
    {"name": "Registration_Agency", "desc": "Cơ quan kính gửi/cơ quan đăng ký nếu tờ khai ghi rõ."},
    {"name": "Registration_Type", "desc": 'Loại đăng ký: "Đăng ký mới" hoặc "Ghi vào sổ việc nhận cha, mẹ, con đã được đăng ký tại cơ quan có thẩm quyền của nước ngoài".'},
    {"name": "Confirmation_Type", "desc": 'Loại xác nhận, một trong: "Cha nhận con", "Mẹ nhận con", "Con nhận cha", "Con nhận mẹ".'},
    {"name": "Relationship_Claim", "desc": "Cụm quan hệ thực tế đọc từ tờ khai/ADN, ví dụ cha-con, mẹ-con, bố-con."},
    {"name": "CopyRequest_WantsCopy", "desc": '"Có" nếu tờ khai tích đề nghị cấp bản sao, "Không" nếu tích không.'},
    {"name": "CopyRequest_Quantity", "desc": "Số lượng bản sao đề nghị cấp, chỉ trả số nếu tờ khai ghi rõ."},
]

ALLOWED = {f["name"] for f in FIELDS}
ALIASES: dict[str, list[str]] = {}

COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}
for _name in (
    "Requester_BirthDate",
    "Requester_IdIssueDate",
    "Parent_BirthDate",
    "Parent_IdIssueDate",
    "Child_BirthDate",
    "Child_IdIssueDate",
    "Child_BirthDocumentIssueDate",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"
for _name in (
    "Requester_ResidenceDomestic",
    "Parent_ResidenceDomestic",
    "Child_ResidenceDomestic",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

UI_COMP_BY_NAME = {
    # I. Người yêu cầu.
    "HoVaTenC": "x-input",
    "SoDinhDanhC": "x-input",
    "LoaiGiayToDinhDanhC": "x-select",
    "TenGiayToC": "x-select-area",
    "SoGiayToDinhDanhC": "x-input",
    "NgayCapDDC": "x-date",
    "NoiCapDDC": "x-input",
    "DiaChiC": "x-input",
    "TT_TinhThanhC": "x-select",
    "TT_PhuongXaC": "x-select",
    "nycSoDienThoai": "x-input",
    "nycEmail": "x-input",
    "Quanhe": "x-radio",
    "LoaiDangKy": "x-radio",
    "loaiXacNhan": "x-select-default",

    # II. Cha/mẹ.
    "HotenA": "x-input",
    "ngaysinhA": "x-date",
    "gioitinhA": "x-select",
    "dantocA": "x-select",
    "dantockhacA": "x-select-area",
    "quoctichA": "x-select",
    "sodinhdanhA": "x-input",
    "loaigiaytoA": "x-select",
    "tengiaytoA": "x-select-area",
    "sogiaytodinhdanhA": "x-input",
    "ngaycapA": "x-date",
    "NoiCapA": "x-input",
    "loaicutruA": "x-select",
    "noicutruA": "x-radio",
    "noicutruA_TrongNuoc": "x-select-area",
    "noicutruA_NuocNgoai": "x-select-area",

    # III. Người con.
    "hotenB": "x-input",
    "ngaysinhB": "x-date",
    "gioitinhB": "x-select",
    "dantocB": "x-select",
    "dantockhacB": "x-select-area",
    "quoctichB": "x-select",
    "sodinhdanhB": "x-input",
    "loaigiaytoB": "x-select",
    "tengiaytoB": "x-select-area",
    "sogiaytodinhdanhB": "x-input",
    "ngaycapB": "x-date",
    "noicapB": "x-input",
    "loaicutruB": "x-select",
    "noicutruB": "x-radio",
    "noicutruB_TrongNuoc": "x-select-area",
    "noicutruB_NuocNgoai": "x-select-area",
    "CapBanSao": "x-radio",
}
