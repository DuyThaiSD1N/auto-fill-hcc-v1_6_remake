"""Cổng liên thông (lienthong.dichvucong.gov.vn, form Angular) — dẫn đủ 6 bước của cổng.

    1 Chọn cơ quan thực hiện → 2 Kê khai → 3 Xem lại các tờ khai chi tiết → 4 Đính kèm thành phần hồ sơ
    → 5 Lựa chọn hình thức nhận kết quả → 6 Hoàn thành

Mỗi bước có câu hướng dẫn, nút đi tiếp trong khung chat và lệnh nói "bước tiếp theo"; công dân tự bấm trên trang
cũng được (watcher báo `lienThongStep` qua page_status, trợ lý dẫn tiếp từ bước mới). Thẻ tiến trình chỉ có ở chặng
hệ thống đang xử lý (tu_phap_v2: bóc tách → điền; xếp giấy tờ → đính kèm) — bước chờ công dân không có vòng xoay.

Phần chung vẫn đi đường cũ của flow.py: chọn cơ quan (agencyFillPlan), nhận giấy tờ, điền, đính kèm, nhận nộp
thành công. File này chỉ thêm: nút / lệnh nói chuyển bước, câu bước Xem lại, chọn cách nhận kết quả
theo TỪNG giấy tờ (registry lienThongFlow.resultGroups) và nút nộp (= bấm "Hoàn thành").

Bật khi thủ tục khai `lienThongFlow` và extension khai supportsLienThongFlow; chế độ Mông giữ luồng cũ (câu chỉ có
bản tiếng Việt). flow.py chỉ gọi các hàm ở đây; mỗi hàm tự trả lại reply cũ khi luồng không bật.
"""
import json
import re

from app.channels.handfree.chat import field_review
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import tu_phap_v2
from app.channels.handfree.chat.intents import Intent, asks_next_step, asks_submit
from app.channels.handfree.chat.tu_phap_moi import fill_result

CAPABILITY = field_review.LIEN_THONG_CAPABILITY
AGENCY, DECLARATION, REVIEW, ATTACHMENT, RESULT, DONE = 1, 2, 3, 4, 5, 6
SUBMIT_SEND = "__action:lt_submit"
_COMMANDS = {"lt_next", "lt_back", "lt_step_report", "lt_result_report", "lt_result_pick", "lt_submit",
             "lt_submit_report"}
_MAX_TEXT = 160
_MAX_OPTIONS = 8


def is_active(proc: dict | None) -> bool:
    return field_review.lien_thong(proc)


def enabled(conv: dict, proc: dict | None) -> bool:
    caps = conv.get("client_capabilities") or {}
    return is_active(proc) and caps.get(CAPABILITY) is True and (conv.get("lang") or "vi") != "hmong"


def _st(conv: dict) -> dict:
    return conv.setdefault("lien_thong", {})


def _say(tpl: dict, **kw) -> tuple[str, str]:
    return tpl["md"].format(**kw), tpl["tts"].format(**kw)


def _clean(value, limit: int = _MAX_TEXT) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _page_step(payload: dict | None) -> int:
    try:
        step = int((payload or {}).get("lienThongStep") or 0)
    except (TypeError, ValueError):
        return 0
    return step if AGENCY <= step <= DONE else 0


def _reply(md_tts: tuple[str, str] = ("", "")):
    from app.channels.handfree.chat.flow import Reply

    return Reply(*md_tts)


def _next_chip(step: int) -> dict:
    """Nút đi tiếp của bước `step` (to, nổi bật)."""
    label = {AGENCY: vi.LT_AGENCY_CHIP, DECLARATION: vi.LT_REVIEW_CHIP, REVIEW: vi.LT_ATTACH_CHIP,
             ATTACHMENT: vi.LT_RESULT_CHIP}.get(step, vi.LT_REVIEW_CHIP)
    return {"label": label, "send": "__action:lt_next", "solid": True, "cta": True}


