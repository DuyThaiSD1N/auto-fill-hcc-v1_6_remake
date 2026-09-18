"""GET /api/v1/voice/config — FE gọi 1 lần lúc init: tắt = ẩn nút 🎤 / không auto-đọc.

Cho phép deploy nơi chưa có dịch vụ voice: để trống env → extension tự ẩn tính năng.
"""
from fastapi import APIRouter, Depends

from app.channels.handfree.chat import script_mong as mong
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import fold
from app.channels.handfree.voice import catalog
from app.config import settings
from app.core.deps import require_auth

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])

# Quầy ở các tỉnh này ĐỌC TRỌN câu rồi mới sang câu sau, thay vì cắt ngang khi chuyển bước.
# Lai Châu: công dân nghe tiếng Mông qua lời dịch, mất nửa câu là mất hẳn ý — khác quầy nói
# tiếng phổ thông, nơi cắt ngang giúp bot không đọc hướng dẫn đã hết hiệu lực.
# Thêm tỉnh = sửa đúng dòng này, KHÔNG phải phát hành lại extension.
_FINISH_SENTENCE_PROVINCES = ("lai chau",)


def _finish_sentence_before_next(user: dict) -> bool:
    tinh = fold(str(user.get("tinh") or ""))
    return any(p in tinh for p in _FINISH_SENTENCE_PROVINCES)


@router.get("/config")
async def voice_config(user: dict = Depends(require_auth)):
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
        # Danh mục giọng + mặc định: màn Cài đặt dựng ô chọn từ đây nên thêm/bớt giọng KHÔNG
        # phải phát hành lại extension. Ngôn ngữ chỉ còn một giọng thì FE tự ẩn ô chọn.
        "voices": {lang: catalog.voices_for(lang) for lang in langs},
        "defaultVoice": {lang: catalog.default_voice(lang) for lang in langs},
        # Thẻ phản hồi máy quét do extension tự dựng (sự kiện scan không phải một lượt chat),
        # nhưng chữ vẫn phát từ đây để bản Mông nằm cùng chỗ với lời thoại còn lại — thêm câu
        # hay sửa bản dịch KHÔNG phải phát hành lại extension.
        "scanFeedback": {
            lang: (mong.SCAN_FEEDBACK if lang == "hmong" else vi.SCAN_FEEDBACK)
            for lang in langs
        },
        "scanGuide": {
            lang: (mong.SCAN_GUIDE if lang == "hmong" else vi.SCAN_GUIDE)
            for lang in langs
        },
        # Chuyển bước: đọc hết câu đang đọc rồi mới đọc câu mới, thay vì cắt ngang.
        "finishSentenceBeforeNext": _finish_sentence_before_next(user),
    }
