"""Nghiệp vụ quản lý tài khoản xã/phường (chỉ admin)."""
import asyncio
import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError

from app.auth.access_control import MAINTENANCE_MESSAGE
from app.core.errors import AppError
from app.db.mongo import get_db
from app.locations.catalog import canonical_location, province_name_variants
from app.users import password_vault
from app.users.schemas import Role, UserCreate, UserUpdate
from app.users.roles import (
    NOT_DELETED,
    SUPER_ADMIN_ROLE,
    TDP_PARENT_ROLE,
    TDP_ROLE,
    normalized_role,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value) -> str | None:
    """ISO có KÈM offset UTC.

    Driver không bật tz_aware nên Mongo trả datetime NAIVE (giá trị là UTC vì mọi chỗ ghi đều
    dùng datetime.now(timezone.utc)). Trả naive ra API thì chuỗi không có offset, trình duyệt
    hiểu là giờ ĐỊA PHƯƠNG → cột "Đăng nhập lần cuối" hiện sớm 7 tiếng.
    """
    if not isinstance(value, datetime):
        return None
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


def _parent_public(parent: dict | None) -> dict | None:
    if not parent:
        return None
    return {
        "id": str(parent["_id"]),
        "username": parent.get("username"),
        "name": parent.get("name"),
        "xa": parent.get("xa"),
        "tinh": parent.get("tinh"),
    }


def _public(user: dict, parent: dict | None = None) -> dict:
    is_tdp = normalized_role(user.get("role")) == TDP_ROLE
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
        # Có giá trị = đã xóa mềm. FE dựa vào đây để đổi hàng sang trạng thái "Đã xóa" kèm
        # nút Khôi phục thay cho Sửa/Xóa.
        "deleted_at": _iso(user.get("deleted_at")),
        # Chỉ báo CÓ/KHÔNG có bản mã hoá; bản thân `password_enc` không bao giờ rời BE qua đây.
        "password_stored": bool(user.get("password_enc")),
        # Tổ dân phố: HCC xã cha (địa bàn đã chép theo cha). Role khác luôn None.
        "parent_id": user.get("parent_id") if is_tdp else None,
        "parent": _parent_public(parent) if is_tdp else None,
    }


async def _parents_by_id(db, users: list[dict]) -> dict[str, dict]:
    """Một truy vấn cho mọi xã cha của các tổ dân phố trong danh sách (không lọc xóa mềm: cha
    đã xóa vẫn phải hiện đúng tên)."""
    oids = []
    for user in users:
        if normalized_role(user.get("role")) != TDP_ROLE or not user.get("parent_id"):
            continue
        try:
            oids.append(ObjectId(user["parent_id"]))
        except (InvalidId, TypeError):
            continue
    if not oids:
        return {}
    cursor = db.users.find(
        {"_id": {"$in": oids}}, {"username": 1, "name": 1, "xa": 1, "tinh": 1},
    )
    return {str(doc["_id"]): doc async for doc in cursor}


async def _public_with_parent(db, user: dict) -> dict:
    parents = await _parents_by_id(db, [user])
    return _public(user, parents.get(str(user.get("parent_id") or "")))


async def _tdp_parent(db, parent_id: str | None, *, self_id: ObjectId | None = None) -> dict:
    """Xã cha hợp lệ của tổ dân phố: tồn tại, chưa xóa, đúng role HCC xã."""
    if not parent_id:
        raise AppError(
            "TDP_PARENT_REQUIRED", "Tổ dân phố phải chọn HCC xã/phường mà nó trực thuộc.", 400,
        )
    try:
        parent_oid = ObjectId(parent_id)
    except (InvalidId, TypeError):
        parent_oid = None
    parent = (
        await db.users.find_one({"_id": parent_oid, **NOT_DELETED})
        if parent_oid is not None and parent_oid != self_id
        else None
    )
    if not parent or normalized_role(parent.get("role")) != TDP_PARENT_ROLE:
        raise AppError(
            "TDP_PARENT_INVALID",
            "HCC xã/phường cha không tồn tại, đã bị xóa hoặc không phải tài khoản Hành chính công xã.",
            400,
        )
    return parent


