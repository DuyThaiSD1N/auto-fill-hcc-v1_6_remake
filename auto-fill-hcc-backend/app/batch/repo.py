"""MongoDB durable queue cho batch extraction."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument

from app.config import settings
from app.db.mongo import get_db


TERMINAL_ITEM_STATUSES = {"done", "failed", "cancelled"}
ACTIVE_ITEM_STATUSES = {"staged", "queued", "running", "paused"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_job_id() -> str:
    return "job_" + uuid.uuid4().hex[:16]


def new_item_id() -> str:
    return "item_" + uuid.uuid4().hex[:16]


async def create_job(*, name: str, procedure: str) -> dict:
    created_at = now()
    doc = {
        "job_id": new_job_id(),
        "name": name,
        "procedure": procedure,
        "status": "draft",
        "created_at": created_at,
        "updated_at": created_at,
        "started_at": None,
        "finished_at": None,
    }
    await get_db().batch_jobs.insert_one(doc)
    return doc


async def get_job(job_id: str) -> dict | None:
    return await get_db().batch_jobs.find_one({"job_id": job_id})


async def get_item(item_id: str) -> dict | None:
    return await get_db().batch_items.find_one({"item_id": item_id})


async def find_existing_item(
    *,
    job_id: str,
    client_dossier_id: str | None = None,
    idempotency_key: str | None = None,
    input_fingerprint: str | None = None,
) -> dict | None:
    alternatives: list[dict] = []
    if client_dossier_id:
        alternatives.append({"client_dossier_id": client_dossier_id})
    if idempotency_key:
        alternatives.append({"idempotency_key": idempotency_key})
    if input_fingerprint:
        alternatives.append({"input_fingerprint": input_fingerprint})
    if not alternatives:
        return None
    return await get_db().batch_items.find_one({"job_id": job_id, "$or": alternatives})


async def count_active_items() -> int:
    return await get_db().batch_items.count_documents({"status": {"$in": list(ACTIVE_ITEM_STATUSES)}})


async def create_item(
    *,
    item_id: str,
    job_id: str,
    client_dossier_id: str,
    procedure: str,
    options: dict,
    files: list[dict],
    total_bytes: int,
    input_fingerprint: str,
    idempotency_key: str | None,
) -> dict:
    created_at = now()
    doc = {
        "item_id": item_id,
        "job_id": job_id,
        "client_dossier_id": client_dossier_id,
        "procedure": procedure,
        "options": options or {},
        "files": files,
        "total_bytes": total_bytes,
        "input_fingerprint": input_fingerprint,
        "idempotency_key": idempotency_key or None,
        "status": "staged",
        "attempts": 0,
        "available_at": created_at,
        "worker_id": None,
        "lease_until": None,
        "result": None,
        "error": None,
        "has_errors": False,
        "created_at": created_at,
        "updated_at": created_at,
        "started_at": None,
        "finished_at": None,
    }
    await get_db().batch_items.insert_one(doc)
    return doc


async def item_counts(job_id: str) -> dict[str, int]:
    rows = await get_db().batch_items.aggregate([
        {"$match": {"job_id": job_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]).to_list(length=20)
    counts = {str(row["_id"]): int(row["count"]) for row in rows}
    counts["total"] = sum(counts.values())
    counts["done_with_errors"] = await get_db().batch_items.count_documents({
        "job_id": job_id,
        "status": "done",
        "has_errors": True,
    })
    return counts


async def start_job(job_id: str) -> dict | None:
    db = get_db()
    if await db.batch_items.count_documents({"job_id": job_id, "status": "staged"}) == 0:
        return None
    changed = await db.batch_jobs.find_one_and_update(
        {"job_id": job_id, "status": "draft"},
        {"$set": {"status": "running", "started_at": now(), "updated_at": now()}},
        return_document=ReturnDocument.AFTER,
    )
    if changed:
        await db.batch_items.update_many(
            {"job_id": job_id, "status": "staged"},
            {"$set": {"status": "queued", "available_at": now(), "updated_at": now()}},
        )
    return changed


async def pause_job(job_id: str) -> dict | None:
    db = get_db()
    changed = await db.batch_jobs.find_one_and_update(
        {"job_id": job_id, "status": "running"},
        {"$set": {"status": "paused", "updated_at": now()}},
        return_document=ReturnDocument.AFTER,
    )
    if changed:
        await db.batch_items.update_many(
            {"job_id": job_id, "status": "queued"},
            {"$set": {"status": "paused", "updated_at": now()}},
        )
    return changed


async def resume_job(job_id: str) -> dict | None:
    db = get_db()
    changed = await db.batch_jobs.find_one_and_update(
        {"job_id": job_id, "status": "paused"},
        {"$set": {"status": "running", "updated_at": now()}},
        return_document=ReturnDocument.AFTER,
    )
    if changed:
        await db.batch_items.update_many(
            {"job_id": job_id, "status": "paused"},
            {"$set": {"status": "queued", "available_at": now(), "updated_at": now()}},
        )
    return changed


async def cancel_job(job_id: str) -> dict | None:
    db = get_db()
    changed = await db.batch_jobs.find_one_and_update(
        {"job_id": job_id, "status": {"$in": ["draft", "running", "paused"]}},
        {"$set": {"status": "cancelled", "finished_at": now(), "updated_at": now()}},
        return_document=ReturnDocument.AFTER,
    )
    if changed:
        await db.batch_items.update_many(
            {"job_id": job_id, "status": {"$in": ["staged", "queued", "paused"]}},
            {"$set": {"status": "cancelled", "finished_at": now(), "updated_at": now()}},
        )
    return changed


async def list_items(job_id: str, *, skip: int, limit: int, status: str | None = None) -> list[dict]:
    query: dict = {"job_id": job_id}
    if status:
        query["status"] = status
    cursor = (
        get_db().batch_items.find(query, {"files.path": 0, "result": 0})
        .sort("created_at", 1)
        .skip(max(skip, 0))
        .limit(max(min(limit, 200), 1))
    )
    return [item async for item in cursor]


async def list_completed_items(job_id: str, *, skip: int, limit: int) -> list[dict]:
    cursor = (
        get_db().batch_items.find({"job_id": job_id, "status": "done"}, {"files.path": 0})
        .sort("created_at", 1)
        .skip(max(skip, 0))
        .limit(max(min(limit, 200), 1))
    )
    return [item async for item in cursor]


async def claim_next(worker_id: str) -> dict | None:
    current = now()
    return await get_db().batch_items.find_one_and_update(
        {"status": "queued", "available_at": {"$lte": current}},
        {"$set": {
            "status": "running",
            "worker_id": worker_id,
            "lease_until": current + timedelta(seconds=settings.batch_lease_seconds),
            "started_at": current,
            "updated_at": current,
            "error": None,
        }, "$inc": {"attempts": 1}},
        sort=[("created_at", 1)],
        return_document=ReturnDocument.AFTER,
    )


async def recover_expired_items() -> int:
    db = get_db()
    expired = [
        item async for item in db.batch_items.find(
            {"status": "running", "lease_until": {"$lt": now()}},
            {"item_id": 1, "job_id": 1},
        )
    ]
    recovered = 0
    for item in expired:
        job = await db.batch_jobs.find_one({"job_id": item["job_id"]}, {"status": 1})
        job_status = (job or {}).get("status")
        target_status = {
            "running": "queued",
            "paused": "paused",
            "cancelled": "cancelled",
        }.get(job_status, "failed")
        update = {
            "status": target_status,
            "worker_id": None,
            "lease_until": None,
            "updated_at": now(),
            "available_at": now(),
            "error": "Worker dừng trước khi hoàn tất; hồ sơ đã được thu hồi.",
        }
        if target_status in TERMINAL_ITEM_STATUSES:
            update["finished_at"] = now()
        result = await db.batch_items.update_one(
            {"item_id": item["item_id"], "status": "running"},
            {"$set": update},
        )
        recovered += result.modified_count
    return recovered


async def extend_lease(item_id: str, worker_id: str) -> bool:
    """Gia hạn quyền xử lý để OCR/LLM lâu không bị worker khác nhận lại."""
    current = now()
    result = await get_db().batch_items.update_one(
        {"item_id": item_id, "status": "running", "worker_id": worker_id},
        {"$set": {
            "lease_until": current + timedelta(seconds=settings.batch_lease_seconds),
            "updated_at": current,
        }},
    )
    return bool(result.modified_count)


async def complete_item(item_id: str, worker_id: str, result: dict) -> bool:
    update = await get_db().batch_items.update_one(
        {"item_id": item_id, "status": "running", "worker_id": worker_id},
        {"$set": {
            "status": "done",
            "result": result,
            "has_errors": bool(result.get("errors")),
            "worker_id": None,
            "lease_until": None,
            "finished_at": now(),
            "updated_at": now(),
        }},
    )
    return bool(update.modified_count)


async def cancel_running_item(item_id: str, worker_id: str) -> None:
    await get_db().batch_items.update_one(
        {"item_id": item_id, "status": "running", "worker_id": worker_id},
        {"$set": {
            "status": "cancelled",
            "worker_id": None,
            "lease_until": None,
            "finished_at": now(),
            "updated_at": now(),
        }},
    )


async def fail_item(item: dict, worker_id: str, error: str, *, retryable: bool) -> str:
    attempts = int(item.get("attempts") or 0)
    should_retry = retryable and attempts < settings.batch_max_attempts
    status = "queued" if should_retry else "failed"
    delay = min(5 * (2 ** max(attempts - 1, 0)), 300) if should_retry else 0
    update: dict = {
        "status": status,
        "error": error[:2000],
        "worker_id": None,
        "lease_until": None,
        "updated_at": now(),
        "available_at": now() + timedelta(seconds=delay),
    }
    if not should_retry:
        update["finished_at"] = now()
    await get_db().batch_items.update_one(
        {"item_id": item["item_id"], "status": "running", "worker_id": worker_id},
        {"$set": update},
    )
    return status


async def retry_item(item_id: str) -> dict | None:
    db = get_db()
    item = await db.batch_items.find_one({"item_id": item_id, "status": "failed"})
    if not item:
        return None
    job = await db.batch_jobs.find_one({"job_id": item["job_id"]}, {"status": 1})
    job_status = (job or {}).get("status")
    target = {
        "running": "queued",
        "paused": "paused",
        "draft": "staged",
        "completed": "queued",
    }.get(job_status)
    if not target:
        return None
    if job_status == "completed":
        reopened = await db.batch_jobs.update_one(
            {"job_id": item["job_id"], "status": "completed"},
            {"$set": {"status": "running", "finished_at": None, "updated_at": now()}},
        )
        if not reopened.modified_count:
            return None
    return await db.batch_items.find_one_and_update(
        {"item_id": item_id, "status": "failed"},
        {"$set": {
            "status": target,
            "attempts": 0,
            "available_at": now(),
            "error": None,
            "finished_at": None,
            "updated_at": now(),
        }},
        return_document=ReturnDocument.AFTER,
    )


async def finish_job_if_terminal(job_id: str) -> None:
    db = get_db()
    active = await db.batch_items.count_documents({
        "job_id": job_id,
        "status": {"$in": ["staged", "queued", "running", "paused"]},
    })
    if active == 0:
        await db.batch_jobs.update_one(
            {"job_id": job_id, "status": "running"},
            {"$set": {"status": "completed", "finished_at": now(), "updated_at": now()}},
        )


async def delete_terminal_job(job_id: str) -> bool:
    """Xóa metadata sau khi caller đã lấy kết quả; không đụng batch còn worker chạy."""
    db = get_db()
    running = await db.batch_items.count_documents({"job_id": job_id, "status": "running"})
    if running:
        return False
    job = await db.batch_jobs.find_one(
        {"job_id": job_id, "status": {"$in": ["completed", "cancelled"]}},
        {"_id": 1},
    )
    if not job:
        return False
    await db.batch_items.delete_many({"job_id": job_id})
    deleted = await db.batch_jobs.delete_one({"_id": job["_id"]})
    return bool(deleted.deleted_count)
