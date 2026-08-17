"""WS /ws/upload-sessions/{sid} — sidebar VÀ trang mobile cùng subscribe (docs/05 §1).

Registry in-memory theo session id; server đơn instance (đúng quy mô pilot).
Event: session_opened · files_added · progress · complete · file_removed · expired.
"""
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

_SUBS: dict[str, set[WebSocket]] = {}


async def broadcast(sid: str, payload: dict) -> None:
    dead = []
    for ws in _SUBS.get(sid, set()):
        try:
            await ws.send_json(payload)
        except Exception:  # noqa: BLE001 — client rớt thì dọn
            dead.append(ws)
    for ws in dead:
        _SUBS.get(sid, set()).discard(ws)


@router.websocket("/ws/upload-sessions/{sid}")
async def ws_upload_session(ws: WebSocket, sid: str):
    await ws.accept()
    _SUBS.setdefault(sid, set()).add(ws)
    # role=mobile → báo cho sidebar biết điện thoại đã kết nối (bước 5 prototype).
    role = ws.query_params.get("role", "")
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