def _submit_chip() -> dict:
    return {"label": vi.LT_SUBMIT_CHIP, "send": SUBMIT_SEND, "solid": True, "cta": True}


def _result_groups(proc: dict | None) -> list[dict]:
    groups = ((proc or {}).get("lienThongFlow") or {}).get("resultGroups") or []
    return [dict(g) for g in groups if isinstance(g, dict) and g.get("name")]


# ── Bước 1: chọn cơ quan ──

def agency_reply(conv: dict, proc: dict | None, reply):
    """Trợ lý vừa điền khối chọn cơ quan: câu có nút sang Kê khai (bước chờ công dân → không thẻ tiến trình)."""
    if not enabled(conv, proc) or not reply.actions:
        return reply
    loc = conv.get("location") or {}
    r = _reply(_say(vi.LT_AGENCY_FILLING, ward=loc.get("ward") or "", province=loc.get("province") or ""))
    r.actions = list(reply.actions)
    r.chips = [_next_chip(AGENCY)]
    _st(conv)["at"] = AGENCY
    return r


# ── Bước 2: kê khai ──

def fill_report_reply(conv: dict, proc: dict | None, rep: dict, review):
    """Khung kết quả điền + khung kết luận: còn ô đỏ → Bổ sung; đủ → nút "Xem lại tờ khai" to. None = luồng cũ."""
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
        md, tts = _say(vi.LT_FILL_NEXT)
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
    if not step or step >= RESULT:
        return _reply()
    target = step + 1
    r = _reply(_say(vi.LT_MOVING, step=vi.LT_STEP_NAMES.get(target, "")))
    action = {"type": "lien_thong_next", "expect": target}
    if step == DECLARATION:
        # Cổng chặn khi còn ô bắt buộc trống (tô vàng các ô đó) → extension tô lại theo quy tắc ô của thủ tục.
        rules = field_review.fill_action_extra(conv, proc)
        if rules:
            action["fieldReview"] = rules
    r.actions = [action]
    return r


def _back_reply():
    r = _reply(_say(vi.LT_MOVING_BACK))
    r.actions = [{"type": "lien_thong_next", "expect": DECLARATION, "back": True}]
    return r


def _step_report(conv: dict, proc: dict | None, payload: dict):
    expect = _page_step({"lienThongStep": payload.get("expect")})
    if payload.get("ok") and expect:
        # Đã sang bước mới: nói luôn câu của bước đó; page_status cùng bước tới sau thì im.
        arrived = _arrive(conv, proc, expect)
        return arrived if arrived is not None else _reply()
    message = _clean(payload.get("message"), 200)
    note = f": *{message}*" if message else ""
    back = bool(payload.get("back"))
    if not back and expect == REVIEW and isinstance(payload.get("stats"), dict):
        stats = field_review.update_stats(conv, payload["stats"])
        if stats["required"]:
            r = _reply(_say(vi.LT_BLOCKED_FORM, required=stats["required"], message=note))
            r.chips = [field_review._start_chip(), {**_next_chip(DECLARATION), "solid": False, "cta": False}]
            return r
    name = vi.LT_STEP_NAMES.get(expect, "")
    r = _reply(_say(vi.LT_BLOCKED, step=name, message=note))
    r.chips = [{"label": vi.LT_RETRY_CHIP, "send": "__action:lt_back" if back else "__action:lt_next",
                "solid": True}]
    return r


def _arrive(conv: dict, proc: dict | None, step: int):
    """Trang vừa sang bước `step` (trợ lý bấm hoặc công dân tự bấm). None = để flow cũ xử lý bước đó."""
    st = _st(conv)
    before = int(st.get("at") or 0)
    st["at"] = step
    if step == REVIEW:
        r = _reply(_say(vi.LT_REVIEW_STEP))
        r.chips = [_next_chip(REVIEW), {"label": vi.LT_BACK_CHIP, "send": "__action:lt_back"}]
        return r
    if step == DECLARATION and before > DECLARATION:
        r = _reply(_say(vi.LT_BACK_TO_FORM))
        empty = ((conv.get("field_review") or {}).get("stats") or {}).get("empty")
        r.chips = [_next_chip(DECLARATION), *([field_review._start_chip()] if empty else [])]
        if empty:
            r.chips[1]["solid"] = False
        return r
    if step == RESULT:
        r = _reply(_say(vi.LT_RESULT_READING))
        r.actions = [{"type": "lien_thong_result_scan", "groups": _result_groups(proc)}]
        return r
    return None


