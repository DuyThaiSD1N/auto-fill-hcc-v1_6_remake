"""Client LLM: vLLM/Qwen (OpenAI-compatible) — LB ngoài (nếu có) → máy chính / phụ do BE tự chia
(app/services/endpoint_pool.py). Hết máy thì ném lỗi, không gửi ra dịch vụ ngoài.
"""
import hashlib
import json
import logging
import re
import sys
import time
from contextvars import ContextVar

import httpx

from app.archive.config import archive_settings
from app.config import settings
from app.monitor import recorder as mon
from app.services.endpoint_pool import Pool, Target

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"```json\s*([\s\S]*?)\s*```", re.IGNORECASE)
_BRACE_RE = re.compile(r"\{[\s\S]*\}")
_THINK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)

# Máy LLM vừa lỗi bị xếp sau 60 s (lỗi kết nối bỏ sau _CONNECT_TIMEOUT_S thay vì chờ hết trần đọc). OCR Qwen dùng
# chung pool này vì chạy trên cùng các máy vLLM.
POOL = Pool(down_s=60)
_CONNECT_TIMEOUT_S = 10

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

# Khóa phần chi tiết (số nhà/đường/thôn/xóm/tổ...) của object địa chỉ: model thấy tên "chiTietDuoiXa" — tên
# "diaChi" bị hiểu là cả dòng địa chỉ nên hay bị nhét tên xã/tỉnh vào. Code và extension vẫn dùng "diaChi":
# đổi tên ở chiều gửi (kể cả chỗ prompt còn sót / JSON ngữ cảnh dựng từ code) và đổi ngược ở chiều nhận.
ADDRESS_DETAIL_KEY = "chiTietDuoiXa"
_ADDRESS_DETAIL_OLD_RE = re.compile(r"(?<![\w\[.\-/])diaChi(?![\w\]])")


def to_model_text(value):
    """Chuỗi gửi model → khóa chi tiết địa chỉ theo tên model thấy."""
    return _ADDRESS_DETAIL_OLD_RE.sub(ADDRESS_DETAIL_KEY, value) if isinstance(value, str) else value


def to_model_keys(messages: list[dict]) -> list[dict]:
    """Bản sao messages với khóa chi tiết địa chỉ theo tên model thấy."""
    text = to_model_text
    out = []
    for message in messages:
        content = message.get("content")
        if isinstance(content, list):
            content = [{**part, "text": text(part["text"])} if isinstance(part, dict) and "text" in part else part
                       for part in content]
        else:
            content = text(content)
        out.append({**message, "content": content})
    return out


def from_model_keys(text: str) -> str:
    """Output model → khóa chi tiết địa chỉ theo tên code/extension dùng."""
    return text.replace(ADDRESS_DETAIL_KEY, "diaChi") if isinstance(text, str) else text


