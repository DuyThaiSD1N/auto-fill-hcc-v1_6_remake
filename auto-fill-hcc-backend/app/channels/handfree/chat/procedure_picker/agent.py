"""Agent CHỌN THỦ TỤC: một lượt LLM, đọc vài lượt hội thoại gần nhất + danh sách thủ tục của tỉnh.

LLM trả SỐ THỨ TỰ trong danh sách (không phải key) — agent đổi ngược ra key. Số nằm ngoài danh sách
của tỉnh tài khoản bị bỏ: LLM không bịa được thủ tục, cũng không chọn được thủ tục khóa cho tỉnh
khác (thủ tục đó không có trong danh sách nên coi như không nhận ra).
"""
import json
import logging
import re
from dataclasses import dataclass, field

from app.channels.handfree.chat import store
from app.channels.handfree.chat.procedure_picker import prompt
from app.channels.handfree.procedure_registry import public_list_for
from app.services.llm.client import chat as llm_chat

logger = logging.getLogger(__name__)

_RESULTS = {"pick", "ask_about", "unclear", "not_procedure"}
_MAX_CANDIDATES = 3
_HISTORY_TURNS = 6


@dataclass
class PickResult:
    result: str                    # pick | ask_about | unclear | not_procedure | error
    key: str = ""
    candidates: list[str] = field(default_factory=list)


def _province_slug(conv: dict) -> str:
    return str(((conv or {}).get("auth_user") or {}).get("province_slug") or "")


def _key_at(value, keys: list[str]) -> str:
    """Số thứ tự (1-based) LLM trả → key; ngoài danh sách / không phải số → ""."""
    try:
        n = int(str(value).strip().strip("[]"))
    except (TypeError, ValueError):
        return ""
    return keys[n - 1] if 1 <= n <= len(keys) else ""


async def pick(message: str, conv: dict | None) -> PickResult:
    conv = conv or {}
    procedures = public_list_for(_province_slug(conv))
    keys = [p["key"] for p in procedures]
    shown = [(keys.index(k) + 1, procedures[keys.index(k)])
             for k in (conv.get("procedure_candidates") or []) if k in keys]
    system = prompt.SYSTEM.format(procedures=prompt.catalog(procedures),
                                  candidates=prompt.candidates_block(shown))
    messages = [{"role": "system", "content": system},
                *store.recent_dialogue(conv, _HISTORY_TURNS),
                {"role": "user", "content": str(message or "")[:500]}]
    try:
        raw = await llm_chat(messages, temperature=0.0, max_tokens=120, purpose="procedure_picker")
        m = re.search(r"\{[\s\S]*\}", raw or "")
        data = json.loads(m.group(0)) if m else {}
    except Exception as e:  # noqa: BLE001 — LLM là best-effort, flow phải sống tiếp
        logger.warning("[procedure_picker] LLM lỗi: %s", e)
        return PickResult("error")

    result = str(data.get("result") or "")
    key = _key_at(data.get("id"), keys)
    raw_candidates = data.get("candidates") if isinstance(data.get("candidates"), list) else []
    candidates = [k for k in dict.fromkeys(_key_at(c, keys) for c in raw_candidates) if k]
    candidates = candidates[:_MAX_CANDIDATES]
    if result not in _RESULTS:
        return PickResult("unclear", "", candidates)
    if result in ("pick", "ask_about"):
        if key:
            return PickResult(result, key, [])
        # Số ngoài danh sách: hỏi thì vẫn trả lời chung, chọn thì quay về gợi ý.
        return PickResult("ask_about", "", []) if result == "ask_about" else PickResult("unclear", "", candidates)
    if result == "unclear":
        return PickResult("unclear", "", candidates)
    return PickResult("not_procedure")
