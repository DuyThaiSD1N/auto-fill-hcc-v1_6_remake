"""Truy cập Mongo cho báo lỗi: collection `bug_reports` + bộ đếm mã `bug_report_counters`.

Xoá là xoá MỀM (`deleted_at`) như tài khoản: lỗi đã xoá ẩn khỏi mọi danh sách nhưng ảnh và
nhật ký vẫn còn để đối chiếu.
"""
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from app.db.mongo import get_db

NOT_DELETED = {"deleted_at": None}
_TRACE_LIMIT = 20


def now() -> datetime:
    return datetime.now(timezone.utc)


def object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


async def next_seq(prefix: str) -> int:
    """Số thứ tự theo TIỀN TỐ mã (không theo đơn vị): hai xã cùng chữ đầu không ra trùng mã."""
    doc = await get_db().bug_report_counters.find_one_and_update(
        {"_id": prefix}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER,
    )
    return int(doc["seq"])


async def insert(doc: dict) -> None:
    await get_db().bug_reports.insert_one(doc)


async def get(report_id: str) -> dict | None:
    oid = object_id(report_id)
    if oid is None:
        return None
    return await get_db().bug_reports.find_one({"_id": oid, **NOT_DELETED})


async def find_dossier(dossier_id: str, user_ids: list[str]) -> dict | None:
    return await get_db().dossiers.find_one(
        {"_id": dossier_id, "user_id": {"$in": user_ids}},
        {"procedure": 1, "procedure_label": 1, "started_at": 1, "experience": 1},
    )


async def list_page(query: dict, *, skip: int, limit: int) -> tuple[list[dict], int]:
    db = get_db()
    total = await db.bug_reports.count_documents(query)
    docs = await (
        db.bug_reports.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    )
    return docs, total


async def count_by(query: dict, field: str) -> dict[str, int]:
    rows = await get_db().bug_reports.aggregate([
        {"$match": query},
        {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
    ]).to_list(length=None)
    return {str(row["_id"] or ""): int(row["count"]) for row in rows}


async def update(report_id: ObjectId, changes: dict, log: list[dict]) -> dict | None:
    return await get_db().bug_reports.find_one_and_update(
        {"_id": report_id, **NOT_DELETED},
        {"$set": changes, "$push": {"log": {"$each": log}}},
        return_document=ReturnDocument.AFTER,
    )


async def trace_requests(dossier_id: str) -> list[dict]:
    """Các lượt chạy của hồ sơ (mã hỗ trợ = request_id) để admin tra trên web Monitor/quản trị."""
    docs = await (
        get_db().traces.find({"dossier_id": dossier_id}, {"request_id": 1, "kind": 1, "created_at": 1})
        .sort("created_at", -1).limit(_TRACE_LIMIT).to_list(length=_TRACE_LIMIT)
    )
    return docs
