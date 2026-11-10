"""Vòng bổ sung ô bản 2: agent ĐIỀU PHỐI + agent CHUYÊN MÔN, code chỉ kiểm tra.

Mỗi câu công dân nói khi đang hỏi một ô:
    điều phối (hiểu muốn gì: trả lời / sửa ô khác / sửa nhiều ô / đi tới ô / hỏi rõ / lệnh của bước…)
      → chuyên môn (một lượt cho mọi ô được giao: đọc giá trị từ nguyên câu nói)
      → kiểm tra (không đạt thì chuyên môn đọc lại một lần, vẫn không đạt thì hỏi lại công dân)
      → đọc lại giá trị (xác nhận rõ khi cần) → extension điền từng ô theo hàng đợi → quay về ô đang hỏi dở.

Extension điền một ô mỗi lệnh field_review_next (apply + focus) nên nhiều ô đi theo HÀNG ĐỢI: mỗi field_review_focus
trả về thì gửi ô kế tiếp. Ô danh sách chưa mở (chưa biết lựa chọn) phải đưa con trỏ tới để extension đọc danh sách rồi
mới giao chuyên môn. Bật theo từng thủ tục (FIELD_REVIEW_V2 = True trong app/pipelines/<tt>/handfree/field_review.py);
chỉ tiếng Việt (câu hỏi lại do agent viết, chưa có bản Mông). Agent điều phối lỗi → trả None, bên gọi chạy luồng cũ.
"""
import logging
import re

from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.field_review.v2 import specialist, coordinator, context, groups
from app.channels.handfree.chat.intents import fold

logger = logging.getLogger(__name__)

YES = "field_review_v2_yes"
NO = "field_review_v2_no"
COMMANDS = {YES, NO}
# Trạng thái riêng của bản 2 trong conv["field_review"], xoá khi bắt đầu vòng mới.
STATE_KEYS = ("v2", "queue", "inflight", "matching", "ask_override", "return_key", "confirm", "log", "partial",
              "catalog", "v2_leads", "last_text", "thread", "suggest", "specialist_thread", "group", "group_anchor",
              "focus_sent", "redirected", "v2_done", "held", "optional_go")
_THREAD_KEEP = 4
_LOG_KEEP = 10
_MAX_CATALOG = 200


def enabled(conv: dict, proc: dict | None) -> bool:
    if (conv.get("lang") or "vi") != "vi":
        return False
    return bool((_fr().config(proc) or {}).get("v2"))


def _fr():
    from app.channels.handfree.chat import field_review
    return field_review


def _reply(md: str = "", tts: str = ""):
    from app.channels.handfree.chat.flow import Reply
    return Reply(md, tts)


# ── Đọc lại / hiển thị ──

def value_tts(value: str) -> str:
    text = str(value or "")
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", text)
    if m:
        return f"ngày {int(m.group(1))} tháng {int(m.group(2))} năm {m.group(3)}"
    m = re.fullmatch(r"(\d{2})/(\d{4})", text)
    if m:
        return f"tháng {int(m.group(1))} năm {m.group(2)}"
    if "@" in text:
        return text.replace("@", " a còng ").replace(".", " chấm ")
    if re.fullmatch(r"\d{6,}", text):
        return " ".join(text)  # đọc từng chữ số cho dễ soát
    return text.replace("/", " xẹt ")


def _where_md(item: dict) -> str:
    return f" · *{item['where']}*" if item.get("where") else ""


def _applied_lead(item: dict) -> tuple[str, str]:
    """Hiện từng ô đã điền kèm giá trị (công dân soát bằng mắt) nhưng không đọc: đọc lại từng ô tốn thời gian — cả lượt
    chỉ đọc một câu "Đã điền xong" (FR2_APPLIED_DONE)."""
    return _fr()._say(vi.FR2_APPLIED, label=item["label"], where_md=_where_md(item), value=item["shown"])[0], ""


def _join(leads: list[tuple[str, str]]) -> tuple[str, str]:
    leads = [lead for lead in leads if lead and (lead[0] or lead[1])]
    return "\n\n".join(md for md, _ in leads if md), "".join(tts for _, tts in leads)


