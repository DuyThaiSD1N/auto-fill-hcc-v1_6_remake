"""Cổng Bộ Xây dựng (dvc.moc.gov.vn, iGate: stepper 4 bước + tờ khai Form.io) — phần CHUNG của các thủ tục Bộ.

    (chọn cơ quan DVCQG → hộp thoại "Chọn trường hợp giải quyết": đã tự động ở flow.py)
    1 Thông tin hồ sơ → 2 Thành phần hồ sơ → 3 Hình thức nhận kết quả → 4 Nộp hồ sơ

Mỗi bước có câu hướng dẫn, nút đi tiếp trong khung chat và lệnh nói "bước tiếp theo"; công dân tự bấm trên trang cũng
được (watcher báo wizardStep qua page_status, trợ lý dẫn tiếp từ bước mới). Phần chung vẫn đi đường cũ của flow.py:
nhận giấy tờ, điền, đính kèm, nhận nộp thành công. File này chỉ thêm: nút / lệnh nói chuyển bước, câu chặn khi cổng
không cho qua, chọn hình thức nhận kết quả (registry bxdFlow.resultGroups, thẻ dùng chung với cổng liên thông) và nút
nộp (= bấm "Nộp hồ sơ" của cổng sau khi soát ô cam đoan + mã xác nhận). Thẻ tiến trình là thẻ 2 chặng của tu_phap_v2
(chỉ khi đang xử lý). Phần riêng từng thủ tục (mapper, ô bắt buộc) nằm ở app/pipelines/<thủ tục>/.

Bật khi thủ tục khai `bxdFlow` và extension khai supportsBxdFlow; chế độ Mông giữ luồng cũ (câu chỉ có bản tiếng
Việt). flow.py chỉ gọi các hàm ở đây; mỗi hàm tự trả lại reply cũ khi luồng không bật.
"""
import re

from app.channels.handfree.chat import field_review
from app.channels.handfree.chat import lien_thong
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import tu_phap_v2
from app.channels.handfree.chat.intents import Intent, asks_next_step, asks_submit
from app.channels.handfree.chat.tu_phap_moi import fill_result

CAPABILITY = field_review.BXD_CAPABILITY
DECLARATION, ATTACHMENT, RESULT, DONE = 1, 2, 3, 4
SUBMIT_SEND = "__action:bxd_submit"
_COMMANDS = {"bxd_next", "bxd_step_report", "bxd_result_report", "bxd_result_pick", "bxd_submit",
             "bxd_submit_report"}


def is_active(proc: dict | None) -> bool:
    return field_review.bxd(proc)


def enabled(conv: dict, proc: dict | None) -> bool:
    caps = conv.get("client_capabilities") or {}
    return is_active(proc) and caps.get(CAPABILITY) is True and (conv.get("lang") or "vi") != "hmong"


def _st(conv: dict) -> dict:
    return conv.setdefault("bxd", {})


def _say(tpl: dict, **kw) -> tuple[str, str]:
    return tpl["md"].format(**kw), tpl["tts"].format(**kw)


def _clean(value, limit: int = 200) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _reply(md_tts: tuple[str, str] = ("", "")):
    from app.channels.handfree.chat.flow import Reply

    return Reply(*md_tts)


def _page_step(payload: dict | None) -> int:
    try:
        step = int((payload or {}).get("wizardStep") or 0)
    except (TypeError, ValueError):
        return 0
    return step if DECLARATION <= step <= DONE else 0


def _next_chip(step: int) -> dict:
    label = vi.BXD_RESULT_CHIP if step == ATTACHMENT else vi.BXD_ATTACH_CHIP
    return {"label": label, "send": "__action:bxd_next", "solid": True, "cta": True}


def _submit_chip() -> dict:
    return {"label": vi.BXD_SUBMIT_CHIP, "send": SUBMIT_SEND, "solid": True, "cta": True}


