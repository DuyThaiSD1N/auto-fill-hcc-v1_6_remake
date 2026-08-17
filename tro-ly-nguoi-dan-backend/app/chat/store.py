"""Conversation store — phiên hội thoại toàn trình (docs/03a §1-2).

Nguồn sự thật DUY NHẤT của phiên nằm ở đây (Mongo `conversations`, TTL 24h trượt theo
updated_at — index khai ở app/db/indexes.py). FE chỉ giữ con trỏ conversation_id.
"""
import uuid
from datetime import datetime, timezone

from app.db.mongo import get_db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def new_conversation(location: dict | None = None) -> dict:
    return {
        "_id": f"c-{uuid.uuid4().hex[:20]}",
        "state": "greet",
        "location": location or {},          # {province, province_slug, ward}
        "procedure_key": None,
        "doc_method": None,                   # qr | scan | profile
        "upload_session_id": None,
        "fields": [],                         # kết quả pipeline (hợp đồng cũ) — Bước 6
        "fill_report": {},                    # {filled, missing, assumed} — Bước 6
        "attach_done": False,
        "awaiting_events": [],                # watcher FE chỉ canh đúng những event này
        "phone": None,
        "profile_id": None,
        "history": [],                        # [{role, text, state, source, ts}]
        "last_reply": None,                   # Reply đã render lượt gần nhất (khôi phục sidebar)
        "created_at": _now(),
        "updated_at": _now(),
    }


async def get(conv_id: str) -> dict | None:
    if not conv_id:
        return None
    return await get_db().conversations.find_one({"_id": conv_id})


async def save(conv: dict) -> None:
    conv["updated_at"] = _now()
    await get_db().conversations.replace_one({"_id": conv["_id"]}, conv, upsert=True)


def push_history(conv: dict, role: str, text: str, source: str = "") -> None:
    conv["history"].append({
        "role": role,
        "text": text,
        "state": conv.get("state", ""),
        "source": source,
        "ts": _now(),
    })
    # Giữ history gọn (phiên dài chủ yếu là sự kiện) — 200 lượt là quá đủ để khôi phục UI.
    if len(conv["history"]) > 200:
        conv["history"] = conv["history"][-200:]
