"""Nghiệp vụ auth: login, rotate refresh token."""
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from app.config import settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    token_hash,
    verify_password,
)
from app.db.mongo import get_db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user_public(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "name": user.get("name"),
        "role": user.get("role") or "user",
        "xa": user.get("xa"),
        "tinh": user.get("tinh"),
    }


async def _store_refresh(user_id: str, refresh_token: str, device_info: str | None) -> None:
    await get_db().refresh_tokens.insert_one({
        "user_id": user_id,
        "token_hash": token_hash(refresh_token),
        "device_info": device_info,
        "expires_at": _now() + timedelta(seconds=settings.jwt_refresh_ttl),
        "revoked_at": None,
        "created_at": _now(),
    })


async def login(
    username: str, password: str, device_info: str | None = None, admin_only: bool = False
) -> dict:
    user = await get_db().users.find_one({"username": username.lower()})
    if not user or not verify_password(password, user["password_hash"]):
        raise AppError("INVALID_CREDENTIALS", "Tên đăng nhập hoặc mật khẩu không đúng", 401)

    # Login từ trang quản lý (adminOnly): mật khẩu đúng nhưng không phải admin → CHẶN ngay,
    # không cấp/lưu token. Extension gọi login không kèm cờ này nên tài khoản phường không dính.
    if admin_only and (user.get("role") or "user") != "admin":
        raise AppError("NOT_ADMIN", "Tài khoản này không có quyền truy cập trang quản lý.", 403)

    user_id = str(user["_id"])
    access = create_access_token(user_id, user["username"])
    refresh = create_refresh_token(user_id)
    await _store_refresh(user_id, refresh, device_info)
    await get_db().users.update_one({"_id": user["_id"]}, {"$set": {"last_login_at": _now()}})

    return {"accessToken": access, "refreshToken": refresh, "user": _user_public(user)}


async def refresh(refresh_token: str, device_info: str | None = None) -> dict:
    payload = decode_refresh_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise AppError("INVALID_REFRESH", "Refresh token không hợp lệ", 401)

    db = get_db()
    stored = await db.refresh_tokens.find_one({"token_hash": token_hash(refresh_token)})
    if not stored or stored.get("revoked_at"):
        raise AppError("INVALID_REFRESH", "Refresh token đã bị thu hồi hoặc không tồn tại", 401)

    user_id = payload["sub"]
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise AppError("USER_NOT_FOUND", "Không tìm thấy người dùng", 401)

    # Rotate: revoke token cũ, cấp cặp mới.
    await db.refresh_tokens.update_one({"_id": stored["_id"]}, {"$set": {"revoked_at": _now()}})
    access = create_access_token(user_id, user["username"])
    new_refresh = create_refresh_token(user_id)
    await _store_refresh(user_id, new_refresh, device_info)

    return {"accessToken": access, "refreshToken": new_refresh, "user": _user_public(user)}