def _result_groups(proc: dict | None) -> list[dict]:
    groups = ((proc or {}).get("bxdFlow") or {}).get("resultGroups") or []
    return [dict(g) for g in groups if isinstance(g, dict) and g.get("name")]


# ── Bước 1: thông tin hồ sơ ──

def fill_report_reply(conv: dict, proc: dict | None, rep: dict, review):
    """Khung kết quả điền + khung kết luận: còn ô đỏ → Bổ sung; đủ → nút "Sang Thành phần hồ sơ" to. None = luồng cũ."""
    from app.channels.handfree.chat.flow import _supplement_documents_chip

    if not enabled(conv, proc):
        return None
    _st(conv)["at"] = DECLARATION
    small = [{"label": "🔁 Điền lại thông tin", "send": "__action:refill"}, _supplement_documents_chip()]
    reviewing = field_review.flow_v2(conv, proc) and isinstance(review, dict)
    stats = field_review.begin(conv, review) if reviewing else {"filled": rep["filled"]}
    r = _reply(fill_result(conv, rep, stats))
    if reviewing:
        md, tts, chips = field_review.conclusion(conv, proc, small)
    else:
        md, tts = _say(vi.BXD_FILL_NEXT)
        chips = [_next_chip(DECLARATION), *small]
    r.actions = [tu_phap_v2._card(conv, "fill", vi.FLOW2_FILL_STEPS, active=2, done=True),
                 {"type": "trail_message", "md": md}]
    r.tts_text += tts if tts.startswith(" ") else f" {tts}"
    r.chips = chips
    return r


# ── Chuyển bước ──

def _current(conv: dict, page_context: dict | None = None) -> int:
    return _page_step(page_context) or int(_st(conv).get("at") or 0)


def next_reply(conv: dict, proc: dict | None, *, voice: bool = False, confirmed: bool = False):
    """Nút / lệnh nói đi tiếp ở bước hiện tại. Bước nhận kết quả: đi tiếp = nộp hồ sơ (nói thì hỏi xác nhận)."""
    step = _current(conv)
    if step == RESULT:
        return _submit_reply(conv, voice=voice, confirmed=confirmed)
    if step not in (DECLARATION, ATTACHMENT):
        return _reply()
    target = step + 1
    r = _reply(_say(vi.BXD_MOVING, step=vi.BXD_STEP_NAMES[target]))
    action = {"type": "bxd_next", "expect": target}
    if step == DECLARATION:
        # Cổng chặn khi còn ô bắt buộc trống (Form.io báo lỗi dưới từng ô) → extension tô lại theo quy tắc ô.
        rules = field_review.fill_action_extra(conv, proc)
        if rules:
            action["fieldReview"] = rules
    r.actions = [action]
    return r


def _step_report(conv: dict, proc: dict | None, payload: dict):
    expect = _page_step({"wizardStep": payload.get("expect")})
    if payload.get("ok") and expect:
        # Đã sang bước mới: nói luôn câu của bước đó; page_status cùng bước tới sau thì im.
        arrived = _arrive(conv, proc, expect)
        return arrived if arrived is not None else _reply()
    message = _clean(payload.get("message"))
    note = f": *{message}*" if message else ""
    if expect == ATTACHMENT and isinstance(payload.get("stats"), dict):
        stats = field_review.update_stats(conv, payload["stats"])
        if stats["required"]:
            r = _reply(_say(vi.BXD_BLOCKED_FORM, required=stats["required"], message=note))
            r.chips = [field_review._start_chip(), {**_next_chip(DECLARATION), "solid": False, "cta": False}]
            return r
    r = _reply(_say(vi.BXD_BLOCKED, step=vi.BXD_STEP_NAMES.get(expect, ""), message=note))
    r.chips = [{"label": vi.BXD_RETRY_CHIP, "send": "__action:bxd_next", "solid": True}]
    return r


