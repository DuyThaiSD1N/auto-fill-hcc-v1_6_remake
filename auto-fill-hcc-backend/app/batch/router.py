"""API nhận hồ sơ batch; OCR/LLM luôn chạy ở worker riêng."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile, status
from pymongo.errors import DuplicateKeyError

from app.batch import repo, storage
from app.batch.auth import require_batch_auth
from app.batch.schemas import BatchJobCreate
from app.config import settings
from app.core.errors import AppError
from app.procedures.registry import get_pipeline, get_procedure


router = APIRouter(
    prefix="/api/v1/batch",
    tags=["batch"],
    dependencies=[Depends(require_batch_auth)],
)

_ITEM_STATUSES = {"staged", "queued", "running", "paused", "done", "failed", "cancelled"}


def _iso(value) -> str | None:
    """ISO có KÈM offset UTC — Mongo trả datetime NAIVE (driver không bật tz_aware) nên thiếu
    offset là trình duyệt hiểu thành giờ địa phương và hiện lệch 7 tiếng."""
    if not isinstance(value, datetime):
        return None
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


def _public_job(job: dict, counts: dict[str, int] | None = None) -> dict:
    return {
        "jobId": job.get("job_id"),
        "name": job.get("name"),
        "procedure": job.get("procedure"),
        "status": job.get("status"),
        "counts": counts or {},
        "createdAt": _iso(job.get("created_at")),
        "startedAt": _iso(job.get("started_at")),
        "finishedAt": _iso(job.get("finished_at")),
    }


def _public_item(item: dict, *, include_result: bool = False) -> dict:
    files = item.get("files") or []
    out = {
        "itemId": item.get("item_id"),
        "jobId": item.get("job_id"),
        "clientDossierId": item.get("client_dossier_id"),
        "procedure": item.get("procedure"),
        "status": item.get("status"),
        "attempts": item.get("attempts") or 0,
        "fileCount": len(files),
        "totalBytes": item.get("total_bytes") or 0,
        "hasErrors": item.get("has_errors") is True,
        "error": item.get("error"),
        "createdAt": _iso(item.get("created_at")),
        "startedAt": _iso(item.get("started_at")),
        "finishedAt": _iso(item.get("finished_at")),
    }
    if include_result:
        out["result"] = item.get("result")
        out["files"] = [
            {
                "name": file.get("name"),
                "type": file.get("type"),
                "role": file.get("role"),
                "size": file.get("size"),
                "sha256": file.get("sha256"),
            }
            for file in files
        ]
    return out


async def _require_job(job_id: str) -> dict:
    job = await repo.get_job(job_id)
    if not job:
        raise AppError("BATCH_JOB_NOT_FOUND", "Không tìm thấy batch.", 404)
    return job


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
async def create_job(body: BatchJobCreate) -> dict:
    proc = get_procedure(body.procedure)
    if not proc or not get_pipeline(body.procedure):
        raise AppError("UNKNOWN_PROCEDURE", f"Thủ tục không hỗ trợ bóc tách: {body.procedure}", 400)
    job = await repo.create_job(name=body.name, procedure=body.procedure)
    return _public_job(job, {"total": 0})


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    job = await _require_job(job_id)
    return _public_job(job, await repo.item_counts(job_id))


@router.post("/jobs/{job_id}/items", status_code=status.HTTP_202_ACCEPTED)
async def add_item(
    job_id: str,
    metadata: str = Form(...),
    files: list[UploadFile] = File(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    job = await _require_job(job_id)
    if job.get("status") != "draft":
        raise AppError("BATCH_JOB_NOT_DRAFT", "Chỉ có thể thêm hồ sơ khi batch đang ở bản nháp.", 409)

    parsed = storage.parse_item_metadata(metadata, len(files))
    key = (idempotency_key or "").strip() or None
    if key and len(key) > 200:
        raise AppError("BAD_IDEMPOTENCY_KEY", "Idempotency-Key quá dài.", 400)

    existing = await repo.find_existing_item(
        job_id=job_id,
        client_dossier_id=parsed.clientDossierId,
        idempotency_key=key,
    )
    if existing:
        return {**_public_item(existing), "duplicate": True}

    if await repo.count_active_items() >= settings.batch_max_pending_items:
        raise AppError(
            "BATCH_QUEUE_FULL",
            "Hàng đợi batch đã đầy. Vui lòng thử lại sau.",
            429,
        )

    item_id = repo.new_item_id()
    files_meta, total_bytes = await storage.save_uploads(
        job_id=job_id,
        item_id=item_id,
        uploads=files,
        metadata=parsed,
    )
    fingerprint = storage.input_fingerprint(job["procedure"], files_meta)
    existing = await repo.find_existing_item(
        job_id=job_id,
        input_fingerprint=fingerprint,
    )
    if existing:
        storage.remove_item_files(job_id, item_id)
        return {**_public_item(existing), "duplicate": True}

    try:
        item = await repo.create_item(
            item_id=item_id,
            job_id=job_id,
            client_dossier_id=parsed.clientDossierId,
            procedure=job["procedure"],
            options=parsed.options,
            files=files_meta,
            total_bytes=total_bytes,
            input_fingerprint=fingerprint,
            idempotency_key=key,
        )
    except DuplicateKeyError:
        storage.remove_item_files(job_id, item_id)
        existing = await repo.find_existing_item(
            job_id=job_id,
            client_dossier_id=parsed.clientDossierId,
            idempotency_key=key,
            input_fingerprint=fingerprint,
        )
        if not existing:
            raise AppError("BATCH_ITEM_CONFLICT", "Hồ sơ bị trùng nhưng không thể đối chiếu.", 409)
        return {**_public_item(existing), "duplicate": True}
    return {**_public_item(item), "duplicate": False}


@router.post("/jobs/{job_id}/start")
async def start_job(job_id: str) -> dict:
    await _require_job(job_id)
    job = await repo.start_job(job_id)
    if not job:
        raise AppError("BATCH_CANNOT_START", "Batch không ở bản nháp hoặc chưa có hồ sơ.", 409)
    return _public_job(job, await repo.item_counts(job_id))


@router.post("/jobs/{job_id}/pause")
async def pause_job(job_id: str) -> dict:
    await _require_job(job_id)
    job = await repo.pause_job(job_id)
    if not job:
        raise AppError("BATCH_CANNOT_PAUSE", "Chỉ batch đang chạy mới có thể tạm dừng.", 409)
    return _public_job(job, await repo.item_counts(job_id))


@router.post("/jobs/{job_id}/resume")
async def resume_job(job_id: str) -> dict:
    await _require_job(job_id)
    job = await repo.resume_job(job_id)
    if not job:
        raise AppError("BATCH_CANNOT_RESUME", "Chỉ batch đang tạm dừng mới có thể chạy tiếp.", 409)
    return _public_job(job, await repo.item_counts(job_id))


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict:
    await _require_job(job_id)
    job = await repo.cancel_job(job_id)
    if not job:
        raise AppError("BATCH_CANNOT_CANCEL", "Batch đã kết thúc hoặc đã bị hủy.", 409)
    return _public_job(job, await repo.item_counts(job_id))


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str) -> dict:
    job = await _require_job(job_id)
    if job.get("status") not in {"completed", "cancelled"}:
        raise AppError("BATCH_CANNOT_DELETE", "Chỉ batch đã hoàn tất hoặc đã hủy mới được xóa.", 409)
    counts = await repo.item_counts(job_id)
    if counts.get("running", 0):
        raise AppError(
            "BATCH_STILL_PROCESSING",
            "Batch vẫn còn hồ sơ đang xử lý; hãy chờ worker dừng trước khi xóa.",
            409,
        )
    # Dọn file trước khi xóa metadata để nếu disk lỗi vẫn còn bản ghi cho phép thử lại.
    await asyncio.to_thread(storage.remove_job_files, job_id)
    if not await repo.delete_terminal_job(job_id):
        raise AppError("BATCH_CANNOT_DELETE", "Chỉ batch đã hoàn tất hoặc đã hủy mới được xóa.", 409)
    return {"jobId": job_id, "deleted": True}


@router.get("/jobs/{job_id}/items")
async def list_items(
    job_id: str,
    item_status: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, alias="pageSize", ge=1, le=200),
) -> dict:
    await _require_job(job_id)
    if item_status and item_status not in _ITEM_STATUSES:
        raise AppError("BAD_BATCH_STATUS", "Trạng thái hồ sơ batch không hợp lệ.", 400)
    items = await repo.list_items(
        job_id,
        skip=(page - 1) * page_size,
        limit=page_size,
        status=item_status,
    )
    return {"items": [_public_item(item) for item in items], "page": page, "pageSize": page_size}


@router.get("/items/{item_id}/result")
async def get_item_result(item_id: str) -> dict:
    item = await repo.get_item(item_id)
    if not item:
        raise AppError("BATCH_ITEM_NOT_FOUND", "Không tìm thấy hồ sơ batch.", 404)
    return _public_item(item, include_result=True)


@router.post("/items/{item_id}/retry")
async def retry_item(item_id: str) -> dict:
    item = await repo.retry_item(item_id)
    if not item:
        raise AppError("BATCH_CANNOT_RETRY", "Chỉ hồ sơ lỗi trong batch còn hiệu lực mới chạy lại được.", 409)
    return _public_item(item)


@router.get("/jobs/{job_id}/results")
async def list_results(
    job_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, alias="pageSize", ge=1, le=200),
) -> dict:
    await _require_job(job_id)
    items = await repo.list_completed_items(
        job_id,
        skip=(page - 1) * page_size,
        limit=page_size,
    )
    return {
        "items": [_public_item(item, include_result=True) for item in items],
        "page": page,
        "pageSize": page_size,
    }
