"""Hỏi bổ sung ô còn trống ở bước Thông tin chủ hồ sơ (thủ tục quét sớm — guidedSteps.ownerScan).

Giấy tờ quét lên điền được ô nào thì đã điền; ô còn trống (ngày cấp, nơi cấp, số điện thoại, địa chỉ chi tiết)
thì hỏi từng ô — công dân nói hoặc gõ. Mỗi câu trả lời hợp lệ được ghi vào `owner_fields` rồi phát lại đúng lệnh
`fill_owner_fields` mà engine điền chủ hồ sơ của extension đang nhận; báo cáo điền quay về đây để biết ô nào còn
thiếu thật trên trang, rồi hỏi ô kế tiếp. Không cần extension mới: chỉ dùng lệnh điền, lead_message, listen_after_tts
đã có sẵn.

Bật theo đúng hàng rào của luồng quét sớm (`supportsOwnerScan`), và cho thủ tục tư pháp form cũ (kết hôn, giám hộ…)
đang có vòng bổ sung ô tờ khai (`supportsFieldReview`) — cùng lệnh điền chủ hồ sơ, hỏi xong thì nút sang Kê khai. Chế
độ Mông giữ câu "công dân tự điền" cũ vì các câu hỏi ở đây chưa có bản dịch.
"""

import json

from app.channels.handfree.chat import field_review
from app.channels.handfree.chat import guided_steps as guided
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.field_review import agent
from app.channels.handfree.owner_info.runner import issue_place_for_date
from app.channels.handfree.owner_info.schema import ISSUE_PLACE_OPTIONS

_STATE = "owner_review"
_COMMANDS = {"owner_review_answer", "owner_review_pick", "owner_review_skip", "owner_review_stop"}
# Lưu thông tin vừa điền vào "Thông tin định danh" của công dân (tick ô trên cổng + Xác nhận hộp thoại ghi đè).
_SAVE = "save_owner_profile"
_SAVE_REPORT = "save_owner_profile_report"
SAVE_CAPABILITY = "supportsSaveOwnerProfile"
# Khóa ô (ownerInfo.fields[*].key) → cách hỏi. Ô khác (khối ủy quyền) không hỏi ở đây: công dân tự điền như cũ.
_ASKABLE = {
    "issueDate": {"kind": "date"},
    "issuePlace": {"kind": "select", "options": list(ISSUE_PLACE_OPTIONS)},
    # Ô SĐT của cổng chỉ nhận di động: đúng 10 số.
    "phoneNumber": {"kind": "text", "mobile_only": True},
    "detailedAddress": {"kind": "text"},
}
_WHERE = "Thông tin chủ hồ sơ"


def _legacy_form(conv: dict, proc: dict | None) -> bool:
    """Tư pháp form cũ (bước 2 là tờ khai eForm) đã có vòng bổ sung ô tờ khai trên client này."""
    return ((proc or {}).get("mode") != "attach" and field_review.legacy_wizard(proc)
            and field_review.active(conv, proc))


def enabled(conv: dict, proc: dict | None) -> bool:
    return ((guided.owner_scan_enabled(conv, proc) or _legacy_form(conv, proc))
            and (conv.get("lang") or "vi") != "hmong")


def _next_chip(conv: dict, proc: dict | None) -> dict:
    # Form cũ: bước kế tiếp là Kê khai (nút của vòng bổ sung ô); thủ tục quét sớm: nút dẫn bước sang Thành phần hồ sơ.
    return field_review.owner_cta() if _legacy_form(conv, proc) else guided.owner_cta_chip(proc)


def asking(conv: dict) -> bool:
    return bool((conv.get(_STATE) or {}).get("current"))


def _say(tpl: dict, **kw) -> tuple[str, str]:
    return tpl["md"].format(**kw), tpl["tts"].format(**kw)


def _owner_field(conv: dict, key: str) -> dict | None:
    return next((f for f in conv.get("owner_fields") or [] if f.get("key") == key), None)


