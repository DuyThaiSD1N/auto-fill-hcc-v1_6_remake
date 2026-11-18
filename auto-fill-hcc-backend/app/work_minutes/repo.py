"""Truy cập Mongo cho biên bản làm việc.

- `work_minutes`: biên bản đã xuất (mỗi lần xuất lưu lại; mở để sửa rồi xuất lại thì cập nhật bản đó).
- `work_minute_drafts`: bản nháp đang làm, mỗi đơn vị một bản (`_id` = unitId) — đổi máy vẫn làm tiếp.
"""
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from app.db.mongo import get_db

HISTORY_CAP = 200
SUGGESTION_CAP = 8


def now() -> datetime:
    return datetime.now(timezone.utc)


def object_id(value: str | None) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


async def get(minutes_id: str) -> dict | None:
    oid = object_id(minutes_id)
    return await get_db().work_minutes.find_one({"_id": oid}) if oid else None


async def latest(unit_id: str) -> dict | None:
    return await get_db().work_minutes.find_one({"unit_id": unit_id}, sort=[("period_to", -1), ("created_at", -1)])


async def history(unit_id: str) -> list[dict]:
    return await (
        get_db().work_minutes.find({"unit_id": unit_id}, {"log": 0, "base": 0})
        .sort([("period_to", -1), ("created_at", -1)]).limit(HISTORY_CAP).to_list(length=HISTORY_CAP)
    )


async def insert(values: dict) -> dict:
    result = await get_db().work_minutes.insert_one(values)
    return {**values, "_id": result.inserted_id}


async def update(minutes_id: ObjectId, values: dict, entry: dict) -> dict | None:
    return await get_db().work_minutes.find_one_and_update(
        {"_id": minutes_id}, {"$set": values, "$push": {"log": entry}}, return_document=ReturnDocument.AFTER,
    )


async def get_draft(unit_id: str) -> dict | None:
    return await get_db().work_minute_drafts.find_one({"_id": unit_id})


async def save_draft(unit_id: str, values: dict) -> dict:
    return await get_db().work_minute_drafts.find_one_and_update(
        {"_id": unit_id}, {"$set": values}, upsert=True, return_document=ReturnDocument.AFTER,
    )


async def delete_draft(unit_id: str) -> None:
    await get_db().work_minute_drafts.delete_one({"_id": unit_id})


async def difficulties(unit_id: str, date_from: str, date_to: str) -> list[dict]:
    """Ô "Khó khăn" trong báo cáo hằng ngày của kỳ — gợi ý cho mục III, mới nhất trước, bỏ câu trùng."""
    docs = await (
        get_db().daily_reports.find(
            {"unit_id": unit_id, "date": {"$gte": date_from, "$lte": date_to}, "difficulties": {"$nin": ["", None]}},
            {"date": 1, "difficulties": 1},
        ).sort("date", -1).limit(100).to_list(length=100)
    )
    out: dict[str, dict] = {}
    for d in docs:
        text = str(d.get("difficulties") or "").strip()
        if text and text not in out:
            out[text] = {"text": text, "date": d.get("date")}
    return list(out.values())[:SUGGESTION_CAP]
