"""GET /api/v1/voice/config — FE gọi 1 lần lúc init: tắt = ẩn nút 🎤 / không auto-đọc.

Cho phép deploy nơi chưa có dịch vụ voice: để trống env → extension tự ẩn tính năng.
"""
from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


@router.get("/config")
async def voice_config():
    return {
        "asr": bool(settings.asr_grpc_uri),
        "tts": bool(settings.tts_ws_url and settings.tts_api_key),
        "langs": ["vi"],
        "rate": settings.asr_rate,
        "format": "S16LE",
    }
