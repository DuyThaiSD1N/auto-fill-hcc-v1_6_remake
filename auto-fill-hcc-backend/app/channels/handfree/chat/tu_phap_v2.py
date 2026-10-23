"""Tư pháp form cũ (tờ khai eForm → Xem trước → Xác nhận → Thành phần hồ sơ, profile "tu-phap") — luồng bản 2.

Extension khai supportsFlowV2: mỗi khung một việc, hai thẻ tiến trình vì giữa hai chặng công dân Xem trước / Xác
nhận trên cổng:
    nhận tệp → [Bóc tách → Điền tờ khai] → kết quả điền → kết luận (còn ô đỏ → Bổ sung; đủ → Xem trước to)
    … Xác nhận → [Xếp giấy tờ → Đính kèm] → kết quả đính kèm → bước tiếp theo.
Áp cho mọi thủ tục tư pháp form cũ; phần ô đỏ / Bổ sung / Xem trước to chỉ có ở thủ tục đã có vòng bổ sung ô
(field_review.flow_v2). flow.py chỉ gọi các hàm ở đây; mỗi hàm tự trả lại reply cũ khi luồng bản 2 không bật.
Cổng liên thông (chat/lien_thong.py, cờ supportsLienThongFlow) dùng chung hai thẻ này; kết quả điền và kết quả đính
kèm của liên thông do lien_thong.py nói (bước sau là Xem lại tờ khai / Nhận kết quả chứ không phải Xem trước / nộp).
Chế độ Mông giữ luồng cũ (câu chỉ có bản tiếng Việt).
"""

from app.channels.handfree.chat import field_review
from app.channels.handfree.chat import guided_steps as guided
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.tu_phap_moi import fill_result, steps_action


def enabled(conv: dict, proc: dict | None) -> bool:
    caps = conv.get("client_capabilities") or {}
    supported = ((field_review.legacy_wizard(proc) and caps.get(field_review.FLOW_V2_CAPABILITY) is True)
                 or (field_review.lien_thong(proc) and caps.get(field_review.LIEN_THONG_CAPABILITY) is True))
    return supported and (conv.get("lang") or "vi") != "hmong"


def _say(tpl: dict, **kw) -> tuple[str, str]:
    return tpl["md"].format(**kw), tpl["tts"].format(**kw)


def _card(conv: dict, name: str, steps: tuple[str, ...], *, start: bool = False, **state) -> dict:
    """Thẻ đang hiện là của chặng khác (hoặc chưa có) → dựng thẻ mới; cùng chặng → cập nhật tại chỗ (không thì lệnh
    cập nhật của chặng đính kèm sẽ sửa lại thẻ chặng điền đã xong)."""
    fresh = start or conv.get("flow2_card") != name
    conv["flow2_card"] = name
    return steps_action(steps if fresh else None, **state)


def _silent(actions: list[dict]):
    from app.channels.handfree.chat.flow import Reply

    r = Reply()
    r.actions = actions
    return r


def docs_received_reply(conv: dict, proc: dict | None, reply, files_count: int, *, all_received: bool):
    """Nhận tệp, pipeline điền chạy: câu không hứa số giây + thẻ chặng điền."""
    from app.channels.handfree.chat.flow import Reply

    if not enabled(conv, proc):
        return reply
    if all_received:
        reply = Reply(*_say(vi.FLOW2_DOCS_RECEIVED_FILL, files_count=files_count))
    reply.actions = [*reply.actions, _card(conv, "fill", vi.FLOW2_FILL_STEPS, start=True)]
    return reply


def attach_only_started(conv: dict, proc: dict | None, reply):
    """Thủ tục chỉ đính kèm (chứng thực…): planner vừa chạy ngay khi nhận tệp → thẻ chặng đính kèm."""
    if enabled(conv, proc) and conv.get("pipeline_status") == "running":
        reply.actions = [*reply.actions, _card(conv, "attach", vi.FLOW2_ATTACH_STEPS, start=True)]
    return reply


def refill_reply(conv: dict, proc: dict | None, reply):
    from app.channels.handfree.chat.flow import Reply

    if not enabled(conv, proc):
        return reply
    r = Reply(*_say(vi.FLOW2_REFILL))
    r.actions = [_card(conv, "fill", vi.FLOW2_FILL_STEPS, start=True)]
    return r


def main_form_started_reply(conv: dict, proc: dict | None, reply):
    """Từ bước chủ hồ sơ sang Kê khai, điền tờ khai bằng giấy tờ đã nhận ở bước trước: mở thẻ chặng điền ngay (không
    thì extension dựng thẻ một dòng cũ, rồi thẻ chặng điền mọc thêm khi dữ liệu về)."""
    from app.channels.handfree.chat.flow import Reply

    if not enabled(conv, proc):
        return reply
    r = Reply(*_say(vi.FLOW2_MAIN_FORM))
    r.actions = [_card(conv, "fill", vi.FLOW2_FILL_STEPS, start=True)]
    return r


