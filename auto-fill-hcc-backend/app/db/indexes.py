from pymongo.errors import OperationFailure

from app.config import settings
from app.db.mongo import get_db


async def _ensure_ttl(db, coll: str, field: str, seconds: int) -> None:
    """Đổi TTL an toàn khi index đã tồn tại với expireAfterSeconds khác."""
    try:
        await db[coll].create_index(field, expireAfterSeconds=seconds)
        return
    except OperationFailure:
        pass
    try:
        await db.command(
            "collMod",
            coll,
            index={"keyPattern": {field: 1}, "expireAfterSeconds": seconds},
        )
    except OperationFailure:
        await db[coll].drop_index(f"{field}_1")
        await db[coll].create_index(field, expireAfterSeconds=seconds)


async def _migrate_legacy_upload_ttl(db) -> None:
    """Backfill ``expires_at`` rồi bỏ TTL cũ theo ``created_at``.

    Phải backfill trước khi drop; nếu không, các session đang sống từ bản cũ không có
    ``expires_at`` sẽ không bao giờ được Mongo TTL dọn nữa.
    """
    try:
        base_date = {"$ifNull": ["$updated_at", {"$ifNull": ["$created_at", "$$NOW"]}]}
        handfree_filter = {
            "expires_at": {"$exists": False},
            "$or": [
                {"conversation_id": {"$exists": True}},
                {"procedure_key": {"$exists": True}},
                {"required_docs": {"$exists": True}},
            ],
        }
        await db.upload_sessions.update_many(
            handfree_filter,
            [{"$set": {"experience": "handfree", "expires_at": {
                "$add": [base_date, settings.upload_session_ttl_hours * 3600 * 1000]
            }}}],
        )
        await db.upload_sessions.update_many(
            {"expires_at": {"$exists": False}},
            [{"$set": {"experience": "autofill", "expires_at": {
                "$add": [base_date, settings.upload_session_ttl_minutes * 60 * 1000]
            }}}],
        )
        indexes = await db.upload_sessions.index_information()
        legacy = indexes.get("created_at_1") or {}
        if "expireAfterSeconds" in legacy:
            await db.upload_sessions.drop_index("created_at_1")
    except OperationFailure:
        # Không làm hỏng startup nếu Mongo managed không cho sửa index; health/deploy sẽ
        # phát hiện TTL cũ qua kiểm tra index sau khi ứng dụng khởi động.
        pass


