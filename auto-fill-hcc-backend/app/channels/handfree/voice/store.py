"""Cấu hình giọng nói do quản trị chỉnh trên web: bảng setting_tts, setting_asr (mỗi bảng một bản ghi) và tts_voices.

Thứ tự ưu tiên: cán bộ chọn trong extension (cài đặt tài khoản) → giá trị mặc định trong DB → env. Bảng trống (hoặc
Mongo lỗi) = env, nên deploy chưa cấu hình gì chạy y như trước. Token / API key KHÔNG lưu ở đây — chỉ ở env.
Giọng dự phòng (cán bộ chưa chọn, giọng đã chọn bị tắt / bị máy chủ giọng từ chối) = TTS_VOICE / TTS_VOICE_HMONG.

Đọc rất dày (mỗi câu đọc mở một kết nối TTS) → cache ngắn trong tiến trình. Lưu trên web xoá cache của tiến trình đó;
tiến trình khác nhận giá trị mới sau tối đa CACHE_SECONDS.
"""
import logging
import time
from datetime import datetime, timezone

from app.channels.handfree.voice import catalog
from app.config import settings
from app.db.mongo import get_db

logger = logging.getLogger(__name__)

CACHE_SECONDS = 30
TTS_COLL = "setting_tts"
ASR_COLL = "setting_asr"
VOICES_COLL = "tts_voices"
DOC_ID = "default"
# Tần số máy chủ giọng hỗ trợ (resample_rate). Extension cũ chỉ phát 16000 → giọng khác 16000 chỉ áp cho bản khai
# hỗ trợ (ws_tts, tham số sr).
SAMPLE_RATES = (8000, 16000, 22050, 24000)
DEFAULT_SAMPLE_RATE = 16000
GENDERS = ("nam", "nu")
REGIONS = ("bac", "trung", "nam")
# Giọng ghi dân tộc này chỉ dùng cho chế độ tiếng Mông; giọng còn lại là tiếng Việt.
HMONG_ETHNICITY = "H'Mông"

TTS_FIELDS = ("wsUrl", "wsUrlHmong", "defaultTempo", "pitch", "tempoMin", "tempoMax")
ASR_FIELDS = ("grpcUri", "grpcUriHmong", "rate", "silenceTimeout", "speechTimeout", "speechMax")


def _tts_env() -> dict:
    return {
        "wsUrl": settings.tts_ws_url,
        "wsUrlHmong": settings.tts_ws_url_hmong,
        "defaultTempo": settings.tts_tempo,
        "pitch": 0,
        "tempoMin": 0.8,
        "tempoMax": 1.3,
    }


def _asr_env() -> dict:
    return {
        "grpcUri": settings.asr_grpc_uri,
        "grpcUriHmong": settings.asr_grpc_uri_hmong,
        "rate": settings.asr_rate,
        "silenceTimeout": settings.asr_silence_timeout,
        "speechTimeout": settings.asr_speech_timeout,
        "speechMax": settings.asr_speech_max,
    }


_cache: dict[str, tuple[float, object]] = {}


def clear_cache() -> None:
    _cache.clear()


async def _cached(key: str, loader):
    hit = _cache.get(key)
    now = time.monotonic()
    if hit and now - hit[0] < CACHE_SECONDS:
        return hit[1]
    value = await loader()
    _cache[key] = (now, value)
    return value


async def _load_doc(coll: str) -> dict:
    try:
        return await get_db()[coll].find_one({"_id": DOC_ID}) or {}
    except Exception as e:  # noqa: BLE001 — Mongo lỗi không được làm câm giọng đọc / tắt mic
        logger.warning("[voice] không đọc được %s, dùng env: %s", coll, e)
        return {}


def _merge(env: dict, doc: dict, fields: tuple[str, ...]) -> dict:
    return {key: doc[key] if doc.get(key) not in (None, "") else env[key] for key in fields}


async def tts() -> dict:
    """Cấu hình TTS đang hiệu lực (DB đè env theo từng khoá). Chỉ cache bản ghi DB; env đọc lại mỗi lần."""
    return _merge(_tts_env(), await _cached(TTS_COLL, lambda: _load_doc(TTS_COLL)), TTS_FIELDS)


