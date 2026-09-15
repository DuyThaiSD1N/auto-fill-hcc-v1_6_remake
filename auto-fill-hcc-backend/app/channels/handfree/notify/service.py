"""Đăng ký SĐT nhận thông báo tiến độ (docs/08 §2).

Phase đầu: lưu đăng ký + LogNotifier (in log). Interface `send()` tách riêng để thay
SMS brandname / Zalo ZNS khi có hợp đồng — KHÔNG đổi flow.
"""
import logging
import re
from datetime import datetime, timezone

from app.db.mongo import get_db

logger = logging.getLogger(__name__)

_PHONE_RE = re.compile(r"^(0|\+84)\d{9,10}$")


def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"[\s.\-()]", "", str(raw or ""))
    if digits.startswith("+84"):
        digits = "0" + digits[3:]
    return digits if _PHONE_RE.match(digits) else None


async def subscribe(conv: dict, phone: str) -> bool:
    p = normalize_phone(phone)
    if not p:
        return False
    await get_db().notify_subscriptions.update_one(
        {"conversation_id": conv["_id"]},
        {"$set": {
            "phone": p,
            "procedure_key": conv.get("procedure_key"),
            "location": conv.get("location", {}),
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    conv["phone"] = p
    send(p, f"Trợ lý nhân dân: đã ghi nhận hồ sơ {conv.get('procedure_key') or ''} của công dân. "
            "Có tiến độ mới chúng tôi sẽ nhắn ngay.")
    return True


def send(phone: str, message: str) -> None:
    """LogNotifier — thay bằng SMS/ZNS provider khi có (giữ nguyên chữ ký)."""
    logger.info("[notify→%s] %s", phone, message)
