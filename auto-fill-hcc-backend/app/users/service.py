"""Nghiệp vụ quản lý tài khoản xã/phường (chỉ admin)."""
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError

from app.auth.access_control import MAINTENANCE_MESSAGE
from app.core.errors import AppError
from app.core.security import hash_password
from app.db.mongo import get_db
from app.locations.catalog import canonical_location
from app.users.schemas import Role, UserCreate, UserUpdate


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
        "access_disabled": user.get("access_disabled") is True,
        "created_at": _iso(user.get("created_at")),
        "last_login_at": _iso(user.get("last_login_at")),
    }


def _oid(user_id: str) -> ObjectId:
    try:
        return ObjectId(user_id)
    except (InvalidId, TypeError):
        raise AppError("USER_NOT_FOUND", "Không tìm thấy tài khoản", 404)


def _role_query(role: Role | None) -> dict:
    """Tài khoản cũ thiếu role vẫn hành xử như user nên phải xuất hiện khi lọc Người dùng."""
    if role is None:
        return {}
    if role == "user":
        return {"$or": [
            {"role": "user"},
            {"role": {"$exists": False}},
            {"role": None},
        ]}
    return {"role": role}


async def list_users(*, skip: int = 0, limit: int = 20, role: Role | None = None) -> dict:
    db = get_db()
    query = _role_query(role)
    total = await db.users.count_documents(query)
    cursor = (
        db.users.find(query).sort("username", 1).skip(max(skip, 0)).limit(max(min(limit, 100), 1))
    )
    items = [_public(u) async for u in cursor]
    return {"items": items, "total": total}


async def create_user(body: UserCreate) -> dict:
    now = _now()
    tinh, xa = canonical_location(body.tinh, body.xa)
    doc = {
        "username": body.username,
        "password_hash": hash_password(body.password),
        "name": body.name,
        "xa": xa,
        "tinh": tinh,
        "role": body.role,
        "access_disabled": False,
        "created_at": now,
        "updated_at": now,
    }
    try:
        res = await get_db().users.insert_one(doc)
    except DuplicateKeyError:
        raise AppError("USERNAME_EXISTS", "Tên đăng nhập đã tồn tại", 409)
    doc["_id"] = res.inserted_id
    return _public(doc)


async def update_user(user_id: str, body: UserUpdate, current_user_id: str) -> dict:
    db = get_db()
    oid = _oid(user_id)
    now = _now()
    updates: dict = {"updated_at": now}
    unset_fields: dict = {}
    if body.name is not None:
        updates["name"] = body.name
    location_fields = body.model_fields_set & {"tinh", "xa"}
    if location_fields:
        # PATCH có thể chỉ gửi một nửa cặp tỉnh-xã. Ghép với dữ liệu đang lưu rồi mới
        # kiểm tra để không cho một xã cũ bị giữ lại dưới tỉnh mới.
        current = await db.users.find_one({"_id": oid})
        if not current:
            raise AppError("USER_NOT_FOUND", "Không tìm thấy tài khoản", 404)
        tinh_input = body.tinh if "tinh" in location_fields else current.get("tinh")
        xa_input = body.xa if "xa" in location_fields else current.get("xa")
        tinh, xa = canonical_location(tinh_input, xa_input)
        updates["tinh"] = tinh
        updates["xa"] = xa
    if body.role is not None:
        updates["role"] = body.role
    if body.access_disabled is not None:
        if body.access_disabled and str(oid) == current_user_id:
            raise AppError("CANNOT_DISABLE_SELF", "Không thể tự khóa tài khoản của chính mình", 400)
        updates["access_disabled"] = body.access_disabled
        if body.access_disabled:
            updates["access_disabled_reason"] = MAINTENANCE_MESSAGE
            updates["access_disabled_at"] = now
        else:
            unset_fields = {"access_disabled_reason": "", "access_disabled_at": ""}
    if body.password:
        updates["password_hash"] = hash_password(body.password)

    update_doc: dict = {"$set": updates}
    if unset_fields:
        update_doc["$unset"] = unset_fields
    result = await db.users.find_one_and_update(
        {"_id": oid}, update_doc, return_document=True
    )
    if not result:
        raise AppError("USER_NOT_FOUND", "Không tìm thấy tài khoản", 404)
    if body.access_disabled is True:
        # Access token đang sống bị chặn bởi require_auth; thu hồi refresh token để
        # phiên cũ không thể tự gia hạn trong lúc bảo trì.
        await db.refresh_tokens.update_many(
            {"user_id": str(oid), "revoked_at": None},
            {"$set": {"revoked_at": now}},
        )
    return _public(result)


async def delete_user(user_id: str, current_user_id: str) -> None:
    oid = _oid(user_id)
    if str(oid) == current_user_id:
        raise AppError("CANNOT_DELETE_SELF", "Không thể tự xóa tài khoản của chính mình", 400)
    res = await get_db().users.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise AppError("USER_NOT_FOUND", "Không tìm thấy tài khoản", 404)
