"""Dependency xác thực Bearer token → current user."""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.mongo import get_db

_bearer = HTTPBearer(auto_error=False)


async def require_auth(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if not creds or not creds.credentials:
        raise AppError("MISSING_TOKEN", "Thiếu access token", 401)
    payload = decode_access_token(creds.credentials)
    if not payload or payload.get("type") != "access":
        raise AppError("TOKEN_EXPIRED", "Access token không hợp lệ hoặc đã hết hạn", 401)

    from bson import ObjectId

    user_id = payload.get("sub")
    try:
        user = await get_db().users.find_one({"_id": ObjectId(user_id)})
    except Exception:  # noqa: BLE001
        user = None
    if not user:
        raise AppError("USER_NOT_FOUND", "Không tìm thấy người dùng", 401)
    user["id"] = str(user["_id"])
    return user


async def require_admin(user: dict = Depends(require_auth)) -> dict:
    """Chỉ cho phép tài khoản role=admin. Thiếu role coi như 'user'."""
    if (user.get("role") or "user") != "admin":
        raise AppError("FORBIDDEN", "Chỉ quản trị viên mới được thực hiện thao tác này", 403)
    return user


async def require_ward(user: dict = Depends(require_auth)) -> dict:
    """Cổng cho BẢNG THỐNG KÊ PHƯỜNG (self-service của tài khoản phường).

    Yêu cầu tài khoản đã được gán tỉnh + xã. Phạm vi số liệu về sau LUÔN khóa theo chính
    user trong token (dashboard chỉ đếm trace của user_id này), endpoint KHÔNG nhận
    xã/userId từ client — token phường A không thể đọc phường B dù sửa request tay.
    """
    if not (user.get("tinh") and user.get("xa")):
        raise AppError(
            "WARD_NOT_ASSIGNED",
            "Tài khoản chưa được gán phường/xã. Liên hệ quản trị để cập nhật.",
            403,
        )
    return user
