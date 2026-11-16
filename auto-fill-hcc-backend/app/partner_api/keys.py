"""API key cho nhóm API thống kê đối tác (/partner-api/v1).

Key gốc chỉ in ra MỘT lần lúc tạo (scripts/api_keys.py); Mongo `api_keys` chỉ giữ sha256 của key
nên lộ DB cũng không dùng lại được key. Key chỉ được nhóm API này đọc (header X-API-Key); mọi API
khác vẫn đòi Bearer token đăng nhập nên key gửi sang đó bị 401.
"""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends
from fastapi.security import APIKeyHeader

from app.core.errors import AppError
from app.db.mongo import get_db

logger = logging.getLogger(__name__)

GROUP_STATS = "stats"
PREFIX = "hcc_stats_"
_TOUCH_EVERY = timedelta(minutes=1)

_header = APIKeyHeader(name="X-API-Key", auto_error=False, description="API key do quản trị cấp.")


def now() -> datetime:
    return datetime.now(timezone.utc)


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_key() -> str:
    return PREFIX + secrets.token_urlsafe(32)


async def require_stats_key(raw: str | None = Depends(_header)) -> dict:
    """Key hợp lệ, chưa thu hồi, đúng nhóm thống kê → bản ghi key; sai hoặc thiếu → 401."""
    if not raw:
        raise AppError("MISSING_API_KEY", "Thiếu header X-API-Key.", 401)
    doc = await get_db().api_keys.find_one({"key_hash": hash_key(raw.strip()), "group": GROUP_STATS})
    if not doc or doc.get("revoked_at"):
        raise AppError("INVALID_API_KEY", "API key không hợp lệ hoặc đã bị thu hồi.", 401)
    at = now()
    last = doc.get("last_used_at")
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    # Ghi lần dùng cuối tối đa mỗi phút một lần, đủ để biết key còn dùng mà không ghi DB mỗi request.
    if last is None or at - last >= _TOUCH_EVERY:
        await get_db().api_keys.update_one({"_id": doc["_id"]}, {"$set": {"last_used_at": at}})
    return doc


def scope_user(key: dict) -> dict:
    """Tài khoản giả để dùng lại phân giải phạm vi của bảng thống kê (app/dashboard/scope.py).

    Key toàn hệ thống = phạm vi admin; key khoá tỉnh = phạm vi tài khoản Tỉnh của tỉnh đó.
    """
    scope = key.get("scope") or {}
    base = {"_id": f"apikey:{key['_id']}", "id": f"apikey:{key['_id']}", "name": key.get("name")}
    if scope.get("kind") == "province" and scope.get("tinh"):
        return {**base, "role": "province_admin", "tinh": scope["tinh"]}
    return {**base, "role": "admin"}
