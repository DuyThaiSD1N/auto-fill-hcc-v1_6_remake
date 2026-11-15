"""Truy cập Mongo cho báo cáo hằng ngày: collection `daily_reports`, mỗi tài khoản đơn vị 1 báo cáo/ngày
(khoá duy nhất user_id + date). Gửi lại trong ngày = cập nhật, có nhật ký `log`."""
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from app.db.mongo import get_db

EXPORT_CAP = 20_000


def now() -> datetime:
    return datetime.now(timezone.utc)


def object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


async def get(report_id: str) -> dict | None:
    oid = object_id(report_id)
    return await get_db().daily_reports.find_one({"_id": oid}) if oid else None


async def find_day(user_id: str, day: str) -> dict | None:
    return await get_db().daily_reports.find_one({"user_id": user_id, "date": day})


async def upsert_day(user_id: str, day: str, values: dict, on_insert: dict, entry: dict) -> dict:
    return await get_db().daily_reports.find_one_and_update(
        {"user_id": user_id, "date": day},
        {"$set": values, "$setOnInsert": on_insert, "$push": {"log": entry}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )


async def list_page(query: dict, *, skip: int, limit: int) -> tuple[list[dict], int]:
    db = get_db()
    total = await db.daily_reports.count_documents(query)
    docs = await (
        db.daily_reports.find(query, {"log": 0})
        .sort([("date", -1), ("unit_name", 1)]).skip(skip).limit(limit).to_list(length=limit)
    )
    return docs, total


async def totals(query: dict) -> dict:
    rows = await get_db().daily_reports.aggregate([
        {"$match": query},
        {"$group": {
            "_id": None,
            "reports": {"$sum": 1},
            "assistant": {"$sum": "$assistant_count"},
            "actual": {"$sum": "$actual_count"},
            "units": {"$addToSet": "$unit_id"},
            "firstDate": {"$min": "$date"},
        }},
    ]).to_list(length=1)
    row = rows[0] if rows else {}
    return {
        "reports": int(row.get("reports") or 0),
        "assistant": int(row.get("assistant") or 0),
        "actual": int(row.get("actual") or 0),
        "units": len(row.get("units") or []),
        "firstDate": row.get("firstDate"),
    }


async def by_day(query: dict) -> list[dict]:
    rows = await get_db().daily_reports.aggregate([
        {"$match": query},
        {"$group": {
            "_id": "$date",
            "reports": {"$sum": 1},
            "assistant": {"$sum": "$assistant_count"},
            "actual": {"$sum": "$actual_count"},
        }},
        {"$sort": {"_id": 1}},
    ]).to_list(length=None)
    return [
        {"date": r["_id"], "reports": int(r["reports"]), "assistant": int(r["assistant"]), "actual": int(r["actual"])}
        for r in rows
    ]


async def units_on(query: dict, day: str) -> set[str]:
    ids = await get_db().daily_reports.distinct("unit_id", {**query, "date": day})
    return {str(i) for i in ids if i}


async def for_export(query: dict) -> list[dict]:
    return await (
        get_db().daily_reports.find(query, {"log": 0})
        .sort([("date", 1), ("province", 1), ("unit_name", 1)]).limit(EXPORT_CAP).to_list(length=EXPORT_CAP)
    )
