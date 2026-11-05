"""WS /ws/tts — relay 2 chiều tới nhà cung cấp TTS (port từ chatbot-hcc-base-ts ws-tts.ts).

Protocol với FE (GIỮ NGUYÊN để services/tts.js chạy không sửa):
  WS → FE:  {"ready":true}  (sau khi upstream mở + gửi config giọng)
  FE → WS:  {"text":"câu đã normalize"}  rồi {"text":""} (kết thúc lượt đọc)
  WS → FE:  forward NGUYÊN VĂN từ upstream: {"audio":"<base64 PCM S16LE>"} … {"isFinal":true}

Envelope upstream kiểu ElevenLabs: frame đầu mang voice_settings + xi_api_key.

Giọng / tốc độ: query (?voice=&tempo=) do extension gửi theo cài đặt tài khoản → cài đặt tài khoản lưu ở BE (bản
extension cũ không gửi tempo) → mặc định ở web quản trị (voice/store.py) → env. Máy chủ giọng từ chối giọng ("Invalid
voice_id", rồi đóng kết nối) trước khi có âm thanh → mở lại bằng giọng dự phòng ở env và gửi lại chữ đã nhận, công dân
không bị mất tiếng.
"""
import json
import asyncio
import logging

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.channels.handfree.voice import catalog, store
from app.channels.handfree.voice.access import authenticate_voice_websocket

logger = logging.getLogger(__name__)

router = APIRouter()


def _config_frame(voice: str, tempo: float, pitch: float, resample_rate: int) -> str:
    return json.dumps({
        "text": " ",
        "voice_settings": {
            "voiceId": voice,
            "resample_rate": resample_rate,
            "tempo": tempo,
            "pitch": pitch,
            "stability": 0.5,
            "similarity_boost": 0.7,
        },
        # Biên mỗi khúc = một nhịp nghỉ khi đọc. Xem settings.tts_chunk_lengths.
        "generator_config": {"chunk_length_schedule": settings.tts_chunk_lengths},
        "xi_api_key": settings.tts_api_key,
    })


def _tempo(raw: str | None, account: dict, cfg: dict) -> float:
    """Tốc độ cán bộ chọn, ép vào khoảng quản trị cho phép; không chọn → mặc định của web quản trị."""
    for value in (raw, account.get("ttsTempo")):
        try:
            tempo = float(value)
        except (TypeError, ValueError):
            continue
        return round(min(float(cfg["tempoMax"]), max(float(cfg["tempoMin"]), tempo)), 2)
    return float(cfg["defaultTempo"])


def _voice_error(frame: str) -> bool:
    try:
        error = json.loads(frame).get("error")
    except (ValueError, TypeError, AttributeError):
        return False
    return isinstance(error, str) and "voice" in error.lower()


def _has_audio(frame: str) -> bool:
    try:
        data = json.loads(frame)
    except (ValueError, TypeError):
        return False
    return isinstance(data, dict) and bool(data.get("audio") or data.get("status") == "authenticated")