def _lines_md(items: list[dict]) -> str:
    return "\n".join(vi.FR2_CONFIRM_LINE_MD.format(label=it["label"], where_md=_where_md(it), value=it["shown"])
                     for it in items)


def _lines_tts(items: list[dict]) -> str:
    return ", ".join(f"{_fr()._tts(it['label'])} là {value_tts(it['shown'])}" for it in items)


def _confirm_chips(st: dict) -> list[dict]:
    return [{"label": vi.FR2_CONFIRM_YES_CHIP, "send": f"__action:{YES}", "solid": True},
            {"label": vi.FR2_CONFIRM_NO_CHIP, "send": f"__action:{NO}", "tone": "back"},
            *[c for c in _fr()._chips(st) if c.get("tone") in {"skip", "stop"}]]


def _ask(st: dict, md: str, tts: str):
    """Hỏi lại ngay tại ô đang hỏi (không đổi ô)."""
    r = _reply(md, tts or md)
    r.actions = [{"type": "listen_after_tts"}]
    r.chips = _fr()._chips(st)
    return r


# ── Hàng đợi điền ──

def _item(field: dict, checked, copy_pair: tuple[str, ...]) -> list[dict]:
    """Một kết quả đạt → một hoặc hai lệnh điền (ô bản sao chọn Có xong điền tiếp ô số lượng cổng mới dựng)."""
    extra = checked.extra or {}
    item = {"key": field["key"], "label": field.get("label") or "", "where": field.get("where") or "",
            "value": checked.value, "shown": checked.shown or checked.value, "old": field.get("value") or ""}
    if checked.match:
        item["match"] = True  # ô danh sách chưa mở: mở ra đọc danh sách thật rồi mới khớp giá trị
    other = field.get("other") or {}
    if extra.get("other") and other.get("name"):
        item["extra"] = [{"name": other["name"], "comp": "raw", "value": extra["other"]}]
    items = [item]
    if extra.get("quantity") and len(copy_pair) == 2 and field.get("copy_choice"):
        items.append({"key": copy_pair[1], "label": vi.FR2_COPY_COUNT_LABEL, "where": item["where"],
                      "value": extra["quantity"], "shown": extra["quantity"], "old": ""})
    return items


def _final_focus(st: dict) -> str:
    if st.get("ask_override"):
        return st["ask_override"]["key"]
    return st.pop("return_key", "") or ""


def planned_focus(proc: dict | None, st: dict, applying: str | None = None) -> str:
    """Ô hỏi kế tiếp theo cụm (bản đồ tờ khai extension gửi); extension cũ không gửi bản đồ → "" (extension tự chọn)."""
    if not st.get("catalog"):
        return ""
    return groups.next_key(st["catalog"], _fr().config(proc), st, (applying,) if applying else ())


_ADMIN_PREFIX = r"^(tinh|thanh pho|xa|phuong|dac khu|thi tran|quan|huyen|thi xa)\s+"


def _match_option(value: str, options: list[str]) -> str:
    """Giá trị agent đọc khi CHƯA mở danh sách → đúng một dòng của danh sách thật: chỉ nhận khi trùng hẳn (bỏ dấu, hoa
    thường, tiền tố cấp hành chính). Không trùng thì để agent chọn từ danh sách — code không đoán gần đúng."""
    def norm(text: str) -> str:
        return re.sub(_ADMIN_PREFIX, "", re.sub(r"\s+", " ", fold(text)).strip())
    want = norm(value)
    same = [o for o in options if norm(o) == want] if want else []
    return same[0] if len(same) == 1 else ""


def _dispatch(proc: dict | None, st: dict):
    fr = _fr()
    r = _reply()
    queue = st.get("queue") or []
    if queue and queue[0].get("match"):
        # Ô danh sách chưa mở: đưa con trỏ tới để extension đọc danh sách thật, rồi mới khớp giá trị (on_focus).
        st["matching"] = queue.pop(0)
        st["current"] = None
        r.actions = [fr._next_action(proc, st, focus=st["matching"]["key"])]
        return r
    if queue:
        item = queue.pop(0)
        st["inflight"] = item
        follow = queue[0]["key"] if queue else _final_focus(st)
        apply = {"key": item["key"], "value": item["value"]}
        if item.get("extra"):
            apply["extra"] = item["extra"]
        st["current"] = None
        r.actions = [fr._next_action(proc, st, apply, focus=follow)]
        return r
    st["current"] = None
    r.actions = [fr._next_action(proc, st, focus=_final_focus(st))]
    return r


