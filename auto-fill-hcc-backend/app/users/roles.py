"""Định nghĩa role tài khoản dùng chung cho thống kê và báo cáo."""


OFFICIAL_ACCOUNT_ROLES = frozenset({"commune", "province"})


def normalized_role(value: object) -> str:
    """Tài khoản legacy thiếu role được hiểu là user, không tự nâng thành tài khoản HCC."""
    return str(value or "user")


def is_official_account_role(value: object) -> bool:
    return normalized_role(value) in OFFICIAL_ACCOUNT_ROLES