async def _chat_vllm(messages: list[dict], temperature: float, max_tokens: int,
                     enable_thinking: bool, *, base_url: str, model: str, usage: dict | None = None) -> str:
    """Gọi 1 endpoint vLLM/Qwen (OpenAI-compatible). ``usage`` (nếu truyền) nhận token của lượt để đo tải máy."""
    timeout = httpx.Timeout(settings.llm_timeout_ms / 1000, connect=_CONNECT_TIMEOUT_S)
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
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"} if settings.llm_api_key else None
    async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
        r = await client.post(url, json=payload, headers=headers)
    if r.status_code >= 400:
        raise RuntimeError(f"LLM HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    choices = data.get("choices") or []
    content = (choices[0].get("message", {}).get("content", "") if choices else "") or ""
    if usage is not None:
        usage.update(data.get("usage") or {})
    call = _call.get()
    if call is not None:
        u = data.get("usage") or {}
        call["tokens_in"] = u.get("prompt_tokens")
        call["tokens_out"] = u.get("completion_tokens")
        call["finish_reason"] = choices[0].get("finish_reason") if choices else None
        call["model"] = data.get("model") or model
    if not content:
        raise RuntimeError(f"LLM trả content rỗng. raw={str(data)[:300]}")
    return content


def llm_targets() -> list[Target]:
    """Các máy LLM theo vai: LB (nếu có), máy chính, máy phụ (nếu có). Thứ tự gọi do POOL.order quyết."""
    targets = []
    if settings.llm_lb_base_url:
        targets.append(Target(settings.llm_lb_base_url, "lb", settings.llm_model))
    targets.append(Target(settings.llm_base_url, "chinh", settings.llm_model))
    if settings.fallback_llm_base_url:
        targets.append(Target(settings.fallback_llm_base_url, "phu",
                              settings.fallback_llm_model or settings.llm_model))
    return targets


def work_units(usage: dict) -> float:
    """Khối việc của một lượt để so thời gian giữa lượt to và nhỏ: token sinh ra + token đọc vào (đọc nhanh hơn
    sinh nhiều lần nên quy đổi 20 : 1)."""
    return (usage.get("completion_tokens") or 0) + (usage.get("prompt_tokens") or 0) / 20 or 1


async def _chat_primary(messages: list[dict], temperature: float, max_tokens: int,
                        enable_thinking: bool = False) -> str:
    """Thử lần lượt các máy theo POOL.order (LB → máy chính / phụ do BE tự chia). Ném lỗi cuối nếu tất cả fail."""
    last_exc: Exception | None = None
    call = _call.get()
    for target in POOL.order(llm_targets()):
        t0 = time.perf_counter()
        try:
            with POOL.track(target.url) as m:
                usage: dict = {}
                out = await _chat_vllm(messages, temperature, max_tokens, enable_thinking,
                                       base_url=target.url, model=target.model, usage=usage)
                m["units"] = work_units(usage)
            _note_try(call, target.kind, t0, None)
            return out
        except Exception as e:  # noqa: BLE001
            last_exc = e
            _note_try(call, target.kind, t0, e)
            logger.warning("LLM %s lỗi [%s]: %r", target.kind, type(e).__name__, e)
    raise last_exc if last_exc else RuntimeError("Không có endpoint LLM nào khả dụng")


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
        # Máy phục vụ (lb / chinh / phu) đếm vào timing.n; phải thử máy khác sau một máy lỗi → cờ llm_fallback.
        if call.get("target"):
            rec.count(f"llm_{call['target']}")
        if len(call.get("tries") or []) > 1:
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
    return from_model_keys(await _monitored(_chat, "chat", _caller_module(), purpose,
                                            to_model_keys(messages), temperature, max_tokens, enable_thinking))


async def _chat(
    messages: list[dict],
    temperature: float | None = None,
    max_tokens: int | None = None,
    enable_thinking: bool = False,
) -> str:
    temperature = settings.llm_temperature if temperature is None else temperature
    max_tokens = settings.llm_max_tokens if max_tokens is None else max_tokens

    out = await _chat_primary(messages, temperature, max_tokens, enable_thinking)
    if (settings.llm_debug and not archive_settings.enabled):
        logger.info("[LLM OK] model=%s len=%d content=%r", settings.llm_model, len(out), out[:1500])
    return out


async def chat_text(
    messages: list[dict],
    temperature: float | None = None,
    max_tokens: int | None = None,
    enable_thinking: bool = False,
    *,
    purpose: str | None = None,
) -> str:
    """Chat trả text (không ép JSON object)."""
    return from_model_keys(await _monitored(_chat_text, "chat_text", _caller_module(), purpose,
                                            to_model_keys(messages), temperature, max_tokens, enable_thinking))


async def _chat_text(
    messages: list[dict],
    temperature: float | None = None,
    max_tokens: int | None = None,
    enable_thinking: bool = False,
) -> str:
    temperature = settings.llm_temperature if temperature is None else temperature
    max_tokens = settings.llm_max_tokens if max_tokens is None else max_tokens

    return await _chat_primary(messages, temperature, max_tokens, enable_thinking)


async def chat_self_hosted(
    messages: list[dict],
    temperature: float | None = None,
    max_tokens: int | None = None,
    enable_thinking: bool = False,
    *,
    purpose: str | None = None,
) -> str:
    """Chỉ máy chủ AI riêng (vLLM primary → fallback vLLM), KHÔNG rơi sang OpenAI — cho nội dung người dùng
    không được gửi ra dịch vụ ngoài. Hết máy chủ riêng thì ném lỗi để nơi gọi báo "thử lại sau"."""
    return from_model_keys(await _monitored(_chat_self_hosted, "chat_self_hosted", _caller_module(), purpose,
                                            to_model_keys(messages), temperature, max_tokens, enable_thinking))


async def _chat_self_hosted(
    messages: list[dict],
    temperature: float | None = None,
    max_tokens: int | None = None,
    enable_thinking: bool = False,
) -> str:
    temperature = settings.llm_temperature if temperature is None else temperature
    max_tokens = settings.llm_max_tokens if max_tokens is None else max_tokens
    return await _chat_primary(messages, temperature, max_tokens, enable_thinking)


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
        return _loads_or_close(m.group(1).strip())
    m = _BRACE_RE.search(text)
    if m:
        return _loads_or_close(m.group(0))
    raise ValueError("Không tìm thấy JSON trong response LLM:\n" + text[:300])


def _loads_or_close(src: str) -> tuple[dict, str]:
    """json.loads; hỏng thì thử đóng nốt ngoặc LLM bỏ sót ở cuối (vd thiếu một `}` → mất trắng mọi field)."""
    try:
        return json.loads(src), src
    except json.JSONDecodeError as e:
        closed = _close_brackets(src)
        if closed is not None:
            try:
                return json.loads(closed), closed
            except json.JSONDecodeError:
                pass
        raise e


def _close_brackets(src: str) -> str | None:
    """Thêm các ngoặc còn mở ở cuối chuỗi; None nếu ngoặc lệch nhau hoặc đứt giữa chuỗi."""
    stack: list[str] = []
    in_str = esc = False
    for ch in src:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if not stack or stack.pop() != ch:
                return None
    if in_str or not stack:
        return None
    return src + "".join(reversed(stack))
