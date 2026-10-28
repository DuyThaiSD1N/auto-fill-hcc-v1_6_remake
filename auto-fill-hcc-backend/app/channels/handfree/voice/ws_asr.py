"""WS /ws/asr — cầu nối mic extension ↔ dịch vụ ASR gRPC (port từ chatbot-hcc-base-ts ws-asr.ts).

Protocol với FE (GIỮ NGUYÊN để services/asr.js của extension chạy không sửa):
  FE → WS:  {"type":"start","lang":"vi","rate":16000}  rồi stream BINARY PCM S16LE
            {"type":"stop"} (hủy giữa chừng)
  WS → FE:  {"type":"transcript","data":{"transcript":"…","isFinal":bool,"confidence":n}}
            {"type":"error","message":"…"} | {"type":"end"}

Server ASR tự cắt câu khi im lặng (speech_timeout) → isFinal — FE không cần VAD.
Bản extension cũ: mỗi WS connection = 1 lượt nói (push-to-talk), final xong FE tự đóng.

Giữ sẵn phiên (voice/config `asrWarm`, extension mới): một WS sống suốt phiên làm việc, mỗi lượt nói là một luồng
gRPC riêng trên cùng kênh — bấm mic chỉ còn gửi "start" rồi đẩy âm thanh, không bắt tay WS / xác thực / nối gRPC lại.
  FE → WS:  {"type":"warm","lang":"vi"}            mở sẵn kênh gRPC (chưa mở luồng)
            {"type":"start",...,"turn":n}            lượt mới; transcript / end / error của lượt mang lại "turn":n
            {"type":"cancel"}                        bỏ lượt đang nghe, GIỮ WS (khác "stop" = đóng WS)
            {"type":"ping"}  →  {"type":"pong"}      giữ kết nối qua proxy khi chưa ai nói
"""
import asyncio
import json
import logging
import time

import grpc
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.channels.handfree.voice import streaming_voice_pb2 as pb2
from app.channels.handfree.voice import streaming_voice_pb2_grpc as pb2_grpc
from app.channels.handfree.voice.access import authenticate_voice_websocket

logger = logging.getLogger(__name__)

router = APIRouter()

_QUEUE_END = object()  # sentinel kết thúc stream gửi lên gRPC

# Lỗi gửi về extension LUÔN là câu cố định: chi tiết gRPC/server ASR chứa địa chỉ dịch vụ nội bộ
# (vd "address lookup failed for http://<ip>:<port>") và sẽ hiện nguyên văn trên sidebar công dân.
# Chi tiết thật chỉ ghi log máy chủ.
_CLIENT_ERROR = "Dịch vụ nhận giọng nói đang gặp sự cố, công dân thử lại sau hoặc gõ chữ giúp em ạ."


def _grpc_target(uri: str) -> str:
    """gRPC nhận "host:port", không nhận URL. Cấu hình hay ghi kèm http:// → bóc đi, kẻo mọi lượt
    nói đều hỏng với lỗi phân giải tên miền."""
    target = (uri or "").strip()
    for scheme in ("http://", "https://", "grpc://", "grpcs://"):
        if target.lower().startswith(scheme):
            target = target[len(scheme):]
            break
    return target.rstrip("/")


async def _request_gen(queue: asyncio.Queue):
    while True:
        item = await queue.get()
        if item is _QUEUE_END:
            return
        yield pb2.VoiceRequest(byte_buff=item)


def _grpc_metadata(rate: str) -> list[tuple[str, str]]:
    # Khớp client mẫu speech_code/client_grpc.py + ws-asr.ts (nhánh tiếng Việt).
    return [
        ("token", settings.asr_grpc_token),
        ("id", f"tlnd_{int(time.time())}"),
        ("channels", "1"),
        ("rate", rate),
        ("format", "S16LE"),
        ("silence_timeout", str(settings.asr_silence_timeout)),
        ("speech_timeout", str(settings.asr_speech_timeout)),
        ("speech_max", str(settings.asr_speech_max)),
    ]


