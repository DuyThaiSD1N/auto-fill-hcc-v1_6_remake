"""Compact source-fact schema shared by the two eForms in the procedure."""

FIELDS: list[dict] = [
    {"name": "Requester_FullName", "desc": "Họ tên người yêu cầu trên tờ khai."},
    {"name": "Requester_BirthDate", "desc": "Ngày sinh người yêu cầu, dd/mm/yyyy."},
    {"name": "Requester_IdNumber", "desc": "Số định danh/CCCD/CMND người yêu cầu; giữ nguyên số 0 đầu."},
    {"name": "Requester_IdIssueDate", "desc": "Ngày cấp giấy tờ người yêu cầu, dd/mm/yyyy."},
    {"name": "Requester_IdIssuePlace", "desc": "Nơi cấp giấy tờ người yêu cầu."},
    {"name": "Requester_ResidenceDomestic", "desc": "Nơi cư trú người yêu cầu, object {quocGia,tinh,xa,diaChi}."},
    {"name": "Requester_PhoneNumber", "desc": "Số điện thoại người yêu cầu nếu có."},
    {"name": "Requester_Email", "desc": "Email người yêu cầu nếu có."},
    {"name": "Requester_RelationshipToChild", "desc": "Quan hệ của người yêu cầu với trẻ: Cha, Mẹ hoặc quan hệ khác."},

    {"name": "Father_FullName", "desc": "Họ tên người cha."},
    {"name": "Father_BirthDate", "desc": "Ngày sinh người cha, dd/mm/yyyy."},
    {"name": "Father_Gender", "desc": "Giới tính người cha, thường là Nam."},
    {"name": "Father_Ethnicity", "desc": "Dân tộc người cha."},
    {"name": "Father_Nationality", "desc": "Quốc tịch người cha."},
    {"name": "Father_IdNumber", "desc": "Số định danh/CCCD/CMND người cha; giữ nguyên số 0 đầu."},
    {"name": "Father_IdIssueDate", "desc": "Ngày cấp giấy tờ người cha, dd/mm/yyyy."},
    {"name": "Father_IdIssuePlace", "desc": "Nơi cấp giấy tờ người cha."},
    {"name": "Father_ResidenceDomestic", "desc": "Nơi cư trú người cha, object {quocGia,tinh,xa,diaChi}."},
    {"name": "Father_OriginDomestic", "desc": "Quê quán người cha, object {quocGia,tinh,xa,diaChi} nếu có."},

    {"name": "Mother_FullName", "desc": "Họ tên người mẹ."},
    {"name": "Mother_BirthDate", "desc": "Ngày sinh người mẹ, dd/mm/yyyy."},
    {"name": "Mother_Ethnicity", "desc": "Dân tộc người mẹ."},
    {"name": "Mother_Nationality", "desc": "Quốc tịch người mẹ."},
    {"name": "Mother_IdNumber", "desc": "Số định danh/CCCD/CMND người mẹ; giữ nguyên số 0 đầu."},
    {"name": "Mother_IdIssueDate", "desc": "Ngày cấp giấy tờ người mẹ, dd/mm/yyyy nếu có."},
    {"name": "Mother_IdIssuePlace", "desc": "Nơi cấp giấy tờ người mẹ nếu có."},
    {"name": "Mother_ResidenceDomestic", "desc": "Nơi cư trú người mẹ, object {quocGia,tinh,xa,diaChi}."},

    {"name": "Child_FullName", "desc": "Tên dự kiến đăng ký cho trẻ theo các tờ khai."},
    {"name": "Child_NameOnBirthCertificate", "desc": "Tên trẻ ghi riêng trên giấy chứng sinh, kể cả khi khác tờ khai."},
    {"name": "Child_BirthDate", "desc": "Ngày sinh trẻ, dd/mm/yyyy."},
    {"name": "Child_Gender", "desc": "Giới tính trẻ: Nam hoặc Nữ."},
    {"name": "Child_Ethnicity", "desc": "Dân tộc trẻ theo tờ khai."},
    {"name": "Child_Nationality", "desc": "Quốc tịch trẻ theo tờ khai."},
    {"name": "Child_BirthPlaceDomestic", "desc": "Nơi sinh, object {quocGia,tinh,xa,diaChi}; diaChi có thể là tên cơ sở y tế."},
    {"name": "Child_OriginDomestic", "desc": "Quê quán trẻ, object {quocGia,tinh,xa,diaChi}."},
    {"name": "Child_ResidenceDomestic", "desc": "Nơi cư trú của trẻ, object {quocGia,tinh,xa,diaChi}."},
    {"name": "Child_BirthDocumentNumber", "desc": "Mã/số giấy chứng sinh nếu có."},
    {"name": "Child_BirthDocumentIssueDate", "desc": "Ngày cấp giấy chứng sinh nếu có, dd/mm/yyyy."},
    {"name": "Child_BirthDocumentIssuePlace", "desc": "Cơ sở cấp giấy chứng sinh nếu có."},

    {"name": "Registration_Agency", "desc": "Cơ quan ở dòng Kính gửi nếu giấy tờ ghi rõ."},
    {"name": "Parents_MarriageRegistrationInfo", "desc": "Thông tin đăng ký kết hôn của cha mẹ, chỉ trả khi giấy tờ xác nhận đã đăng ký kết hôn."},
    {"name": "Recognition_RegistrationType", "desc": "Đăng ký mới hoặc ghi vào sổ việc đã đăng ký ở nước ngoài."},
    {"name": "Recognition_ConfirmationType", "desc": "Một trong: Cha nhận con, Mẹ nhận con, Con nhận cha, Con nhận mẹ."},
    {"name": "Recognition_RelationshipClaim", "desc": "Quan hệ thực tế được đề nghị/có chứng cứ, ví dụ cha-con."},
    {"name": "Recognition_CopyRequest", "desc": "Có hoặc Không nếu tờ khai tích đề nghị cấp bản sao."},
]

ALLOWED = {field["name"] for field in FIELDS}
ALIASES: dict[str, list[str]] = {}
COMPACT_COMP_BY_NAME = {name: "x-input" for name in ALLOWED}

for _name in (
    "Requester_BirthDate",
    "Requester_IdIssueDate",
    "Father_BirthDate",
    "Father_IdIssueDate",
    "Mother_BirthDate",
    "Mother_IdIssueDate",
    "Child_BirthDate",
    "Child_BirthDocumentIssueDate",
):
    COMPACT_COMP_BY_NAME[_name] = "x-date"

for _name in (
    "Requester_ResidenceDomestic",
    "Father_ResidenceDomestic",
    "Father_OriginDomestic",
    "Mother_ResidenceDomestic",
    "Child_BirthPlaceDomestic",
    "Child_OriginDomestic",
    "Child_ResidenceDomestic",
):
    COMPACT_COMP_BY_NAME[_name] = "x-select-area"

