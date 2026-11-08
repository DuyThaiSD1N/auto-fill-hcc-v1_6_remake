"""Collection `dossier_resume`: mỗi hồ sơ handfree đang làm dở (chưa nộp) một bản ghi, `_id` = conversation_id.

Hội thoại bị xoá ngay khi sidebar về màn đầu và archiver xoá sau 30 phút không thao tác, nên dữ liệu từng bước
được sao sang đây sau mỗi lượt chat. Bản ghi tự hết hạn 30 phút sau lần thao tác cuối hoặc sau lúc phiên bị đóng
(TTL trên `expires_at`, khai ở app/db/indexes.py). Không đưa vào kho: mọi giá trị ở đây là bản sao của hội thoại
và form-snapshot vốn đã được archiver / relay gửi kho; hết hạn là xoá như `bac_ninh_prefill`.
"""
from datetime import datetime, timedelta, timezone

from app.db.mongo import get_db

COLL = "dossier_resume"
WINDOW = timedelta(minutes=30)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def minutes_left(record: dict) -> int:
    expires = _aware(record.get("expires_at"))
    return max(0, int((expires - _now()).total_seconds() // 60)) if expires else 0


async def get(record_id: str) -> dict | None:
    if not record_id:
        return None
    record = await get_db()[COLL].find_one({"_id": record_id})
    return record if record and minutes_left(record) > 0 else None


async def latest(user_id: str, procedure_key: str) -> dict | None:
    """Hồ sơ dở mới nhất của tài khoản quầy cho đúng thủ tục, còn hạn."""
    if not user_id or not procedure_key:
        return None
    return await get_db()[COLL].find_one(
        {"user_id": user_id, "procedure_key": procedure_key, "expires_at": {"$gt": _now()}},
        sort=[("last_activity_at", -1)],
    )


async def save(record_id: str, fields: dict) -> None:
    """Ghi mốc mới nhất của hồ sơ; khoá do đường khác ghi (declaration_snapshot) không bị đụng tới."""
    now = _now()
    await get_db()[COLL].update_one(
        {"_id": record_id},
        {"$set": {**fields, "last_activity_at": now, "expires_at": now + WINDOW},
         "$setOnInsert": {"created_at": now}},
        upsert=True,
    )


async def rekey(record: dict, new_id: str) -> dict:
    """Khôi phục sang hội thoại mới: chuyển nguyên bản ghi sang khoá mới để lần gián đoạn sau vẫn khôi phục được."""
    moved = {**record, "_id": new_id, "resumed_from": record["_id"]}
    moved.pop("closed_at", None)
    moved.pop("close_reason", None)
    await get_db()[COLL].replace_one({"_id": new_id}, moved, upsert=True)
    await delete(record["_id"])
    return moved


async def close(record_id: str, reason: str) -> None:
    """Phiên bị đóng (hết giờ chờ / cổng văng về trang chủ): giữ thêm đúng một cửa sổ tính từ lúc đóng."""
    now = _now()
    await get_db()[COLL].update_one(
        {"_id": record_id},
        {"$set": {"closed_at": now, "close_reason": reason, "expires_at": now + WINDOW}},
    )


async def delete(record_id: str) -> None:
    if record_id:
        await get_db()[COLL].delete_one({"_id": record_id})


async def set_declaration_snapshot(user_id: str, request_id: str, snapshot: dict) -> bool:
    """Ảnh chụp tờ khai mới nhất (bản cán bộ đã sửa) của lượt điền `request_id`. Ảnh cũ hơn bản đang giữ thì bỏ."""
    if not user_id or not request_id:
        return False
    res = await get_db()[COLL].update_one(
        {"user_id": user_id, "steps.declaration.request_id": request_id, "expires_at": {"$gt": _now()},
         "$or": [{"declaration_snapshot": None},
                 {"declaration_snapshot.request_id": {"$ne": request_id}},
                 {"declaration_snapshot.at": {"$lte": snapshot["at"]}}]},
        {"$set": {"declaration_snapshot": {**snapshot, "request_id": request_id}}},
    )
    return res.matched_count > 0

