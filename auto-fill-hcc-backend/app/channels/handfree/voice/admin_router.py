"""API quản trị giọng nói (web quản trị, tab "Giọng nói" — chỉ admin): cấu hình TTS / ASR và danh sách giọng.

Lưu ở voice/store.py. Token / API key không có ở đây: chỉ env, web chỉ thấy đã cấu hình hay chưa.
"""
import re
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pymongo.errors import DuplicateKeyError

from app.channels.handfree.voice import catalog, store
from app.config import settings
from app.core.deps import require_admin
from app.core.errors import AppError

router = APIRouter(prefix="/api/v1/admin/voice", tags=["admin-voice"])

_VOICE_ID = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
# Đuôi mã giọng của máy chủ giọng (vd phuongnhi-north, ngocanh-central) → gợi ý vùng miền khi thêm giọng.
_REGION_SUFFIX = {"north": "bac", "central": "trung", "south": "nam"}


def _check_gender(v):
    if v not in (None, "", *store.GENDERS):
        raise ValueError("Giới tính chỉ nhận nam hoặc nu")
    return v


def _check_region(v):
    if v not in (None, "", *store.REGIONS):
        raise ValueError("Vùng miền chỉ nhận bac, trung hoặc nam")
    return v


def _check_sample_rate(v):
    if v is not None and v not in store.SAMPLE_RATES:
        raise ValueError(f"Tần số chỉ nhận {', '.join(map(str, store.SAMPLE_RATES))}")
    return v


def _ws_url(value: str | None) -> str | None:
    if value in (None, ""):
        return value
    value = value.strip()
    if not re.match(r"^wss?://[^\s/]+", value) or len(value) > 300:
        raise ValueError("Địa chỉ phải bắt đầu bằng ws:// hoặc wss://")
    return value


class TtsSettingsIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    wsUrl: str | None = None
    wsUrlHmong: str | None = None
    defaultTempo: float | None = Field(default=None, ge=0.5, le=2.0)
    pitch: float | None = Field(default=None, gt=-100, le=100)
    tempoMin: float | None = Field(default=None, ge=0.5, le=2.0)
    tempoMax: float | None = Field(default=None, ge=0.5, le=2.0)

    @field_validator("wsUrl", "wsUrlHmong")
    @classmethod
    def _url(cls, v):
        return _ws_url(v)


class AsrSettingsIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    grpcUri: str | None = Field(default=None, max_length=300)
    grpcUriHmong: str | None = Field(default=None, max_length=300)
    rate: int | None = None
    silenceTimeout: int | None = Field(default=None, ge=1, le=60)
    speechTimeout: float | None = Field(default=None, ge=0.3, le=10)
    speechMax: int | None = Field(default=None, ge=5, le=120)

    @field_validator("rate")
    @classmethod
    def _rate(cls, v):
        if v is not None and v not in (8000, 16000):
            raise ValueError("Tần số thu âm chỉ nhận 8000 hoặc 16000")
        return v


class VoiceIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=80)
    gender: str = ""
    region: str = ""
    ethnicity: str = Field(default="", max_length=40)
    sampleRate: int = store.DEFAULT_SAMPLE_RATE
    enabled: bool = True

    _gender = field_validator("gender")(_check_gender)
    _region = field_validator("region")(_check_region)
    _rate = field_validator("sampleRate")(_check_sample_rate)


class VoiceCreate(VoiceIn):
    voiceId: str

    @field_validator("voiceId")
    @classmethod
    def _id(cls, v):
        v = v.strip()
        if not _VOICE_ID.match(v):
            raise ValueError("Mã giọng chỉ gồm chữ không dấu, số, dấu chấm, gạch nối, gạch dưới (tối đa 80 ký tự)")
        return v


class VoicePatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = Field(default=None, min_length=1, max_length=80)
    gender: str | None = None
    region: str | None = None
    ethnicity: str | None = Field(default=None, max_length=40)
    sampleRate: int | None = None
    enabled: bool | None = None

    _gender = field_validator("gender")(_check_gender)
    _region = field_validator("region")(_check_region)
    _rate = field_validator("sampleRate")(_check_sample_rate)


