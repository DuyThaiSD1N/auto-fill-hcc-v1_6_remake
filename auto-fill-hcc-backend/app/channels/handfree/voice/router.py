"""GET /api/v1/voice/config — FE gọi 1 lần lúc init: tắt = ẩn nút 🎤 / không auto-đọc.

Cho phép deploy nơi chưa có dịch vụ voice: để trống env → extension tự ẩn tính năng.
"""
from fastapi import APIRouter, Depends

from app.config import settings
from app.core.deps import require_auth

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


@router.get("/config")
async def voice_config(_: dict = Depends(require_auth)):
    # "hmong" chỉ xuất hiện khi đã cấu hình ASR tiếng Mông — FE dựa vào đây (cùng điều kiện
    # tài khoản tỉnh Lai Châu) để hiện/ẩn switch tiếng Mông.
    langs = ["vi"]
    if settings.asr_grpc_uri_hmong:
        langs.append("hmong")
    return {
        "asr": bool(settings.asr_grpc_uri and settings.asr_grpc_token),
        "tts": bool(settings.tts_ws_url and settings.tts_api_key),
        "langs": langs,
        "rate": settings.asr_rate,
        "format": "S16LE",
    }
