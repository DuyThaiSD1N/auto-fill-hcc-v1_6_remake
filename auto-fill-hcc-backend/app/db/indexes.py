from app.config import settings
from app.db.mongo import get_db


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
    # Tra trace theo "mã hỗ trợ" (request_id) cán bộ copy từ extension khi báo lỗi.
    await db.traces.create_index("request_id")
    # Cache OCR (_id = hash nội dung, tra bằng index primary). TTL tự dọn text OCR cũ.
    await db.ocr_cache.create_index(
        "created_at", expireAfterSeconds=settings.ocr_cache_ttl_days * 86400
    )
