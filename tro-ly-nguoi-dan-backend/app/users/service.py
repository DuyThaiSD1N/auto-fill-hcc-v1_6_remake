"""Nghiệp vụ quản lý tài khoản xã/phường (chỉ admin)."""
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError

from app.core.errors import AppError
from app.core.security import hash_password
from app.db.mongo import get_db
from app.users.schemas import UserCreate, UserUpdate


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def _public(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "name": user.get("name"),
        "xa": user.get("xa"),
        "tinh": user.get("tinh"),
        "role": user.get("role") or "user",
        "created_at": _iso(user.get("created_at")),
        "last_login_at": _iso(user.get("last_login_at")),
    }


def _oid(user_id: str) -> ObjectId:
    try:
        return ObjectId(user_id)
    except (InvalidId, TypeError):
        raise AppError("USER_NOT_FOUND", "Không tìm thấy tài khoản", 404)


async def list_users(*, skip: int = 0, limit: int = 20) -> dict:
    db = get_db()
    total = await db.users.count_documents({})
    cursor = (
        db.users.find().sort("username", 1).skip(max(skip, 0)).limit(max(min(limit, 100), 1))
    )
    items = [_public(u) async for u in cursor]
    return {"items": items, "total": total}


async def create_user(body: UserCreate) -> dict:
    now = _now()
    doc = {
        "username": body.username,
        "password_hash": hash_password(body.password),
        "name": body.name,
        "xa": body.xa,
        "tinh": body.tinh,
        "role": body.role,
        "created_at": now,
        "updated_at": now,
    }
    try:
        res = await get_db().users.insert_one(doc)
    except DuplicateKeyError:
        raise AppError("USERNAME_EXISTS", "Tên đăng nhập đã tồn tại", 409)
    doc["_id"] = res.inserted_id
    return _public(doc)


async def update_user(user_id: str, body: UserUpdate) -> dict:
    db = get_db()
    oid = _oid(user_id)
    updates: dict = {"updated_at": _now()}
    if body.name is not None:
        updates["name"] = body.name
    if body.xa is not None:
        updates["xa"] = body.xa
    if body.tinh is not None:
        updates["tinh"] = body.tinh
    if body.role is not None:
        updates["role"] = body.role
    if body.password:
        updates["password_hash"] = hash_password(body.password)

    result = await db.users.find_one_and_update(
        {"_id": oid}, {"$set": updates}, return_document=True
    )
    if not result:
        raise AppError("USER_NOT_FOUND", "Không tìm thấy tài khoản", 404)
    return _public(result)


async def delete_user(user_id: str, current_user_id: str) -> None:
    oid = _oid(user_id)
    if str(oid) == current_user_id:
        raise AppError("CANNOT_DELETE_SELF", "Không thể tự xóa tài khoản của chính mình", 400)
    res = await get_db().users.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise AppError("USER_NOT_FOUND", "Không tìm thấy tài khoản", 404)
