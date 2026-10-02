"""WS /ws/upload-sessions/{sid} — extension popup subscribe để nhận ảnh điện thoại realtime.

Registry kết nối nằm trong RAM từng worker uvicorn. Chạy nhiều worker (--workers >1) thì request
phát sự kiện và kết nối WS nhận sự kiện có thể ở hai worker khác nhau → mọi sự kiện còn được ghi
vào capped collection `ws_events`; mỗi worker tail collection đó (relay_events_forever) để đẩy
sự kiện của worker khác xuống các WS mình đang giữ. Reverse proxy (nginx) phải cho Upgrade websocket.
Sự kiện: session_opened (điện thoại vừa mở trang) · files_added (vừa có ảnh mới) · các sự kiện
tiến độ/pipeline của Handfree.
"""
import asyncio
import logging
import os
import socket
import uuid
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pymongo import CursorType
from pymongo.errors import PyMongoError

from app.config import settings
from app.db.mongo import get_db
from app.upload_session import store
from app.upload_session.access import upload_session_experience, verify_upload_capability

logger = logging.getLogger(__name__)

router = APIRouter()

_SUBS: dict[str, set[WebSocket]] = {}

EVENTS_COLLECTION = "ws_events"
# Capped: Mongo tự đè bản cũ nhất, không cần TTL; tailable cursor chỉ chạy trên capped collection
# (Mongo trong compose là standalone, không có change stream).
EVENTS_CAPPED_BYTES = 16 * 1024 * 1024
# Phân biệt sự kiện do chính worker này phát (đã giao trực tiếp) với sự kiện của worker khác.
_WORKER_ID = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"
# Mở lại cursor sau lỗi: đọc lùi một khoảng để không sót sự kiện ghi trong lúc cursor đứt;
# trùng lặp do đọc lùi được chặn bằng tập _id đã xử lý.
_RESUME_MARGIN = timedelta(seconds=5)
_SEEN_MAX = 5000


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _deliver_local(sid: str, payload: dict) -> None:
    dead = []
    for ws in _SUBS.get(sid, set()):
        try:
            await ws.send_json(payload)
        except Exception:  # noqa: BLE001 — client rớt thì dọn
            dead.append(ws)
    for ws in dead:
        _SUBS.get(sid, set()).discard(ws)


async def broadcast(sid: str, payload: dict) -> None:
    await _deliver_local(sid, payload)
    try:
        await get_db()[EVENTS_COLLECTION].insert_one(
            {"sid": sid, "payload": payload, "origin": _WORKER_ID, "at": _now()}
        )
    except PyMongoError:
        # Mất Mongo thì WS ở worker khác lỡ sự kiện này; Auto Fill còn poll, không chặn luồng chính.
        logger.warning("Không ghi được ws_events sid=%s", sid, exc_info=True)


async def handle_relayed_event(doc: dict, seen: "OrderedDict") -> bool:
    """Giao một sự kiện đọc từ ws_events. Trả True nếu đã đẩy xuống WS của worker này."""
    event_id = doc.get("_id")
    if event_id in seen:
        return False
    seen[event_id] = None
    while len(seen) > _SEEN_MAX:
        seen.popitem(last=False)
    sid = doc.get("sid")
    if doc.get("origin") == _WORKER_ID or sid not in _SUBS:
        return False
    await _deliver_local(sid, doc.get("payload") or {})
    return True


async def relay_events_forever() -> None:
    """Tail ws_events suốt vòng đời worker; lỗi/cursor chết thì mở lại sau 1 giây."""
    coll = get_db()[EVENTS_COLLECTION]
    seen: OrderedDict = OrderedDict()
    since = _now()
    while True:
        try:
            # Không lọc trong query: tailable cursor với điều kiện không khớp bản nào sẽ chết
            # ngay; bỏ sự kiện cũ ở phía client theo mốc `at`.
            cursor = coll.find({}, cursor_type=CursorType.TAILABLE_AWAIT)
            while cursor.alive:
                async for doc in cursor:
                    at = doc.get("at")
                    if at is None or at < since - _RESUME_MARGIN:
                        continue
                    since = max(since, at)
                    await handle_relayed_event(doc, seen)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — relay không được chết theo một lỗi Mongo/WS
            logger.warning("Relay ws_events lỗi, mở lại cursor", exc_info=True)
        await asyncio.sleep(1)


@router.websocket("/ws/upload-sessions/{sid}")
@router.websocket("/ws/assistant/document-sessions/{sid}")
async def ws_upload_session(ws: WebSocket, sid: str):
    # Mobile không có JWT nên capability đi qua WebSocket subprotocol. Token không đặt trong
    # query string để tránh lọt vào Nginx access log. Route mới còn chặn mở nhầm UI Handfree.
    role = ws.query_params.get("role", "")
    if ws.url.path.startswith("/ws/assistant/") and not settings.handfree_enabled:
        await ws.close(code=4404, reason="Kênh Handfree chưa được bật")
        return
    accept_subprotocol = None
    if role == "mobile":
        protocols = [
            value.strip()
            for value in ws.headers.get("sec-websocket-protocol", "").split(",")
            if value.strip()
        ]
        token = next(
            (
                value.removeprefix("tlnd-token.")
                for value in protocols
                if value.startswith("tlnd-token.")
            ),
            "",
        )
        if not verify_upload_capability(sid, token):
            await ws.close(code=4401, reason="Upload capability không hợp lệ")
            return
        sess = await store.get(sid)
        if not sess:
            await ws.close(code=4404, reason="Phiên không tồn tại hoặc đã hết hạn")
            return
        if (ws.url.path.startswith("/ws/assistant/")
                and upload_session_experience(sess) != "handfree"):
            await ws.close(code=4409, reason="Phiên không thuộc Handfree")
            return
        if "tlnd-upload" in protocols:
            accept_subprotocol = "tlnd-upload"

    await ws.accept(subprotocol=accept_subprotocol)
    _SUBS.setdefault(sid, set()).add(ws)
    if role == "mobile":
        await broadcast(sid, {"type": "session_opened"})
    try:
        while True:
            await ws.receive_text()  # giữ kết nối; client không cần gửi gì
    except WebSocketDisconnect:
        pass
    finally:
        _SUBS.get(sid, set()).discard(ws)
        if not _SUBS.get(sid):
            _SUBS.pop(sid, None)
