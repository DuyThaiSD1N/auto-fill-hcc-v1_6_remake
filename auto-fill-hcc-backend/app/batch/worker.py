"""Worker OCR + LLM batch với concurrency hữu hạn và Mongo lease."""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import socket
from pathlib import Path

from app.batch import repo
from app.batch.storage import batch_root
from app.config import settings
from app.core.errors import AppError
from app.process.schemas import FileItem, ProcessReq, ProcessResp
from app.process.service import execute_process, prepare_process
from app.procedures.registry import get_pipeline, get_procedure


logger = logging.getLogger(__name__)


async def _heartbeat(item_id: str, worker_id: str, stop: asyncio.Event) -> None:
    """Giữ lease khi OCR/LLM chạy lâu; mất ownership thì tự dừng."""
    interval = max(min(settings.batch_lease_seconds / 3, 60), 1)
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
            return
        except asyncio.TimeoutError:
            if not await repo.extend_lease(item_id, worker_id):
                return


def _resolve_batch_file(relative_path: str) -> Path:
    root = batch_root()
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise AppError("BATCH_FILE_INVALID", "Đường dẫn file batch không hợp lệ.", 400) from exc
    if not target.is_file():
        raise AppError("BATCH_FILE_MISSING", "File batch không còn trên hệ thống.", 400)
    return target


def _load_file_items(item: dict) -> list[FileItem]:
    files: list[FileItem] = []
    for meta in item.get("files") or []:
        path = _resolve_batch_file(str(meta.get("path") or ""))
        raw = path.read_bytes()
        media_type = str(meta.get("type") or "application/octet-stream")
        files.append(FileItem(
            name=str(meta.get("name") or path.name),
            type=media_type,
            role=str(meta.get("role") or "doc"),
            hasHandwriting=meta.get("hasHandwriting") is True,
            dataUrl=f"data:{media_type};base64,{base64.b64encode(raw).decode('ascii')}",
        ))
    return files


async def process_item(item: dict, worker_id: str) -> None:
    item_id = item["item_id"]
    job_id = item["job_id"]
    heartbeat_stop = asyncio.Event()
    heartbeat_task = asyncio.create_task(_heartbeat(item_id, worker_id, heartbeat_stop))
    try:
        job = await repo.get_job(job_id)
        if not job or job.get("status") == "cancelled":
            await repo.cancel_running_item(item_id, worker_id)
            return

        body = ProcessReq(
            procedure=item["procedure"],
            options=item.get("options") or {},
            files=await asyncio.to_thread(_load_file_items, item),
        )
        prepared = prepare_process(
            body,
            proc=get_procedure(body.procedure),
            pipeline=get_pipeline(body.procedure),
            include_review=False,
        )
        raw_result = await execute_process(prepared)
        raw_result.pop("_review", None)
        result = ProcessResp.model_validate({
            "fields": raw_result.get("fields") or [],
            "extracted": raw_result.get("extracted") or {},
            "stats": raw_result.get("stats") or {},
            "errors": raw_result.get("errors") or [],
            "sessionId": item_id,
            "requestId": item_id,
            "pages": raw_result.get("pages"),
            "businessFlow": raw_result.get("businessFlow"),
        }).model_dump(mode="json")

        job = await repo.get_job(job_id)
        if not job or job.get("status") == "cancelled":
            await repo.cancel_running_item(item_id, worker_id)
        else:
            await repo.complete_item(item_id, worker_id, result)
    except AppError as exc:
        await repo.fail_item(item, worker_id, f"{exc.error}: {exc.message}", retryable=False)
        logger.warning("Batch item %s lỗi không retry: %s", item_id, exc.error)
    except Exception as exc:  # noqa: BLE001 - worker phải lưu lỗi và tiếp tục item kế.
        target = await repo.fail_item(item, worker_id, str(exc), retryable=True)
        logger.exception("Batch item %s lỗi -> %s", item_id, target)
    finally:
        heartbeat_stop.set()
        await asyncio.gather(heartbeat_task, return_exceptions=True)
        await repo.finish_job_if_terminal(job_id)


async def _worker_slot(slot: int, stop: asyncio.Event) -> None:
    worker_id = f"{socket.gethostname()}:{os.getpid()}:{slot}"
    while not stop.is_set():
        item = await repo.claim_next(worker_id)
        if not item:
            try:
                await asyncio.wait_for(stop.wait(), timeout=max(settings.batch_poll_seconds, 0.1))
            except asyncio.TimeoutError:
                pass
            continue
        await process_item(item, worker_id)


async def _recovery_loop(stop: asyncio.Event) -> None:
    while not stop.is_set():
        recovered = await repo.recover_expired_items()
        if recovered:
            logger.warning("Đã thu hồi %d batch item hết lease", recovered)
        try:
            await asyncio.wait_for(stop.wait(), timeout=30)
        except asyncio.TimeoutError:
            pass


async def run_worker(stop: asyncio.Event | None = None) -> None:
    stop = stop or asyncio.Event()
    concurrency = max(int(settings.batch_worker_concurrency), 1)
    logger.info("Khởi động batch worker concurrency=%d", concurrency)
    tasks = [asyncio.create_task(_worker_slot(index + 1, stop)) for index in range(concurrency)]
    tasks.append(asyncio.create_task(_recovery_loop(stop)))
    try:
        await asyncio.gather(*tasks)
    finally:
        stop.set()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
