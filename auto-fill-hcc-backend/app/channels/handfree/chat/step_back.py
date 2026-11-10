"""Quay lại bước trước trên wizard tư pháp (profile "tu-phap": Chủ hồ sơ → Kê khai → Thành phần hồ sơ → Nhận kết quả).

Cổng chỉ có nút "Quay lại" ở cuối trang; state của trợ lý không lùi theo (đang chờ đính kèm mà trang về Kê khai thì
im lặng). Ở đây:
- công dân nói "quay lại bước trước" → trợ lý bấm nút Quay lại của cổng (action guided_click_back);
- trang lùi bước (bấm trên web hoặc trợ lý bấm) → state về đúng bước:
  · Kê khai: extension đếm lại ô của tờ khai (step_back_scan). Tờ khai mất phần lớn dữ liệu → điền lại từ dữ liệu đã
    đọc (conv["fields"], không chạy lại OCR); còn giữ → báo đủ ô bắt buộc kèm nút Xem trước, nút Bổ sung chỉ khi còn ô
    trống;
  · Thành phần hồ sơ: không đính lần hai (tránh trùng tệp), có nút Đính kèm lại;
  · Chủ hồ sơ: nhắc bấm Bước tiếp theo; tới lại Kê khai thì kiểm tờ khai như trên.
Bật khi extension khai supportsStepBack; chỉ tiếng Việt (câu thoại chưa có bản Mông).
"""
from app.channels.handfree.chat import field_review, guided_steps
from app.channels.handfree.chat import script_vi as vi

CAPABILITY = "supportsStepBack"
# Chỉ theo bước sau khi đã điền tờ khai; trước đó luồng nhận giấy tờ tự theo trang (docs_target).
_AFTER_FILL = {"reviewing", "attaching", "done"}


def enabled(conv: dict, proc: dict | None) -> bool:
    return (field_review.legacy_wizard(proc) and (conv.get("lang") or "vi") == "vi"
            and (conv.get("client_capabilities") or {}).get(CAPABILITY) is True)


def _int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _steps(proc: dict | None) -> tuple[int, int, int]:
    wizard = (proc or {}).get("wizard") or {}
    return (_int(wizard.get("ownerStep")) or 1, _int(wizard.get("declarationStep")) or 2,
            _int(wizard.get("attachmentStep")) or 3)


def _reply(tpl: dict, **kw):
    from app.channels.handfree.chat.flow import Reply

    return Reply(*field_review._say(tpl, **kw))


def handle(conv: dict, proc: dict | None, intent):
    """Lệnh / sự kiện riêng của việc quay lại bước → Reply; không phải → None."""
    if not enabled(conv, proc):
        return None
    if intent.kind == "action" and intent.value == "step_back":
        r = _reply(vi.STEP_BACK_CLICK)
        r.actions = [*_stop_review(conv), {"type": "guided_click_back"}]
        return r
    if intent.kind == "event" and intent.value == "step_back_failed":
        return _reply(vi.STEP_BACK_NO_BUTTON)
    if intent.kind == "event" and intent.value == "step_back_form":
        return _on_form(conv, proc, intent.payload or {})
    return None