def _log(st: dict, item: dict) -> None:
    entry = {k: item.get(k, "") for k in ("key", "label", "where", "old")}
    entry["new"] = item.get("shown") or item.get("value") or ""
    st["log"] = [entry, *(st.get("log") or [])][:_LOG_KEEP]
    for f in st.get("catalog") or []:
        if f.get("key") == entry["key"]:
            f["value"] = entry["new"]  # bản đồ tờ khai đúng ngay cả khi lượt sau extension không gửi lại
    (st.get("partial") or {}).pop(item.get("key"), None)


# ── Kết quả chuyên môn → việc kế tiếp ──

def _after_specialist(conv: dict, proc: dict | None, st: dict, outcomes: list):
    fr = _fr()
    oks = [o for o in outcomes if o.kind == "ok"]
    asks = [o for o in outcomes if o.kind == "ask"]
    current_key = (st.get("current") or {}).get("key")
    handled = {o.field.get("key") for o in outcomes}
    if current_key and current_key not in handled:
        st["return_key"] = current_key
    # Ô đang chờ xác nhận trước câu này (công dân nói thêm / sửa một ô): giữ lại, gộp vào lượt đọc lại sau.
    items = [it for it in st.pop("held", None) or [] if it.get("key") not in handled]
    sure = []
    for o in oks:
        for it in _item(o.field, o.checked, fr._copy_pair(proc)):
            if it.get("match"):
                it.update(text=st.get("last_text", ""), job=o.job)  # khớp danh sách sau: agent cần lại nguyên câu nói
            (items if o.confirm else sure).append(it)
    if asks:
        ask = asks[0]
        label = ask.field.get("label") or ""
        md, tts = (ask.question, ask.question) if ask.question else fr._say(
            vi.FR2_SAY_AGAIN, label=label, label_tts=fr._tts(label))
        st["ask_override"] = {"key": ask.field["key"], "md": md, "tts": tts}
        st.setdefault("partial", {})[ask.field["key"]] = st.get("last_text", "")
        # Còn thiếu / mơ hồ: mạch làm rõ chưa xong → lượt sau điều phối và chuyên môn còn thấy các câu đã nói.
        st["thread"] = [*(st.get("specialist_thread") or []), st.get("last_text", "")][-_THREAD_KEEP:]
    if sure and (items or asks):
        # Ô chắc chắn điền ngay; ô agent chưa chắc / còn thiếu hỏi SAU khi điền xong (câu hỏi gắn vào ô đó qua
        # ask_override, lệnh điền đưa con trỏ tới ô đó).
        st.setdefault("queue", []).extend(sure)
        if asks:
            override = st["ask_override"]
            if items:
                st["confirm"] = {"items": items}
                md, tts = fr._say(vi.FR2_HEARD_ASK, lines_md=_lines_md(items), lines_tts=_lines_tts(items),
                                  question_md=override["md"], question_tts=override["tts"])
                override.update(md=md, tts=tts, confirm=True)
        else:
            st["confirm"] = {"items": items}
            md, tts = fr._say(vi.FR2_CONFIRM, lines_md=_lines_md(items), lines_tts=_lines_tts(items))
            st["ask_override"] = {"key": items[0]["key"], "md": md, "tts": tts, "confirm": True}
        return _dispatch(proc, st)
    unsure = bool(items)
    items = [*items, *sure]
    lines_md, lines_tts = _lines_md(items), _lines_tts(items)
    chips = _confirm_chips(st)
    if unsure and asks:
        # Ô agent chưa chắc kèm ô còn thiếu: đọc lại ô chưa chắc kèm câu hỏi phần còn thiếu; công dân nói tiếp thì
        # gộp cả vào một lượt xác nhận.
        st["confirm"] = {"items": items}
        override = st["ask_override"]
        r = _reply(*fr._say(vi.FR2_HEARD_ASK, lines_md=lines_md, lines_tts=lines_tts, question_md=override["md"],
                            question_tts=override["tts"]))
        r.actions = [{"type": "listen_after_tts"}]
        r.chips = chips
        return r
    # Chỉ đọc lại khi agent chuyên môn chưa chắc (sửa nghe nhầm đáng kể, tên lạ, ghép giá trị cũ…); chắc chắn thì
    # điền luôn, kể cả một câu ra nhiều ô.
    if unsure:
        st["confirm"] = {"items": items}
        r = _reply(*fr._say(vi.FR2_CONFIRM, lines_md=lines_md, lines_tts=lines_tts))
        r.actions = [{"type": "listen_after_tts"}]
        r.chips = chips
        return r
    if items:
        st.setdefault("queue", []).extend(items)
        return _dispatch(proc, st)
    if asks:
        override = st["ask_override"]
        if override["key"] == current_key:
            st.pop("ask_override", None)
            st.pop("return_key", None)
            return _ask(st, override["md"], override["tts"])
        return _dispatch(proc, st)
    current = st.get("current") or {}
    if (current.get("kind") == "radio" and len(current.get("options") or []) == 1
            and any(o.kind == "none" and o.field.get("key") == current.get("key") for o in outcomes)):
        # Ô tích một lựa chọn ("Đăng ký lần đầu"): agent đọc ra "không" = không tích → để trống, hỏi ô kế tiếp.
        st.pop("return_key", None)
        return fr._skip_current(proc, st)
    st.pop("return_key", None)
    return _ask(st, *fr._say(vi.FR2_UNCLEAR))


