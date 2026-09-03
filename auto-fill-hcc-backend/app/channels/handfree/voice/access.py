"""Xác thực JWT cho WebSocket voice của extension Handfree.

WebSocket phía trình duyệt không gắn được header Authorization. Extension gửi access token
qua subprotocol ``tlnd-auth.<jwt>``; token không nằm trong URL nên không lọt vào access log.
"""
from bson import ObjectId
from fastapi import WebSocket

from app.auth.access_control import ensure_account_available
from app.core.security import decode_access_token
from app.db.mongo import get_db


def _protocols(ws: WebSocket) -> list[str]:
    return [
        item.strip()
        for item in ws.headers.get("sec-websocket-protocol", "").split(",")
        if item.strip()
    ]


async def authenticate_voice_websocket(ws: WebSocket) -> tuple[dict | None, str | None]:
    """Trả ``(user, accepted_subprotocol)``; tự đóng WS với 4401/4403 khi không hợp lệ."""
    protocols = _protocols(ws)
    raw_token = next(
        (
            item.removeprefix("tlnd-auth.")
            for item in protocols
            if item.startswith("tlnd-auth.")
        ),
        "",
    )
    payload = decode_access_token(raw_token) if raw_token else None
    if not payload or payload.get("type") != "access" or not payload.get("sub"):
        await ws.close(code=4401, reason="Access token voice không hợp lệ hoặc đã hết hạn")
        return None, None

    try:
        user = await get_db().users.find_one({"_id": ObjectId(payload["sub"])})
    except Exception:  # noqa: BLE001 - sub sai format cũng là token không hợp lệ
        user = None
    if not user:
        await ws.close(code=4401, reason="Không tìm thấy tài khoản voice")
        return None, None
    try:
        ensure_account_available(user)
    except Exception:  # noqa: BLE001 - không phơi chi tiết trạng thái tài khoản qua WS
        await ws.close(code=4403, reason="Tài khoản không được phép sử dụng voice")
        return None, None

    user["id"] = str(user["_id"])
    accepted = "tlnd-voice" if "tlnd-voice" in protocols else None
    return user, accepted