def on_page(conv: dict, proc: dict | None, ctx: dict):
    """page_status: trang đổi bước wizard. None = không phải lùi bước / đi lại sau khi lùi, luồng thường xử lý."""
    step = _int((ctx or {}).get("wizardStep"))
    if not step:
        return None
    prev = _int(conv.get("portal_step"))
    conv["portal_step"] = step
    if not enabled(conv, proc) or conv.get("state") not in _AFTER_FILL or not prev or step == prev:
        return None
    owner, declaration, attachment = _steps(proc)
    if step < prev:
        conv["step_back_trip"] = True
        milestones = conv.get("milestones") or []
        if "guided_result" in milestones:
            milestones.remove("guided_result")  # tới lại bước nhận kết quả vẫn được hướng dẫn
        if step == declaration:
            r = _enter_declaration(conv, proc)
        elif step == attachment:
            r = _enter_attachment(conv, proc, vi.STEP_BACK_ATTACHMENT)
        elif step == owner:
            conv["state"] = "attaching"
            r = _reply(vi.STEP_BACK_OWNER)
            if guided_steps.enabled(conv, proc):
                r.chips = [guided_steps.owner_cta_chip(proc)]
        else:
            return None
        r.actions = [*_stop_review(conv), *r.actions]
        return r
    if not conv.get("step_back_trip"):
        return None
    # Đi tiếp lại sau một lần lùi.
    if step == declaration:
        return _enter_declaration(conv, proc)
    if step == attachment and conv.get("attach_done"):
        return _enter_attachment(conv, proc, vi.STEP_BACK_ATTACHED_BEFORE)
    return None


def _stop_review(conv: dict) -> list[dict]:
    st = conv.get("field_review") or {}
    if not st.get("running"):
        return []
    st.update(running=False, current=None)
    return [{"type": "field_review_stop"}]


def _enter_declaration(conv: dict, proc: dict | None):
    # attaching: tới lại Thành phần hồ sơ thì đính theo kế hoạch đã có (nếu lượt trước chưa đính) như sau lần điền đầu.
    conv["state"] = "attaching"
    review = field_review.fill_action_extra(conv, proc)
    if not review:
        return _no_form_reply(conv)
    r = _reply(vi.STEP_BACK_DECLARATION)
    r.actions = [{"type": "step_back_scan", "fieldReview": review}]
    return r


def _no_form_reply(conv: dict):
    r = _reply(vi.STEP_BACK_NO_FORM)
    r.chips = [field_review._preview_chip(), *_refill_chip(conv)]
    return r


def _refill_chip(conv: dict) -> list[dict]:
    return [{"label": vi.STEP_BACK_REFILL_CHIP, "send": "__action:refill"}] if conv.get("upload_session_id") else []


def _on_form(conv: dict, proc: dict | None, payload: dict):
    if not isinstance(payload.get("stats"), dict):
        return _no_form_reply(conv)
    stats = field_review._stats(payload["stats"])
    filled_before = _int((conv.get("fill_report") or {}).get("filled"))
    if conv.get("fields") and stats["filled"] * 2 < filled_before:
        # Cổng dựng lại tờ khai trống (mất quá nửa số ô trợ lý đã điền) → điền lại từ dữ liệu đã đọc; báo cáo điền
        # (fill_report) đi tiếp luồng thường: số ô, nút Bổ sung / Xem trước, chờ bước đính kèm.
        from app.channels.handfree.chat.flow import _fill_fields_reply

        conv["state"] = "filling"
        return field_review._with_lead(_fill_fields_reply(conv), field_review._say(vi.STEP_BACK_REFILL))
    conv["field_review"] = {"chips": [], "stats": stats}
    if stats["required"]:
        r = _reply(vi.FR_FILL_STATS, **stats)
        r.chips = [field_review._start_chip(), field_review._preview_chip()]
    else:
        from app.channels.handfree.chat.flow import Reply

        md, tts = field_review._ready(proc, conv["field_review"])
        r = Reply(md, tts.strip())
        r.chips = field_review.next_chips(conv, proc, [])
    return field_review._with_lead(r, field_review._say(vi.STEP_BACK_FORM_KEPT))


def _enter_attachment(conv: dict, proc: dict | None, tpl: dict):
    conv["state"] = "attaching"
    r = _reply(tpl)
    chips = []
    if guided_steps.enabled(conv, proc):
        chips.append(guided_steps.attach_cta_chip())
    if conv.get("attach_plan"):
        chips.append({"label": vi.STEP_BACK_REATTACH_CHIP, "send": "__event:attach_ready"})
    r.chips = chips
    return r
