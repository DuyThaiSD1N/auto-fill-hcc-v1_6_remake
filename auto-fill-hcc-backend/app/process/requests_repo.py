"""Lưu bản ghi mỗi request /process vào collection process_requests.

Mỗi request có _id mới (ObjectId), created_at, danh sách file đã lưu + trạng thái + stats.
"""
from datetime import datetime, timezone

from bson import ObjectId

from app.archive.config import archive_settings
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
    if archive_settings.enabled:
        doc["archive_pending"] = True
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
            **({"archive_pending": True} if archive_settings.enabled else {}),
        }},
    )


async def get_request_by_request_id(request_id: str, user_id: str | None = None) -> dict | None:
    query: dict = {"request_id": request_id}
    if user_id:
        query["user_id"] = user_id
    return await get_db().process_requests.find_one(query)


async def find_stored_files(user_id: str, sha256s: list[str], since: datetime) -> dict[str, str]:
    """{sha256: đường dẫn tương đối} của tệp CHÍNH tài khoản này đã gửi từ ``since`` (lượt điền/đính)."""
    found: dict[str, str] = {}
    cursor = get_db().process_requests.find(
        {"user_id": user_id, "created_at": {"$gte": since}, "files.sha256": {"$in": sha256s}},
        {"files.sha256": 1, "files.path": 1},
    ).sort("created_at", -1)
    async for doc in cursor:
        for f in doc.get("files") or []:
            if f.get("sha256") in sha256s and f.get("path"):
                found.setdefault(f["sha256"], f["path"])
    return found
