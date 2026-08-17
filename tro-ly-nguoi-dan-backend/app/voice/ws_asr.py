"""WS /ws/asr — cầu nối mic extension ↔ dịch vụ ASR gRPC (port từ chatbot-hcc-base-ts ws-asr.ts).

Protocol với FE (GIỮ NGUYÊN để services/asr.js của extension chạy không sửa):
  FE → WS:  {"type":"start","lang":"vi","rate":16000}  rồi stream BINARY PCM S16LE
            {"type":"stop"} (hủy giữa chừng)
  WS → FE:  {"type":"transcript","data":{"transcript":"…","isFinal":bool,"confidence":n}}
            {"type":"error","message":"…"} | {"type":"end"}

Server ASR tự cắt câu khi im lặng (speech_timeout) → isFinal — FE không cần VAD.
Mỗi WS connection = 1 lượt nói (push-to-talk): final xong FE tự đóng.
"""
import asyncio
import json
import logging
import time

import grpc
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.voice import streaming_voice_pb2 as pb2
from app.voice import streaming_voice_pb2_grpc as pb2_grpc

logger = logging.getLogger(__name__)

router = APIRouter()

_QUEUE_END = object()  # sentinel kết thúc stream gửi lên gRPC


async def _request_gen(queue: asyncio.Queue):
    while True:
        item = await queue.get()
        if item is _QUEUE_END:
            return
        yield pb2.VoiceRequest(byte_buff=item)


def _grpc_metadata(rate: str) -> list[tuple[str, str]]:
    # Khớp client mẫu speech_code/client_grpc.py + ws-asr.ts (nhánh tiếng Việt).
    return [
        ("token", settings.asr_grpc_token or "test_token"),
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
    await ws.accept()
    if not settings.asr_grpc_uri:
        await ws.send_json({"type": "error", "message": "ASR chưa được cấu hình (ASR_GRPC_URI)."})
        await ws.close()
        return

    queue: asyncio.Queue = asyncio.Queue()
    channel: grpc.aio.Channel | None = None
    forward_task: asyncio.Task | None = None
    started = False

    async def _forward(call):
        """gRPC → WS: đẩy transcript về FE; kết thúc stream → {"type":"end"}."""
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
                    })
                elif resp.status != 0:
                    logger.warning("[asr] grpc status=%s msg=%s", resp.status, resp.msg)
                    await ws.send_json({"type": "error", "message": resp.msg or "asr error"})
            await ws.send_json({"type": "end"})
        except grpc.aio.AioRpcError as e:
            logger.warning("[asr] grpc error: %s", e.details())
            try:
                await ws.send_json({"type": "error", "message": e.details() or "Mất kết nối ASR."})
            except Exception:  # noqa: BLE001 — WS có thể đã đóng
                pass
        except Exception:  # noqa: BLE001 — WS đóng giữa chừng là bình thường (FE teardown)
            pass

    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if msg.get("bytes") is not None:
                if started:
                    queue.put_nowait(msg["bytes"])
                continue
            text = msg.get("text") or ""
            try:
                parsed = json.loads(text)
            except (ValueError, TypeError):
                continue
            if parsed.get("type") == "start" and not started:
                rate = str(parsed.get("rate") or settings.asr_rate)
                channel = grpc.aio.insecure_channel(settings.asr_grpc_uri)
                stub = pb2_grpc.StreamVoiceStub(channel)
                call = stub.SendVoice(_request_gen(queue), metadata=_grpc_metadata(rate))
                forward_task = asyncio.create_task(_forward(call))
                started = True
                logger.info("[asr] gRPC opened (%s rate=%s)", settings.asr_grpc_uri, rate)
            elif parsed.get("type") == "stop":
                break
    except WebSocketDisconnect:
        pass
    finally:
        queue.put_nowait(_QUEUE_END)
        if forward_task:
            # Cho server trả nốt final đang dở tối đa 3s rồi mới hủy.
            try:
                await asyncio.wait_for(forward_task, timeout=3)
            except (asyncio.TimeoutError, Exception):  # noqa: BLE001
                forward_task.cancel()
        if channel:
            await channel.close()
        try:
            await ws.close()
        except Exception:  # noqa: BLE001
            pass