async def asr() -> dict:
    return _merge(_asr_env(), await _cached(ASR_COLL, lambda: _load_doc(ASR_COLL)), ASR_FIELDS)


async def _update(coll: str, changes: dict, fields: tuple[str, ...]) -> None:
    changes = {key: value for key, value in changes.items() if key in fields}
    if changes:
        await get_db()[coll].update_one(
            {"_id": DOC_ID},
            {"$set": {**changes, "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
    clear_cache()


async def update_tts(changes: dict) -> dict:
    await _update(TTS_COLL, changes, TTS_FIELDS)
    return await tts()


async def update_asr(changes: dict) -> dict:
    await _update(ASR_COLL, changes, ASR_FIELDS)
    return await asr()


# ── Danh sách giọng ──

def _voice_out(doc: dict) -> dict:
    return {
        "voiceId": doc["_id"],
        "name": doc.get("name") or "",
        "gender": doc.get("gender") or "",
        "region": doc.get("region") or "",
        "ethnicity": doc.get("ethnicity") or "",
        "sampleRate": int(doc.get("sampleRate") or DEFAULT_SAMPLE_RATE),
        "enabled": doc.get("enabled") is not False,
    }


async def _load_voices() -> list[dict]:
    try:
        docs = await get_db()[VOICES_COLL].find({}).to_list(length=500)
    except Exception as e:  # noqa: BLE001
        logger.warning("[voice] không đọc được %s, dùng danh mục cũ: %s", VOICES_COLL, e)
        return []
    order = {region: i for i, region in enumerate(REGIONS)}
    voices = [_voice_out(doc) for doc in docs]
    return sorted(voices, key=lambda v: (order.get(v["region"], len(REGIONS)), v["name"].lower(), v["voiceId"]))


async def list_voices() -> list[dict]:
    return await _cached(VOICES_COLL, _load_voices)


def voice_lang(voice: dict) -> str:
    return "hmong" if voice.get("ethnicity") == HMONG_ETHNICITY else "vi"


async def voices_for(lang: str) -> list[dict]:
    """Giọng đang bật của một ngôn ngữ. Bảng trống → rỗng (nơi gọi dùng danh mục cũ)."""
    lang = "hmong" if str(lang or "").lower() == "hmong" else "vi"
    return [v for v in await list_voices() if v["enabled"] and voice_lang(v) == lang]


async def find_voice(voice_id: str) -> dict | None:
    return next((v for v in await list_voices() if v["voiceId"] == voice_id), None)


async def resolve_voice(lang: str, requested: str | None) -> dict:
    """Giọng gửi máy chủ đọc: giọng cán bộ chọn nếu còn bật trong bảng (hoặc thuộc danh mục cũ khi bảng trống — bản
    extension cũ chọn từ đó), không thì giọng dự phòng ở env. Không bao giờ nhận mã tuỳ ý từ query string."""
    wanted = str(requested or "").strip()
    table = await voices_for(lang)
    if table:
        match = next((v for v in table if v["voiceId"] == wanted), None)
        if match:
            return match
    elif wanted and any(entry["id"] == wanted for entry in catalog.voices_for(lang)):
        return {"voiceId": wanted, "sampleRate": DEFAULT_SAMPLE_RATE}
    fallback = catalog.default_voice(lang)
    return {"voiceId": fallback, "sampleRate": int((await find_voice(fallback) or {}).get("sampleRate")
                                                   or DEFAULT_SAMPLE_RATE)}


async def create_voice(data: dict) -> dict:
    doc = {"_id": data["voiceId"], **{k: v for k, v in data.items() if k != "voiceId"},
           "updated_at": datetime.now(timezone.utc)}
    await get_db()[VOICES_COLL].insert_one(doc)
    clear_cache()
    return _voice_out(doc)


async def update_voice(voice_id: str, changes: dict) -> dict | None:
    doc = await get_db()[VOICES_COLL].find_one_and_update(
        {"_id": voice_id},
        {"$set": {**changes, "updated_at": datetime.now(timezone.utc)}},
        return_document=True,
    )
    clear_cache()
    return _voice_out(doc) if doc else None


async def delete_voice(voice_id: str) -> bool:
    res = await get_db()[VOICES_COLL].delete_one({"_id": voice_id})
    clear_cache()
    return res.deleted_count > 0