def _arrive(conv: dict, proc: dict | None, step: int):
    """Trang vừa sang bước `step` (trợ lý bấm hoặc công dân tự bấm). None = để flow cũ xử lý bước đó (nhận giấy tờ
    ở Thông tin hồ sơ lần đầu, đính kèm ở Thành phần hồ sơ, nhận nộp thành công)."""
    st = _st(conv)
    before = int(st.get("at") or 0)
    st["at"] = step
    if step == DECLARATION and before > DECLARATION:
        r = _reply(_say(vi.BXD_BACK_TO_FORM))
        empty = ((conv.get("field_review") or {}).get("stats") or {}).get("empty")
        r.chips = [_next_chip(DECLARATION), *([{**field_review._start_chip(), "solid": False}] if empty else [])]
        return r
    if step == RESULT:
        r = _reply(_say(vi.BXD_RESULT_READING))
        r.actions = [{"type": "bxd_result_scan", "groups": _result_groups(proc)}]
        return r
    return None


def _on_page(conv: dict, proc: dict | None, payload: dict):
    step = _page_step(payload)
    if not step or step == int(_st(conv).get("at") or 0):
        return None
    return _arrive(conv, proc, step)


# ── Bước 2: đính kèm xong ──

def attach_done_reply(conv: dict, proc: dict | None, reply, *, attached: int, skipped: int, errors: list[str],
                      split: bool):
    """Đính kèm xong: thay lời "tự bấm nộp" bằng nút sang bước hình thức nhận kết quả (+ lệnh nói)."""
    from app.channels.handfree.chat import flow

    if not enabled(conv, proc):
        return reply
    card = tu_phap_v2._card(conv, "attach", vi.FLOW2_ATTACH_STEPS, active=1, done=not errors, failed=bool(errors))
    if split or errors:
        reply.actions = [*reply.actions, card]
        reply.chips = [*[c for c in reply.chips if not c.get("cta")], _next_chip(ATTACHMENT)]
        return reply
    if attached == 0 and skipped > 0:
        r = flow.Reply(*_say(vi.FLOW2_ATTACH_ALL_EXIST))
    else:
        plan_list = "\n".join(flow._attachment_plan_line(p) for p in (conv.get("attach_plan") or [])[:10])
        r = flow.Reply(*_say(vi.FLOW2_ATTACH_RESULT, attached=attached, plan_list=plan_list))
    md, tts = _say(vi.BXD_ATTACH_NEXT)
    r.actions = [*reply.actions, card, {"type": "trail_message", "md": md}]
    r.tts_text += tts
    r.chips = [flow._supplement_documents_chip(), _next_chip(ATTACHMENT)]
    return r


# ── Bước 3: hình thức nhận kết quả ──

def _result_report(conv: dict, proc: dict | None, payload: dict):
    rows = lien_thong.result_rows(_result_groups(proc), payload.get("groups"))
    _st(conv)["result_rows"] = rows
    if not rows:
        r = _reply(_say(vi.LT_RESULT_UNREAD))
        r.chips = [_submit_chip()]
        return r
    changed = payload.get("changed") if isinstance(payload.get("changed"), dict) else None
    card = lien_thong.result_card(rows, "bxd_result_pick")
    if changed:
        label = next((row["label"] for row in rows if row["name"] == changed.get("name")), "")
        value = _clean(changed.get("value"), 80)
        if changed.get("ok"):
            md, tts = _say(vi.LT_RESULT_CHANGED, label=label, value=value)
            fields = ", ".join(_clean(x, 60) for x in payload.get("missing") or [] if _clean(x, 60))[:200]
            if fields:
                hint_md, hint_tts = _say(vi.LT_RESULT_FILL_HINT, label=label, fields=fields)
                md, tts = md + hint_md, tts + hint_tts
        else:
            md, tts = _say(vi.LT_RESULT_FAILED, label=label, value=value)
        r = _reply((md, tts))
        r.cards = [card]
        r.chips = [_submit_chip()]
        return r
    r = _reply(lien_thong.result_summary(rows))
    guide_md, guide_tts = _say(vi.BXD_SUBMIT_GUIDE)
    r.cards = [card]
    r.actions = [{"type": "trail_message", "md": guide_md}]
    r.tts_text += guide_tts
    r.chips = [_submit_chip()]
    return r