async def _specialist(conv: dict, proc: dict | None, st: dict, targets: list[tuple[dict, str]], text: str,
                      suggest: list[dict] | None = None):
    """Mọi ô được giao đi chuyên môn trong MỘT lượt — kể cả ô danh sách chưa mở (agent đọc tên lựa chọn công dân nói,
    tới lúc điền mới khớp với danh sách thật) để công dân xác nhận một lần cho cả câu. Ô công dân nói trước thông tin
    (chưa hỏi tới) đi kèm cùng lượt với việc "goi_y": giá trị chỉ được giữ lại để gợi ý khi tới ô đó, không điền ngay."""
    handled_keys = {f.get("key") for f, _ in targets}
    extra = [(f, "goi_y") for f in suggest or [] if f.get("key") not in handled_keys and not f.get("value")]
    st["last_text"] = text
    outcomes = await specialist.solve([*targets, *extra], text, conv, st)
    kept = st.setdefault("suggest", {})
    copy_pair = _fr()._copy_pair(proc)
    for o in outcomes:
        if o.job == "goi_y" and o.kind == "ok":
            item = _item(o.field, o.checked, copy_pair)[0]
            if item.get("match"):
                item["text"] = text  # ô danh sách chưa mở: tới ô mới khớp với danh sách thật, agent cần lại nguyên câu
            kept[o.field["key"]] = item
    return _after_specialist(conv, proc, st, [o for o in outcomes if o.job != "goi_y"])


def _vocabulary(proc: dict | None) -> str:
    return str((_fr().config(proc) or {}).get("vocabulary") or "")


def _go_to(proc: dict | None, st: dict, goal: dict, question: str):
    fr = _fr()
    current_key = (st.get("current") or {}).get("key")
    st["skip"] = [k for k in st.get("skip") or [] if k != goal["key"]]
    if current_key and current_key != goal["key"]:
        st["return_key"] = current_key
    label = goal.get("label") or ""
    md, tts = (question, question) if question else fr._say(vi.FR2_SAY_AGAIN, label=label,
                                                            label_tts=fr._tts(label))
    if goal["key"] == current_key:
        return _ask(st, md, tts)
    st["ask_override"] = {"key": goal["key"], "md": md, "tts": tts}
    return _dispatch(proc, st)


def _proceed(conv: dict, proc: dict | None, st: dict):
    fr = _fr()
    if fr.flow_v2(conv, proc):
        return fr._proceed(conv, proc, st)
    if fr.legacy_wizard(proc):
        from app.channels.handfree.chat.intents import Intent

        st.update(running=False, current=None)
        r = fr._preview_step(proc, st, Intent("action", "field_review_preview", {}))
        r.actions = [{"type": "field_review_stop"}, *r.actions]
        return r
    return fr._finish_reply(conv, proc, stopped=True)