async def _ensure_no_active_children(db, oid: ObjectId, action: str) -> None:
    count = await db.users.count_documents(
        {"parent_id": str(oid), "role": TDP_ROLE, **NOT_DELETED},
    )
    if count:
        raise AppError(
            "HAS_CHILD_ACCOUNTS",
            f"Tài khoản đang có {count} tổ dân phố trực thuộc. Hãy chuyển các tổ dân phố sang "
            f"HCC xã khác hoặc xóa chúng trước khi {action}.",
            409,
        )


def _oid(user_id: str) -> ObjectId:
    try:
        return ObjectId(user_id)
    except (InvalidId, TypeError):
        raise AppError("USER_NOT_FOUND", "Không tìm thấy tài khoản", 404)


def _role_query(role: Role | None) -> dict:
    """Lọc role công khai và luôn giấu tài khoản Monitor khỏi UI quản lý hiện tại."""
    if role is None:
        return {"role": {"$ne": SUPER_ADMIN_ROLE}}
    if role == "user":
        return {"$or": [
            {"role": "user"},
            {"role": {"$exists": False}},
            {"role": None},
        ]}
    return {"role": role}


async def _ensure_not_last_admin(db, oid: ObjectId) -> None:
    """Chặn thao tác làm hệ thống không còn quản trị viên nào dùng được.

    Áp cho cả ba đường ra: hạ vai trò admin, tạm khóa admin, xóa admin. Mất hết admin thì
    không ai vào được trang quản trị nữa — phải chạy scripts/seed_user.py trên server để cứu.

    Giới hạn đã biết: hai quản trị viên thao tác cùng lúc vẫn có thể lọt qua khe giữa lần đếm
    này và lần ghi. Chặn tuyệt đối cần transaction; cái giá đó không tương xứng với xác suất.
    """
    remaining = await db.users.count_documents({
        **NOT_DELETED,
        "role": "admin",
        "access_disabled": {"$ne": True},
        "_id": {"$ne": oid},
    })
    if remaining == 0:
        raise AppError(
            "LAST_ADMIN",
            "Đây là quản trị viên hoạt động cuối cùng. Hãy cấp quyền quản trị cho một tài "
            "khoản khác trước khi đổi vai trò, tạm khóa hoặc xóa tài khoản này.",
            409,
        )


def _search_query(keyword: str | None) -> dict:
    """Khớp tên đăng nhập HOẶC tên hiển thị.

    re.escape là bắt buộc: quản trị viên gõ "." hay "(" mà ném thẳng vào $regex thì hoặc ra
    kết quả sai, hoặc Mongo ném lỗi cú pháp regex.
    """
    text = (keyword or "").strip()
    if not text:
        return {}
    pattern = {"$regex": re.escape(text), "$options": "i"}
    return {"$or": [{"username": pattern}, {"name": pattern}]}


def _province_query(tinh: str | None) -> dict:
    """Lọc theo tỉnh, chịu được mọi cách ghi tên đang có trong DB.

    Tài khoản cũ lưu "Đà Nẵng", bản mới lưu "Thành phố Đà Nẵng" — so chuỗi thẳng thì sót một
    nửa. Dựng sẵn các biến thể từ danh mục rồi $in: chính xác hơn regex và còn dùng được index.
    """
    text = (tinh or "").strip()
    if not text:
        return {}
    return {"tinh": {"$in": province_name_variants(text)}}


def _status_query(status: str) -> dict:
    """`deleted` là cửa DUY NHẤT nhìn thấy tài khoản đã xóa mềm (để khôi phục)."""
    if status == "deleted":
        return {"deleted_at": {"$ne": None}}
    if status == "active":
        return {**NOT_DELETED, "access_disabled": {"$ne": True}}
    if status == "disabled":
        return {**NOT_DELETED, "access_disabled": True}
    return dict(NOT_DELETED)