@router.websocket("/ws/tts")
async def ws_tts(ws: WebSocket, lang: str = "vi", voice: str = "", tempo: str = "", sr: str = ""):
    user, subprotocol = await authenticate_voice_websocket(ws)
    if not user:
        return
    await ws.accept(subprotocol=subprotocol)
    lang = str(lang or "vi").lower()
    cfg = await store.tts()
    account = user.get("account_settings") or {}
    # Máy quầy chọn giọng trong Cài đặt và gửi kèm ?voice=. Chỉ nhận giọng trong bảng (hoặc danh mục cũ): id lạ rơi về
    # giọng dự phòng, không cho query string bơm voiceId tuỳ ý lên server TTS.
    requested = voice or account.get("ttsVoiceHmong" if lang == "hmong" else "ttsVoiceVi")
    chosen = await store.resolve_voice(lang, requested)
    fallback = catalog.default_voice(lang)
    speed = _tempo(tempo, account, cfg)
    pitch = float(cfg.get("pitch") or 0)

    def resample_for(voice_info: dict) -> int:
        # Extension cũ phát cố định 16000 Hz → tần số riêng của giọng chỉ áp cho bản khai sr=1.
        return int(voice_info.get("sampleRate") or settings.tts_resample_rate) if sr == "1" \
            else settings.tts_resample_rate

    # Tiếng Mông có thể ở server riêng (wsUrlHmong); rỗng = cùng server, chỉ khác voice.
    upstream_url = cfg["wsUrlHmong"] if lang == "hmong" and cfg["wsUrlHmong"] else cfg["wsUrl"]
    if not upstream_url or not settings.tts_api_key:
        logger.error("[tts] thiếu cấu hình TTS_WS_URL / TTS_API_KEY")
        await ws.send_json({"error": "tts not configured"})
        await ws.close()
        return

    async def open_upstream(voice_info: dict):
        conn = await websockets.connect(upstream_url, open_timeout=5)
        await conn.send(_config_frame(voice_info["voiceId"], speed, pitch, resample_for(voice_info)))
        return conn

    try:
        upstream = await open_upstream(chosen)
    except Exception as e:  # noqa: BLE001 — upstream chết thì báo FE rồi đóng
        logger.warning("[tts] không nối được upstream: %s", e)
        await ws.send_json({"error": "tts upstream error"})
        await ws.close()
        return

    try:
        await ws.send_json({"ready": True})
    except WebSocketDisconnect:
        # FE có thể hủy lượt đọc trong lúc upstream vừa kết nối; đây là teardown bình thường,
        # không phải lỗi ASGI cần in nguyên traceback.
        try:
            await upstream.close()
        except Exception:  # noqa: BLE001
            pass
        return
    logger.info("[tts] upstream opened (voice=%s lang=%s tempo=%s)", chosen["voiceId"], lang, speed)

    # Chữ FE gửi trước khi có âm thanh đầu tiên — giữ lại để gửi lại nếu phải đổi sang giọng dự phòng.
    state = {"upstream": upstream, "pending": [], "started": False,
             "can_fallback": chosen["voiceId"] != fallback}

    async def client_to_upstream():
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                return
            text = msg.get("text")
            if text is None:
                continue
            if not state["started"]:
                state["pending"].append(text)
            try:
                await state["upstream"].send(text)
            except websockets.ConnectionClosed:
                if state["started"]:
                    return  # upstream đóng giữa lượt đọc thật → kết thúc như cũ
                # Đang đổi giọng: chữ đã nằm trong pending, sẽ gửi lại trên kết nối mới.

    async def upstream_to_client():
        while True:
            try:
                frame = await state["upstream"].recv()
            except websockets.ConnectionClosed:
                return
            frame = frame if isinstance(frame, str) else frame.decode("utf-8", "ignore")
            if not state["started"] and state["can_fallback"] and _voice_error(frame):
                state["can_fallback"] = False
                logger.warning("[tts] máy chủ giọng từ chối %s → dùng giọng dự phòng %s", chosen["voiceId"], fallback)
                old = state["upstream"]
                try:
                    state["upstream"] = await open_upstream(await store.resolve_voice(lang, fallback))
                except Exception as e:  # noqa: BLE001
                    logger.warning("[tts] không nối lại được bằng giọng dự phòng: %s", e)
                    await ws.send_text(frame)
                    return
                try:
                    await old.close()
                except Exception:  # noqa: BLE001
                    pass
                for text in state["pending"]:
                    await state["upstream"].send(text)
                continue
            if not state["started"] and _has_audio(frame):
                state["started"] = True
                state["pending"].clear()
            await ws.send_text(frame)

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
            await state["upstream"].close()
        except Exception:  # noqa: BLE001
            pass
        try:
            await ws.close()
        except Exception:  # noqa: BLE001
            pass