def _settings_out(tts: dict, asr: dict) -> dict:
    return {
        "tts": {
            **tts,
            # Giọng dự phòng và khoá dịch vụ nằm ở env: web chỉ xem, không sửa.
            "fallbackVoiceVi": catalog.default_voice("vi"),
            "fallbackVoiceHmong": catalog.default_voice("hmong"),
            "apiKeyConfigured": bool(settings.tts_api_key),
        },
        "asr": {**asr, "tokenConfigured": bool(settings.asr_grpc_token)},
    }


@router.get("/settings")
async def get_settings(_: dict = Depends(require_admin)):
    return _settings_out(await store.tts(), await store.asr())


@router.put("/settings/tts")
async def put_tts(body: TtsSettingsIn, _: dict = Depends(require_admin)):
    changes = body.model_dump(exclude_none=True)
    merged = {**await store.tts(), **changes}
    if not merged["tempoMin"] <= merged["defaultTempo"] <= merged["tempoMax"]:
        raise AppError("INVALID_TEMPO", "Tốc độ mặc định phải nằm trong khoảng tốc độ nhỏ nhất – lớn nhất", 422)
    tts = await store.update_tts(changes)
    return _settings_out(tts, await store.asr())


@router.put("/settings/asr")
async def put_asr(body: AsrSettingsIn, _: dict = Depends(require_admin)):
    asr = await store.update_asr(body.model_dump(exclude_none=True))
    return _settings_out(await store.tts(), asr)


@router.get("/voices")
async def get_voices(_: dict = Depends(require_admin)):
    return {"voices": await store.list_voices()}


@router.post("/voices")
async def post_voice(body: VoiceCreate, _: dict = Depends(require_admin)):
    try:
        return await store.create_voice(body.model_dump())
    except DuplicateKeyError as e:
        raise AppError("VOICE_EXISTS", f"Mã giọng {body.voiceId} đã có trong danh sách", 409) from e


@router.patch("/voices/{voice_id}")
async def patch_voice(voice_id: str, body: VoicePatch, _: dict = Depends(require_admin)):
    voice = await store.update_voice(voice_id, body.model_dump(exclude_none=True))
    if not voice:
        raise AppError("VOICE_NOT_FOUND", "Không tìm thấy giọng", 404)
    return voice


@router.delete("/voices/{voice_id}")
async def delete_voice(voice_id: str, _: dict = Depends(require_admin)):
    if not await store.delete_voice(voice_id):
        raise AppError("VOICE_NOT_FOUND", "Không tìm thấy giọng", 404)
    return {"ok": True}


def _provider_voices_url(ws_url: str) -> str:
    """wss://host[:port]/... → https://host[:port]/voices (tài liệu máy chủ giọng: GET /voices cùng địa chỉ)."""
    parts = urlsplit(ws_url)
    scheme = "https" if parts.scheme == "wss" else "http"
    return urlunsplit((scheme, parts.netloc, "/voices", "", ""))


@router.get("/voices/provider")
async def provider_voices(_: dict = Depends(require_admin)):
    """Danh sách mã giọng trên máy chủ giọng — chỉ để GỢI Ý khi thêm giọng vào bảng, không tự thêm."""
    ws_url = (await store.tts())["wsUrl"]
    if not ws_url:
        return {"ok": False, "error": "Chưa cấu hình địa chỉ máy chủ đọc (TTS).", "voices": []}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            res = await client.get(_provider_voices_url(ws_url))
            res.raise_for_status()
            raw = res.json()
    except Exception:  # noqa: BLE001 — máy chủ giọng không trả lời thì vẫn thêm tay được
        return {"ok": False, "error": "Không lấy được danh sách từ máy chủ giọng.", "voices": []}
    items = raw if isinstance(raw, list) else (raw.get("voices") if isinstance(raw, dict) else None) or []
    known = {v["voiceId"] for v in await store.list_voices()}
    out = []
    for item in items:
        voice_id = str((item or {}).get("id") or "").strip() if isinstance(item, dict) else ""
        if not _VOICE_ID.match(voice_id):
            continue
        suffix = next((s for s in _REGION_SUFFIX if f"-{s}" in voice_id.lower()), "")
        out.append({
            "id": voice_id,
            "samplingRate": item.get("sampling_rate"),
            "inTable": voice_id in known,
            "suggestedRegion": _REGION_SUFFIX.get(suffix, ""),
        })
    return {"ok": True, "voices": out}
