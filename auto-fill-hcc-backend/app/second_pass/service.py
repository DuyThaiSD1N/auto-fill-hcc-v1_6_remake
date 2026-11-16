"""Điền đợt 2: lượt điền đầu trả cho extension như cũ, lượt soát chạy ở nền rồi extension hỏi lấy các ô cần ghi lại.

Trạng thái nằm ở Mongo (collection ``second_pass``, _id = request_id) vì BE chạy nhiều worker: lượt hỏi kết quả có thể
rơi vào worker khác worker đang soát. Bản ghi mang giá trị trường của người dân nên có TTL ngắn (app/db/indexes.py);
bản lưu lâu dài đi cùng ``process_requests`` qua archiver."""
from __future__ import annotations

import asyncio
import contextvars
import logging
import time
from datetime import datetime, timezone
from typing import Awaitable, Callable

from app.archive.config import archive_settings
from app.config import settings
from app.db.mongo import get_db

logger = logging.getLogger(__name__)

# (ô UI lượt đầu) → {"fields": các ô cần ghi lại, "rulings": biên bản, "timing": thời gian}
Run = Callable[[list[dict]], Awaitable[dict]]

_running: set[asyncio.Task] = set()
# Bản ghi process_requests do tác vụ lưu vết của lượt đầu tạo, có thể chưa kịp có khi lượt soát xong.
_KEEP_TRIES = 4
_KEEP_WAIT_SECONDS = 3


def capability(procedure: dict | None) -> str:
    """Tên năng lực extension phải khai để thủ tục này chạy điền đợt 2. Thủ tục trên form cũ (eForm x-*, entry
    registry khai ``secondPass: "legacy"``) cần bản extension biết ghi lại ô trên form cũ — bản chỉ biết form
    SurveyJS khai "secondPass" thì không chạy."""
    kind = (procedure or {}).get("secondPass")
    if kind == "legacy":
        return "secondPassLegacy"
    # Form Angular (cổng liên thông): bản extension phải biết ghi lại ô trên form Angular.
    return "secondPassAngular" if kind == "angular" else "secondPass"


def wanted(user: dict | None, client_supports: bool) -> bool:
    """Chỉ chạy khi BE bật, extension khai biết áp bản vá, và tài khoản nằm trong diện thí điểm (trống = mọi tài khoản)."""
    if not settings.second_pass_enabled or not client_supports:
        return False
    pilot = {name.strip() for name in settings.second_pass_usernames.split(",") if name.strip()}
    return not pilot or str((user or {}).get("username") or "") in pilot


async def start(request_id: str | None, user_id: str | None, run: Run, base_fields: list[dict]) -> bool:
    """Ghi trạng thái "đang soát" rồi thả lượt soát chạy nền. False = không chạy (quá tải / thiếu định danh / lỗi ghi)."""
    if not request_id or not user_id or len(_running) >= settings.second_pass_max_running:
        return False
    try:
        await get_db().second_pass.insert_one({
            "_id": request_id, "user_id": str(user_id), "status": "pending", "at": datetime.now(timezone.utc),
        })
    except Exception as exc:  # noqa: BLE001 — đợt 2 là phần thêm, hỏng thì lượt đầu vẫn nguyên
        logger.warning("Đợt 2: không ghi được trạng thái (%s): %r", request_id, exc)
        return False
    # Context rỗng: lượt soát không ghi span / lượt LLM của mình vào bản ghi Monitor của lượt đầu đang được lưu.
    task = asyncio.create_task(_job(request_id, run, base_fields), context=contextvars.Context())
    _running.add(task)
    task.add_done_callback(_running.discard)
    return True


async def _job(request_id: str, run: Run, base_fields: list[dict]) -> None:
    t0 = time.monotonic()
    update: dict = {"status": "failed"}
    try:
        outcome = await asyncio.wait_for(run(base_fields), settings.second_pass_timeout_seconds)
        update = {"status": "done", "fields": outcome.get("fields") or [], "rulings": outcome.get("rulings") or [],
                  "timing": outcome.get("timing") or {}}
    except asyncio.TimeoutError:
        update["reason"] = "timeout"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Đợt 2: lượt soát lỗi (%s): %r", request_id, exc)
        update["reason"] = repr(exc)[:200]
    update["ms"] = int((time.monotonic() - t0) * 1000)
    try:
        await get_db().second_pass.update_one({"_id": request_id}, {"$set": update})
        await _keep(request_id, update)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Đợt 2: không lưu được kết quả (%s): %r", request_id, exc)


async def _keep(request_id: str, outcome: dict) -> None:
    """Lưu kết quả đợt 2 cạnh kết quả lượt đầu (``process_requests.fields`` giữ nguyên) để đối chiếu về sau."""
    change = {"second_pass": outcome, **({"archive_pending": True} if archive_settings.enabled else {})}
    for attempt in range(_KEEP_TRIES):
        done = await get_db().process_requests.update_one({"request_id": request_id}, {"$set": change})
        if done.matched_count:
            return
        if attempt + 1 < _KEEP_TRIES:
            await asyncio.sleep(_KEEP_WAIT_SECONDS)


async def result(request_id: str, user_id: str) -> dict:
    """pending = đang soát; done = đã xong (``fields`` có thể rỗng); none = không có đợt 2 cho lượt này."""
    doc = await get_db().second_pass.find_one({"_id": request_id, "user_id": str(user_id)})
    if not doc:
        return {"status": "none"}
    if doc.get("status") == "done":
        return {"status": "done", "fields": doc.get("fields") or []}
    at = doc.get("at")
    if doc.get("status") == "pending" and isinstance(at, datetime):
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        # Worker đang soát bị khởi động lại thì bản ghi kẹt ở "pending": quá hạn chạy coi như không có.
        if (datetime.now(timezone.utc) - at).total_seconds() <= settings.second_pass_timeout_seconds + 5:
            return {"status": "pending"}
    return {"status": "none"}