async def list_users(
    *,
    skip: int = 0,
    limit: int = 20,
    role: Role | None = None,
    keyword: str | None = None,
    tinh: str | None = None,
    status: str = "all",
) -> dict:
    db = get_db()
    query = {
        **_role_query(role),
        **_status_query(status),
        **_province_query(tinh),
        **_search_query(keyword),
    }
    total = await db.users.count_documents(query)
    cursor = (
        db.users.find(query).sort("username", 1).skip(max(skip, 0)).limit(max(min(limit, 100), 1))
    )
    docs = [u async for u in cursor]
    parents = await _parents_by_id(db, docs)
    items = [_public(u, parents.get(str(u.get("parent_id") or ""))) for u in docs]
    return {"items": items, "total": total}


async def list_parent_accounts() -> list[dict]:
    """HCC xã chưa xóa — lựa chọn "Thuộc HCC xã" khi tạo/sửa tổ dân phố."""
    cursor = get_db().users.find(
        {**NOT_DELETED, "role": TDP_PARENT_ROLE},
        {"username": 1, "name": 1, "xa": 1, "tinh": 1},
    ).sort([("tinh", 1), ("xa", 1), ("username", 1)])
    return [_parent_public(doc) async for doc in cursor]


async def create_user(body: UserCreate) -> dict:
    now = _now()
    parent = None
    if body.role == TDP_ROLE:
        # Địa bàn của tổ dân phố là địa bàn xã cha — không nhận tỉnh/xã từ form.
        parent = await _tdp_parent(get_db(), body.parent_id)
        tinh, xa = parent.get("tinh"), parent.get("xa")
    else:
        tinh, xa = canonical_location(body.tinh, body.xa)
    password_set, _ = password_vault.password_fields(body.password)
    doc = {
        "username": body.username,
        **password_set,
        "name": body.name,
        "xa": xa,
        "tinh": tinh,
        "role": body.role,
        "access_disabled": False,
        "created_at": now,
        "updated_at": now,
    }
    if parent is not None:
        doc["parent_id"] = str(parent["_id"])
    try:
        res = await get_db().users.insert_one(doc)
    except DuplicateKeyError:
        raise AppError("USERNAME_EXISTS", "Tên đăng nhập đã tồn tại", 409)
    doc["_id"] = res.inserted_id
    return _public(doc, parent)


