"""GET /api/v1/voice/config — FE gọi 1 lần lúc init: tắt = ẩn nút 🎤 / không auto-đọc.

Cho phép deploy nơi chưa có dịch vụ voice: để trống env → extension tự ẩn tính năng.
"""
from fastapi import APIRouter, Depends

from app.channels.handfree.chat import script_mong as mong
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import xung_ho
from app.channels.handfree.chat.intents import fold
from app.channels.handfree.voice import catalog, store
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


async def _voice_options(lang: str) -> list[dict]:
    """Giọng cán bộ chọn được: bảng giọng đang bật; bảng trống → danh mục cũ."""
    table = await store.voices_for(lang)
    if not table:
        return [{"id": v["id"], "name": v["label"], "gender": v.get("gender") or "", "region": "", "ethnicity": ""}
                for v in catalog.voices_for(lang)]
    return [{"id": v["voiceId"], "name": v["name"], "gender": v["gender"], "region": v["region"],
             "ethnicity": v["ethnicity"]} for v in table]


@router.get("/config")
async def voice_config(user: dict = Depends(require_auth)):
    # "hmong" chỉ xuất hiện khi đã cấu hình ASR tiếng Mông — FE dựa vào đây (cùng điều kiện
    # tài khoản tỉnh Lai Châu) để hiện/ẩn switch tiếng Mông.
    asr_cfg = await store.asr()
    tts_cfg = await store.tts()
    langs = ["vi"]
    if asr_cfg["grpcUriHmong"]:
        langs.append("hmong")
    return {
        "asr": bool(asr_cfg["grpcUri"] and settings.asr_grpc_token),
        # /ws/asr nhận nhiều lượt nói trên một WS (start/cancel/warm/ping) → extension mới giữ sẵn mic + WS, bấm mic
        # chỉ còn truyền âm thanh. Extension cũ không đọc khoá này, vẫn mở / đóng WS mỗi lượt.
        "asrWarm": True,
        "tts": bool(tts_cfg["wsUrl"] and settings.tts_api_key),
        "langs": langs,
        "rate": asr_cfg["rate"],
        "format": "S16LE",
        # Danh mục giọng + mặc định: màn Cài đặt dựng ô chọn từ đây nên thêm/bớt giọng KHÔNG
        # phải phát hành lại extension. Ngôn ngữ chỉ còn một giọng thì FE tự ẩn ô chọn.
        # Khoá "voices" giữ danh mục cũ cho bản extension trên chợ (vẽ mỗi giọng một nút trên một hàng — cả bảng
        # vài chục giọng sẽ vỡ màn Cài đặt). Bản mới đọc "voiceOptions" = bảng giọng của web quản trị.
        "voices": {lang: catalog.voices_for(lang) for lang in langs},
        "voiceOptions": {lang: await _voice_options(lang) for lang in langs},
        "defaultVoice": {lang: catalog.default_voice(lang) for lang in langs},
        "tempo": {"default": tts_cfg["defaultTempo"], "min": tts_cfg["tempoMin"], "max": tts_cfg["tempoMax"]},
        # Thẻ phản hồi máy quét do extension tự dựng (sự kiện scan không phải một lượt chat),
        # nhưng chữ vẫn phát từ đây để bản Mông nằm cùng chỗ với lời thoại còn lại — thêm câu
        # hay sửa bản dịch KHÔNG phải phát hành lại extension.
        "scanFeedback": {
            # Trợ lý tự xưng "tôi" (chat/xung_ho.py) — bản Mông là bản dịch riêng, không đổi.
            lang: (mong.SCAN_FEEDBACK if lang == "hmong" else xung_ho.strings(vi.SCAN_FEEDBACK))
            for lang in langs
        },
        "scanGuide": {
            lang: (mong.SCAN_GUIDE if lang == "hmong" else xung_ho.strings(vi.SCAN_GUIDE))
            for lang in langs
        },
        # Chuyển bước: đọc hết câu đang đọc rồi mới đọc câu mới, thay vì cắt ngang.
        "finishSentenceBeforeNext": _finish_sentence_before_next(user),
    }
