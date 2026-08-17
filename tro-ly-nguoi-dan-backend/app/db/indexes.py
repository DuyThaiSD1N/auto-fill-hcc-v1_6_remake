from pymongo.errors import OperationFailure

from app.db.mongo import get_db


async def _ensure_ttl(db, coll: str, field: str, seconds: int) -> None:
    """create_index KHÔNG cho đổi expireAfterSeconds trên index đã tồn tại (IndexOptionsConflict)
    → đổi TTL bằng collMod (không rebuild); Mongo không hỗ trợ thì drop + tạo lại."""
    try:
        await db[coll].create_index(field, expireAfterSeconds=seconds)
        return
    except OperationFailure:
        pass
    try:
        await db.command("collMod", coll,
                         index={"keyPattern": {field: 1}, "expireAfterSeconds": seconds})
    except OperationFailure:
        await db[coll].drop_index(f"{field}_1")
        await db[coll].create_index(field, expireAfterSeconds=seconds)


async def ensure_indexes() -> None:
    db = get_db()
    await db.users.create_index("username", unique=True)
    await db.refresh_tokens.create_index("token_hash")
    await db.refresh_tokens.create_index("user_id")
    # TTL: tự xoá refresh token hết hạn.
    await db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.audit_logs.create_index([("user_id", 1), ("created_at", -1)])
    await db.audit_logs.create_index([("procedure", 1), ("created_at", -1)])
    await db.process_requests.create_index([("user_id", 1), ("created_at", -1)])
    await db.process_requests.create_index("request_id")
    await db.process_requests.create_index([("procedure", 1), ("created_at", -1)])
    # Trace màn theo dõi /process.
    await db.traces.create_index([("created_at", -1)])
    await db.traces.create_index([("user_id", 1), ("created_at", -1)])
    await db.traces.create_index([("procedure", 1), ("created_at", -1)])
    # Phiên hội thoại trợ lý (docs/03a): TTL 24h TRƯỢT theo updated_at (mỗi lượt chat gia hạn).
    await _ensure_ttl(db, "conversations", "updated_at", 24 * 3600)
    # Phiên tải giấy tờ QR (docs/05): TTL cứng theo created_at — KHỚP vòng đời hội thoại
    # (đổi số giờ trong config vẫn an toàn nhờ _ensure_ttl).
    from app.config import settings as _st
    await _ensure_ttl(db, "upload_sessions", "created_at", _st.upload_session_ttl_hours * 3600)
