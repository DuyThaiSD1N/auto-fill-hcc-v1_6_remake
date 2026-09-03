"""Định nghĩa role tài khoản dùng chung cho thống kê và báo cáo."""


OFFICIAL_ACCOUNT_ROLES = frozenset({"commune", "province"})

# Role CHỈ dùng để XEM báo cáo cấp tỉnh trên bảng thống kê (KHÁC "province" của HCC — role đó là
# tài khoản nghiệp vụ cấp tỉnh). Tài khoản này không xử lý hồ sơ; chỉ được xem số liệu tổng hợp của
# mọi phường/xã cùng tỉnh (khóa theo `tinh` của chính tài khoản, không nhận tỉnh/xã từ client).
PROVINCE_ADMIN_ROLE = "province_admin"

# Role nội bộ dành riêng cho web Monitor chứa OCR/LLM và giấy tờ hồ sơ. Không đưa role này
# vào ``users.schemas.Role``: nếu dùng chung enum công khai, trang quản lý tài khoản hiện tại
# sẽ vô tình cho phép admin thường tạo hoặc nâng quyền một tài khoản thành super admin.
SUPER_ADMIN_ROLE = "super_admin"


def normalized_role(value: object) -> str:
    """Tài khoản legacy thiếu role được hiểu là user, không tự nâng thành tài khoản HCC."""
    return str(value or "user")


def is_official_account_role(value: object) -> bool:
    return normalized_role(value) in OFFICIAL_ACCOUNT_ROLES


def is_province_admin_role(value: object) -> bool:
    return normalized_role(value) == PROVINCE_ADMIN_ROLE
