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
    # Thống kê v2: dossier_ids là multikey; hash nằm trên từng attachment. Hai index này
    # phục vụ đối soát/tra cứu riêng, còn lọc dashboard dùng procedure + created_at ở trên.
    await db.traces.create_index("dossier_ids")
    await db.traces.create_index("attachments.sha256")
    # Cache OCR (_id = hash nội dung, tra bằng index primary). TTL tự dọn text OCR cũ.
    await db.ocr_cache.create_index(
        "created_at", expireAfterSeconds=settings.ocr_cache_ttl_days * 86400
    )
    # Phiên tải ảnh QR: TTL tự dọn phiên hết hạn (bytes ảnh trên đĩa dọn theo cron/thủ công).
    await db.upload_sessions.create_index(
        "created_at", expireAfterSeconds=settings.upload_session_ttl_minutes * 60
    )
    # Bằng chứng chấp thuận PDPL — KHÔNG TTL (phải giữ lâu dài để đối soát).
    await db.consent_logs.create_index("log_id")
    await db.consent_logs.create_index([("user_id", 1), ("created_at", -1)])