def _confirm_yes(proc: dict | None, st: dict):
    items = (st.pop("confirm", None) or {}).get("items") or []
    st.setdefault("queue", []).extend(items)
    return _dispatch(proc, st)


def _confirm_no(proc: dict | None, st: dict):
    fr = _fr()
    items = (st.pop("confirm", None) or {}).get("items") or []
    st.pop("ask_override", None)
    if len(items) == 1:
        return _go_to(proc, st, {"key": items[0]["key"], "label": items[0]["label"]}, "")
    st.pop("return_key", None)
    return _ask(st, *fr._say(vi.FR2_UNCLEAR))


async def answer(conv: dict, proc: dict | None, st: dict, text: str):
    """Câu công dân nói khi đang hỏi một ô → Reply; None = agent điều phối lỗi, bên gọi chạy luồng cũ."""
    fr = _fr()
    st["v2"] = True
    ctx = context.build(st)
    try:
        decision = await coordinator.decide(ctx, st, conv, text, _vocabulary(proc))
    except Exception as e:  # noqa: BLE001 — LLM best-effort, vòng hỏi phải sống tiếp
        logger.warning("[field_review.v2] điều phối lỗi, dùng luồng cũ: %s", e)
        return None
    kind = decision.kind
    # Mạch làm rõ: trợ lý đang hỏi lại → giữ câu vừa nói để lượt sau ghép (công dân trả lời từng mẩu). Ra việc thì xoá.
    thread = list(st.get("thread") or [])
    if kind in {"hoi_ro", "di_toi", "nhac_lai"}:
        st["thread"] = [*thread, text][-_THREAD_KEEP:]
    else:
        st.pop("thread", None)
    if st.get("confirm") and kind not in {"xac_nhan", "tu_choi"}:
        pending = st.pop("confirm", None) or {}
        if kind == "chuyen_mon":
            # Nói thêm / sửa một ô khi đang chờ xác nhận: các ô còn lại vẫn giữ, gộp vào lượt đọc lại sau.
            st["held"] = list(pending.get("items") or [])
    try:
        if kind == "xac_nhan":
            return _confirm_yes(proc, st) if st.get("confirm") else _ask(st, *fr._say(vi.FR2_UNCLEAR))
        if kind == "tu_choi":
            if st.get("confirm"):
                return _confirm_no(proc, st)
            # Không có gì chờ xác nhận: "sai rồi" là chê ô vừa điền → về lại ô đó hỏi lại.
            last = (st.get("log") or [None])[0]
            if last:
                return _go_to(proc, st, {"key": last["key"], "label": last.get("label") or ""}, "")
            return _ask(st, *fr._say(vi.FR2_UNCLEAR))
        if kind == "chuyen_mon":
            st["specialist_thread"] = thread
            return await _specialist(conv, proc, st, decision.targets, text, decision.suggest)
    except Exception as e:  # noqa: BLE001
        logger.warning("[field_review.v2] chuyên môn lỗi: %s", e)
        st.pop("held", None)
        return _ask(st, *fr._say(vi.FR2_UNCLEAR))
    if kind == "di_toi":
        return _go_to(proc, st, decision.goal, decision.question)
    if kind == "khoi_phuc":
        entry = next((e for e in st.get("log") or [] if e["key"] == decision.goal["key"]), None)
        label = decision.goal.get("label") or ""
        if not entry or not entry.get("old"):
            return _ask(st, *fr._say(vi.FR2_RESTORE_EMPTY, label=label, label_tts=fr._tts(label)))
        current_key = (st.get("current") or {}).get("key")
        if current_key and current_key != entry["key"]:
            st["return_key"] = current_key
        st.setdefault("queue", []).append({"key": entry["key"], "label": entry["label"], "where": entry["where"],
                                           "value": entry["old"], "shown": entry["old"], "old": entry["new"]})
        return _dispatch(proc, st)
    if kind == "bo_qua":
        return skip(proc, st, [t[0]["key"] for t in decision.targets]) or fr._skip_current(proc, st)
    if kind == "dung":
        return fr._finish_reply(conv, proc, stopped=True)
    if kind == "sang_buoc_sau":
        return _proceed(conv, proc, st)
    if kind == "lenh_khac":
        rerouted = await fr._reroute(conv, proc, st, text)
        if rerouted is not None:
            return rerouted
    if kind == "nhac_lai":
        return fr._ask_reply(st)
    if decision.question:
        return _ask(st, decision.question, decision.question)
    return _ask(st, *fr._say(vi.FR2_UNCLEAR))


