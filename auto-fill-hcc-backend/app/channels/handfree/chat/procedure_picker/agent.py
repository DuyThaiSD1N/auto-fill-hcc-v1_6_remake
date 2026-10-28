"""Agent CHỌN THỦ TỤC: một lượt LLM, đọc vài lượt hội thoại gần nhất + danh sách thủ tục của tỉnh.

LLM trả SỐ THỨ TỰ trong danh sách (không phải key) — agent đổi ngược ra key. Số nằm ngoài danh sách
của tỉnh tài khoản bị bỏ: LLM không bịa được thủ tục, cũng không chọn được thủ tục khóa cho tỉnh
khác (thủ tục đó không có trong danh sách nên coi như không nhận ra).

Danh sách đưa LLM theo thứ tự KHAI BÁO trong registry, không theo thứ tự thẻ màn chào: màn chào
đẩy chứng thực chữ ký xuống dòng cuối, và ở dòng cuối model hay đọc nhầm sang dòng ngay trên
(Bắc Ninh 101 thủ tục: "chứng thực chữ ký" [101] → trả 100 = đăng ký tạm trú, cả tên lẫn số).
LLM chép kèm "ten" (đầu tên thủ tục của số đã chọn) để bắt lỗi đếm lệch số: tên không khớp số →
lấy dòng khớp tên, không chắc → hỏi lại.
"""
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field

from app.channels.handfree.chat import store
from app.channels.handfree.chat.procedure_picker import prompt
from app.channels.handfree.procedure_registry import PROCEDURES, is_allowed_in_province
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


def procedures_for(province_slug: str | None) -> list[dict]:
    """Thủ tục của tỉnh theo thứ tự khai báo — số [n] trong prompt là vị trí trong danh sách này."""
    return [p for p in PROCEDURES if is_allowed_in_province(p, province_slug)]


def _key_at(value, keys: list[str]) -> str:
    """Số thứ tự (1-based) LLM trả → key; ngoài danh sách / không phải số → ""."""
    try:
        n = int(str(value).strip().strip("[]"))
    except (TypeError, ValueError):
        return ""
    return keys[n - 1] if 1 <= n <= len(keys) else ""


def _norm(text) -> str:
    text = unicodedata.normalize("NFD", str(text or "").replace("Đ", "D").replace("đ", "d"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn").lower()
    text = re.sub(r"^\s*\[\d+\]\s*", "", text)  # model chép cả "[101] " đầu dòng
    return " ".join(re.sub(r"[^\w]+", " ", text).split())


def _name_matches(name: str, proc: dict) -> bool:
    label = _norm(proc.get("label") or proc.get("shortLabel") or proc["key"])
    return bool(label) and (name in label or label in name)


def _checked_key(value, name, procedures: list[dict]) -> tuple[str, list[str]]:
    """(key, candidates) sau khi đối chiếu số với "ten" LLM chép.

    Thiếu "ten" → tin số như cũ. Số khớp tên → giữ. Lệch → dòng khớp tên gần số nhất (lỗi đếm lệch
    thường chỉ ±1); không có dòng khớp hoặc khớp nhiều dòng xa nhau → key rỗng + gợi ý để hỏi lại.
    """
    keys = [p["key"] for p in procedures]
    key = _key_at(value, keys)
    name = _norm(name)
    if len(name) < 4:
        return key, []
    if key and _name_matches(name, procedures[keys.index(key)]):
        return key, []
    matched = [n for n, p in enumerate(procedures, 1) if _name_matches(name, p)]
    try:
        n = int(str(value).strip().strip("[]"))
    except (TypeError, ValueError):
        n = 0
    near = [m for m in matched if abs(m - n) <= 1]
    fixed = near if len(near) == 1 else matched if len(matched) == 1 else []
    if fixed:
        logger.info("[procedure_picker] số %s lệch tên %r → lấy [%s] %s", value, name, fixed[0], keys[fixed[0] - 1])
        return keys[fixed[0] - 1], []
    logger.warning("[procedure_picker] số %s không khớp tên %r → hỏi lại", value, name)
    return "", list(dict.fromkeys([*(keys[m - 1] for m in matched), *([key] if key else [])]))


async def pick(message: str, conv: dict | None) -> PickResult:
    conv = conv or {}
    procedures = procedures_for(_province_slug(conv))
    keys = [p["key"] for p in procedures]
    shown = [(keys.index(k) + 1, procedures[keys.index(k)])
             for k in (conv.get("procedure_candidates") or []) if k in keys]
    system = prompt.SYSTEM.format(procedures=prompt.catalog(procedures),
                                  candidates=prompt.candidates_block(shown))
    messages = [{"role": "system", "content": system},
                *store.recent_dialogue(conv, _HISTORY_TURNS),
                {"role": "user", "content": str(message or "")[:500]}]
    try:
        raw = await llm_chat(messages, temperature=0.0, max_tokens=200, purpose="procedure_picker")
        m = re.search(r"\{[\s\S]*\}", raw or "")
        data = json.loads(m.group(0)) if m else {}
    except Exception as e:  # noqa: BLE001 — LLM là best-effort, flow phải sống tiếp
        logger.warning("[procedure_picker] LLM lỗi: %s", e)
        return PickResult("error")

    result = str(data.get("result") or "")
    key, name_candidates = _checked_key(data.get("id"), data.get("ten"), procedures)
    raw_candidates = data.get("candidates") if isinstance(data.get("candidates"), list) else []
    candidates = [k for k in dict.fromkeys(_key_at(c, keys) for c in raw_candidates) if k]
    candidates = candidates[:_MAX_CANDIDATES]
    if result not in _RESULTS:
        return PickResult("unclear", "", candidates)
    if result in ("pick", "ask_about"):
        if key:
            return PickResult(result, key, [])
        if name_candidates and result == "pick":
            # Số và tên trỏ hai thủ tục khác nhau: không đoán, hỏi lại công dân giữa các dòng đó.
            return PickResult("unclear", "", name_candidates[:_MAX_CANDIDATES])
        # Số ngoài danh sách: hỏi thì vẫn trả lời chung, chọn thì quay về gợi ý.
        return PickResult("ask_about", "", []) if result == "ask_about" else PickResult("unclear", "", candidates)
    if result == "unclear":
        return PickResult("unclear", "", candidates)
    return PickResult("not_procedure")
