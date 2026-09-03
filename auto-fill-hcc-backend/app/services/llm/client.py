"""Client LLM: primary vLLM/Qwen (OpenAI-compatible) → fallback OpenAI khi primary lỗi.

Nếu base LLM (LLM_BASE_URL) lỗi và có OPENAI_API_KEY → tự gọi OpenAI thay thế.
"""
import json
import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"```json\s*([\s\S]*?)\s*```", re.IGNORECASE)
_BRACE_RE = re.compile(r"\{[\s\S]*\}")
_THINK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)

# OpenAI client khởi tạo lazy (chỉ khi cần fallback) để không bắt buộc có key.
_openai_client = None


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
    for base_url, model, tag in _vllm_targets():
        try:
            out = await _chat_vllm(messages, temperature, max_tokens, enable_thinking,
                                   base_url=base_url, model=model)
            if tag != "primary":
                logger.warning("LLM %s [%s model=%s] OK sau khi primary lỗi", tag, base_url, model)
            return out
        except Exception as e:  # noqa: BLE001
            last_exc = e
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


async def chat(
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
        out = await _chat_openai(messages, temperature)
        if settings.llm_debug:
            logger.info("[LLM fallback OpenAI OK] model=%s len=%d content=%r",
                        settings.openai_model, len(out), out[:1500])
        return out


async def chat_text(
    messages: list[dict],
    temperature: float | None = None,
    max_tokens: int | None = None,
    enable_thinking: bool = False,
) -> str:
    """Chat trả text; primary như cũ, fallback OpenAI không ép JSON object."""
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
        return await _chat_openai_text(messages, temperature)


def extract_json_block(text: str) -> dict:
    """Ưu tiên block ```json ... ```; fallback cặp {...} đầu tiên.

    Bỏ khối <think>...</think> (khi bật reasoning) trước khi tìm JSON.
    """
    text = _THINK_RE.sub("", text)
    m = _FENCE_RE.search(text)
    if m:
        return json.loads(m.group(1).strip())
    m = _BRACE_RE.search(text)
    if m:
        return json.loads(m.group(0))
    raise ValueError("Không tìm thấy JSON trong response LLM:\n" + text[:300])