def _display(field: dict) -> str:
    return str(field.get("reportLabel") or field.get("label") or "").strip()


def _ask_field(conv: dict, key: str) -> dict:
    spec = _owner_field(conv, key) or {}
    return {"label": str(spec.get("label") or ""), "where": _WHERE, "options": [], **_ASKABLE[key]}


def _chips(key: str) -> list[dict]:
    chips = []
    if key == "issuePlace":
        chips = [{"label": label, "send": "__action:owner_review_pick:" + json.dumps({"index": i})}
                 for i, label in enumerate(vi.OR_ISSUE_PLACE_CHIPS)]
    return [*chips,
            {"label": vi.FR_SKIP_CHIP, "send": "__action:owner_review_skip", "tone": "skip"},
            {"label": vi.OR_STOP_CHIP, "send": "__action:owner_review_stop", "tone": "stop"}]


def _ask(conv: dict, st: dict, key: str, *leads: tuple[str, str]):
    from app.channels.handfree.chat.flow import Reply

    st["current"] = key
    md, tts = _say(vi.OR_QUESTIONS[key])
    r = Reply(*_say(vi.OR_ASK, question_md=md, question_tts=tts))
    r.actions = [{"type": "listen_after_tts"}]
    r.chips = _chips(key)
    return field_review._with_lead(r, *leads)


def _missing_keys(conv: dict, missing_labels: list[str]) -> list[str]:
    wanted = {str(label).strip().casefold() for label in missing_labels}
    return [str(f.get("key")) for f in conv.get("owner_fields") or []
            if _display(f).casefold() in wanted and f.get("key") in _ASKABLE]


def start(conv: dict, proc: dict | None, completed: list[str], missing: list[str]):
    """Báo cáo điền đầu tiên còn ô thiếu → mở vòng hỏi. None = không có ô nào hỏi được, giữ câu cũ."""
    if not enabled(conv, proc):
        return None
    queue = _missing_keys(conv, missing)
    if not queue:
        return None
    st = {"queue": queue[1:], "missing": list(missing)}
    conv[_STATE] = st
    from app.channels.handfree.chat.flow import _join_owner_labels

    done = _say(vi.OR_FILLED, completed=_join_owner_labels(completed)) if completed else ("", "")
    return _ask(conv, st, queue[0], done, _say(vi.OR_START, count=len(queue)))


def finalize(conv: dict, intent) -> None:
    """Bấm nút khác / trang rời bước chủ hồ sơ giữa vòng hỏi → dừng vòng, để câu gõ sau không bị coi là câu trả lời."""
    st = conv.get(_STATE)
    if not st:
        return
    if intent.kind == "action" and intent.value not in {*_COMMANDS, _SAVE, _SAVE_REPORT, "owner_fill_report"}:
        conv[_STATE] = {}
    elif intent.kind == "event" and intent.value == "page_status":
        step = (intent.payload or {}).get("wizardStep")
        if step not in (None, "", 1):
            conv[_STATE] = {}


async def handle(conv: dict, proc: dict | None, intent):
    if intent.kind == "action" and intent.value in {_SAVE, _SAVE_REPORT}:
        return _save_step(conv, proc, intent)
    st = conv.get(_STATE) or {}
    if not st:
        return None
    if intent.kind == "event" and intent.value == "page_status":
        return _page_filled(conv, proc, st, intent.payload or {})
    if intent.kind != "action":
        return None
    if intent.value == "owner_fill_report" and st.get("applying"):
        return _after_fill(conv, proc, st, intent.payload or {})
    key = st.get("current")
    if not key or intent.value not in _COMMANDS:
        return None
    if intent.value == "owner_review_skip":
        return _next(conv, proc, st, _skipped(conv, key))
    if intent.value == "owner_review_stop":
        return _finish(conv, proc, st)
    if intent.value == "owner_review_pick":
        try:
            index = int((intent.payload or {}).get("index"))
        except (TypeError, ValueError):
            index = -1
        if key != "issuePlace" or not 0 <= index < len(ISSUE_PLACE_OPTIONS):
            return _ask(conv, st, key)
        return _apply(conv, st, key, ISSUE_PLACE_OPTIONS[index])
    field = _ask_field(conv, key)
    answer = await agent.interpret(str((intent.payload or {}).get("text") or ""), field)
    if answer.action == "skip":
        return _next(conv, proc, st, _skipped(conv, key))
    if answer.action in {"stop", "proceed"}:
        return _finish(conv, proc, st)
    if answer.action != "value":
        return _unclear(conv, st, key, field, answer)
    return _apply(conv, st, key, answer.value)