def _on_page(conv: dict, proc: dict | None, payload: dict):
    step = _page_step(payload)
    if not step or step == int(_st(conv).get("at") or 0):
        return None
    return _arrive(conv, proc, step)


# ── Bước 4: đính kèm xong ──

def attach_done_reply(conv: dict, proc: dict | None, reply, *, attached: int, skipped: int, errors: list[str],
                      split: bool):
    """Đính kèm xong: thay lời "tự bấm nộp" bằng nút sang bước nhận kết quả (+ lệnh nói)."""
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
    md, tts = _say(vi.LT_ATTACH_NEXT)
    r.actions = [*reply.actions, card, {"type": "trail_message", "md": md}]
    r.tts_text += tts
    r.chips = [flow._supplement_documents_chip(), _next_chip(ATTACHMENT)]
    return r


# ── Bước 5: cách nhận kết quả từng giấy tờ ──

# Thẻ "cách nhận kết quả" (card lt_result_groups) dùng chung với luồng Bộ Xây dựng (chat/bxd): mỗi ô chọn một dòng.

def _pick_send(action: str, name: str, value: str) -> str:
    return f"__action:{action}:" + json.dumps({"name": name, "value": value}, ensure_ascii=False)


def result_rows(configs: list[dict], groups) -> list[dict]:
    """Dòng của thẻ chọn cách nhận: theo thứ tự registry, chỉ ô có trên trang; ô khoá / không có lựa chọn = cố định."""
    read = {str(g.get("name")): g for g in groups or [] if isinstance(g, dict)}
    rows = []
    for cfg in configs:
        got = read.get(cfg["name"])
        if not got or got.get("present") is False:
            continue
        options = [_clean(o, 80) for o in got.get("options") or [] if _clean(o, 80)][:_MAX_OPTIONS]
        fixed = bool(got.get("fixed")) or not options
        rows.append({"name": cfg["name"], "label": str(cfg.get("label") or cfg["name"]),
                     "value": _clean(got.get("value"), 80), "place": _clean(got.get("place"), 120),
                     "fixed": fixed, "options": [] if fixed else options})
    return rows


def result_card(rows: list[dict], action: str = "lt_result_pick") -> dict:
    return {"kind": "lt_result_groups", "rows": [
        {**row, "options": [{"label": o, "send": _pick_send(action, row["name"], o), "selected": o == row["value"]}
                            for o in row["options"]]}
        for row in rows]}


def result_summary(rows: list[dict]) -> tuple[str, str]:
    if len(rows) == 1:
        row = rows[0]
        place = vi.LT_RESULT_PLACE.format(place=row["place"]) if row["place"] else ""
        return _say(vi.LT_RESULT_SUMMARY_ONE, value=row["value"] or vi.LT_RESULT_EMPTY,
                    place=place + (vi.LT_RESULT_FIXED if row["fixed"] else ""))
    lines_md, lines_tts = [], []
    for row in rows:
        value = row["value"] or vi.LT_RESULT_EMPTY
        place = vi.LT_RESULT_PLACE.format(place=row["place"]) if row["place"] else ""
        lines_md.append(vi.LT_RESULT_LINE.format(label=row["label"], value=value, place=place)
                        + (vi.LT_RESULT_FIXED if row["fixed"] else ""))
        lines_tts.append(f"{row['label']}: {value}")
    return _say(vi.LT_RESULT_SUMMARY, lines_md="\n".join(lines_md), lines_tts="; ".join(lines_tts))


