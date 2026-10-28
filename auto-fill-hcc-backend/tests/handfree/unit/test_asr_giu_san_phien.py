"""/ws/asr giữ sẵn phiên: một WS nhiều lượt nói (mỗi lượt một luồng gRPC trên cùng kênh), bấm mic chỉ còn gửi
"start" + âm thanh. Extension cũ (một WS một lượt, không gửi "turn") chạy y như trước."""
import asyncio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.channels.handfree.voice import ws_asr


def _resp(text, final):
    hyp = SimpleNamespace(transcript=text, confidence=0.9)
    return SimpleNamespace(status=0, msg="", result=SimpleNamespace(hypotheses=[hyp], final=final))


class _Stub:
    calls = 0

    def __init__(self, channel):
        self.channel = channel

    def SendVoice(self, requests, metadata=None):  # noqa: N802 — tên theo proto
        _Stub.calls += 1

        async def stream():
            got = 0
            async for _ in requests:
                got += 1
                if got == 1:
                    yield _resp("xin chào", False)
                if got == 2:
                    yield _resp(f"xin chào {_Stub.calls}", True)
            # chiều gửi đóng → server kết thúc luồng
        return stream()


class _Channel:
    async def channel_ready(self):
        return None

    async def close(self):
        return None


@pytest.fixture
def client(monkeypatch):
    channels = []

    def make_channel(uri):
        channels.append(uri)
        return _Channel()

    async def auth(ws):
        return {"_id": "u"}, None

    _Stub.calls = 0
    monkeypatch.setattr(ws_asr, "authenticate_voice_websocket", auth)
    monkeypatch.setattr(ws_asr.settings, "asr_grpc_uri", "asr:1")
    monkeypatch.setattr(ws_asr.settings, "asr_grpc_token", "t")
    monkeypatch.setattr(ws_asr.grpc.aio, "insecure_channel", make_channel)
    monkeypatch.setattr(ws_asr.pb2_grpc, "StreamVoiceStub", _Stub)
    app = FastAPI()
    app.include_router(ws_asr.router)
    with TestClient(app) as c:
        c.channels = channels
        yield c


def _until(ws, pred):
    while True:
        msg = ws.receive_json()
        if pred(msg):
            return msg


def test_hai_luot_noi_tren_mot_ws_mot_kenh_grpc(client):
    with client.websocket_connect("/ws/asr") as ws:
        ws.send_json({"type": "warm", "lang": "vi"})
        ws.send_json({"type": "ping"})
        assert _until(ws, lambda m: m["type"] == "pong")
        for turn in (1, 2):
            ws.send_json({"type": "start", "lang": "vi", "rate": 16000, "turn": turn})
            ws.send_bytes(b"\x00\x00" * 160)
            ws.send_bytes(b"\x00\x00" * 160)
            final = _until(ws, lambda m: m["type"] == "transcript" and m["data"]["isFinal"])
            assert final["turn"] == turn and final["data"]["transcript"] == f"xin chào {turn}"
            # sau final BE tự đóng luồng gRPC của lượt → end mang đúng lượt
            assert _until(ws, lambda m: m["type"] == "end")["turn"] == turn
    assert client.channels == ["asr:1"], "một kênh gRPC cho cả phiên, không nối lại mỗi lượt"
    assert _Stub.calls == 2


def test_ban_cu_mot_ws_mot_luot_khong_co_turn(client):
    with client.websocket_connect("/ws/asr") as ws:
        ws.send_json({"type": "start", "lang": "vi", "rate": 16000})
        ws.send_json({"type": "start", "lang": "vi", "rate": 16000})  # bản cũ: start thứ hai bị bỏ qua
        ws.send_bytes(b"\x00\x00" * 160)
        ws.send_bytes(b"\x00\x00" * 160)
        final = _until(ws, lambda m: m["type"] == "transcript" and m["data"]["isFinal"])
        assert "turn" not in final
    assert _Stub.calls == 1


def test_cancel_bo_luot_dang_nghe_giu_ws(client):
    with client.websocket_connect("/ws/asr") as ws:
        ws.send_json({"type": "start", "lang": "vi", "rate": 16000, "turn": 1})
        ws.send_bytes(b"\x00\x00" * 160)
        assert _until(ws, lambda m: m["type"] == "transcript")["turn"] == 1
        ws.send_json({"type": "cancel"})
        ws.send_json({"type": "start", "lang": "vi", "rate": 16000, "turn": 2})
        ws.send_bytes(b"\x00\x00" * 160)
        ws.send_bytes(b"\x00\x00" * 160)
        final = _until(ws, lambda m: m["type"] == "transcript" and m["data"]["isFinal"])
        assert final["turn"] == 2


def test_config_bao_giu_san_phien():
    src = open(ws_asr.__file__.replace("ws_asr.py", "router.py"), encoding="utf-8").read()
    assert '"asrWarm": True' in src
