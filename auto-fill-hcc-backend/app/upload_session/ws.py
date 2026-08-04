"""WS /ws/upload-sessions/{sid} — extension popup subscribe để nhận ảnh điện thoại realtime.

Registry in-memory theo sid (quy mô pilot, server đơn instance). LƯU Ý DEPLOY: nếu chạy
nhiều worker uvicorn (--workers >1), event chỉ tới worker đang giữ kết nối WS đó → tuyến WS
cần chạy 1 worker hoặc sticky session. Reverse proxy (nginx) phải cho Upgrade websocket.
Sự kiện: session_opened (điện thoại vừa mở trang) · files_added (vừa có ảnh mới).
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
    # role=mobile → báo cho popup biết điện thoại đã mở trang (đổi trạng thái "đang chờ quét").
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
