"""Quy tắc khóa tài khoản trong thời gian bảo trì, dùng chung mọi đường auth."""
from app.core.errors import AppError


MAINTENANCE_ERROR = "SYSTEM_MAINTENANCE"
MAINTENANCE_MESSAGE = "Hệ thống đang được tối ưu và nâng cấp. Vui lòng quay lại sau"

DELETED_ERROR = "ACCOUNT_DELETED"
DELETED_MESSAGE = "Tài khoản không còn hiệu lực. Vui lòng liên hệ quản trị viên."


def ensure_account_available(user: dict) -> None:
    """Chốt DUY NHẤT cho mọi đường auth (đăng nhập, refresh, require_auth, WebSocket voice).

    Xóa tài khoản là xóa MỀM (users.deleted_at) nên document vẫn còn trong Mongo — thiếu kiểm
    ở đây là tài khoản đã xóa vẫn đăng nhập được như thường.
    """
    if user.get("deleted_at") is not None:
        raise AppError(DELETED_ERROR, DELETED_MESSAGE, 403)
    if user.get("access_disabled") is True:
        raise AppError(MAINTENANCE_ERROR, MAINTENANCE_MESSAGE, 503)