def confirm_chip(proc: dict | None, st: dict, yes: bool):
    if not st.get("confirm"):
        return _reply()
    return _confirm_yes(proc, st) if yes else _confirm_no(proc, st)


async def on_focus(conv: dict, proc: dict | None, st: dict, payload: dict, field: dict | None):
    """Extension vừa điền (nếu có) và đưa con trỏ tới ô → điền tiếp hàng đợi / khớp ô danh sách / hỏi (gộp cả cụm khi
    cụm còn nhiều ô trống) kèm câu đọc lại. None = không có việc của bản 2, luồng cũ hỏi ô như thường."""
    fr = _fr()
    catalog = payload.get("catalog")
    if isinstance(catalog, list):
        st["catalog"] = [f for f in (_with_part(fr, proc, raw) for raw in catalog[:_MAX_CATALOG]) if f]
    if field is not None and isinstance(payload.get("field"), dict):
        field["part"] = fr._section(payload["field"].get("section"))
    if not st.get("v2"):
        return None
    applied = payload.get("applied")
    leads = st.setdefault("v2_leads", [])
    item = st.pop("inflight", None)
    if item:
        if isinstance(applied, dict) and applied.get("ok") is True and applied.get("key") == item["key"]:
            _log(st, item)
            leads.append(_applied_lead(item))
            st["v2_done"] = True
        else:
            st.setdefault("skip", []).append(item["key"])
            leads.append(fr._say(vi.FR_APPLY_FAILED, label=item["label"], label_tts=fr._tts(item["label"])))
    elif st.get("pending") and isinstance(applied, dict) and applied.get("ok") is True:
        pending = st["pending"]  # điền bằng nút lựa chọn (luồng cũ lo câu báo) — chỉ ghi nhật ký
        _log(st, {"key": pending.get("key"), "label": pending.get("label"), "where": pending.get("where"),
                  "old": "", "shown": pending.get("value")})
    queue = st.get("queue") or []
    matching = st.pop("matching", None)
    if not matching and queue and queue[0].get("match") and field is not None and field["key"] == queue[0]["key"]:
        matching = queue.pop(0)  # lệnh điền trước đã đưa con trỏ tới đúng ô danh sách cần khớp → khớp luôn
    if matching:
        if field is not None and field["key"] == matching["key"]:
            return await _resolve(conv, proc, st, matching, field)
        leads.append(fr._say(vi.FR_APPLY_FAILED, label=matching["label"], label_tts=fr._tts(matching["label"])))
        return _dispatch(proc, st)
    if queue:
        return _dispatch(proc, st)
    override = st.get("ask_override")
    own = bool(override and field is not None and override["key"] == field["key"])
    stats = st.get("stats") or {}
    if (field is not None and not own and not field.get("required") and not stats.get("required")
            and not st.get("optional_go")):
        # Đã đủ ô bắt buộc: dừng hỏi, báo còn ô không bắt buộc kèm nút đi tiếp / nút bổ sung (công dân bấm bổ sung thì
        # vòng mới hỏi tiếp ô không bắt buộc).
        st.pop("ask_override", None)
        done = [fr._say(vi.FR2_APPLIED_DONE)] if st.pop("v2_done", False) else []
        lead = _join([fr._outcome_lead(st, applied), *st.pop("v2_leads", []), *done])
        return fr._finish_reply(conv, proc, stopped=False, lead=lead)
    if field is not None and not own:
        moved = _redirect(proc, st, field, applied)
        if moved is not None:
            return moved
    st.pop("focus_sent", None)
    suggestion = None
    if field is not None and not field.get("value") and not own:
        suggestion = (st.get("suggest") or {}).pop(field["key"], None)
    # Hỏi từng ô; cụm của ô chỉ là ngữ cảnh cho điều phối (công dân nói luôn các ô cùng cụm thì điền cả).
    st.pop("group", None)
    if field is not None:
        st["group_anchor"] = groups.group_id(field, _groups(proc))
        group = _group_of(proc, st, field) if not field.get("value") else None
        if group:
            st["group"] = group
    if not leads and not override and not suggestion:
        st.pop("v2_leads", None)
        return None
    # Câu báo của luồng cũ (điền bằng nút / bỏ qua / quay lại) đứng trước câu báo của bản 2.
    done = [fr._say(vi.FR2_APPLIED_DONE)] if st.pop("v2_done", False) else []
    lead = _join([fr._outcome_lead(st, applied), *st.pop("v2_leads", []), *done])
    if field is None:
        st.pop("ask_override", None)
        return fr._finish_reply(conv, proc, stopped=False, lead=lead)
    st["current"] = field
    visited = [v for v in st.get("visited") or [] if v.get("key") != field["key"]]
    st["visited"] = [*visited, {"key": field["key"], "label": field["label"], "where": field["where"]}]
    phase = fr._optional_phase(conv, proc, st, field)
    if own:
        st.pop("ask_override", None)
        r = _ask(st, override["md"], override["tts"])
        if override.get("confirm") and st.get("confirm"):
            r.chips = _confirm_chips(st)
    elif suggestion:
        st.pop("ask_override", None)
        r = _suggest_reply(st, suggestion)
    else:
        st.pop("ask_override", None)
        r = fr._ask_reply(st)
    return fr._with_lead(r, lead, phase)


