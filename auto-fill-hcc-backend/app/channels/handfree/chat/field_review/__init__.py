"""Bổ sung ô còn trống ngay trên tờ khai eForm sau khi điền.

Điền xong, extension tô từng ô: có giá trị → xanh, trống không bắt buộc → cam, trống bắt buộc → đỏ, rồi
báo số ô kèm báo cáo điền. Còn ô trống thì có nút "Bổ sung các thông tin còn thiếu": trợ lý đi lần lượt
từng ô trống từ trên xuống (con trỏ tới ô, hỏi), công dân nói/gõ, LLM hiểu câu trả lời, extension điền
đúng ô đó rồi tìm ô kế tiếp.

    fill_report(review) → [Bổ sung…] → field_review_next → __event:field_review_focus{field}
        → hỏi → câu trả lời → field_review_next{apply} → __event:field_review_focus{applied, field} → …

Bật khi thủ tục có app/pipelines/<tên>/handfree/field_review.py (xem registry.py) VÀ extension khai cờ
supportsFieldReview.
Chế độ tiếng Mông giữ luồng cũ: nhãn ô lấy nguyên văn tiếng Việt trên tờ khai.
"""
import json
import re

from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.field_review import agent, registry
from app.channels.handfree.chat.intents import fold

CAPABILITY = "supportsFieldReview"
_COMMANDS = {"field_review_start", "field_review_skip", "field_review_stop", "field_review_back",
             "field_review_answer", "field_review_pick", "field_review_reload", "field_review_owner_next",
             "field_review_preview", "field_review_preview_report", "field_review_preview_close",
             "field_review_confirm", "field_review_confirm_report"}
# Đang ở Kê khai mà công dân nói "xong rồi / xem trước / đính kèm đi" → bước kế tiếp là Xem trước → Xác nhận
# trên cổng (không có lệnh nào khác đưa được sang Thành phần hồ sơ).
_NEXT_STEP_INTENTS = {("action", "confirm_review"), ("action", "request_attach")}
# Pha riêng cho cú bấm "Bước tiếp theo" ở bước chủ hồ sơ (dùng lại engine guided_click_next của extension)
# để báo cáo quay về đây, không lẫn với luồng dẫn từng bước (guided_steps) của thủ tục khác.
OWNER_PHASE = "field_review_owner"
_FEW_CHOICES = 6  # ô có tới chừng này lựa chọn thì đọc hết lựa chọn trong câu hỏi + hiện nút chọn
_MAX_OPTIONS = 400
_MAX_TEXT = 160


def config(proc: dict | None) -> dict | None:
    return registry.get((proc or {}).get("key"))


def active(conv: dict, proc: dict | None) -> bool:
    return (
        config(proc) is not None
        and (conv.get("client_capabilities") or {}).get(CAPABILITY) is True
        and (conv.get("lang") or "vi") != "hmong"
    )


def asking(conv: dict) -> bool:
    return bool((conv.get("field_review") or {}).get("current"))


def _required(proc: dict | None) -> list[str]:
    return [str(name) for name in (config(proc) or {}).get("required") or [] if str(name).strip()]


def _no_section(proc: dict | None) -> set[str]:
    return {str(name) for name in (config(proc) or {}).get("noSection") or []}


def fill_action_extra(conv: dict, proc: dict | None) -> dict | None:
    """Kèm vào action fill_fields: extension tô 3 màu và đếm ô sau khi điền."""
    if not active(conv, proc):
        return None
    return {"required": _required(proc)}


def _say(tpl: dict, **kw) -> tuple[str, str]:
    return tpl["md"].format(**kw), tpl["tts"].format(**kw)