async def update_user(user_id: str, body: UserUpdate, current_user_id: str) -> dict:
    db = get_db()
    oid = _oid(user_id)
    now = _now()
    current = await db.users.find_one({"_id": oid})
    if not current:
        raise AppError("USER_NOT_FOUND", "Không tìm thấy tài khoản", 404)
    if current.get("role") == SUPER_ADMIN_ROLE:
        raise AppError(
            "PROTECTED_ACCOUNT",
            "Tài khoản Monitor được bảo vệ và không thể sửa tại trang quản lý này.",
            403,
        )
    is_self = str(oid) == current_user_id
    was_active_admin = (
        current.get("role") == "admin" and current.get("access_disabled") is not True
    )
    updates: dict = {"updated_at": now}
    unset_fields: dict = {}
    if body.name is not None:
        updates["name"] = body.name
    current_role = normalized_role(current.get("role"))
    new_role = body.role if body.role is not None else current_role
    if current_role == TDP_PARENT_ROLE and new_role != TDP_PARENT_ROLE:
        await _ensure_no_active_children(db, oid, "đổi vai trò")
    location_fields = body.model_fields_set & {"tinh", "xa"}
    if new_role == TDP_ROLE:
        # Tổ dân phố không tự có địa bàn: luôn chép lại từ xã cha (kể cả khi chỉ đổi tên), để
        # địa bàn đã lệch vì dữ liệu cũ cũng tự về đúng.
        parent = await _tdp_parent(db, body.parent_id or current.get("parent_id"), self_id=oid)
        updates["parent_id"] = str(parent["_id"])
        updates["tinh"] = parent.get("tinh")
        updates["xa"] = parent.get("xa")
    elif location_fields:
        # PATCH có thể chỉ gửi một nửa cặp tỉnh-xã. Ghép với dữ liệu đang lưu rồi mới
        # kiểm tra để không cho một xã cũ bị giữ lại dưới tỉnh mới.
        tinh_input = body.tinh if "tinh" in location_fields else current.get("tinh")
        xa_input = body.xa if "xa" in location_fields else current.get("xa")
        tinh, xa = canonical_location(tinh_input, xa_input)
        updates["tinh"] = tinh
        updates["xa"] = xa
    if current_role == TDP_ROLE and new_role != TDP_ROLE:
        unset_fields["parent_id"] = ""
    if body.role is not None and body.role != (current.get("role") or "user"):
        # require_admin đọc lại user từ DB mỗi request, nên tự hạ quyền là mất trang quản trị
        # NGAY, không đợi token hết hạn. Đứng cạnh CANNOT_DISABLE_SELF bên dưới vì cùng một
        # loại tai nạn: tự khóa chính mình ra ngoài.
        if is_self:
            raise AppError(
                "CANNOT_CHANGE_OWN_ROLE",
                "Không thể tự đổi vai trò của chính mình. Hãy nhờ một quản trị viên khác.",
                400,
            )
        if was_active_admin:
            await _ensure_not_last_admin(db, oid)
    if body.role is not None:
        updates["role"] = body.role
    if body.access_disabled is not None:
        if body.access_disabled and str(oid) == current_user_id:
            raise AppError("CANNOT_DISABLE_SELF", "Không thể tự khóa tài khoản của chính mình", 400)
        if body.access_disabled and was_active_admin:
            await _ensure_not_last_admin(db, oid)
        updates["access_disabled"] = body.access_disabled
        if body.access_disabled:
            updates["access_disabled_reason"] = MAINTENANCE_MESSAGE
            updates["access_disabled_at"] = now
        else:
            unset_fields = {"access_disabled_reason": "", "access_disabled_at": ""}
    if body.password:
        password_set, password_unset = password_vault.password_fields(body.password)
        updates.update(password_set)
        unset_fields = {**unset_fields, **password_unset}

    update_doc: dict = {"$set": updates}
    if unset_fields:
        update_doc["$unset"] = unset_fields
    result = await db.users.find_one_and_update(
        {"_id": oid, "role": {"$ne": SUPER_ADMIN_ROLE}, **NOT_DELETED},
        update_doc,
        return_document=True,
    )
    if not result:
        raise AppError("USER_NOT_FOUND", "Không tìm thấy tài khoản", 404)
    if new_role == TDP_PARENT_ROLE and (
        result.get("tinh") != current.get("tinh") or result.get("xa") != current.get("xa")
    ):
        # Địa bàn tổ dân phố là bản chép của xã cha — cha đổi thì con đổi theo, kể cả con đã
        # xóa mềm (khôi phục ra vẫn đúng địa bàn).
        await db.users.update_many(
            {"parent_id": str(oid), "role": TDP_ROLE},
            {"$set": {"tinh": result.get("tinh"), "xa": result.get("xa"), "updated_at": now}},
        )
    if body.access_disabled is True:
        # Access token đang sống bị chặn bởi require_auth; thu hồi refresh token để
        # phiên cũ không thể tự gia hạn trong lúc bảo trì.
        await db.refresh_tokens.update_many(
            {"user_id": str(oid), "revoked_at": None},
            {"$set": {"revoked_at": now}},
        )
    return await _public_with_parent(db, result)


