from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.channels.handfree.voice import access, router
from app.core.deps import require_auth
from app.core.errors import AppError, app_error_handler


class _VoiceWebSocket:
    def __init__(self, protocols: str = ""):
        self.headers = {"sec-websocket-protocol": protocols}
        self.closed = None

    async def close(self, code: int, reason: str):
        self.closed = (code, reason)


def test_voice_config_bat_buoc_dang_nhap(monkeypatch):
    app = FastAPI()
    app.include_router(router.router)
    app.add_exception_handler(AppError, app_error_handler)
    client = TestClient(app)
    assert client.get("/api/v1/voice/config").status_code == 401

    app.dependency_overrides[require_auth] = lambda: {"id": "u1"}
    monkeypatch.setattr(router.settings, "asr_grpc_uri", "127.0.0.1:9112")
    monkeypatch.setattr(router.settings, "asr_grpc_token", "")
    monkeypatch.setattr(router.settings, "tts_ws_url", "ws://127.0.0.1:8767")
    monkeypatch.setattr(router.settings, "tts_api_key", "key")
    data = client.get("/api/v1/voice/config").json()
    assert data["asr"] is False
    assert data["tts"] is True


async def test_voice_ws_thieu_jwt_bi_dong_truoc_khi_truy_db(monkeypatch):
    ws = _VoiceWebSocket("tlnd-voice")
    db = AsyncMock()
    monkeypatch.setattr(access, "get_db", lambda: db)

    user, protocol = await access.authenticate_voice_websocket(ws)

    assert user is None and protocol is None
    assert ws.closed[0] == 4401


async def test_voice_ws_nhan_jwt_dung_tai_khoan(monkeypatch):
    ws = _VoiceWebSocket("tlnd-voice, tlnd-auth.access-token")
    user = {"_id": "507f1f77bcf86cd799439011", "status": "active"}

    class _Users:
        find_one = AsyncMock(return_value=user)

    class _Db:
        users = _Users()

    monkeypatch.setattr(
        access,
        "decode_access_token",
        lambda token: {
            "type": "access",
            "sub": "507f1f77bcf86cd799439011",
        } if token == "access-token" else None,
    )
    monkeypatch.setattr(access, "get_db", lambda: _Db())
    monkeypatch.setattr(access, "ensure_account_available", lambda _user: None)

    authenticated, protocol = await access.authenticate_voice_websocket(ws)

    assert authenticated["id"] == "507f1f77bcf86cd799439011"
    assert protocol == "tlnd-voice"
    assert ws.closed is None