@router.websocket("/ws/asr")
async def ws_asr(ws: WebSocket):
    user, subprotocol = await authenticate_voice_websocket(ws)
    if not user:
        return
    await ws.accept(subprotocol=subprotocol)
    if not settings.asr_grpc_uri or not settings.asr_grpc_token:
        logger.error("[asr] thiếu cấu hình ASR_GRPC_URI / ASR_GRPC_TOKEN")
        await ws.send_json({"type": "error", "message": _CLIENT_ERROR})
        await ws.close()
        return

    channels: dict[str, grpc.aio.Channel] = {}
    turn: dict | None = None  # lượt đang nghe: {"queue", "task"}

    def _channel_for(lang: str) -> grpc.aio.Channel:
        # lang="hmong" → server ASR tiếng Mông riêng (ASR_GRPC_URI_HMONG, vd :9113);
        # chưa cấu hình thì rơi về server tiếng Việt để không chết phiên.
        grpc_uri = _grpc_target(
            settings.asr_grpc_uri_hmong
            if lang == "hmong" and settings.asr_grpc_uri_hmong
            else settings.asr_grpc_uri
        )
        if grpc_uri not in channels:
            channels[grpc_uri] = grpc.aio.insecure_channel(grpc_uri)
            logger.info("[asr] gRPC channel (%s lang=%s)", grpc_uri, lang)
        return channels[grpc_uri]

    async def _warm(channel: grpc.aio.Channel):
        # Kênh gRPC nối lười tới lượt gọi đầu tiên → ép nối trước để lượt nói đầu khỏi chờ bắt tay HTTP/2.
        try:
            await asyncio.wait_for(channel.channel_ready(), timeout=5)
        except Exception:  # noqa: BLE001 — chưa nối được thì lượt nói tự nối lại như cũ
            pass

    async def _forward(call, turn_id, queue: asyncio.Queue):
        """gRPC → WS: đẩy transcript về FE; kết thúc stream → {"type":"end"}."""
        tag = {} if turn_id is None else {"turn": turn_id}
        try:
            async for resp in call:
                if resp.status == 0 and resp.result.hypotheses:
                    h = resp.result.hypotheses[0]
                    await ws.send_json({
                        "type": "transcript",
                        "data": {
                            "transcript": h.transcript or "",
                            "isFinal": bool(resp.result.final),
                            "confidence": h.confidence or 0,
                        },
                        **tag,
                    })
                    # Giữ sẵn phiên: chốt câu là hết lượt → đóng chiều gửi để server ASR kết thúc luồng ngay (bản cũ thì
                    # FE đóng hẳn WS sau final nên không cần).
                    if turn_id is not None and resp.result.final:
                        queue.put_nowait(_QUEUE_END)
                elif resp.status != 0:
                    logger.warning("[asr] grpc status=%s msg=%s", resp.status, resp.msg)
                    await ws.send_json({"type": "error", "message": _CLIENT_ERROR, **tag})
            await ws.send_json({"type": "end", **tag})
        except grpc.aio.AioRpcError as e:
            logger.warning("[asr] grpc error: %s", e.details())
            try:
                await ws.send_json({"type": "error", "message": _CLIENT_ERROR, **tag})
            except Exception:  # noqa: BLE001 — WS có thể đã đóng
                pass
        except Exception:  # noqa: BLE001 — WS đóng giữa chừng là bình thường (FE teardown)
            pass

    async def _end_turn(wait: bool):
        nonlocal turn
        if turn is None:
            return
        current, turn = turn, None
        current["queue"].put_nowait(_QUEUE_END)
        if not wait:
            current["task"].cancel()
            return
        # Cho server trả nốt final đang dở tối đa 3s rồi mới hủy.
        try:
            await asyncio.wait_for(current["task"], timeout=3)
        except (asyncio.TimeoutError, Exception):  # noqa: BLE001
            current["task"].cancel()

    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if msg.get("bytes") is not None:
                if turn is not None and not turn["task"].done():
                    turn["queue"].put_nowait(msg["bytes"])
                continue
            text = msg.get("text") or ""
            try:
                parsed = json.loads(text)
            except (ValueError, TypeError):
                continue
            kind = parsed.get("type")
            if kind == "start":
                if turn is not None and not turn["task"].done() and parsed.get("turn") is None:
                    continue  # bản cũ: một WS chỉ một lượt
                # Lượt cũ còn dở (FE bấm lại giữa chừng) → bỏ, mở lượt mới trên cùng kênh.
                await _end_turn(wait=False)
                rate = str(parsed.get("rate") or settings.asr_rate)
                lang = str(parsed.get("lang") or "vi").lower()
                turn_id = parsed.get("turn")
                stub = pb2_grpc.StreamVoiceStub(_channel_for(lang))
                queue: asyncio.Queue = asyncio.Queue()
                call = stub.SendVoice(_request_gen(queue), metadata=_grpc_metadata(rate))
                turn = {"queue": queue, "task": asyncio.create_task(_forward(call, turn_id, queue))}
                logger.info("[asr] gRPC turn opened (lang=%s rate=%s turn=%s)", lang, rate, turn_id)
            elif kind == "warm":
                asyncio.create_task(_warm(_channel_for(str(parsed.get("lang") or "vi").lower())))
            elif kind == "cancel":
                await _end_turn(wait=False)
            elif kind == "ping":
                await ws.send_json({"type": "pong"})
            elif kind == "stop":
                break
    except WebSocketDisconnect:
        pass
    finally:
        await _end_turn(wait=True)
        for channel in channels.values():
            await channel.close()
        try:
            await ws.close()
        except Exception:  # noqa: BLE001
            pass
