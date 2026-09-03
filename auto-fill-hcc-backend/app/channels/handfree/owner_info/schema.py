"""Backend-only contract for fields shown on the Justice owner-information page."""

ISSUE_PLACE_OPTIONS: tuple[str, ...] = (
    "Cục cảnh sát đăng ký quản lý cư trú và dữ liệu quốc gia về dân cư",
    "Cục cảnh sát quản lý hành chính về trật tự xã hội",
    "Bộ công an",
    "Cục quản lý xuất nhập cảnh",
)

FIELDS: list[dict] = [
    {"name": "Owner_FullName", "desc": "Họ tên của đúng người chủ hồ sơ được chọn từ tài liệu."},
    {"name": "Owner_IdentityNumber", "desc": "Số CCCD/định danh của đúng người chủ hồ sơ."},
    {"name": "Owner_IssueDate", "desc": "Ngày cấp CCCD của chủ hồ sơ, dd/mm/yyyy."},
    {"name": "Owner_IssuePlace", "desc": (
        "Nơi cấp giấy tờ của chủ hồ sơ. Chỉ được trả đúng một trong bốn giá trị: "
        + " | ".join(ISSUE_PLACE_OPTIONS)
        + ". Không khớp rõ ràng thì không trả field này."
    )},
    {"name": "Owner_PhoneNumber", "desc": "Số điện thoại chỉ khi tài liệu ghi rõ là của chủ hồ sơ."},
    {"name": "Owner_DetailedAddress", "desc": (
        "Địa chỉ chủ hồ sơ có thể trả object địa chỉ chuẩn; backend chỉ lấy khóa diaChi "
        "để điền trang chủ hồ sơ."
    )},
]

AUTHORIZATION_FIELDS: list[dict] = [
    {"name": "Authorization_DocumentTitle", "desc": (
        "Tiêu đề đúng của giấy/văn bản/hợp đồng ủy quyền. Không có văn bản ủy quyền thật thì bỏ."
    )},
    {"name": "Authorization_RecipientFullName", "desc": (
        "Họ tên người được ủy quyền/được nhận ủy quyền trên văn bản ủy quyền."
    )},
    {"name": "Authorization_RecipientIdentityNumber", "desc": (
        "Số CCCD/CMND/hộ chiếu của người được ủy quyền trên văn bản ủy quyền."
    )},
    {"name": "Authorization_GrantorFullName", "desc": (
        "Họ tên người ủy quyền/bên ủy quyền trên văn bản ủy quyền."
    )},
    {"name": "Authorization_GrantorDateOfBirth", "desc": (
        "Ngày sinh người ủy quyền, dd/mm/yyyy; chỉ trả khi tài liệu ghi rõ."
    )},
    {"name": "Authorization_Relationship", "desc": (
        "Quan hệ của người ủy quyền với người được ủy quyền; chỉ trả khi tài liệu ghi rõ, không suy đoán."
    )},
    {"name": "Authorization_GrantorIdentityNumber", "desc": (
        "Số CCCD/CMND/hộ chiếu của người ủy quyền; giữ nguyên chữ và số có ý nghĩa."
    )},
]

ALLOWED = {field["name"] for field in FIELDS}
COMP_BY_NAME = {name: "raw" for name in ALLOWED}
COMP_BY_NAME["Owner_IssueDate"] = "x-date"


def fields_for(include_authorization: bool) -> list[dict]:
    """Keep the self branch completely free of authorization schema."""
    return [*FIELDS, *AUTHORIZATION_FIELDS] if include_authorization else list(FIELDS)


def allowed_for(include_authorization: bool) -> set[str]:
    return {field["name"] for field in fields_for(include_authorization)}


def comp_by_name_for(include_authorization: bool) -> dict[str, str]:
    result = {name: "raw" for name in allowed_for(include_authorization)}
    result["Owner_IssueDate"] = "x-date"
    if include_authorization:
        result["Authorization_GrantorDateOfBirth"] = "x-date"
    return result