async def ensure_indexes() -> None:
    db = get_db()
    await db.users.create_index("username", unique=True)
    await db.refresh_tokens.create_index("token_hash")
    await db.refresh_tokens.create_index("user_id")
    # TTL: tự xoá refresh token hết hạn.
    await db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.audit_logs.create_index([("user_id", 1), ("created_at", -1)])
    await db.audit_logs.create_index([("procedure", 1), ("created_at", -1)])
    await db.audit_logs.create_index([("experience", 1), ("created_at", -1)])
    await db.process_requests.create_index([("user_id", 1), ("created_at", -1)])
    await db.process_requests.create_index("request_id")
    await db.process_requests.create_index([("procedure", 1), ("created_at", -1)])
    await db.process_requests.create_index([("experience", 1), ("request_id", 1)])
    # Batch extraction: job/item tách khỏi traces để chiến dịch test không làm sai báo cáo hồ sơ thật.
    await db.batch_jobs.create_index("job_id", unique=True)
    await db.batch_jobs.create_index([("status", 1), ("created_at", -1)])
    await db.batch_items.create_index("item_id", unique=True)
    await db.batch_items.create_index([("job_id", 1), ("client_dossier_id", 1)], unique=True)
    await db.batch_items.create_index([("job_id", 1), ("input_fingerprint", 1)], unique=True)
    await db.batch_items.create_index([("status", 1), ("available_at", 1), ("created_at", 1)])
    await db.batch_items.create_index([("job_id", 1), ("status", 1), ("created_at", 1)])
    await db.batch_items.create_index(
        [("job_id", 1), ("idempotency_key", 1)],
        unique=True,
        partialFilterExpression={"idempotency_key": {"$type": "string"}},
    )
    # Trace màn theo dõi /process.
    await db.traces.create_index([("created_at", -1)])
    await db.traces.create_index([("user_id", 1), ("created_at", -1)])
    await db.traces.create_index([("procedure", 1), ("created_at", -1)])
    await db.traces.create_index([("experience", 1), ("created_at", -1)])
    await db.traces.create_index([("experience", 1), ("user_id", 1), ("created_at", -1)])
    # Tra trace theo "mã hỗ trợ" (request_id) cán bộ copy từ extension khi báo lỗi.
    await db.traces.create_index("request_id")
    # Thống kê v2: dossier_ids là multikey; hash nằm trên từng attachment. Hai index này
    # phục vụ đối soát/tra cứu riêng, còn lọc dashboard dùng procedure + created_at ở trên.
    await db.traces.create_index("dossier_ids")
    # Khóa hồ sơ dùng chung 2 kênh (= dossiers._id) — tra mọi lượt điền/đính kèm của 1 hồ sơ.
    await db.traces.create_index("dossier_id")
    await db.traces.create_index("attachments.sha256")
    # Cache OCR (_id = hash nội dung, tra bằng index primary). TTL tự dọn text OCR cũ.
    await db.ocr_cache.create_index(
        "created_at", expireAfterSeconds=settings.ocr_cache_ttl_hours * 3600
    )
    # Mỗi channel có vòng đời khác nhau nên document tự mang expires_at; TTL index dùng 0.
    await _migrate_legacy_upload_ttl(db)
    await _ensure_ttl(db, "upload_sessions", "expires_at", 0)
    # Hội thoại Handfree gia hạn theo mỗi lượt chat.
    await _ensure_ttl(db, "conversations", "updated_at", 24 * 3600)
    # Vòng đời hồ sơ Handfree (_id = conversation_id) — KHÔNG TTL: conversations tự xoá sau
    # 24h, mốc bắt đầu/nộp phải sống lâu hơn thế thì báo cáo mới dùng được.
    await db.dossiers.create_index([("user_id", 1), ("started_at", -1)])
    await db.dossiers.create_index([("procedure", 1), ("started_at", -1)])
    # Lọc nhanh "hồ sơ đã nộp" (submit_clicked_at tồn tại) theo thời gian.
    await db.dossiers.create_index([("submit_clicked_at", -1)])
    # Cách đếm hồ sơ từ 15/9/2026 (app/stats/cutover.py) quét theo đúng ba khóa này: nguồn
    # kênh, tập đơn vị trong phạm vi tài khoản, rồi mốc nộp.
    await db.dossiers.create_index([("experience", 1), ("user_id", 1), ("submit_clicked_at", -1)])
    # Nhật ký phiên tải ảnh QR (_id = sid) — KHÔNG TTL. `upload_sessions` tự xoá sau 30 phút
    # (Auto Fill) / 24h (Handfree); nhật ký phải sống lâu hơn thì mới điều tra được ca
    # "điện thoại báo đã gửi mà máy tính không thấy".
    await db.upload_session_logs.create_index([("user_id", 1), ("created_at", -1)])
    await db.upload_session_logs.create_index([("experience", 1), ("created_at", -1)])
    # Lọc nhanh phiên có gửi lên mà máy tính chưa lấy hết.
    await db.upload_session_logs.create_index([("delivered", 1), ("received", 1)])
    # Bằng chứng chấp thuận PDPL — KHÔNG TTL (phải giữ lâu dài để đối soát).
    await db.consent_logs.create_index("log_id")
    await db.consent_logs.create_index([("user_id", 1), ("created_at", -1)])
    await db.consent_logs.create_index([("experience", 1), ("created_at", -1)])