def _count(value) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _stats(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    stats = {key: _count(raw.get(key)) for key in ("filled", "optional", "required")}
    stats["empty"] = stats["optional"] + stats["required"]
    return stats


def _start_chip() -> dict:
    return {"label": vi.FR_CHIP, "send": "__action:field_review_start", "solid": True}


def _preview_chip() -> dict:
    return {"label": vi.FR_PREVIEW_CHIP, "send": "__action:field_review_preview", "solid": True}


def reviewing_fill(conv: dict, proc: dict | None, review) -> bool:
    """Báo cáo điền này đi theo vòng bổ sung (extension mới đã tô 3 màu và đếm ô)."""
    return active(conv, proc) and isinstance(review, dict)


def fill_ready_reply(count: int):
    """Câu khi dữ liệu điền về: màu ô là xanh / cam / đỏ nên không đọc "ô vàng" như FILL_READY."""
    from app.channels.handfree.chat.flow import Reply

    return Reply(*_say(vi.FR_FILL_READY, count=count))


def decorate_fill_report(conv: dict, proc: dict | None, reply, review, tail: dict | None = None) -> None:
    """Báo cáo điền tách bong bóng: kết quả điền (câu của flow) → số ô xanh/cam/đỏ + nút "Bổ sung…" → bước tiếp
    theo. Lượt điền mới = vòng bổ sung mới."""
    if not reviewing_fill(conv, proc, review):
        return
    stats = _stats(review)
    conv["field_review"] = {"chips": [dict(c) for c in reply.chips], "stats": stats}
    trails = [_say(vi.FR_FILL_STATS, **stats)] if stats["empty"] else []
    if tail:
        trails.append((tail["md"].strip(), tail["tts"]))
    reply.actions = [*reply.actions, *({"type": "trail_message", "md": md} for md, _ in trails)]
    reply.tts_text += "".join(tts for _, tts in trails)
    reply.chips = [*([_start_chip()] if stats["empty"] else []), _preview_chip(), *reply.chips]


def _clean(text, limit: int = _MAX_TEXT) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()[:limit]


def _tts(text: str) -> str:
    """Nhãn đọc lên: bỏ dấu phẩy (TTS ngắt vụn "Ngày, tháng, năm sinh") và đọc "/" là "hoặc"."""
    text = str(text or "").replace("/", " hoặc ").replace(",", " ")
    return re.sub(r"\s+", " ", text).strip()


_PROVINCE_OPTION = re.compile(r"^(tinh|thanh pho)\s")
_WARD_OPTION = re.compile(r"^(phuong|xa|dac khu|thi tran)\s")


def _unit_suffix(label: str, options: list[str]) -> str:
    """Hai ô chọn liền nhau chung một nhãn (vd "Cơ quan đăng ký hộ tịch trước đây": ô tỉnh rồi ô xã) → nêu cấp
    theo chính danh sách lựa chọn để công dân không tưởng máy hỏi lặp."""
    folded = fold(label)
    if not options or any(w in folded for w in ("tinh", "thanh pho", "xa", "phuong")):
        return ""
    for pattern, suffix in ((_PROVINCE_OPTION, " (tỉnh hoặc thành phố)"), (_WARD_OPTION, " (xã hoặc phường)")):
        if sum(bool(pattern.match(fold(o))) for o in options) >= 0.8 * len(options):
            return suffix
    return ""


def _label(text) -> str:
    # Nhãn tờ khai có số thứ tự "(14)" và dấu ":" cuối — đọc lên chỉ gây rối.
    text = re.sub(r"^\(\s*\d+\s*\)\s*", "", _clean(text))
    return text.rstrip(" :").strip()


def _section(text) -> str:
    text = re.sub(r"^[IVXLC]+\s*[.)]\s*", "", _label(text))
    text = re.sub(r"^Thông tin (về )?", "", text, flags=re.IGNORECASE)
    return text[:1].upper() + text[1:] if text else ""


def _field(raw, no_section: set[str] = frozenset()) -> dict | None:
    if not isinstance(raw, dict) or not _clean(raw.get("key")):
        return None
    options = [_clean(o, 120) for o in (raw.get("options") or []) if _clean(o, 120)][:_MAX_OPTIONS]
    label = _label(raw.get("label")) or _clean(raw.get("name"))
    label += _unit_suffix(label, options)
    # Ô Tỉnh/Xã/Địa chỉ trong khối địa chỉ: nhãn chung chung, phải nêu khối (Nơi sinh, Quê quán…).
    # Tên khối lấy từ nhãn ô Quốc gia đầu khối ("Quốc gia nơi sinh của …") → bỏ chữ "Quốc gia".
    where = ""
    if raw.get("name") in no_section:
        where = None  # ô không thuộc phần nào trên tờ khai: hỏi không kèm tên phần
    elif raw.get("role") in {"tinh", "xa", "diaChi"}:
        where = re.sub(r"^Quốc gia\s+", "", _label(raw.get("group")), flags=re.IGNORECASE)
        where = where[:1].upper() + where[1:]
    return {
        "key": _clean(raw.get("key"), 200),
        "label": label,
        "where": "" if where is None else (where or _section(raw.get("section")) or "Tờ khai"),
        "kind": raw.get("kind") if raw.get("kind") in {"text", "date", "select", "radio"} else "text",
        "required": raw.get("required") is True,
        "year_only": raw.get("kind") == "date" and raw.get("yearOnly") is True,
        "value": _clean(raw.get("value"), 200),
        "options": options,
        # Tỉnh đã có mà cổng không nạp danh sách xã → không hỏi gõ tự do (gõ cũng không chọn được).
        "province": _clean(raw.get("province"), 120) if raw.get("optionsFailed") is True and not options else "",
    }


def _next_action(proc: dict | None, st: dict, apply: dict | None = None, focus: str = "") -> dict:
    action = {"type": "field_review_next", "required": _required(proc), "skip": list(st.get("skip") or [])}
    if apply:
        action["apply"] = apply
    if focus:
        action["focus"] = focus  # quay lại đúng ô này dù ô đã có giá trị (sửa ô vừa điền)
    return action


# Nút lựa chọn = câu trả lời cho ô → nút đặc (màu chính). Nút điều hướng tô theo nghĩa (tone, sidebar tô màu;
# extension cũ không biết khoá này thì bỏ qua): bỏ qua cam như ô trống không bắt buộc, sửa ô trước xanh dương,
# dừng đỏ nhạt, tải lại danh sách xã xanh dương đặc vì là việc chính khi cổng chưa nạp danh sách.
def _choice_chip(option: str) -> dict:
    return {"label": option, "send": "__action:field_review_pick:" + json.dumps({"value": option}, ensure_ascii=False),
            "solid": True}


def _country_field(field: dict) -> bool:
    label = fold(field.get("label") or "")
    return ("quoc gia" in label or "quoc tich" in label) and any(fold(o) == "viet nam" for o in field["options"])


def _chips(st: dict) -> list[dict]:
    field = st.get("current") or {}
    options = field.get("options") or []
    chips = ([{"label": vi.FR_RELOAD_CHIP, "send": "__action:field_review_reload", "tone": "reload"}]
             if field.get("province") else [])
    if 0 < len(options) <= _FEW_CHOICES:
        chips = [_choice_chip(o) for o in options]
    elif options and _country_field(field):
        chips = [_choice_chip(next(o for o in options if fold(o) == "viet nam"))]
    chips.append({"label": vi.FR_SKIP_CHIP, "send": "__action:field_review_skip", "tone": "skip"})
    if st.get("last"):
        chips.append({"label": vi.FR_BACK_CHIP, "send": "__action:field_review_back", "tone": "back"})
    chips.append({"label": vi.FR_STOP_CHIP, "send": "__action:field_review_stop", "tone": "stop"})
    return chips


def _with_lead(r, *leads: tuple[str, str]):
    """Kết quả ô trước (đã điền / bỏ qua / quay lại), lời mở đầu… mỗi thứ MỘT bong bóng riêng phía trên câu chính;
    lời đọc nối liền theo đúng thứ tự."""
    leads = [lead for lead in leads if lead and (lead[0] or lead[1])]
    r.actions = [*({"type": "lead_message", "md": md} for md, _ in leads if md), *r.actions]
    r.tts_text = "".join(tts for _, tts in leads) + r.tts_text
    return r


def _ask_reply(st: dict, lead: tuple[str, str] = ("", ""), back: bool = False):
    from app.channels.handfree.chat.flow import Reply

    field = st["current"]
    first = st.pop("intro", False)
    word = vi.FR_LEAD_FIRST if first else vi.FR_LEAD_NEXT
    current = vi.FR_CURRENT_MD.format(value=field["value"]) if field.get("value") else ""
    options = field.get("options") or []
    head = vi.FR_HEAD_BACK if back else (vi.FR_HEAD if field["where"] else vi.FR_HEAD_NO_PART)
    head_md, head_tts = _say(head, lead=word, where=field["where"], where_tts=_tts(field["where"]),
                             label_tts=_tts(field["label"]))
    kw = dict(badge="🟥 " if field["required"] else "", label=field["label"], current_md=current,
              head_md=head_md, head_tts=head_tts, label_tts=_tts(field["label"]))
    if field.get("province"):
        r = Reply(*_say(vi.FR_ASK_WARDS_FAILED, province=field["province"], province_tts=_tts(field["province"]),
                        **kw))
        _with_lead(r, lead, _say(vi.FR_START) if first else ("", ""))
        r.chips = _chips(st)
        return r
    if 0 < len(options) <= _FEW_CHOICES:
        ask_md, ask_tts = _say(vi.FR_ASK_CHOICES, choices_md=" · ".join(f"**{o}**" for o in options),
                               choices_tts=" hoặc ".join(_tts(o) for o in options), **kw)
    elif options and _country_field(field):
        ask_md, ask_tts = _say(vi.FR_ASK_COUNTRY, **kw)
    else:
        ask_md, ask_tts = _say(vi.FR_ASK, **kw)
    r = Reply(ask_md, ask_tts)
    r.actions = [{"type": "listen_after_tts"}]
    _with_lead(r, lead, _say(vi.FR_START) if first else ("", ""))
    r.chips = _chips(st)
    return r


def _finish_reply(conv: dict, *, stopped: bool, lead: tuple[str, str] = ("", "")):
    from app.channels.handfree.chat.flow import Reply

    st = conv.setdefault("field_review", {})
    st.update(running=False, current=None)
    stats = st.get("stats") or _stats({})
    missing = vi.FR_MISSING_NOTE.format(count=stats["required"]) if stats["required"] else ""
    r = Reply(*_say(vi.FR_STOPPED if stopped else vi.FR_DONE, missing_note=missing))
    r.actions = [{"type": "field_review_stop"}]
    _with_lead(r, lead)
    # Bỏ qua bớt ô → còn ô trống: cho bổ sung lại một vòng mới (danh sách bỏ qua làm lại từ đầu).
    chips = [dict(c) for c in st.get("chips") or []]
    r.chips = [*([_start_chip()] if stats["empty"] else []), _preview_chip(), *chips]
    return r


def _outcome_lead(st: dict, applied) -> tuple[str, str]:
    if st.pop("back_label", ""):
        label = (st.get("last") or {}).get("label") or ""
        return _say(vi.FR_BACK, label=label, label_tts=_tts(label))
    pending = st.pop("pending", None) or {}
    if isinstance(applied, dict) and pending:
        label, where = pending.get("label") or "", pending.get("where") or ""
        if applied.get("ok") is True:
            st["last"] = {"key": pending.get("key"), "label": label}
            return _say(vi.FR_APPLIED if where else vi.FR_APPLIED_NO_PART, label=label, where=where, value=pending.get("value") or "",
                        label_tts=_tts(label), where_tts=_tts(where))
        # Điền hỏng: extension đã tự bỏ ô này khỏi lượt tìm kế tiếp; ghi vào danh sách bỏ qua để các
        # lượt sau cũng không hỏi lại một ô điền không được.
        st.setdefault("skip", []).append(pending.get("key"))
        return _say(vi.FR_APPLY_FAILED, label=label, label_tts=_tts(label))
    skipped = st.pop("skipped_label", "")
    return _say(vi.FR_SKIPPED, label=skipped, label_tts=_tts(skipped)) if skipped else ("", "")


def _skip_current(proc: dict | None, st: dict):
    from app.channels.handfree.chat.flow import Reply

    field = st.get("current") or {}
    st.setdefault("skip", []).append(field.get("key"))
    st["skipped_label"] = field.get("label") or ""
    st["current"] = None
    r = Reply()
    r.actions = [_next_action(proc, st)]
    return r


def _visited_before(st: dict) -> list[dict]:
    """Các ô đã hỏi trong vòng này (điền rồi hoặc đã bỏ qua), trừ ô đang hỏi — đích của "quay lại ô …"."""
    current = (st.get("current") or {}).get("key")
    return [v for v in st.get("visited") or [] if v.get("key") != current]


def _back(proc: dict | None, st: dict, target: int = 0):
    """Quay lại sửa một ô: `target` = số thứ tự trong `_visited_before` (công dân nêu tên ô, kể cả ô đã bỏ
    qua); 0 = ô VỪA điền. Con trỏ về đúng ô đó (dù đã có giá trị) và hỏi lại; điền xong đi tiếp từ trên xuống."""
    from app.channels.handfree.chat.flow import Reply

    visited = _visited_before(st)
    goal = visited[target - 1] if 1 <= target <= len(visited) else (st.get("last") or {})
    if not goal.get("key"):
        return _ask_reply(st, _say(vi.FR_NO_BACK)) if st.get("current") else Reply()
    st["back_label"] = goal.get("label") or ""
    # Ô đã bỏ qua mà công dân xin quay lại → bỏ khỏi danh sách bỏ qua để hỏi lại được.
    st["skip"] = [k for k in st.get("skip") or [] if k != goal["key"]]
    st["current"] = None
    r = Reply()
    r.actions = [_next_action(proc, st, focus=goal["key"])]
    return r


def _reload(proc: dict | None, st: dict):
    """Ô Xã chưa có danh sách: extension về lại đúng ô đó và chọn lại tỉnh cho cổng nạp danh sách xã."""
    from app.channels.handfree.chat.flow import Reply

    key = (st.get("current") or {}).get("key")
    st["current"] = None
    r = Reply()
    r.actions = [_next_action(proc, st, focus=key)]
    return r


async def _answer(conv: dict, proc: dict | None, st: dict, text: str):
    from app.channels.handfree.chat.flow import Reply

    field = st["current"]
    answer = await agent.interpret(text, field, _visited_before(st))
    if answer.action == "skip":
        return _skip_current(proc, st)
    if answer.action == "stop":
        return _finish_reply(conv, stopped=True)
    if answer.action == "repeat":
        return _ask_reply(st)
    if answer.action == "back":
        return _back(proc, st, answer.target)
    if field.get("province"):
        return _ask_reply(st)  # chưa có danh sách xã thì giá trị nói ra cũng không chọn được trên cổng
    if answer.action != "value":
        if field["kind"] == "date":
            hint = vi.FR_YEAR_HINT if field.get("year_only") else vi.FR_DATE_HINT
        else:
            hint = vi.FR_OPTION_HINT if field["options"] else ""
        r = Reply(*_say(vi.FR_UNCLEAR, label=field["label"], hint=hint, label_tts=_tts(field["label"])))
        r.actions = [{"type": "listen_after_tts"}]
        r.chips = _chips(st)
        return r
    return _apply(proc, st, field, answer.value)


def _apply(proc: dict | None, st: dict, field: dict, value: str):
    from app.channels.handfree.chat.flow import Reply

    st["pending"] = {"key": field["key"], "label": field["label"], "where": field["where"], "value": value}
    st.setdefault("history", []).append({"key": field["key"], "value": value})
    st["current"] = None
    r = Reply()
    r.actions = [_next_action(proc, st, {"key": field["key"], "value": value})]
    return r


async def handle(conv: dict, proc: dict | None, intent):
    """Lệnh/sự kiện của vòng bổ sung → Reply; không phải của vòng này → None (flow cũ xử lý)."""
    from app.channels.handfree.chat.flow import Reply

    if not _ours(intent):
        step = _next_step(conv, proc, intent)
        if not step:
            return None
        intent = type(intent)("action", step, {})
    if not active(conv, proc):
        conv.pop("field_review", None)
        return Reply()
    if intent.value in {"field_review_owner_next", "guided_step_report"}:
        return _owner_step(proc, intent)
    st = conv.setdefault("field_review", {})
    if intent.value.startswith(("field_review_preview", "field_review_confirm")):
        return _preview_step(proc, st, intent)
    if intent.value == "field_review_start":
        st.update(running=True, current=None, skip=[], intro=True, visited=[])
        for key in ("pending", "skipped_label", "back_label", "last"):
            st.pop(key, None)
        r = Reply()
        r.actions = [_next_action(proc, st)]
        return r
    if not st.get("running"):
        return Reply()  # sự kiện về muộn của vòng đã dừng
    if intent.value == "field_review_stop":
        return _finish_reply(conv, stopped=True)
    if intent.value == "field_review_skip":
        return _skip_current(proc, st) if st.get("current") else Reply()
    if intent.value == "field_review_back":
        return _back(proc, st) if st.get("current") else Reply()
    if intent.value == "field_review_reload":
        return _reload(proc, st) if st.get("current") else Reply()
    if intent.value == "field_review_pick":
        # Bấm nút lựa chọn: giá trị đã đúng nguyên văn một dòng của ô → điền thẳng, không qua LLM.
        value = str((intent.payload or {}).get("value") or "")
        field = st.get("current") or {}
        if value not in (field.get("options") or []):
            return Reply()
        return _apply(proc, st, field, value)
    if intent.value == "field_review_answer":
        text = str((intent.payload or {}).get("text") or "").strip()
        return await _answer(conv, proc, st, text) if st.get("current") and text else Reply()
    # field_review_focus: extension đã điền ô trước (nếu có) và tìm xong ô trống kế tiếp.
    payload = intent.payload or {}
    if isinstance(payload.get("stats"), dict):
        st["stats"] = _stats(payload["stats"])
    back = bool(st.get("back_label"))
    lead = _outcome_lead(st, payload.get("applied"))
    field = _field(payload.get("field"), _no_section(proc))
    if field is None:
        return _finish_reply(conv, stopped=False, lead=lead)
    st["current"] = field
    visited = [v for v in st.get("visited") or [] if v.get("key") != field["key"]]
    st["visited"] = [*visited, {"key": field["key"], "label": field["label"], "where": field["where"]}]
    return _ask_reply(st, lead, back=back)


def _next_step(conv: dict, proc: dict | None, intent) -> str:
    """Câu "xong rồi / xem trước / đính kèm đi" ở Kê khai → bấm Xem trước (bản xem trước đang mở → Xác nhận)."""
    if not active(conv, proc) or asking(conv) or conv.get("docs_target") != "declaration":
        return ""
    if conv.get("state") not in {"reviewing", "attaching"}:
        return ""
    if intent.kind != "confirm" and (intent.kind, intent.value) not in _NEXT_STEP_INTENTS:
        return ""
    return "field_review_confirm" if (conv.get("field_review") or {}).get("preview_open") else "field_review_preview"


def _preview_step(proc: dict | None, st: dict, intent):
    """Xem trước → Xác nhận trên cổng. Cổng chặn Xem trước khi còn ô bắt buộc trống (chấm đỏ hiện ra) →
    extension tô lại và đếm, trợ lý mời bổ sung; mở được → mời Xác nhận; Xác nhận xong trang sang Thành phần
    hồ sơ và page_status đưa vào bước đính kèm như cũ."""
    from app.channels.handfree.chat.flow import Reply

    payload = intent.payload or {}
    confirm_chips = [{"label": vi.FR_CONFIRM_CTA, "send": "__action:field_review_confirm", "solid": True, "cta": True},
                     {"label": vi.FR_PREVIEW_CLOSE_CHIP, "send": "__action:field_review_preview_close", "tone": "back"}]
    if intent.value == "field_review_preview":
        r = Reply(*_say(vi.FR_PREVIEW_OPENING))
        r.actions = [{"type": "declaration_preview", "required": _required(proc)}]
        return r
    if intent.value == "field_review_preview_report":
        if payload.get("opened"):
            st["preview_open"] = True
            r = Reply(*_say(vi.FR_PREVIEW_OPEN))
            r.chips = confirm_chips
            return r
        st["preview_open"] = False
        if isinstance(payload.get("stats"), dict):
            st["stats"] = _stats(payload["stats"])
        required = (st.get("stats") or {}).get("required") or 0
        if required:
            r = Reply(*_say(vi.FR_PREVIEW_MISSING, count=required))
            r.chips = [_start_chip(), _preview_chip()]
            return r
        message = _clean(payload.get("message"), 200)
        r = Reply(*_say(vi.FR_PREVIEW_FAILED, message=f": *{message}*" if message else ""))
        r.chips = [_preview_chip()]
        return r
    if intent.value == "field_review_preview_close":
        st["preview_open"] = False
        r = Reply(*_say(vi.FR_PREVIEW_CLOSED))
        r.actions = [{"type": "declaration_preview_close"}]
        r.chips = [_preview_chip()]
        return r
    if intent.value == "field_review_confirm":
        if not st.get("preview_open"):
            return _preview_step(proc, st, type(intent)("action", "field_review_preview", {}))
        expect = int(((proc or {}).get("wizard") or {}).get("attachmentStep") or 3)
        r = Reply(*_say(vi.FR_CONFIRMING))
        r.actions = [{"type": "declaration_confirm", "expectStep": expect}]
        return r
    # field_review_confirm_report
    if payload.get("ok"):
        st["preview_open"] = False
        return Reply()  # trang đã sang Thành phần hồ sơ: page_status đưa vào bước đính kèm như cũ
    if payload.get("noPreview"):
        st["preview_open"] = False
        r = Reply(*_say(vi.FR_PREVIEW_CLOSED))
        r.chips = [_preview_chip()]
        return r
    message = _clean(payload.get("message"), 200)
    r = Reply(*_say(vi.FR_CONFIRM_FAILED, message=f": *{message}*" if message else ""))
    r.chips = confirm_chips
    return r


def _ours(intent) -> bool:
    if intent.kind == "action" and intent.value == "guided_step_report":
        return (intent.payload or {}).get("phase") == OWNER_PHASE
    return (intent.kind == "action" and intent.value in _COMMANDS) or (
        intent.kind == "event" and intent.value == "field_review_focus")


def owner_ready(conv: dict, proc: dict | None, page_context: dict | None) -> bool:
    """Bước chủ hồ sơ đã đủ ô bắt buộc (đọc từ trang) → chưa xin đồng ý / giấy tờ, cho sang Kê khai trước.
    Chưa đọc được trạng thái ô hoặc còn ô trống → False, giữ luồng cũ."""
    form = (page_context or {}).get("ownerForm")
    if not active(conv, proc) or not isinstance(form, dict):
        return False
    return _count(form.get("required")) > 0 and _count(form.get("missing")) == 0


def _owner_cta() -> dict:
    return {"label": vi.FR_OWNER_CTA, "send": "__action:field_review_owner_next", "solid": True, "cta": True}


def owner_ready_reply():
    from app.channels.handfree.chat.flow import Reply

    r = Reply(*_say(vi.FR_OWNER_READY))
    r.chips = [_owner_cta()]
    return r


def _owner_step(proc: dict | None, intent):
    from app.channels.handfree.chat.flow import Reply

    if intent.value == "field_review_owner_next":
        expect = int(((proc or {}).get("wizard") or {}).get("declarationStep") or 2)
        r = Reply()
        r.actions = [{"type": "guided_click_next", "phase": OWNER_PHASE, "expectStep": expect}]
        return r
    payload = intent.payload or {}
    if payload.get("ok"):
        return Reply()  # sang Kê khai: page_status của trang mới đưa vào bước xin đồng ý + giấy tờ như cũ
    message = _clean(payload.get("message"), 200)
    r = Reply(*_say(vi.FR_OWNER_BLOCKED, message=f": *{message}*" if message else ""))
    r.chips = [_owner_cta()]
    return r


def finalize(conv: dict, intent, reply) -> None:
    """Bấm nút khác / trang rời bước Kê khai giữa vòng hỏi → dừng vòng (flow cũ đã xử lý lượt đó) và
    nhờ extension gỡ con trỏ, viền ô đang hỏi. Chạy SAU flow để docs_target đã theo trang mới."""
    st = conv.get("field_review") or {}
    if not st.get("running") or _ours(intent):
        return
    leaving = intent.kind == "action" or (
        intent.kind == "event" and intent.value == "page_status"
        and conv.get("docs_target") not in (None, "", "declaration"))
    if leaving:
        st.update(running=False, current=None)
        reply.actions = [*reply.actions, {"type": "field_review_stop"}]