async def _resolve(conv: dict, proc: dict | None, st: dict, item: dict, field: dict):
    """Ô danh sách vừa mở: giá trị trùng hẳn một dòng → điền; không trùng → agent chuyên môn chọn từ danh sách thật
    (không có dòng hợp thì agent hỏi lại công dân, vd xã đã sáp nhập không còn tên cũ)."""
    fr = _fr()
    picked = _match_option(item["value"], field.get("options") or [])
    if picked:
        st.setdefault("queue", []).insert(0, {**item, "value": picked, "shown": picked, "match": False})
        return _dispatch(proc, st)
    st["current"] = field
    visited = [v for v in st.get("visited") or [] if v.get("key") != field["key"]]
    st["visited"] = [*visited, {"key": field["key"], "label": field["label"], "where": field["where"]}]
    if not field.get("options"):
        if field.get("province"):
            # Cổng không nạp được danh sách xã sau khi chọn tỉnh: câu hỏi của luồng cũ đã nói rõ kèm nút tải lại.
            return fr._with_lead(fr._ask_reply(st), _join(st.pop("v2_leads", [])))
        # Danh sách trống mà cổng không báo lỗi: nói rõ vì sao chưa chọn được, không lặp lại nguyên câu hỏi.
        label = field.get("label") or ""
        r = _ask(st, *fr._say(vi.FR2_LIST_NOT_LOADED, label=label, label_tts=fr._tts(label), value=item.get("shown")
                              or item.get("value") or "", value_tts=value_tts(item.get("shown") or item.get("value") or "")))
        return fr._with_lead(r, _join(st.pop("v2_leads", [])))
    st["last_text"] = item.get("text") or ""
    try:
        outcomes = await specialist.solve([(dict(field, code="o1"), item.get("job") or "tra_loi")], st["last_text"],
                                          conv, st)
    except Exception as e:  # noqa: BLE001
        logger.warning("[field_review.v2] chuyên môn lỗi: %s", e)
        outcomes = []
    if any(o.kind != "none" for o in outcomes):
        r = _after_specialist(conv, proc, st, outcomes)
    else:
        label = field.get("label") or ""
        r = _ask(st, *fr._say(vi.FR2_CHOICE_MISSING, label=label, label_tts=fr._tts(label)))
        r.chips = fr._chips(st)
    return fr._with_lead(r, _join(st.pop("v2_leads", [])))


def _groups(proc: dict | None) -> tuple:
    return tuple((_fr().config(proc) or {}).get("groups") or ())