async def delete_user(user_id: str, current_user_id: str) -> None:
    oid = _oid(user_id)
    if str(oid) == current_user_id:
        raise AppError("CANNOT_DELETE_SELF", "Không thể tự xóa tài khoản của chính mình", 400)
    db = get_db()
    current = await db.users.find_one({"_id": oid})
    if not current:
        raise AppError("USER_NOT_FOUND", "Không tìm thấy tài khoản", 404)
    if current.get("role") == SUPER_ADMIN_ROLE:
        raise AppError(
            "PROTECTED_ACCOUNT",
            "Tài khoản Monitor được bảo vệ và không thể xóa tại trang quản lý này.",
            403,
        )
    if current.get("deleted_at") is not None:
        return  # đã xóa rồi, coi như thành công (bấm hai lần không báo lỗi)
    if normalized_role(current.get("role")) == TDP_PARENT_ROLE:
        await _ensure_no_active_children(db, oid, "xóa")
    if current.get("role") == "admin" and current.get("access_disabled") is not True:
        await _ensure_not_last_admin(db, oid)

    now = _now()
    res = await db.users.update_one(
        {"_id": oid, "role": {"$ne": SUPER_ADMIN_ROLE}, **NOT_DELETED},
        {"$set": {"deleted_at": now, "deleted_by": current_user_id, "updated_at": now}},
    )
    if res.matched_count == 0:
        raise AppError("USER_NOT_FOUND", "Không tìm thấy tài khoản", 404)
    # Access token đang sống bị ensure_account_available chặn; thu hồi refresh token để phiên
    # cũ không tự gia hạn được.
    await db.refresh_tokens.update_many(
        {"user_id": str(oid), "revoked_at": None},
        {"$set": {"revoked_at": now}},
    )


async def restore_user(user_id: str) -> dict:
    """Bỏ dấu xóa mềm. Không có đường này thì xóa mềm chỉ là giấu đi, không cứu được gì."""
    db = get_db()
    oid = _oid(user_id)
    current = await db.users.find_one({"_id": oid})
    if current and normalized_role(current.get("role")) == TDP_ROLE:
        # Không khôi phục tổ dân phố "mồ côi": xã cha phải còn dùng được.
        await _tdp_parent(db, current.get("parent_id"), self_id=oid)
    result = await db.users.find_one_and_update(
        {"_id": oid, "role": {"$ne": SUPER_ADMIN_ROLE}, "deleted_at": {"$ne": None}},
        {"$set": {"updated_at": _now()}, "$unset": {"deleted_at": "", "deleted_by": ""}},
        return_document=True,
    )
    if not result:
        raise AppError("USER_NOT_FOUND", "Không tìm thấy tài khoản đã xóa", 404)
    return await _public_with_parent(db, result)


async def _manageable_user(db, oid: ObjectId) -> dict:
    current = await db.users.find_one({"_id": oid, **NOT_DELETED})
    if not current:
        raise AppError("USER_NOT_FOUND", "Không tìm thấy tài khoản", 404)
    if current.get("role") == SUPER_ADMIN_ROLE:
        raise AppError(
            "PROTECTED_ACCOUNT",
            "Tài khoản Monitor được bảo vệ và không thể thao tác tại trang quản lý này.",
            403,
        )
    return current


async def set_password(user_id: str, password: str) -> dict:
    """Admin đặt mật khẩu mới (không cần mật khẩu cũ). Ghi cả bcrypt lẫn bản mã hoá."""
    db = get_db()
    oid = _oid(user_id)
    await _manageable_user(db, oid)
    password_set, password_unset = await asyncio.to_thread(password_vault.password_fields, password)
    update_doc: dict = {"$set": {**password_set, "updated_at": _now()}}
    if password_unset:
        update_doc["$unset"] = password_unset
    result = await db.users.find_one_and_update(
        {"_id": oid, "role": {"$ne": SUPER_ADMIN_ROLE}, **NOT_DELETED},
        update_doc,
        return_document=True,
    )
    if not result:
        raise AppError("USER_NOT_FOUND", "Không tìm thấy tài khoản", 404)
    return _public(result)


async def reveal_password(user_id: str) -> tuple[dict, dict]:
    """(kết quả trả FE, tài khoản) — tài khoản chỉ để router ghi nhật ký."""
    current = await _manageable_user(get_db(), _oid(user_id))
    password = password_vault.decrypt(current.get("password_enc"))
    return {
        "stored": password is not None,
        "password": password,
        "vaultEnabled": password_vault.enabled(),
    }, current
