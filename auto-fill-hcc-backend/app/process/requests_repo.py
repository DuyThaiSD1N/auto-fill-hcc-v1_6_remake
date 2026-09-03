"""Lưu bản ghi mỗi request /process vào collection process_requests.

Mỗi request có _id mới (ObjectId), created_at, danh sách file đã lưu + trạng thái + stats.
"""
from datetime import datetime, timezone

from bson import ObjectId

from app.db.mongo import get_db


async def create_request(
    *,
    request_id: str,
    created_at: datetime,
    user_id: str,
    procedure: str,
    options: dict,
    files_meta: list[dict],
    experience: str = "autofill",
) -> str:
    doc = {
        "request_id": request_id,
        "user_id": user_id,
        "procedure": procedure,
        "options": options or {},
        "files": files_meta,
        "status": "processing",
        "experience": experience,
        "created_at": created_at,
    }
    res = await get_db().process_requests.insert_one(doc)
    return str(res.inserted_id)


async def finish_request(
    doc_id: str | None,
    *,
    status: str,
    stats: dict | None = None,
    fields_count: int | None = None,
    fields: list[dict] | None = None,
    extracted: dict | None = None,
    error_code: str | None = None,
) -> None:
    if not doc_id:
        return
    await get_db().process_requests.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {
            "status": status,
            "stats": stats,
            "fields_count": fields_count,
            "fields": fields,
            "extracted": extracted,
            "error_code": error_code,
            "finished_at": datetime.now(timezone.utc),
        }},
    )


async def get_request_by_request_id(request_id: str, user_id: str | None = None) -> dict | None:
    query: dict = {"request_id": request_id}
    if user_id:
        query["user_id"] = user_id
    return await get_db().process_requests.find_one(query)
