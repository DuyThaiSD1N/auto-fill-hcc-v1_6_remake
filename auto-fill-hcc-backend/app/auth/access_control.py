"""Quy tắc khóa tài khoản trong thời gian bảo trì, dùng chung mọi đường auth."""
from app.core.errors import AppError


MAINTENANCE_ERROR = "SYSTEM_MAINTENANCE"
MAINTENANCE_MESSAGE = "Hệ thống đang được tối ưu và nâng cấp. Vui lòng quay lại sau"


def ensure_account_available(user: dict) -> None:
    if user.get("access_disabled") is True:
        raise AppError(MAINTENANCE_ERROR, MAINTENANCE_MESSAGE, 503)
