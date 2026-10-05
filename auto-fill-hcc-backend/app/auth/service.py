"""Nghiệp vụ auth: login, rotate refresh token."""
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from app.auth import audit
from app.auth.access_control import ensure_account_available
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
from app.users.roles import SUPER_ADMIN_ROLE


def _now() -> datetime:
    return datetime.now(timezone.utc)


# Refresh token bị thu hồi DO XOAY VÒNG mà được dùng lại trong khoảng này vẫn được cấp cặp mới.
# Nhiều nơi trên cùng một máy cùng làm mới bằng một token (nhiều tab mở panel, tab tách chứng
# thực, background gửi mốc nộp, đọc giọng nói lúc đang chat): bên đến sau trước đây bị từ chối và
# cán bộ bị đá ra màn đăng nhập. Thu hồi do khoá/xoá tài khoản (không mang lý do "rotated") thì
# không có ân hạn; tài khoản bị khoá/xoá còn bị ensure_account_available chặn lần nữa.
_ROTATION_GRACE = timedelta(seconds=60)
_ROTATED = "rotated"


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
    username: str,
    password: str,
    device_info: str | None = None,
    admin_only: bool = False,
    super_admin_only: bool = False,
    ip: str | None = None,
) -> dict:
    user = await get_db().users.find_one({"username": username.lower()})
    if not user or not verify_password(password, user["password_hash"]):
        await audit.log_auth(get_db(), "login_fail", username=username.lower(), reason="invalid_credentials",
                             device_info=device_info, ip=ip)
        raise AppError("INVALID_CREDENTIALS", "Tên đăng nhập hoặc mật khẩu không đúng", 401)
    ensure_account_available(user)

    # Login từ trang quản lý (adminOnly): mật khẩu đúng nhưng không phải admin → CHẶN ngay,
    # không cấp/lưu token. Extension gọi login không kèm cờ này nên tài khoản phường không dính.
    role = user.get("role") or "user"
    # superAdminOnly có độ ưu tiên cao hơn nếu một client lỗi gửi đồng thời cả hai cờ. Không
    # kiểm hai điều kiện độc lập vì super_admin có chủ ý KHÔNG được đăng nhập web admin cũ.
    if super_admin_only and role != SUPER_ADMIN_ROLE:
        raise AppError(
            "NOT_SUPER_ADMIN",
            "Tài khoản này không có quyền truy cập trang Monitor.",
            403,
        )
    if not super_admin_only and admin_only and role != "admin":
        raise AppError("NOT_ADMIN", "Tài khoản này không có quyền truy cập trang quản lý.", 403)

    user_id = str(user["_id"])
    access = create_access_token(user_id, user["username"])
    refresh = create_refresh_token(user_id)
    await _store_refresh(user_id, refresh, device_info)
    await get_db().users.update_one({"_id": user["_id"]}, {"$set": {"last_login_at": _now()}})
    await audit.log_auth(get_db(), "login", user_id=user_id, username=user["username"], device_info=device_info, ip=ip)

    return {"accessToken": access, "refreshToken": refresh, "user": _user_public(user)}


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)  # Motor trả naive UTC


async def refresh(refresh_token: str, device_info: str | None = None, ip: str | None = None) -> dict:
    db = get_db()
    payload = decode_refresh_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        await audit.log_auth(db, "refresh_fail", reason="invalid_jwt", device_info=device_info, ip=ip)
        raise AppError("INVALID_REFRESH", "Refresh token không hợp lệ", 401)
    user_id = payload["sub"]

    stored = await db.refresh_tokens.find_one({"token_hash": token_hash(refresh_token)})
    if not stored:
        await audit.log_auth(db, "refresh_fail", user_id=user_id, reason="not_found", device_info=device_info, ip=ip)
        raise AppError("INVALID_REFRESH", "Refresh token đã bị thu hồi hoặc không tồn tại", 401)
    revoked_at = stored.get("revoked_at")
    in_grace = bool(revoked_at) and stored.get("revoked_reason") == _ROTATED \
        and _now() - _as_utc(revoked_at) <= _ROTATION_GRACE
    if revoked_at and not in_grace:
        reason = "rotated_reuse" if stored.get("revoked_reason") == _ROTATED else "revoked"
        await audit.log_auth(db, "refresh_fail", user_id=user_id, reason=reason, device_info=device_info, ip=ip)
        raise AppError("INVALID_REFRESH", "Refresh token đã bị thu hồi hoặc không tồn tại", 401)

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        await audit.log_auth(db, "refresh_fail", user_id=user_id, reason="user_not_found", device_info=device_info, ip=ip)
        raise AppError("USER_NOT_FOUND", "Không tìm thấy người dùng", 401)
    try:
        ensure_account_available(user)
    except AppError as exc:
        await audit.log_auth(db, "refresh_fail", user_id=user_id, username=user.get("username"),
                             reason=exc.error.lower(), device_info=device_info, ip=ip)
        raise

    # Rotate: revoke token cũ (đánh dấu lý do để còn nhận ra tranh chấp trong ân hạn), cấp cặp mới.
    if not revoked_at:
        await db.refresh_tokens.update_one(
            {"_id": stored["_id"]}, {"$set": {"revoked_at": _now(), "revoked_reason": _ROTATED}})
    access = create_access_token(user_id, user["username"])
    new_refresh = create_refresh_token(user_id)
    await _store_refresh(user_id, new_refresh, device_info)
    await audit.log_auth(db, "refresh_grace" if in_grace else "refresh", user_id=user_id,
                         username=user["username"], device_info=device_info, ip=ip)

    return {"accessToken": access, "refreshToken": new_refresh, "user": _user_public(user)}
