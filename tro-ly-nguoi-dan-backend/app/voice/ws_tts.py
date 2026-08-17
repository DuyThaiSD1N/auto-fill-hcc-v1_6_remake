"""WS /ws/tts — relay 2 chiều tới nhà cung cấp TTS (port từ chatbot-hcc-base-ts ws-tts.ts).

Protocol với FE (GIỮ NGUYÊN để services/tts.js chạy không sửa):
  WS → FE:  {"ready":true}  (sau khi upstream mở + gửi config giọng)
  FE → WS:  {"text":"câu đã normalize"}  rồi {"text":""} (kết thúc lượt đọc)
  WS → FE:  forward NGUYÊN VĂN từ upstream: {"audio":"<base64 PCM S16LE>"} … {"isFinal":true}

Envelope upstream kiểu ElevenLabs: frame đầu mang voice_settings + xi_api_key.
"""
import json
import asyncio
import logging

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _config_frame() -> str:
    return json.dumps({
        "text": " ",
        "voice_settings": {
            "voiceId": settings.tts_voice,
            "resample_rate": settings.tts_resample_rate,
            "tempo": settings.tts_tempo,
            "stability": 0.5,
            "similarity_boost": 0.7,
        },
        "generator_config": {"chunk_length_schedule": [20]},
        "xi_api_key": settings.tts_api_key,
    })


@router.websocket("/ws/tts")
async def ws_tts(ws: WebSocket, lang: str = "vi"):
    await ws.accept()
    if not settings.tts_ws_url or not settings.tts_api_key:
        await ws.send_json({"error": "TTS chưa được cấu hình (TTS_WS_URL / TTS_API_KEY)."})
        await ws.close()
        return

    try:
        upstream = await websockets.connect(settings.tts_ws_url, open_timeout=5)
    except Exception as e:  # noqa: BLE001 — upstream chết thì báo FE rồi đóng
        logger.warning("[tts] không nối được upstream: %s", e)
        await ws.send_json({"error": "tts upstream error"})
        await ws.close()
        return

    await upstream.send(_config_frame())
    await ws.send_json({"ready": True})
    logger.info("[tts] upstream opened (voice=%s)", settings.tts_voice)

    async def client_to_upstream():
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                return
            text = msg.get("text")
            if text is not None:
                await upstream.send(text)

    async def upstream_to_client():
        async for frame in upstream:
            await ws.send_text(frame if isinstance(frame, str) else frame.decode("utf-8", "ignore"))

    # Chạy song song; bên nào đóng trước thì hủy bên kia (giữ teardown sạch — không leak WS).
    t1 = asyncio.create_task(client_to_upstream())
    t2 = asyncio.create_task(upstream_to_client())
    try:
        await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
    except WebSocketDisconnect:
        pass
    finally:
        for t in (t1, t2):
            t.cancel()
        try:
            await upstream.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            await ws.close()
        except Exception:  # noqa: BLE001
            pass