def with_save_chip(conv: dict, proc: dict | None, chips: list[dict], missing: list[str]) -> list[dict]:
    """Chủ hồ sơ đã đủ ô (trợ lý điền / công dân tự gõ) → nút nhỏ "Lưu vào Thông tin định danh" đứng TRÊN nút chuyển
    bước, để lần sau cổng tự đổ sẵn. Chỉ khi extension có engine lưu, chưa lưu lần nào, và đang có nút chuyển bước."""
    caps = conv.get("client_capabilities") or {}
    next_sends = {"__action:guided_next", field_review.owner_cta()["send"]}
    if (missing or caps.get(SAVE_CAPABILITY) is not True or conv.get("owner_profile_saved")
            or not enabled(conv, proc)
            or not any(chip.get("send") in next_sends for chip in chips)):
        return chips
    return [{"label": vi.OR_SAVE_CHIP, "send": f"__action:{_SAVE}"}, *chips]


def _save_step(conv: dict, proc: dict | None, intent):
    from app.channels.handfree.chat.flow import Reply

    if intent.value == _SAVE:
        r = Reply()
        r.actions = [{"type": _SAVE}]
        return r
    payload = intent.payload or {}
    if payload.get("ok"):
        conv["owner_profile_saved"] = True
        r = Reply(*_say(vi.OR_SAVED))
    else:
        error = str(payload.get("error") or "trang không phản hồi")[:160]
        r = Reply(*_say(vi.OR_SAVE_FAILED, error=error))
    r.chips = [_next_chip(conv, proc)]
    return r


def _page_filled(conv: dict, proc: dict | None, st: dict, payload: dict):
    """Công dân tự gõ nốt trên trang thay vì trả lời (extension báo lại mỗi khi số ô còn trống đổi): đủ hết ô bắt buộc
    thì chốt luôn, đưa nút sang bước tiếp. Đang chờ báo cáo điền của chính trợ lý thì để báo cáo đó quyết."""
    form = payload.get("ownerForm")
    if st.get("applying") or payload.get("wizardStep") != 1 or not isinstance(form, dict):
        return None
    if field_review._count(form.get("required")) == 0 or field_review._count(form.get("missing")) != 0:
        return None
    st["missing"] = []
    r = _finish(conv, proc, st)
    # Điền lại (không ghi đè) chỉ để engine tô lại viền: ô công dân vừa tự gõ đang còn viền đỏ của lượt điền trước.
    r.actions = [*r.actions, {"type": "fill_owner_fields", "fields": conv.get("owner_fields") or []}]
    return r


def _skipped(conv: dict, key: str) -> tuple[str, str]:
    label = _display(_owner_field(conv, key) or {})
    return _say(vi.FR_SKIPPED, label=label, label_tts=label)


def _unclear(conv: dict, st: dict, key: str, field: dict, answer):
    label = _display(_owner_field(conv, key) or {})
    if agent.id_lengths(field) and answer.value and agent.phone_format_wrong(answer.value, agent.id_lengths(field)):
        lead = _say(vi.FR_PHONE_FORMAT, label=label, label_tts=label, heard=answer.value)
    elif agent.id_lengths(field) and answer.value:
        lead = _say(vi.FR_DIGITS_SHORT, label=label, label_tts=label, count=len(answer.value),
                    heard=answer.value, need="10")
    else:
        hint = vi.FR_DATE_HINT if field["kind"] == "date" else ""
        lead = _say(vi.FR_UNCLEAR, label=label, hint=hint, label_tts=label)
    from app.channels.handfree.chat.flow import Reply

    r = Reply(*lead)
    r.actions = [{"type": "listen_after_tts"}]
    r.chips = _chips(key)
    return r


