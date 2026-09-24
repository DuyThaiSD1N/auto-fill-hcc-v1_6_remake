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
                "shortLabel": "cho bản thân",
                "portalValue": "null",
            },
            {
                "key": "authorized_person",
                "label": "Người khác ủy quyền",
                "shortLabel": "do người khác ủy quyền",
                "portalValue": "canhan",
            },
            {
                "key": "enterprise_authorized",
                "label": "Doanh nghiệp ủy quyền",
                "shortLabel": "do doanh nghiệp ủy quyền",
                # Chưa có data-value ổn định từ DOM thật; để rỗng buộc extension
                # khớp chính xác theo nhãn đang hiển thị, tránh đoán nhầm option.
                "portalValue": "",
            },
            {
                "key": "other_person",
                "label": "Làm thủ tục cho người khác",
                "shortLabel": "cho người khác",
                "portalValue": "",
            },
            {
                "key": "organization_representative",
                "label": "Đại diện cơ quan, tổ chức",
                "shortLabel": "với tư cách đại diện cơ quan, tổ chức",
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
    # Dẫn từng bước wizard bằng nút trong sidebar thay vì để công dân tự dò nút của cổng.
    # Tắt mặc định: chỉ thủ tục đã chạy thử trên cổng thật mới bật ("enabled": True), vì câu
    # thoại và nút bấm phải khớp đúng nhãn của từng trang.
    "guidedSteps": {
        "enabled": False,
        # Quét giấy tờ NGAY ở bước Thông tin chủ hồ sơ để tự điền, thay vì đợi tới bước
        # Thành phần hồ sơ. Một lần quét dùng cho cả điền form lẫn đính kèm.
        # Cố ý KHÔNG bật bằng `ownerInfo.enabled` của registry: cờ đó ảnh hưởng cả extension
        # cũ trên chợ (bản cũ sẽ nhận giấy tờ ở bước 1 rồi kẹt vì thủ tục attach-only không
        # có bước kê khai). Cờ này chỉ có tác dụng khi client khai supportsOwnerScan.
        "ownerScan": False,
        # Ô bắt buộc ở bước Thông tin chủ hồ sơ — khai theo KHÓA của ownerInfo.fields để
        # nhãn báo thiếu ("ngày cấp", "nơi cấp"…) luôn lấy từ một chỗ duy nhất. Danh sách này
        # độc lập với ownerInfo.enabled: thủ tục attach-only không tự điền chủ hồ sơ nhưng
        # cổng vẫn bắt buộc đúng các ô đó.
        "ownerRequiredFields": [
            "Owner_IssueDate",
            "Owner_IssuePlace",
            "Owner_PhoneNumber",
            "Owner_DetailedAddress",
        ],
        # Chỉ hiện ở nhánh ủy quyền; trang tự làm không có ô nào khớp nên tự bỏ qua.
        "authorizationRequiredFields": [
            "Authorization_GrantorFullName",
            "Authorization_GrantorDateOfBirth",
            "Authorization_Relationship",
            "Authorization_GrantorIdentityNumber",
        ],
        # Nhãn ĐÚNG CHỮ trên cổng — câu thoại và nút đọc lại nguyên văn để công dân đối chiếu
        # được với màn hình. Nút nộp cuối cổng tư pháp ghi "Gửi hồ sơ", không phải "Nộp hồ sơ".
        "attachmentStepLabel": "Thành phần hồ sơ",
        "resultStepLabel": "Thông tin nhận kết quả",
        "submitLabel": "Gửi hồ sơ",
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
