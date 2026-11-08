"""Agent ĐIỀU PHỐI: hiểu công dân muốn gì và chọn việc kế tiếp. Không đọc giá trị."""
import difflib
import json
import logging
import re
from dataclasses import dataclass, field as dc_field

from app.channels.handfree.chat.field_review.v2 import coordinator_prompt as prompt
from app.channels.handfree.chat import store
from app.channels.handfree.chat.field_review.v2 import context
from app.channels.handfree.chat.intents import fold
from app.services.llm.client import chat as llm_chat

logger = logging.getLogger(__name__)

DECISIONS = {"chuyen_mon", "di_toi", "xac_nhan", "tu_choi", "khoi_phuc", "bo_qua", "dung", "sang_buoc_sau",
             "lenh_khac", "nhac_lai", "hoi_ro"}
_MAX_QUESTION = 200


@dataclass
class Decision:
    kind: str
    targets: list[tuple[dict, str]] = dc_field(default_factory=list)   # (ô, "tra_loi" | "sua")
    suggest: list[dict] = dc_field(default_factory=list)                # ô công dân nói trước thông tin, chưa hỏi tới
    goal: dict | None = None
    question: str = ""
    reason: str = ""
    named: bool = False        # ba khoá kiểm tra agent tự ghi trước khi quyết định
    correcting: bool = False
    has_value: bool = False


def _pending_block(ctx: context.Context, st: dict) -> str:
    items = ((st.get("confirm") or {}).get("items")) or []
    if not items:
        return ""
    lines = "\n".join(f"{context.code_of(ctx, it.get('key'))} · {it.get('label')} ({it.get('where') or 'Tờ khai'}): "
                      f"{it.get('shown')}" for it in items)
    return prompt.PENDING.format(items=lines)


def _latest_block(ctx: context.Context, st: dict) -> str:
    """Ô lời sửa không nêu tên nhắm tới: ô đang chờ xác nhận, không thì ô điền / sửa gần nhất."""
    pending = ((st.get("confirm") or {}).get("items")) or []
    entry = pending[0] if pending else (st.get("log") or [None])[0]
    if not entry:
        return "(không có)"
    return f"{context.code_of(ctx, entry.get('key'))} · {entry.get('label')} ({entry.get('where') or 'Tờ khai'})"


def messages(ctx: context.Context, st: dict, conv: dict, text: str, vocabulary: str) -> list[dict]:
    user = prompt.USER.format(
        to_khai=context.form_block(ctx),
        o_dang_hoi=context.current_block(ctx, st),
        nhat_ky=context.log_block(ctx, st),
        o_vua_dien=_latest_block(ctx, st),
        dang_lam_ro=context.thread_block(st),
        cho_xac_nhan=_pending_block(ctx, st),
        hoi_thoai=context.dialogue_block(conv, context.DIALOGUE_TURNS),
        lenh=context.COMMANDS,
        tu_vung=vocabulary or "(không có)",
        cau=str(text or "")[:600],
    )
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


def parse(raw: str, ctx: context.Context) -> Decision:
    data = _load(raw)
    if not isinstance(data, dict):
        data = {}
    kind = str(data.get("quyet_dinh") or "").strip()
    question = re.sub(r"\s+", " ", str(data.get("cau_hoi") or "")).strip()[:_MAX_QUESTION]
    decision = Decision(kind if kind in DECISIONS else "hoi_ro", question=question,
                        reason=str(data.get("ly_do") or "")[:200],
                        named=bool(str(data.get("ten_o_duoc_neu") or "").strip()),
                        correcting=data.get("co_loi_sua") is True, has_value=data.get("co_gia_tri") is True)
    if decision.kind in {"chuyen_mon", "bo_qua"}:
        for item in data.get("o") or []:
            if not isinstance(item, dict):
                continue
            target = ctx.by_code.get(str(item.get("ma") or "").strip())
            job = "sua" if str(item.get("viec") or "") == "sua" else "tra_loi"
            if target and all(t[0] is not target for t in decision.targets):
                decision.targets.append((target, job))
    if decision.kind == "chuyen_mon":
        if not decision.targets:
            decision.kind = "hoi_ro"
        chosen = {t[0].get("key") for t in decision.targets}
        for code in data.get("o_goi_y") or []:
            target = ctx.by_code.get(str(code or "").strip())
            # Chỉ gợi ý cho ô còn TRỐNG (ô đã có giá trị mà công dân muốn đổi thì phải là việc "sua").
            if (target and not target.get("value") and target.get("key") not in chosen
                    and all(s is not target for s in decision.suggest)):
                decision.suggest.append(target)
    if decision.kind in {"di_toi", "khoi_phuc"}:
        decision.goal = ctx.by_code.get(str(data.get("toi") or "").strip())
        if not decision.goal:
            decision.kind = "hoi_ro"
    return decision