def _result_pick(conv: dict, proc: dict | None, payload: dict):
    name, value = str(payload.get("name") or ""), str(payload.get("value") or "")
    row = next((row for row in _st(conv).get("result_rows") or [] if row["name"] == name), None)
    if not row or value not in row["options"]:
        return _reply()
    r = _reply()
    r.actions = [{"type": "bxd_result_set", "name": name, "value": value, "groups": _result_groups(proc)}]
    return r


# ── Bước 3 → 4: nộp ──

def _submit_reply(conv: dict, *, voice: bool = False, confirmed: bool = False):
    from app.channels.handfree.chat import flow

    if voice and not confirmed:
        return flow._voice_submit_confirm(conv, SUBMIT_SEND)
    r = _reply(_say(vi.BXD_SUBMITTING))
    r.actions = [{"type": "bxd_submit"}]
    return r


def _submit_report(payload: dict):
    missing = [str(x) for x in payload.get("missing") or [] if x in {"camDoan", "captcha"}]
    if missing:
        names = {"camDoan": vi.BXD_MISSING_CAM_DOAN, "captcha": vi.BXD_MISSING_CAPTCHA}
        r = _reply(_say(vi.BXD_SUBMIT_MISSING, missing=" và ".join(names[x] for x in missing)))
        r.chips = [_submit_chip()]
        return r
    message = _clean(payload.get("message"))
    if payload.get("clicked") and not message:
        return _reply()  # cổng sang màn nộp thành công → watcher báo submitted như mọi lần nộp
    r = _reply(_say(vi.BXD_SUBMIT_FAILED, message=f": *{message}*" if message else ""))
    r.chips = [_submit_chip()]
    return r


# ── Điều phối ──

def handle(conv: dict, proc: dict | None, intent):
    """Lệnh / sự kiện của luồng Bộ Xây dựng → Reply; không phải → None (flow cũ xử lý)."""
    if not enabled(conv, proc):
        return None
    payload = intent.payload if isinstance(intent.payload, dict) else {}
    if intent.kind == "event" and intent.value == "page_status":
        return _on_page(conv, proc, payload)
    if intent.kind != "action" or intent.value not in _COMMANDS:
        return None
    if intent.value == "bxd_next":
        return next_reply(conv, proc, voice=bool(payload.get("voice")),
                          confirmed=bool(payload.get("voiceConfirmed")))
    if intent.value == "bxd_step_report":
        return _step_report(conv, proc, payload)
    if intent.value == "bxd_result_report":
        return _result_report(conv, proc, payload)
    if intent.value == "bxd_result_pick":
        return _result_pick(conv, proc, payload)
    if intent.value == "bxd_submit":
        return _submit_reply(conv)
    return _submit_report(payload)


def voice_intent(conv: dict, message: str, page_context: dict | None) -> Intent | None:
    """Câu nói "bước tiếp theo" (bước nhận kết quả: cả "nộp hồ sơ") → lệnh đi tiếp tất định, không qua LLM."""
    from app.channels.handfree.procedure_registry import get_procedure

    proc = get_procedure(conv.get("procedure_key") or "")
    if not enabled(conv, proc):
        return None
    step = _current(conv, page_context)
    # Thông tin hồ sơ: chỉ sau khi đã điền (trước đó "tiếp theo" là chuyện giấy tờ của flow cũ).
    if not step or step >= DONE or (step == DECLARATION and conv.get("state") not in {"reviewing", "attaching"}):
        return None
    if asks_next_step(message) or (step == RESULT and asks_submit(message)):
        return Intent("action", "bxd_next", {"voice": True})
    return None
