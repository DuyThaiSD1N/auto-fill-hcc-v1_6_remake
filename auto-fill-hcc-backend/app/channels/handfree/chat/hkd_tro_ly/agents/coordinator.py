"""Agent ĐIỀU PHỐI của trợ lý hộ kinh doanh: hiểu công dân muốn gì, chỉ ra mục nào có thông tin. Không đọc giá trị."""
import difflib
import json
import logging
import re
from dataclasses import dataclass, field as dc_field

from app.channels.handfree.chat import store
from app.channels.handfree.chat.hkd_tro_ly.agents import context, coordinator_prompt as prompt
from app.channels.handfree.chat.intents import fold
from app.services.llm.client import chat as llm_chat

logger = logging.getLogger(__name__)

DECISIONS = {"tra_loi", "nganh", "dong_y", "bo_qua", "tam_dung", "nhac_lai", "di_toi", "lenh_khac", "hoi_ro"}
_MAX_TEXT = 300


@dataclass
class Decision:
    kind: str
    targets: list[dict] = dc_field(default_factory=list)
    goal: dict | None = None
    nganh_text: str = ""
    question: str = ""
    reason: str = ""
    named: bool = False
    has_value: bool = False


def messages(catalog: list[dict], current: dict, thread: list[str], conv: dict, text: str) -> list[dict]:
    user = prompt.USER.format(ban_do=context.form_block(catalog), dang_hoi=context.current_block(catalog, current),
                              dang_lam_ro=context.thread_block(thread),
                              hoi_thoai=context.dialogue_block(conv, context.DIALOGUE_TURNS), cau=str(text or "")[:600])
    return [{"role": "system", "content": prompt.SYSTEM}, {"role": "user", "content": user}]


def _load(raw: str) -> dict:
    """JSON của model; bị cắt ở khoá giải thích "ly_do" (khoá cuối) thì bỏ khoá đó rồi đọc phần trước."""
    text = raw or ""
    m = re.search(r"\{[\s\S]*\}", text)
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        head = re.split(r',\s*"ly_do"', text[text.find("{"):], maxsplit=1)[0]
        return json.loads(head + "}")


def parse(raw: str, by_code: dict[str, dict]) -> Decision:
    data = _load(raw)
    if not isinstance(data, dict):
        data = {}
    kind = str(data.get("quyet_dinh") or "").strip()
    decision = Decision(kind if kind in DECISIONS else "hoi_ro",
                        nganh_text=re.sub(r"\s+", " ", str(data.get("nganh_mo_ta") or "")).strip()[:_MAX_TEXT],
                        question=re.sub(r"\s+", " ", str(data.get("cau_hoi") or "")).strip()[:200],
                        reason=str(data.get("ly_do") or "")[:200],
                        named=bool(str(data.get("ten_muc_duoc_neu") or "").strip()),
                        has_value=data.get("co_gia_tri") is True)
    if decision.kind == "tra_loi":
        for item in data.get("o") or []:
            target = by_code.get(str((item or {}).get("ma") if isinstance(item, dict) else item or "").strip())
            if target and target not in decision.targets:
                decision.targets.append(target)
        if not decision.targets:
            decision.kind = "nganh" if decision.nganh_text else "hoi_ro"
    if decision.kind == "nganh" and not decision.nganh_text:
        decision.kind = "hoi_ro"
    if decision.kind == "di_toi":
        decision.goal = by_code.get(str(data.get("toi") or "").strip())
        if not decision.goal:
            decision.kind = "hoi_ro"
    return decision


def _plain(text: str) -> str:
    return re.sub(r"[^\w\s]", "", fold(text)).strip()


def _last_bot_line(conv: dict) -> str:
    lines = [m["content"] for m in store.recent_dialogue(conv, 4) if m["role"] == "assistant"]
    return lines[-1] if lines else ""


def inconsistency(decision: Decision, conv: dict) -> str:
    """Quyết định lệch với chính khoá kiểm tra agent ghi, hoặc hỏi lại y câu trợ lý vừa hỏi → câu báo để agent quyết
    lại. Chỉ kiểm, không tự sửa quyết định."""
    if decision.kind in {"hoi_ro", "di_toi"} and decision.question:
        last = _plain(_last_bot_line(conv))
        if last and difflib.SequenceMatcher(None, _plain(decision.question), last).ratio() > 0.85:
            return ("Bạn đang hỏi lại đúng câu trợ lý vừa hỏi, trong khi câu mới chính là câu trả lời cho câu hỏi đó. "
                    "Ghép câu mới với <dang_lam_ro> / <hoi_thoai> để ra việc.")
    if decision.kind == "di_toi" and decision.has_value:
        return (f"Bạn ghi câu có thông tin để ghi nhưng lại chọn \"di_toi\" mục {decision.goal.get('code')}. Có giá trị "
                f"thì chọn \"tra_loi\" mục đó.")
    if decision.kind == "tra_loi" and not decision.named and decision.has_value:
        # Không có xác nhận từng câu như tờ khai hộ tịch: ghi nhầm sang mục khối khác (nhất là khối đã lưu) là sửa âm
        # thầm hồ sơ trên cổng.
        outside = [t for t in decision.targets if t.get("status") != "dang_mo"]
        if outside:
            return (f"Bạn ghi câu không nêu tên mục nào nhưng lại giao mục ngoài khối đang mở "
                    f"{[t['code'] for t in outside]}. Câu chỉ có giá trị là của MỤC ĐANG HỎI.")
    return ""


async def decide(catalog: list[dict], current: dict, thread: list[str], conv: dict, text: str) -> Decision:
    """Lỗi gọi LLM ném ra ngoài để bên gọi lùi về cách hiểu cũ (một lượt LLM) — vòng hỏi không được chết."""
    by_code = context.with_codes(catalog)
    msgs = messages(catalog, current, thread, conv, text)
    raw = await llm_chat(msgs, temperature=0.0, max_tokens=400, purpose="hkd_coordinator")
    decision = parse(raw, by_code)
    problem = inconsistency(decision, conv)
    if problem:
        logger.info("[hkd.agents] điều phối quyết lại: %s", problem)
        retry = [*msgs, {"role": "assistant", "content": raw},
                 {"role": "user", "content": prompt.RECHECK.format(problem=problem)}]
        decision = parse(await llm_chat(retry, temperature=0.0, max_tokens=400, purpose="hkd_coordinator"), by_code)
    logger.info("[hkd.agents] điều phối: %s %s (%s)", decision.kind, [t.get("key") for t in decision.targets],
                decision.reason)
    return decision
