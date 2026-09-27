"""Client LLM: primary vLLM/Qwen (OpenAI-compatible) → fallback OpenAI khi primary lỗi.

Nếu base LLM (LLM_BASE_URL) lỗi và có OPENAI_API_KEY → tự gọi OpenAI thay thế.
"""
import hashlib
import json
import logging
import re
import sys
import time
from contextvars import ContextVar

import httpx

from app.config import settings
from app.monitor import recorder as mon

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"```json\s*([\s\S]*?)\s*```", re.IGNORECASE)
_BRACE_RE = re.compile(r"\{[\s\S]*\}")
_THINK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)

# OpenAI client khởi tạo lazy (chỉ khi cần fallback) để không bắt buộc có key.
_openai_client = None

# Bản ghi của lần gọi đang chạy (web Monitor) — các hàm nội bộ ghi token/endpoint vào đây thay
# vì đổi kiểu trả về (test và code cũ vẫn nhận ``str``). None = không ghi.
_call: ContextVar[dict | None] = ContextVar("llm_monitor_call", default=None)

# Suy mục đích lần gọi từ module gọi; không suy được (vd gọi qua asyncio.gather) → theo loại lượt.
_PURPOSE_BY_MODULE = (
    ("compact_agent", "extract"),
    (".reason", "reason"),
    (".attach.", "plan"),
    ("llm_classifier", "classify"),
    (".intents", "intent"),
)
_PURPOSE_BY_KIND = {"autofill": "extract", "attach": "plan", "classify": "classify"}


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI

        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def _chat_vllm(messages: list[dict], temperature: float, max_tokens: int,
                     enable_thinking: bool, *, base_url: str, model: str) -> str:
    """Gọi 1 endpoint vLLM/Qwen (OpenAI-compatible). Dùng chung cho primary và fallback vLLM."""
    timeout = httpx.Timeout(settings.llm_timeout_ms / 1000)
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": enable_thinking},
    }
    # Base có thể kèm sẵn "/v1" (vd https://llm.tiengnoi.vn/qwen35/v1) hoặc không (vd .../llm);
    # tránh nối "/v1" lần hai gây 404 {"detail":"Not Found"} rồi rơi hết sang fallback.
    base = base_url.rstrip("/")
    url = base + ("/chat/completions" if base.endswith("/v1") else "/v1/chat/completions")
    async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
        r = await client.post(url, json=payload)
    if r.status_code >= 400:
        raise RuntimeError(f"LLM HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    choices = data.get("choices") or []
    content = (choices[0].get("message", {}).get("content", "") if choices else "") or ""
    call = _call.get()
    if call is not None:
        usage = data.get("usage") or {}
        call["tokens_in"] = usage.get("prompt_tokens")
        call["tokens_out"] = usage.get("completion_tokens")
        call["finish_reason"] = choices[0].get("finish_reason") if choices else None
        call["model"] = data.get("model") or model
    if not content:
        raise RuntimeError(f"LLM trả content rỗng. raw={str(data)[:300]}")
    return content


def _vllm_targets() -> list[tuple[str, str, str]]:
    """Danh sách endpoint vLLM theo thứ tự ưu tiên: primary rồi fallback (nếu cấu hình)."""
    targets = [(settings.llm_base_url, settings.llm_model, "primary")]
    if settings.fallback_llm_base_url:
        targets.append((
            settings.fallback_llm_base_url,
            settings.fallback_llm_model or settings.llm_model,
            "fallback-vllm",
        ))
    return targets


async def _chat_primary(messages: list[dict], temperature: float, max_tokens: int,
                        enable_thinking: bool = False) -> str:
    """Thử lần lượt các endpoint vLLM (primary → fallback vLLM). Ném lỗi cuối nếu tất cả fail.

    Tách khỏi fallback OpenAI (tầng cuối) để giữ nguyên: hết vLLM mới rơi sang OpenAI.
    """
    last_exc: Exception | None = None
    call = _call.get()
    for base_url, model, tag in _vllm_targets():
        t0 = time.perf_counter()
        try:
            out = await _chat_vllm(messages, temperature, max_tokens, enable_thinking,
                                   base_url=base_url, model=model)
            if tag != "primary":
                logger.warning("LLM %s [%s model=%s] OK sau khi primary lỗi", tag, base_url, model)
            _note_try(call, tag, t0, None)
            return out
        except Exception as e:  # noqa: BLE001
            last_exc = e
            _note_try(call, tag, t0, e)
            logger.warning("LLM %s lỗi [%s]: %r", tag, type(e).__name__, e)
    raise last_exc if last_exc else RuntimeError("Không có endpoint LLM nào khả dụng")


async def _chat_openai(messages: list[dict], temperature: float) -> str:
    # Ép JSON object output cho ổn định (giống pattern callbot evaluator).
    resp = await _get_openai_client().chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content or ""


async def _chat_openai_text(messages: list[dict], temperature: float) -> str:
    """Fallback OpenAI cho agent cần text tự do, không ép response_format JSON."""
    resp = await _get_openai_client().chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""


def _note_try(call: dict | None, target: str, t0: float, exc: Exception | None) -> None:
    if call is None:
        return
    item = {"target": target, "ms": int((time.perf_counter() - t0) * 1000), "ok": exc is None}
    if exc is not None:
        item["error"] = f"{type(exc).__name__}: {exc}"[:300]
    call.setdefault("tries", []).append(item)
    if exc is None:
        call["target"] = target


async def _monitored(fn, fn_name: str, caller: str, purpose: str | None,
                     messages: list[dict], temperature, max_tokens, enable_thinking) -> str:
    """Bọc một lần gọi LLM: span ``llm.<purpose>`` + bản ghi thời gian/token/output thô."""
    rec = mon.current()
    if rec is None:
        return await fn(messages, temperature, max_tokens, enable_thinking)
    if not purpose:
        purpose = next((p for key, p in _PURPOSE_BY_MODULE if key in caller), None)
        purpose = purpose or _PURPOSE_BY_KIND.get(rec.kind, "call")
    system = next((m.get("content") for m in messages if m.get("role") == "system"), None)
    call = rec.new_llm_call(
        purpose=purpose, caller=caller, fn=fn_name,
        max_tokens=max_tokens if max_tokens is not None else settings.llm_max_tokens,
        thinking=enable_thinking,
        prompt_chars=sum(len(str(m.get("content") or "")) for m in messages),
        # Chỉ lưu hash system prompt để biết lượt nào chạy phiên bản prompt nào (không lưu nội dung).
        system_hash=hashlib.sha1(system.encode("utf-8")).hexdigest()[:12]
        if isinstance(system, str) else None,
    )
    token = _call.set(call)
    t0 = time.perf_counter()
    try:
        with mon.span(f"llm.{purpose}", n=call["n"]) as sp:
            call["span"] = getattr(sp, "id", None)
            out = await fn(messages, temperature, max_tokens, enable_thinking)
        call["raw"] = out
        if "<think>" in out:
            call["think_chars"] = sum(len(m) for m in _THINK_RE.findall(out))
        if call.get("finish_reason") == "length":
            rec.flag("llm_cut")
        if call.get("target") not in (None, "primary"):
            rec.flag("llm_fallback")
        return out
    except Exception as e:  # noqa: BLE001
        call["error"] = f"{type(e).__name__}: {e}"[:300]
        rec.error(f"LLM #{call['n']} {purpose}: {call['error']}")
        raise
    finally:
        call["ms"] = int((time.perf_counter() - t0) * 1000)
        _call.reset(token)


def _caller_module() -> str:
    # Khung 0 = _caller_module, 1 = chat/chat_text, 2 = nơi gọi.
    try:
        return sys._getframe(2).f_globals.get("__name__", "") or ""
    except ValueError:
        return ""


async def chat(
    messages: list[dict],
    temperature: float | None = None,
    max_tokens: int | None = None,
    enable_thinking: bool = False,
    *,
    purpose: str | None = None,
) -> str:
    return await _monitored(_chat, "chat", _caller_module(), purpose,
                            messages, temperature, max_tokens, enable_thinking)


async def _chat(
    messages: list[dict],
    temperature: float | None = None,
    max_tokens: int | None = None,
    enable_thinking: bool = False,
) -> str:
    temperature = settings.llm_temperature if temperature is None else temperature
    max_tokens = settings.llm_max_tokens if max_tokens is None else max_tokens

    try:
        out = await _chat_primary(messages, temperature, max_tokens, enable_thinking)
        if settings.llm_debug:
            logger.info("[LLM primary OK] model=%s len=%d content=%r", settings.llm_model, len(out), out[:1500])
        return out
    except Exception as e:  # noqa: BLE001
        # Log RÕ loại lỗi (str có thể rỗng) để debug vì sao primary fail.
        logger.warning("LLM primary lỗi [%s]: %r → fallback OpenAI %s",
                       type(e).__name__, e, settings.openai_model)
        if not settings.openai_api_key:
            raise  # không cấu hình fallback → ném lỗi gốc
        t0 = time.perf_counter()
        out = await _chat_openai(messages, temperature)
        _note_try(_call.get(), "openai", t0, None)
        if settings.llm_debug:
            logger.info("[LLM fallback OpenAI OK] model=%s len=%d content=%r",
                        settings.openai_model, len(out), out[:1500])
        return out


async def chat_text(
    messages: list[dict],
    temperature: float | None = None,
    max_tokens: int | None = None,
    enable_thinking: bool = False,
    *,
    purpose: str | None = None,
) -> str:
    """Chat trả text; primary như cũ, fallback OpenAI không ép JSON object."""
    return await _monitored(_chat_text, "chat_text", _caller_module(), purpose,
                            messages, temperature, max_tokens, enable_thinking)


async def _chat_text(
    messages: list[dict],
    temperature: float | None = None,
    max_tokens: int | None = None,
    enable_thinking: bool = False,
) -> str:
    temperature = settings.llm_temperature if temperature is None else temperature
    max_tokens = settings.llm_max_tokens if max_tokens is None else max_tokens

    try:
        return await _chat_primary(messages, temperature, max_tokens, enable_thinking)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "LLM primary text lỗi [%s]: %r → fallback OpenAI %s",
            type(e).__name__,
            e,
            settings.openai_model,
        )
        if not settings.openai_api_key:
            raise
        t0 = time.perf_counter()
        out = await _chat_openai_text(messages, temperature)
        _note_try(_call.get(), "openai", t0, None)
        return out