def fill_started_reply(conv: dict, proc: dict | None, reply):
    """Dữ liệu điền về: im lặng, thẻ sang bước "Điền tờ khai"; kết quả điền nói ở khung riêng khi extension báo điền
    xong (chú giải màu cũ của extension tắt)."""
    if not enabled(conv, proc):
        return reply
    actions = [dict(a) for a in reply.actions]
    actions[0]["noLegend"] = True
    return _silent([_card(conv, "fill", vi.FLOW2_FILL_STEPS, active=1), *actions])


def fill_report_reply(conv: dict, proc: dict | None, rep: dict, review, tail: dict, auto_wait: bool):
    """Khung kết quả điền + khung kết luận (bong bóng riêng); thẻ chặng điền chốt. None = luồng cũ."""
    from app.channels.handfree.chat.flow import Reply, _supplement_documents_chip

    if not enabled(conv, proc):
        return None
    small = [{"label": "🔁 Điền lại thông tin", "send": "__action:refill"}, _supplement_documents_chip()]
    reviewing = field_review.flow_v2(conv, proc) and isinstance(review, dict)
    stats = field_review.begin(conv, review) if reviewing else {"filled": rep["filled"]}
    r = Reply(*fill_result(conv, rep, stats))
    if reviewing:
        md, tts, chips = field_review.conclusion(conv, proc, small)
    else:
        # Chưa có vòng bổ sung ô: bước tiếp như luồng cũ (chuyển sang Thành phần hồ sơ / nút đính kèm).
        md, tts = tail["md"].strip(), tail["tts"]
        chips = small if auto_wait else [
            {"label": "📎 Đính kèm giấy tờ ▶", "send": "__action:confirm_review", "solid": True}, *small]
    r.actions = [_card(conv, "fill", vi.FLOW2_FILL_STEPS, active=2, done=True), {"type": "trail_message", "md": md}]
    r.tts_text += tts if tts.startswith(" ") else f" {tts}"
    r.chips = chips
    return r


def attach_planning_reply(conv: dict, proc: dict | None):
    """Planner đính kèm vừa chạy (sang Thành phần hồ sơ / bấm đính kèm): thẻ chặng đính kèm thay câu "đang xếp"."""
    from app.channels.handfree.chat.flow import Reply, _fmt

    if not enabled(conv, proc):
        return Reply(*_fmt(vi.ATTACH_PLANNING))
    return _silent([_card(conv, "attach", vi.FLOW2_ATTACH_STEPS, start=True)])


def attach_plan_reply(conv: dict, proc: dict | None, reply):
    """Kế hoạch xong và phát lệnh đính: thẻ sang bước "Đính kèm"; tệp → dòng nói ở khung kết quả đính kèm. Lý do
    planner bỏ tệp (nếu có) vẫn hiện ngay để cán bộ biết vì sao thiếu tệp."""
    if not enabled(conv, proc):
        return reply
    skipped = "; ".join(str(e) for e in (conv.get("attach_errors") or []) if e)[:300]
    r = _silent([_card(conv, "attach", vi.FLOW2_ATTACH_STEPS, active=1), *reply.actions])
    if skipped:
        r.display_md, r.tts_text = _say(vi.ATTACH_PLAN_SKIPPED_NOTE, skipped_note=skipped)
        r.display_md, r.tts_text = r.display_md.strip(), r.tts_text.strip()
    return r


def attach_failed_reply(conv: dict, proc: dict | None, reply):
    """Không đính được tệp nào: câu cũ (kèm nút Đính kèm lại), thẻ báo lỗi."""
    if enabled(conv, proc):
        reply.actions = [*reply.actions, _card(conv, "attach", vi.FLOW2_ATTACH_STEPS, active=1, failed=True)]
    return reply


def attach_done_reply(conv: dict, proc: dict | None, reply, *, attached: int, skipped: int, errors: list[str],
                      guided_step: bool, split: bool):
    """Khung kết quả đính kèm + khung bước tiếp (bong bóng riêng); thẻ chặng đính kèm chốt. Nút giữ như luồng cũ."""
    from app.channels.handfree.chat import flow

    if not enabled(conv, proc):
        return reply
    card = _card(conv, "attach", vi.FLOW2_ATTACH_STEPS, active=1, done=not errors, failed=bool(errors))
    if split or errors:
        # Tách nhiều hồ sơ / còn lỗi: câu cũ đã liệt kê đủ từng hồ sơ, từng lỗi.
        reply.actions = [*reply.actions, card]
        return reply
    if attached == 0 and skipped > 0:
        r = flow.Reply(*_say(vi.FLOW2_ATTACH_ALL_EXIST))
    else:
        plan_list = "\n".join(flow._attachment_plan_line(p) for p in (conv.get("attach_plan") or [])[:10])
        r = flow.Reply(*_say(vi.FLOW2_ATTACH_RESULT, attached=attached, plan_list=plan_list))
    if guided_step:
        md, tts = _say(vi.FLOW2_NEXT_RESULT_STEP, result_step=guided.step_labels(proc)["result_step"])
    else:
        md, tts = _say(vi.FLOW2_NEXT_SUBMIT)
    r.actions = [*reply.actions, card, {"type": "trail_message", "md": md}]
    r.tts_text += tts
    r.chips = [dict(c) for c in reply.chips]
    return r