def _apply(conv: dict, st: dict, key: str, value: str):
    from app.channels.handfree.chat.flow import Reply

    field = _owner_field(conv, key)
    field["value"] = value
    md, tts = _say(vi.OR_APPLYING, label=_display(field), value=value)
    if key == "issueDate" and "issuePlace" in st["queue"]:
        place = issue_place_for_date(value, (conv.get("owner_context") or {}).get("identityNumber"))
        place_field = _owner_field(conv, "issuePlace")
        if place and place_field is not None:
            place_field["value"] = place
            st["queue"].remove("issuePlace")
            note_md, note_tts = _say(vi.OR_ISSUE_PLACE_DERIVED, place=place)
            md, tts = md + note_md, tts + note_tts
    st.update(current=None, applying=True, last=key)
    r = Reply(md, tts)
    r.actions = [{"type": "fill_owner_fields", "fields": conv.get("owner_fields") or []}]
    return r


def _after_fill(conv: dict, proc: dict | None, st: dict, payload: dict):
    from app.channels.handfree.chat.flow import _owner_report_names

    st["applying"] = False
    _, missing = _owner_report_names(conv, {
        "notFound": list(payload.get("notFound") or []), "errors": list(payload.get("errors") or []),
        "filledLabels": list(payload.get("filledLabels") or []), "keptLabels": list(payload.get("keptLabels") or []),
    })
    st["missing"] = missing
    last = _owner_field(conv, st.pop("last", "")) or {}
    lead = ("", "")
    if last and _display(last) in missing:
        lead = _say(vi.FR_APPLY_FAILED, label=_display(last), label_tts=_display(last))
    return _next(conv, proc, st, lead)


def _next(conv: dict, proc: dict | None, st: dict, lead: tuple[str, str] = ("", "")):
    still = set(_missing_keys(conv, st.get("missing") or []))
    queue = [key for key in st.get("queue") or [] if key in still]
    if not queue:
        return _finish(conv, proc, st, lead)
    st["queue"] = queue[1:]
    return _ask(conv, st, queue[0], lead)


def _finish(conv: dict, proc: dict | None, st: dict, lead: tuple[str, str] = ("", "")):
    from app.channels.handfree.chat.flow import Reply, _join_owner_labels, _owner_step_follow_up

    missing = list(st.get("missing") or [])
    # Còn ô thiếu → vẫn theo dõi trang (không hỏi nữa): công dân tự gõ đủ thì báo đủ + nút sang bước tiếp.
    conv[_STATE] = {"watching": True, "missing": missing} if missing else {}
    note, chips = _owner_step_follow_up(conv, proc or {})
    md, tts = (_say(vi.OR_LEFT, missing=_join_owner_labels(missing)) if missing else _say(vi.OR_COMPLETE))
    # Thủ tục còn câu hỏi riêng ở bước này (chứng thực luôn thẻ căn cước) thì câu đó thay lời bảo bấm nút.
    if _legacy_form(conv, proc):
        tail_md, tail_tts = _say(vi.OR_NEXT_HINT, attachment_step=vi.OR_DECLARATION_STEP)
    elif note:
        tail_md, tail_tts = "\n\n" + note["md"], " " + note["tts"]
    else:
        tail_md, tail_tts = _say(vi.OR_NEXT_HINT, **guided.step_labels(proc))
    r = Reply(md + tail_md, tts + tail_tts)
    r.chips = with_save_chip(conv, proc, chips, missing)
    return field_review._with_lead(r, lead)