def extract_json_block(text: str) -> dict:
    """Ưu tiên block ```json ... ```; fallback cặp {...} đầu tiên.

    Bỏ khối <think>...</think> (khi bật reasoning) trước khi tìm JSON.
    """
    rec = mon.current()
    if rec is None:
        return _extract_json(text)[0]
    call = rec.find_llm_call(text)
    try:
        with mon.span("post.parse", n=call["n"] if call else None):
            parsed, src = _extract_json(text)
    except Exception as e:
        rec.flag("parse_fail")
        if call is not None:
            call["parse_error"] = f"{type(e).__name__}: {e}"[:300]
        raise
    # Giữ CHUỖI JSON (bất biến) chứ không giữ object: nơi gọi thường sửa dict sau khi parse,
    # phần ghi nền parse lại chuỗi này để có đúng output LLM tại thời điểm parse.
    if call is not None:
        call["parsed_src"] = src
    else:
        rec.count("parse_unlinked")
    return parsed


def _extract_json(text: str) -> tuple[dict, str]:
    text = _THINK_RE.sub("", text)
    m = _FENCE_RE.search(text)
    if m:
        src = m.group(1).strip()
        return json.loads(src), src
    m = _BRACE_RE.search(text)
    if m:
        src = m.group(0)
        return json.loads(src), src
    raise ValueError("Không tìm thấy JSON trong response LLM:\n" + text[:300])