def _result_report(conv: dict, proc: dict | None, payload: dict):
    rows = result_rows(_result_groups(proc), payload.get("groups"))
    _st(conv)["result_rows"] = rows
    if not rows:
        r = _reply(_say(vi.LT_RESULT_UNREAD))
        r.chips = [_submit_chip()]
        return r
    changed = payload.get("changed") if isinstance(payload.get("changed"), dict) else None
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
        r.cards = [result_card(rows)]
        r.chips = [_submit_chip()]
        return r
    r = _reply(result_summary(rows))
    guide_md, guide_tts = _say(vi.LT_SUBMIT_GUIDE)
    r.cards = [result_card(rows)]
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
    r.actions = [{"type": "lien_thong_result_set", "name": name, "value": value, "groups": _result_groups(proc)}]
    return r


# ── Bước 5 → 6: nộp ──

def _submit_reply(conv: dict, *, voice: bool = False, confirmed: bool = False):
    from app.channels.handfree.chat import flow

    if voice and not confirmed:
        return flow._voice_submit_confirm(conv, SUBMIT_SEND)
    r = _reply(_say(vi.LT_SUBMITTING))
    r.actions = [{"type": "lien_thong_submit"}]
    return r


def _submit_report(payload: dict):
    missing = [str(x) for x in payload.get("missing") or [] if x in {"camDoan", "captcha"}]
    if missing:
        names = {"camDoan": vi.LT_MISSING_CAM_DOAN, "captcha": vi.LT_MISSING_CAPTCHA}
        r = _reply(_say(vi.LT_SUBMIT_MISSING, missing=" và ".join(names[x] for x in missing)))
        r.chips = [_submit_chip()]
        return r
    message = _clean(payload.get("message"), 200)
    if payload.get("clicked") and not message:
        return _reply()  # cổng sang màn nộp thành công → watcher báo submitted như mọi lần nộp
    r = _reply(_say(vi.LT_SUBMIT_FAILED, message=f": *{message}*" if message else ""))
    r.chips = [_submit_chip()]
    return r


# ── Điều phối ──

def handle(conv: dict, proc: dict | None, intent):
    """Lệnh / sự kiện của luồng liên thông → Reply; không phải → None (flow cũ xử lý)."""
    if not enabled(conv, proc):
        return None
    payload = intent.payload if isinstance(intent.payload, dict) else {}
    if intent.kind == "event" and intent.value == "page_status":
        return _on_page(conv, proc, payload)
    if intent.kind != "action" or intent.value not in _COMMANDS:
        return None
    if intent.value == "lt_next":
        return next_reply(conv, proc, voice=bool(payload.get("voice")),
                          confirmed=bool(payload.get("voiceConfirmed")))
    if intent.value == "lt_back":
        return _back_reply()
    if intent.value == "lt_step_report":
        return _step_report(conv, proc, payload)
    if intent.value == "lt_result_report":
        return _result_report(conv, proc, payload)
    if intent.value == "lt_result_pick":
        return _result_pick(conv, proc, payload)
    if intent.value == "lt_submit":
        return _submit_reply(conv)
    return _submit_report(payload)


def voice_intent(conv: dict, message: str, page_context: dict | None) -> Intent | None:
    """Câu nói "bước tiếp theo" (bước nhận kết quả: cả "nộp hồ sơ") → lệnh đi tiếp tất định, không qua LLM."""
    from app.channels.handfree.procedure_registry import get_procedure

    proc = get_procedure(conv.get("procedure_key") or "")
    if not enabled(conv, proc):
        return None
    step = _current(conv, page_context)
    # Kê khai: chỉ sau khi đã điền (trước đó "tiếp theo" là chuyện giấy tờ của flow cũ).
    if not step or (step == DECLARATION and conv.get("state") not in {"reviewing", "attaching"}):
        return None
    if step >= DONE:
        return None
    if asks_next_step(message) or (step == RESULT and asks_submit(message)):
        return Intent("action", "lt_next", {"voice": True})
    return None
