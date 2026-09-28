"""Nhật ký thao tác nhạy cảm trên mật khẩu tài khoản (xem, đổi, nạp, xuất file).

Không bao giờ ghi mật khẩu — chỉ ai làm, làm gì, trên tài khoản nào, lúc nào.
"""
import logging
from datetime import datetime, timezone

from app.db.mongo import get_db

logger = logging.getLogger(__name__)


async def record(action: str, actor: dict, **details) -> None:
    doc = {
        "action": action,
        "actor_id": str(actor.get("id") or actor.get("_id") or ""),
        "actor_username": actor.get("username"),
        "at": datetime.now(timezone.utc),
        **details,
    }
    try:
        await get_db().account_access_logs.insert_one(doc)
    except Exception:  # noqa: BLE001 — ghi nhật ký hỏng không được chặn thao tác chính
        logger.exception("Không ghi được account_access_logs action=%s", action)