def _latest_key(st: dict) -> str:
    pending = ((st.get("confirm") or {}).get("items")) or []
    entry = pending[0] if pending else (st.get("log") or [None])[0]
    return (entry or {}).get("key") or ""


def _plain(text: str) -> str:
    return re.sub(r"[^\w\s]", "", fold(text)).strip()


def _last_bot_line(conv: dict) -> str:
    lines = [m["content"] for m in store.recent_dialogue(conv, 4) if m["role"] == "assistant"]
    return lines[-1] if lines else ""


def inconsistency(decision: Decision, ctx: context.Context, st: dict, conv: dict | None = None) -> str:
    """Kiểm quyết định có khớp ba khoá kiểm tra CHÍNH agent ghi không, và không hỏi lại y câu trợ lý vừa hỏi — chỉ
    kiểm, không tự sửa quyết định. Lệch → câu báo để agent quyết lại."""
    if decision.kind in {"hoi_ro", "di_toi"} and decision.question and conv is not None:
        last = _plain(_last_bot_line(conv))
        if last and difflib.SequenceMatcher(None, _plain(decision.question), last).ratio() > 0.85:
            return ("Bạn đang hỏi lại đúng câu trợ lý vừa hỏi, trong khi câu mới chính là câu trả lời cho câu hỏi đó. "
                    "Ghép câu mới với <dang_lam_ro> / <hoi_thoai> để ra việc; chỉ hỏi tiếp điều THỰC SỰ còn thiếu.")
    if decision.kind == "di_toi" and decision.has_value and decision.goal:
        return (f"Bạn ghi câu nói (cùng <dang_lam_ro>) đã có giá trị để điền nhưng lại chọn \"di_toi\" ô "
                f"{decision.goal.get('code')}. Có giá trị và biết ô thì giao \"chuyen_mon\" ô đó, không hỏi lại giá trị.")
    if decision.kind != "chuyen_mon" or decision.named or not decision.has_value:
        return ""
    keys = [t[0].get("key") for t in decision.targets]
    current = (ctx.current or {}).get("key")
    latest = _latest_key(st)
    # Ô đang hỏi có cụm: câu không nêu tên ô được chia vào các ô TRONG cụm; không có cụm thì chỉ ô đó. Ô trống ngoài
    # đó vẫn qua bước công dân xác nhận (một câu ra ≥ 2 ô luôn đọc lại) → chỉ chặn GHI ĐÈ ô đã có giá trị; model hay
    # để trống khoá tên ô dù câu có nêu ("ngày cấp là …"), chặn cả ô trống thì bỏ mất ô công dân nói đúng.
    asked = list((st.get("group") or {}).get("keys") or []) or ([current] if current else [])
    overwrite = [t[0] for t in decision.targets if t[0].get("key") not in asked and t[0].get("value")]
    if not decision.correcting and asked and overwrite:
        where = (f"các ô trong cụm đang hỏi {[context.code_of(ctx, k) for k in asked]}" if len(asked) > 1
                 else f"ô đang hỏi {context.code_of(ctx, current)}")
        return (f"Bạn ghi câu không nêu tên ô và không có lời sửa, nhưng lại giao ô ĐÃ CÓ giá trị "
                f"{[f.get('code') for f in overwrite]} ngoài {where}.")
    if decision.correcting and latest and keys != [latest]:
        return (f"Bạn ghi câu có lời sửa và không nêu tên ô → chỉ giao đúng một ô trong <o_loi_sua_nham_toi> "
                f"({context.code_of(ctx, latest)}), không thêm ô khác.")
    return ""


async def decide(ctx: context.Context, st: dict, conv: dict, text: str, vocabulary: str) -> Decision:
    """Lỗi gọi LLM ném ra ngoài để bên gọi lùi về luồng cũ (vòng hỏi không được chết). Quyết định lệch với chính
    các khoá kiểm tra của agent → hỏi lại agent một lần kèm chỗ lệch."""
    msgs = messages(ctx, st, conv, text, vocabulary)
    raw = await llm_chat(msgs, temperature=0.0, max_tokens=400, purpose="field_review_coordinator")
    decision = parse(raw, ctx)
    problem = inconsistency(decision, ctx, st, conv)
    if problem:
        logger.info("[field_review.v2] điều phối quyết lại: %s", problem)
        retry = [*msgs, {"role": "assistant", "content": raw},
                 {"role": "user", "content": prompt.RECHECK.format(problem=problem)}]
        decision = parse(await llm_chat(retry, temperature=0.0, max_tokens=400, purpose="field_review_coordinator"), ctx)
    logger.info("[field_review.v2] điều phối: %s %s (%s)", decision.kind,
                [(t[0].get("code"), t[1]) for t in decision.targets], decision.reason)
    return decision
