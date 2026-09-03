"""Shared portal journey for Ministry of Justice four-step procedures.

Registry usage: ``"flowProfile": "tu-phap"``. A procedure may override only the
keys whose real portal contract differs; all remaining capabilities stay here.
"""

TU_PHAP_FLOW: dict = {
    "needsAgencySelect": True,
    "hasAttachmentStep": True,
    # Backend là nguồn sự thật cho lựa chọn hiển thị ở sidebar và giá trị cần chọn
    # trong modal "Thông tin chung". Extension chỉ render/thao tác theo contract này.
    "executionSubject": {
        "enabled": True,
        "default": "self",
        "options": [
            {
                "key": "self",
                "label": "Làm thủ tục cho bản thân",
                "portalValue": "null",
            },
            {
                "key": "authorized_person",
                "label": "Người khác ủy quyền",
                "portalValue": "canhan",
            },
            {
                "key": "enterprise_authorized",
                "label": "Doanh nghiệp ủy quyền",
                # Chưa có data-value ổn định từ DOM thật; để rỗng buộc extension
                # khớp chính xác theo nhãn đang hiển thị, tránh đoán nhầm option.
                "portalValue": "",
            },
            {
                "key": "other_person",
                "label": "Làm thủ tục cho người khác",
                "portalValue": "",
            },
            {
                "key": "organization_representative",
                "label": "Đại diện cơ quan, tổ chức",
                "portalValue": "",
            },
        ],
    },
    "wizard": {
        "ownerStep": 1,
        "declarationStep": 2,
        "attachmentStep": 3,
        "resultStep": 4,
    },
    "ownerInfo": {
        "enabled": True,
        "fields": {
            "Owner_IssueDate": {
                "key": "issueDate", "label": "Ngày cấp", "comp": "owner-date",
                "reportLabel": "ngày cấp",
            },
            "Owner_IssuePlace": {
                "key": "issuePlace", "label": "Nơi cấp", "comp": "owner-combobox",
                "reportLabel": "nơi cấp",
            },
            "Owner_PhoneNumber": {
                "key": "phoneNumber", "label": "Số điện thoại", "name": "soDienThoai",
                "comp": "owner-input", "reportLabel": "số điện thoại",
            },
            "Owner_DetailedAddress": {
                "key": "detailedAddress", "label": "Địa chỉ chi tiết",
                "name": "diaChiThuongTru", "comp": "owner-input",
                "reportLabel": "địa chỉ",
            },
        },
    },
    # Chỉ ghép contract này vào owner pipeline khi người dân chọn nhánh ủy quyền.
    # Nhánh "self" không nhận schema/prompt/context ủy quyền.
    "authorizationInfo": {
        "enabled": True,
        "activeWhen": {
            "executionSubject": "authorized_person",
        },
        "sectionLabel": "Thông tin ủy quyền cá nhân",
        "fields": {
            "Authorization_GrantorFullName": {
                "key": "grantorFullName", "label": "Họ tên người ủy quyền",
                "name": "hoTen", "dataE2e": "other-fullName-field",
                "comp": "owner-input", "reportLabel": "họ tên người ủy quyền",
                "sectionLabel": "Thông tin ủy quyền cá nhân", "group": "authorization",
            },
            "Authorization_GrantorDateOfBirth": {
                "key": "grantorDateOfBirth", "label": "Ngày tháng năm sinh",
                "comp": "owner-date", "reportLabel": "ngày sinh người ủy quyền",
                "sectionLabel": "Thông tin ủy quyền cá nhân", "group": "authorization",
            },
            "Authorization_Relationship": {
                "key": "relationship", "label": "Quan hệ với người được ủy quyền",
                "name": "relationship", "dataE2e": "other-relationship-field",
                "comp": "owner-input", "reportLabel": "quan hệ với người được ủy quyền",
                "sectionLabel": "Thông tin ủy quyền cá nhân", "group": "authorization",
            },
            "Authorization_GrantorIdentityNumber": {
                "key": "grantorIdentityNumber", "label": "Số giấy tờ",
                "name": "number", "dataE2e": "other-numberOfDocument-field",
                "comp": "owner-input", "reportLabel": "số giấy tờ người ủy quyền",
                "sectionLabel": "Thông tin ủy quyền cá nhân", "group": "authorization",
            },
        },
    },
}