def _redirect(proc: dict | None, st: dict, field: dict, applied):
    """Extension tự chọn ô kế tiếp, hoặc ô dự tính trước khi điền đã lỗi thời (tích "Trong nước" xong cổng mới dựng
    khối địa chỉ) → đưa con trỏ về ô nên hỏi theo cụm. Ô công dân / trợ lý chủ động tới (quay lại, sửa) thì giữ nguyên.
    Mỗi đích chỉ chuyển một lần để không lặp khi extension không tìm thấy ô."""
    fr = _fr()
    sent = st.pop("focus_sent", None) or {}
    if not st.get("catalog") or st.get("copy_carry") or (sent.get("key") and not sent.get("planned")):
        return None
    want = planned_focus(proc, st)
    if not want or want == field["key"] or st.get("redirected") == want:
        st.pop("redirected", None)
        return None
    st["redirected"] = want
    lead = fr._outcome_lead(st, applied)  # câu báo của luồng cũ (đã điền / bỏ qua) giữ sang lượt hỏi sau
    if lead[0] or lead[1]:
        st.setdefault("v2_leads", []).append(lead)
    st["current"] = None
    r = _reply()
    r.actions = [fr._next_action(proc, st, focus=want)]
    st["focus_sent"] = {"key": want, "planned": True}
    return r


def _group_of(proc: dict | None, st: dict, field: dict) -> dict | None:
    """Cụm của ô sắp hỏi còn ô trống khác → ghi lại cho điều phối biết các ô công dân có thể nói luôn."""
    if not st.get("catalog"):
        return None
    members = groups.open_members(st["catalog"], _fr().config(proc), st, field)
    if len(members) < 2:
        return None
    cfg = _groups(proc)
    named = next((m for m in members if m.get("role") in {"tinh", "xa", "diaChi"}), field)
    return {"title": groups.title(named, cfg), "keys": [m["key"] for m in members]}


def skip(proc: dict | None, st: dict, keys: list[str] | None = None):
    """Công dân nói không có / không nhớ các ô điều phối nêu (vd không có giấy tờ → cả cụm giấy tờ). None = chỉ bỏ ô
    đang hỏi → luồng cũ bỏ qua ô đang hỏi."""
    from app.channels.handfree.chat.flow import Reply

    group = st.get("group") or {}
    current = (st.get("current") or {}).get("key")
    keys = [k for k in keys or [] if k]
    if not keys or keys == [current]:
        return None
    st["skip"] = [*(st.get("skip") or []), *(k for k in keys if k not in (st.get("skip") or []))]
    st["skipped_label"] = group.get("title") if keys == group.get("keys") else ", ".join(
        f.get("label") or "" for f in st.get("catalog") or [] if f.get("key") in keys)
    st.pop("group", None)
    st["current"] = None
    r = Reply()
    r.actions = [_fr()._next_action(proc, st)]
    return r


def _with_part(fr, proc: dict | None, raw) -> dict | None:
    field = fr._field(raw, fr._no_section(proc), fr._copy_pair(proc), strip_numbers=fr._bac_ninh_portal(proc))
    if field is not None and isinstance(raw, dict):
        field["part"] = fr._section(raw.get("section"))
    return field


def _suggest_reply(st: dict, item: dict):
    """Tới ô mà công dân đã nói trước thông tin (lúc trả lời ô khác): hỏi ô như thường kèm giá trị đã nghe, chờ xác nhận
    — "đúng rồi" là điền, nói giá trị khác thì theo giá trị mới."""
    fr = _fr()
    asked = fr._ask_reply(st)
    hint_md, hint_tts = fr._say(vi.FR2_SUGGEST, value=item["shown"], value_tts=value_tts(item["shown"]))
    st["confirm"] = {"items": [item]}
    r = _reply(f"{asked.display_md}\n\n{hint_md}", f"{asked.tts_text} {hint_tts}")
    r.actions = [a for a in asked.actions if a.get("type") != "lead_message"]
    r.chips = [{"label": vi.FR2_CONFIRM_YES_CHIP, "send": f"__action:{YES}", "solid": True},
               {"label": vi.FR2_CONFIRM_NO_CHIP, "send": f"__action:{NO}", "tone": "back"},
               *[c for c in asked.chips if c.get("tone") in {"skip", "stop"}]]
    return r
