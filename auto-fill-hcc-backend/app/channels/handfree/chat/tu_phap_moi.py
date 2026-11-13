"""Tư pháp luồng mới — trang nộp MỘT TRANG của Cổng DVC quốc gia (dichvucong.gov.vn/nop-ho-so).

Khác luồng "tu-phap" (wizard 4 bước): bấm "Nộp trực tuyến" là vào thẳng trang có cả form,
bảng thành phần hồ sơ và ô "Hình thức nhận kết quả". Không chờ chuyển bước nào, mỗi chặng do
công dân bấm nút trong khung chat:

    nhận giấy tờ → điền form ─┬─ [Điền lại] [Điều chỉnh giấy tờ]
                              └─ [Đính kèm thành phần hồ sơ] → đính ─┬─ [Điều chỉnh giấy tờ]
                                                                    └─ [Chọn hình thức nhận kết quả]
                                → chọn sẵn cách đầu + thẻ 3 cách → [Lưu và nộp hồ sơ] → soát ô → bấm nộp

Planner đính kèm chạy nền ngay khi điền xong, nên lúc công dân bấm "Đính kèm" thường đã có kế
hoạch. flow.py chỉ gọi vào các hàm ở đây; phần chung (nhận giấy tờ, điền, đánh giá, đăng xuất)
vẫn đi đường cũ.

Luồng bản 2 (field_review.flow_v2 — extension khai thêm supportsFlowV2): mỗi khung một việc.
    nhận tệp → thẻ tiến trình (bóc tách → điền → đính kèm, cập nhật tại chỗ theo mốc thật)
    → kết quả điền → kết quả đính kèm → kết luận: còn ô bắt buộc thì chỉ mời bổ sung; đủ thì
    hiện [Chọn hình thức nhận kết quả] [Lưu và nộp hồ sơ].

Cổng Bộ VHTTDL (form liz, registry `lizFlow`) cũng là trang nộp một trang nên đi chung luồng này, chỉ khi extension khai
supportsLizFlow (bản cũ đi luồng chung điền → đính → tự nộp như trước). Chặng cuối khác: [Tiếp tục] → extension tích ô
cam kết (nút nộp của cổng chỉ mở sau khi tích) → hỏi có nhận kết quả qua bưu điện (ô VNPost) → [Lưu và nộp hồ sơ].
Extension khai thêm supportsLizCommitSelf (yêu cầu 10/11/2026, mọi thủ tục cổng Bộ VHTTDL): ô cam kết là một chặng riêng.
    điền + đính xong (kể cả còn ô bắt buộc trống) → dặn cần tích ô cam kết + nút cam [Tích ô cam kết]
        (extension theo dõi ô — liz_commit_watch — công dân tự tích trên trang cũng được)
        → bấm nút: trợ lý tích ô trên trang (liz_commit_tick)
        → __action:liz_commit_report → hỏi ô "Đề nghị nhận kết quả bản giấy tại nhà qua Bưu chính công ích (VNPost)"
          (user 13/11/2026): [Có, nhận qua bưu điện] [Không]
            không → "nhấn Lưu và nộp hồ sơ" + CHỈ nút cam [Lưu và nộp hồ sơ]
            có → trợ lý tích ô VNPost (không điền hộ khối người nhận) → dặn điền thông tin người nhận + chọn cách thanh
                 toán lệ phí → nút cam [Lưu và nộp hồ sơ]
            đổi ý sau khi đã trả lời (gõ / nói "tôi muốn đổi, nhận qua bưu điện", "không nhận qua bưu điện nữa", "đổi ý")
                 → router bắt tất định (liz_postal_by_text) rồi chạy như bấm nút trả lời kia: tích / bỏ tích ô VNPost
Nút nộp không tích hộ: chưa thấy ô được tích thì không bấm, trả commit=False → dặn bấm [Tích ô cam kết].
"""

import re

from app.channels.handfree.chat import attach_files
from app.channels.handfree.chat import field_review
from app.channels.handfree.chat import guided_steps as guided
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import Intent, fold

PROFILE = "tu-phap-moi"
CAPABILITY = "supportsTuPhapMoi"
# Luồng TỰ ĐỘNG: điền xong tự đính kèm, nút nộp/đổi cách nhận hiện ngay, nộp (bấm trên trang, bấm
# nút trong khung chat, hoặc lưới đỡ toast "Gửi hồ sơ thành công") ở bước nào cũng sang phần sau
# nộp. Extension cũ không khai cờ này → đi nguyên luồng bấm-từng-chặng bên dưới.
AUTO_CAPABILITY = "supportsTpmAutoFlow"
LIZ_CAPABILITY = "supportsLizFlow"
ADJUST_BOTH_LABEL = "✅ Đủ giấy tờ — điền & đính kèm lại"


def _v2(conv: dict, proc: dict | None) -> bool:
    # field_review.flow_v2 gồm cả tư pháp form cũ (chat/tu_phap_v2.py) → ở đây chỉ nhận trang một trang.
    return field_review.single_page(proc) and field_review.flow_v2(conv, proc)


def _v2_say(tpl: dict, **kw) -> tuple[str, str]:
    # Luồng bản 2 tắt ở chế độ Mông (field_review.active) → câu chỉ có bản tiếng Việt.
    return tpl["md"].format(**kw), tpl["tts"].format(**kw)


def steps_action(steps: tuple[str, ...] | None = None, *, active: int = 0, done: bool = False,
                 failed: bool = False) -> dict:
    """Thẻ tiến trình của luồng bản 2: có `steps` = dựng thẻ mới; không có = cập nhật thẻ đang hiện (bước `active`
    đang chạy, các bước trước đã xong; `done` = xong hết; `failed` = bước `active` lỗi)."""
    action = {"type": "pipeline_steps", "active": active}
    if steps:
        action["steps"] = list(steps)
    if done:
        action["done"] = True
    if failed:
        action["failed"] = True
    return action


def docs_received_reply(conv: dict, proc: dict | None, reply, files_count: int, *, all_received: bool):
    """Nhận tệp xong, pipeline điền bắt đầu chạy (luồng bản 2): câu không hứa số giây, kèm thẻ tiến trình 3 bước."""
    from app.channels.handfree.chat import flow

    if not _v2(conv, proc):
        return reply
    if all_received:
        reply = flow.Reply(*_v2_say(vi.FLOW2_DOCS_RECEIVED, files_count=files_count))
    reply.actions = [*reply.actions, steps_action(vi.FLOW2_STEPS)]
    return reply


def fill_started_reply(conv: dict, proc: dict | None, reply):
    """Dữ liệu điền về (luồng bản 2): không nói gì thêm — thẻ tiến trình sang bước "Điền tờ khai"; kết quả điền nói
    ở khung riêng khi extension báo điền xong (chú giải màu cũ của extension tắt)."""
    from app.channels.handfree.chat import flow

    if not _v2(conv, proc):
        return reply
    actions = [dict(a) for a in reply.actions]
    actions[0]["noLegend"] = True
    r = flow.Reply()
    r.actions = [steps_action(active=1), *actions]
    return r


def liz(proc: dict | None) -> bool:
    return bool((proc or {}).get("lizFlow"))


def liz_supported(conv: dict | None) -> bool:
    # Câu của chặng cuối liz chỉ có bản tiếng Việt → chế độ Mông giữ luồng chung.
    conv = conv or {}
    return ((conv.get("client_capabilities") or {}).get(LIZ_CAPABILITY) is True
            and (conv.get("lang") or "vi") != "hmong")


def liz_commit_self(conv: dict | None, proc: dict | None) -> bool:
    """Cổng liz, công dân tự tích ô cam kết (extension khai supportsLizCommitSelf)."""
    return field_review.liz_commit_self(conv, proc)


def is_active(proc: dict | None, conv: dict | None = None) -> bool:
    if not proc:
        return False
    if proc.get("flowProfile") == PROFILE:
        return True
    return liz(proc) and liz_supported(conv)


def supported(conv: dict) -> bool:
    return (conv.get("client_capabilities") or {}).get(CAPABILITY) is True


def auto_flow(conv: dict) -> bool:
    return supported(conv) and (conv.get("client_capabilities") or {}).get(AUTO_CAPABILITY) is True


def _submitted(conv: dict) -> bool:
    """Đã bấm nộp (hoặc cổng báo nộp xong): mọi kết quả về muộn không được phát câu/nút nữa."""
    return bool(conv.get("submit_clicked_at") or conv.get("submitted_completed"))


def tool_account(conv: dict) -> dict:
    """Tỉnh/xã của tài khoản quầy — engine FE dựng "Kính gửi"/"Tại" từ đây như Auto Fill."""
    user = conv.get("auth_user") or {}
    return {"tinh": str(user.get("tinh") or ""), "xa": str(user.get("xa") or "")}


# Nhãn ô do FE đọc nguyên văn trên trang, có kèm gợi ý định dạng "(dd/mm/yyyy)" — đọc lên chỉ gây rối.
_FORMAT_HINT = re.compile(r"\s*\(\s*(?:dd|mm|yyyy|yy|hh)\b[^)]*\)", re.IGNORECASE)


def _missing_labels(payload: dict) -> list[str]:
    labels = [_FORMAT_HINT.sub("", str(x)).strip() for x in (payload.get("missing") or [])]
    return [label for label in labels if label]


def _attach_cta() -> dict:
    return {"label": vi.TPM_ATTACH_CTA, "send": "__action:tpm_attach", "solid": True, "cta": True}


def _result_cta() -> dict:
    return {"label": vi.TPM_RESULT_CTA, "send": "__action:tpm_result_method", "solid": True, "cta": True}


def _submit_cta() -> dict:
    return {"label": vi.TPM_SUBMIT_CTA, "send": "__action:tpm_submit", "solid": True, "cta": True}


def _retry_attach_chip() -> dict:
    return {"label": "🔁 Đính kèm lại", "send": "__action:tpm_attach"}


def _liz_next_cta() -> dict:
    return {"label": vi.LIZ_NEXT_CTA, "send": "__action:tpm_result_method", "solid": True, "cta": True}


def _liz_commit_chip() -> dict:
    # Nút cam: bấm thì trợ lý tích ô cam kết trên trang.
    return {"label": vi.LIZ_COMMIT_CHIP, "send": "__action:liz_commit_tick", "solid": True, "cta": True}


LIZ_POSTAL_YES_SEND = '__action:liz_postal:{"post":true}'
LIZ_POSTAL_NO_SEND = '__action:liz_postal:{"post":false}'


def _liz_postal_chips() -> list[dict]:
    """Hai nút trả lời câu hỏi ô VNPost (sau khi tích ô cam kết)."""
    return [
        {"label": vi.LIZ_POSTAL_YES_CHIP, "send": LIZ_POSTAL_YES_SEND, "solid": True},
        {"label": vi.LIZ_POSTAL_NO_CHIP, "send": LIZ_POSTAL_NO_SEND, "solid": True},
    ]


def _liz_postal_answered(st: dict) -> bool:
    return st.get("liz_postal") in ("yes", "no")


def _liz_go_now(conv: dict) -> list[dict]:
    """Nút đi tiếp của chặng cuối liz (công dân tự tích): chưa tích ô cam kết → nút cam Tích ô cam kết; đã tích, chưa
    trả lời ô VNPost → hai nút Có / Không; trả lời rồi → nút cam Lưu và nộp hồ sơ."""
    st = conv.get("field_review") or {}
    if not st.get("liz_commit_ok"):
        return [_liz_commit_chip()]
    return [_submit_cta()] if _liz_postal_answered(st) else _liz_postal_chips()


def _liz_go_chips(proc: dict | None, conv: dict | None) -> list[dict]:
    if not liz_commit_self(conv, proc):
        return [_liz_next_cta()]
    return _liz_go_now(conv)


def _final_chips(proc: dict | None = None, conv: dict | None = None) -> list[dict]:
    """Sau khi điền + đính: 3 nút sửa nhỏ, 2 nút đi tiếp to (cách nhận kết quả, nộp). Cổng liz: một nút Tiếp tục
    (tích cam kết rồi hỏi bưu điện), nút nộp chỉ hiện sau câu hỏi đó; công dân tự tích ô cam kết thì nút "Tôi đã tích ô
    cam kết", tích xong mới tới nút nộp."""
    from app.channels.handfree.chat import flow

    return [
        flow._supplement_documents_chip(),
        {"label": "🔁 Điền lại", "send": "__action:refill"},
        {"label": "📎 Đính kèm lại", "send": "__action:tpm_attach"},
        *(_liz_go_chips(proc, conv) if liz(proc) else [_result_cta(), _submit_cta()]),
    ]


def adjust_choice_chips() -> list[dict]:
    """Hai nút nhỏ cạnh nút chốt "điền & đính kèm lại" khi công dân điều chỉnh giấy tờ."""
    return [
        {"label": "🔁 Đã đủ giấy tờ - Điền lại tờ khai",
         "send": '__action:tpm_adjust_done:{"then":"declaration"}'},
        {"label": "📎 Đã đủ giấy tờ - Đính kèm lại",
         "send": '__action:tpm_adjust_done:{"then":"attachment"}'},
    ]


def _default_result_note(proc: dict) -> tuple[dict, str]:
    """Câu báo cách nhận kết quả đang để mặc định (cổng chọn sẵn) — tên lấy theo registry."""
    method = guided.default_result_method(proc) or {}
    label = str(method.get("label") or "")
    return (vi.TPM_AUTO_RESULT_DEFAULT if label else vi.TPM_SUBMIT_HINT), label


def update_required_reply(conv: dict):
    from app.channels.handfree.chat import flow

    r = flow.Reply(*flow._fmt(vi.TPM_UPDATE_REQUIRED, procedure=flow._proc_label(conv)))
    r.chips = [{"label": "🆕 Làm thủ tục khác", "send": "__action:new_procedure"}]
    return r


def _spawn_attach_planner(conv: dict) -> None:
    from app.channels.handfree.chat import flow, pipeline_runner

    conv["attach_plan"] = []
    conv["attach_errors"] = []
    conv["attachment_plan_started"] = True
    conv["pipeline_status"] = "running"
    flow._clear_attach_action(conv)
    pipeline_runner.spawn(pipeline_runner.run_attach(
        conv["_id"], conv.get("upload_session_id") or "", conv.get("procedure_key") or "",
        flow._attachment_options(conv),
    ))


def on_fields_ready(conv: dict) -> None:
    """Luồng tự động: dữ liệu điền vừa về (extension bắt đầu điền form) → lập kế hoạch đính kèm
    NGAY lúc này. OCR đã vào cache từ lượt bóc dữ liệu nên planner đọc lại cache, không OCR lần
    hai; chạy song song từ đầu thì hai lượt cùng OCR mà chưa lượt nào kịp ghi cache."""
    if conv.get("tpm_auto_attach") is False:
        return
    _spawn_attach_planner(conv)


async def _auto_fill_report_reply(conv: dict, rep: dict, proc: dict, review=None):
    from app.channels.handfree.chat import flow, tracing

    await tracing.set_report(conv.get("trace_request_id"), "autofill", rep)
    if _v2(conv, proc) and isinstance(review, dict):
        flow._clear_documents_adjustment(conv)
        return await _v2_fill_report_reply(conv, rep, proc, review)
    missing = rep["notFound"]
    missing_note = f"\n\n⚠️ **{len(missing)} ô chưa khớp được**: {', '.join(missing[:8])}" if missing else ""
    flow._clear_documents_adjustment(conv)
    if conv.get("tpm_auto_attach") is False:
        # "Điền lại" / "Đã đủ giấy tờ - Điền lại tờ khai": giấy tờ trên trang giữ nguyên.
        conv["tpm_auto_attach"] = True
        conv["state"] = "done"
        r = flow.Reply(*flow._fmt(vi.FILL_REPORT_REVIEW, filled=rep["filled"],
                                  missing_note=missing_note, note=vi.TPM_SUBMIT_HINT))
        r.chips = _final_chips(proc, conv)
        field_review.decorate_single_page_fill(conv, proc, r, review, offer=True)
        return r
    conv["state"] = "attaching"
    conv["attach_done"] = False
    conv["tpm_attach_requested"] = True
    if conv.get("pipeline_status") == "attach_ready" and not conv.get("attach_action_in_progress"):
        # Kế hoạch đã sẵn: một bong bóng gồm báo điền + KẾ HOẠCH ĐÍNH KÈM (tệp nào → dòng nào) như
        # nhánh kế hoạch về sau. Hai phần đều qua _fmt nên chế độ Mông vẫn đúng tiếng ở từng phần.
        fill_md, fill_tts = flow._fmt(vi.FILL_REPORT_REVIEW, filled=rep["filled"],
                                      missing_note=missing_note)
        attach = await flow._handle_attaching(conv, Intent("event", "attach_ready"))
        r = flow.Reply(f"{fill_md}\n\n{attach.display_md}".strip(),
                       f"{fill_tts} {attach.tts_text}".strip())
        r.actions = attach.actions
        field_review.decorate_single_page_fill(conv, proc, r, review, offer=False)
        return r
    if not (conv.get("attachment_plan_started") and conv.get("pipeline_status") == "running"):
        _spawn_attach_planner(conv)  # chưa chạy (phiên cũ) hoặc lượt lập kế hoạch vừa lỗi
    r = flow.Reply(*flow._fmt(vi.FILL_REPORT_REVIEW, filled=rep["filled"],
                              missing_note=missing_note, note=vi.TPM_AUTO_ATTACH_WAIT))
    field_review.decorate_single_page_fill(conv, proc, r, review, offer=False)
    return r


def fill_result(conv: dict, rep: dict, stats: dict) -> tuple[str, str]:
    """Khung kết quả điền (luồng bản 2, dùng cả ở tư pháp form cũ): số ô xanh cổng đang hiện (khớp đúng số ô công dân
    thấy tô xanh — chưa có vòng bổ sung ô thì là số ô engine điền được), ô điền mặc định (viền vàng), ô engine không
    khớp được trên trang."""
    defaults = sum(1 for f in conv.get("fields") or [] if isinstance(f, dict) and f.get("default"))
    default_md, default_tts = _v2_say(vi.FLOW2_FILL_DEFAULT, count=defaults) if defaults else ("", "")
    missing = [str(m) for m in rep.get("notFound") or []]
    not_found_md = (vi.FLOW2_FILL_NOT_FOUND.format(count=len(missing), labels=", ".join(missing[:8]))
                    if missing else "")
    return _v2_say(vi.FLOW2_FILL_RESULT, filled=stats["filled"], default_md=default_md, default_tts=default_tts,
                   not_found_md=not_found_md)


async def _v2_fill_report_reply(conv: dict, rep: dict, proc: dict, review: dict):
    from app.channels.handfree.chat import flow

    stats = field_review.begin(conv, review)
    r = flow.Reply(*fill_result(conv, rep, stats))
    if conv.get("tpm_auto_attach") is False:
        # "Điền lại": giấy tờ trên trang giữ nguyên → thẻ 2 bước xong, kết luận ngay.
        conv["tpm_auto_attach"] = True
        conv["state"] = "done"
        md, tts, chips = field_review.conclusion(conv, proc, _final_chips(proc, conv))
        r.actions = [steps_action(active=2, done=True), {"type": "trail_message", "md": md}]
        r.tts_text += tts
        r.chips = chips
        return r
    conv["state"] = "attaching"
    conv["attach_done"] = False
    conv["tpm_attach_requested"] = True
    r.actions = [steps_action(active=2)]
    if conv.get("pipeline_status") == "attach_ready" and not conv.get("attach_action_in_progress"):
        attach = await flow._handle_attaching(conv, Intent("event", "attach_ready"))
        r.actions = [*r.actions, *attach.actions]
        return r
    if not (conv.get("attachment_plan_started") and conv.get("pipeline_status") == "running"):
        _spawn_attach_planner(conv)
    return r


async def fill_report_reply(conv: dict, rep: dict, review=None):
    """Điền xong: lập kế hoạch đính kèm ở nền, chờ công dân rà form rồi bấm nút đính kèm.
    `review`: số ô xanh/cam/đỏ extension đếm sau khi điền (vòng bổ sung ô, chỉ ở luồng tự động)."""
    from app.channels.handfree.chat import flow, tracing

    if auto_flow(conv):
        proc = flow.get_procedure(conv.get("procedure_key") or "") or {}
        return await _auto_fill_report_reply(conv, rep, proc, review)

    conv["state"] = "attaching"
    conv["attach_done"] = False
    conv["tpm_attach_requested"] = False
    _spawn_attach_planner(conv)
    await tracing.set_report(conv.get("trace_request_id"), "autofill", rep)
    missing = rep["notFound"]
    note = f"\n\n⚠️ **{len(missing)} ô chưa khớp được**: {', '.join(missing[:8])}" if missing else ""
    r = flow.Reply(*flow._fmt(vi.FILL_REPORT_REVIEW, filled=rep["filled"], missing_note=note,
                              note=vi.TPM_FILL_NEXT))
    flow._clear_documents_adjustment(conv)
    r.chips = [
        {"label": "🔁 Điền lại thông tin", "send": "__action:refill"},
        flow._supplement_documents_chip(),
        _attach_cta(),
    ]
    return r


async def _request_attach(conv: dict):
    """Công dân bấm "Đính kèm thành phần hồ sơ" (hoặc "Đính kèm lại")."""
    from app.channels.handfree.chat import flow

    conv["tpm_attach_requested"] = True
    if conv.get("state") == "done":
        conv["state"] = "attaching"
        conv["attach_done"] = False
    if conv.get("attach_action_in_progress"):
        return flow.Reply(*flow._fmt(vi.ATTACH_RUNNING))
    if (conv.get("pipeline_status") == "attach_ready" and conv.get("attach_plan")
            and not flow._attach_plan_settings_changed(conv)):
        return await flow._handle_attaching(conv, Intent("event", "attach_ready"))
    if conv.get("pipeline_status") == "running" and conv.get("attachment_plan_started"):
        return flow.Reply(*flow._fmt(vi.TPM_ATTACH_WAIT_PLAN))
    # Chưa có kế hoạch hoặc lượt trước lỗi → lập lại trên chính phiên tệp hiện tại.
    _spawn_attach_planner(conv)
    return flow.Reply(*flow._fmt(vi.ATTACH_PLANNING))


def _v2_attach_done_reply(conv: dict, proc: dict, attached: int, skipped: int, errors: list[str]):
    """Khung kết quả đính kèm + khung kết luận (bong bóng riêng); thẻ tiến trình chốt."""
    from app.channels.handfree.chat import flow

    conv.setdefault("field_review", {})["attach_failed"] = bool(errors)
    if errors:
        r = flow.Reply(*_v2_say(vi.FLOW2_ATTACH_ERRORS, attached=attached,
                                error_list="\n".join(f"- {e}" for e in errors[:5])))
    elif attached == 0 and skipped > 0:
        r = flow.Reply(*_v2_say(vi.FLOW2_ATTACH_ALL_EXIST))
    else:
        plan_list = "\n".join(flow._attachment_plan_line(p) for p in (conv.get("attach_plan") or [])[:10])
        r = flow.Reply(*_v2_say(vi.FLOW2_ATTACH_RESULT, attached=attached, plan_list=plan_list))
    md, tts, chips = field_review.conclusion(conv, proc, _final_chips(proc, conv))
    r.actions = [steps_action(active=2, done=not errors, failed=bool(errors)), {"type": "trail_message", "md": md}]
    r.tts_text += tts
    r.chips = chips
    return r


def _auto_attach_done_reply(conv: dict, proc: dict, attached: int, skipped: int, errors: list[str]):
    from app.channels.handfree.chat import flow

    if _v2(conv, proc) and (conv.get("field_review") or {}).get("stats"):
        return _v2_attach_done_reply(conv, proc, attached, skipped, errors)
    note, label = _default_result_note(proc)
    if errors:
        error_list = "\n".join(f"- {e}" for e in errors[:5])
        r = flow.Reply(*flow._fmt(vi.TPM_ATTACH_DONE_WITH_ERRORS, attached=attached,
                                  error_list=error_list, note=note, label=label))
    else:
        template = vi.TPM_AUTO_ALL_EXIST if attached == 0 and skipped > 0 else vi.TPM_AUTO_ATTACH_DONE
        r = flow.Reply(*flow._fmt(template, attached=attached, note=note, label=label))
    r.chips = _final_chips(proc, conv)
    field_review.offer_after_attach(conv, proc, r)
    return r


def _attach_done_reply(conv: dict, payload: dict):
    from app.channels.handfree.chat import flow

    attached = int(payload.get("attached") or 0)
    skipped = int(payload.get("skipped") or 0)
    errors = [str(e) for e in (payload.get("errors") or []) if e]
    if auto_flow(conv):
        proc = flow.get_procedure(conv.get("procedure_key") or "") or {}
        return _auto_attach_done_reply(conv, proc, attached, skipped, errors)
    if errors:
        error_list = "\n".join(f"- {e}" for e in errors[:5])
        r = flow.Reply(*flow._fmt(vi.TPM_ATTACH_DONE_WITH_ERRORS, attached=attached,
                                  error_list=error_list))
        r.chips = [_retry_attach_chip(), flow._supplement_documents_chip(), _result_cta()]
        return r
    template = vi.TPM_ATTACH_ALL_EXIST if attached == 0 and skipped > 0 else vi.TPM_ATTACH_DONE
    r = flow.Reply(*flow._fmt(template, attached=attached))
    r.chips = [flow._supplement_documents_chip(), _result_cta()]
    return r


def _liz_page_action(proc: dict, action: dict | None, key: str = "", conv: dict | None = None) -> dict | None:
    """Cổng liz: mỗi lệnh chặng cuối kèm nhãn ô cam kết (extension tích trước — nút nộp của cổng chỉ mở sau khi tích)
    và, với lệnh chọn cách nhận, trạng thái cần có của ô "nhận kết quả qua bưu chính" (VNPost).
    Công dân tự tích ô cam kết: chọn cách nhận chỉ gạt ô VNPost; nộp thì gửi nhãn + commitSelf để extension soát ô đã
    được tích (chưa tích thì không bấm, không tích hộ)."""
    if not action or not liz(proc):
        return action
    label = field_review.liz_commit_label(proc)
    postal = {"postOffice": key == "postal"} if action.get("type") == "select_result_method" else {}
    if liz_commit_self(conv, proc):
        return {**action, **postal} if postal else {**action, "commitLabel": label, "commitSelf": True}
    return {**action, "commitLabel": label, **postal}


def _result_card_action(conv: dict, proc: dict, key: str) -> tuple[dict, list]:
    conv["result_method"] = key
    action = _liz_page_action(proc, guided.select_result_method_action(proc, key), key, conv)
    return guided.result_methods_card(proc, key), [action] if action else []


def _liz_commit_st(conv: dict) -> dict:
    return conv.setdefault("field_review", {})


_LIZ_GO_SENDS = frozenset({"__action:liz_commit_tick", "__action:tpm_submit", LIZ_POSTAL_YES_SEND, LIZ_POSTAL_NO_SEND})


def _liz_refresh_go(conv: dict) -> None:
    """Bộ nút đã lưu của lượt điền (hiện lại khi hỏi xong vòng bổ sung / công dân tự gõ đủ ô): thay nút đi tiếp cũ bằng
    nút đúng chặng hiện tại (Tích ô cam kết → Có / Không nhận qua bưu điện → Lưu và nộp hồ sơ)."""
    st = _liz_commit_st(conv)
    if not st.get("chips"):
        return
    out, placed = [], False
    for chip in st["chips"]:
        if chip.get("send") not in _LIZ_GO_SENDS:
            out.append(chip)
        elif not placed:
            out.extend(dict(c) for c in _liz_go_now(conv))
            placed = True
    st["chips"] = out


def _liz_required_note(st: dict) -> str:
    required = int((st.get("stats") or {}).get("required") or 0)
    return vi.LIZ_COMMIT_REQUIRED_NOTE.format(required=required) if required else ""


def _liz_commit_ok_reply(conv: dict, proc: dict):
    """Ô cam kết đã được tích → hỏi có đề nghị nhận kết quả bản giấy qua VNPost không (user 13/11) + hai nút Có / Không.
    Đã trả lời câu đó (ô cam kết bị bỏ tích rồi tích lại) → dặn nhấn Lưu và nộp hồ sơ, chỉ một nút cam nộp. Tờ khai còn
    ô bắt buộc trống thì nhắc điền nốt."""
    from app.channels.handfree.chat import flow

    st = _liz_commit_st(conv)
    st["liz_commit_ok"] = True
    _liz_refresh_go(conv)
    note = _liz_required_note(st)
    if _liz_postal_answered(st):
        r = flow.Reply(*_v2_say(vi.LIZ_COMMIT_OK, required_note=note))
        r.chips = [_submit_cta()]
        return r
    st["liz_postal"] = "asked"
    r = flow.Reply(*_v2_say(vi.LIZ_POSTAL_ASK, required_note=note))
    r.chips = _liz_postal_chips()
    return r


def liz_postal_waiting(conv: dict, proc: dict | None) -> bool:
    """Đang chờ công dân trả lời có nhận kết quả qua VNPost không (đã tích ô cam kết, chưa trả lời, chưa nộp)."""
    st = conv.get("field_review") or {}
    return (liz_commit_self(conv, proc) and conv.get("state") == "done" and bool(st.get("liz_commit_ok"))
            and not _liz_postal_answered(st) and not st.get("running") and not _submitted(conv))


# ── Câu gõ / nói ở chặng ô VNPost ──
# Bắt tất định ở router, TRƯỚC vòng hỏi ô và bộ phân loại LLM (user 13/11): công dân đã trả lời Không rồi gõ "Tôi muốn
# đổi, nhận qua bưu điện" thì LLM hiểu chữ "đổi" là Điều chỉnh giấy tờ; chữ "Không" gõ trơn ra câu chưa rõ (hỏi lại).
# Câu có chữ bưu điện / bưu chính / VNPost / giao tận nhà (hoặc nhận trực tiếp, một cửa) là chọn cách nhận; có phủ định
# đi liền ("không nhận", "khỏi gửi", "bỏ tích") là Không. Câu hỏi (bao lâu, phí…) để LLM trả lời như cũ.
_POSTAL_SAID = re.compile(
    r"(?:^|\s)(?:buu dien|buu chinh|buu cuc|vnpost|vn post"
    r"|(?:gui|giao|chuyen|ship|nhan|mang)\s+(?:(?:ve|tai|o|toi|den|tan)\s+){1,2}nha)(?:\s|$)")
_COUNTER_SAID = re.compile(r"(?:^|\s)(?:nhan truc tiep|lay truc tiep|den (?:lay|nhan)|tu (?:den|lay)|mot cua)(?:\s|$)")
_POSTAL_NEG = re.compile(
    r"(?:^|\s)(?:(?:khong|khoi)\s+(?:nhan|gui|qua|can|muon|lay|chon|tich|dung|phai|di|buu|giao)"
    r"|(?:bo|huy)\s+(?:tich|chon|o|nhan)|dung\s+(?:gui|nhan|tich|chon)"
    r"|(?:buu dien|buu chinh|vnpost)\s+(?:thi\s+)?(?:khong|thoi)\s+(?:can|nhan|nua|dau|lay))(?:\s|$)")
_POSTAL_QUESTION = re.compile(r"(?:^|\s)(?:bao lau|bao nhieu|the nao|la gi|tai sao|vi sao|o dau|khi nao|phi)(?:\s|$)")
# Không liệt kê đại từ em ở hai bảng dưới: test_tro_ly_xung_toi quét mọi chuỗi của file này (trợ lý xưng tôi); câu
# kiểu "em đổi ý" không khớp thì để bộ phân loại chung lo như trước.
_POSTAL_DOI_Y = re.compile(r"(?:(?:toi|minh|thoi|muon|cho)\s+)*doi y(?:\s+(?:roi|lai|nhe|nha))*")
_POSTAL_FILLER = frozenset({"a", "da", "nhe", "nha", "oi", "anh", "chi"})
_POSTAL_YES_BARE = frozenset({"co", "vang", "vang co", "co nhan", "dong y", "co dong y", "u", "ok"})
_POSTAL_NO_BARE = frozenset({"khong", "khong nhan", "khong can", "khong co", "khong dong y", "thoi khong"})
_POSTAL_MAX_WORDS = 20


def _postal_choice(words: list[str], current: str, bare: bool) -> bool | None:
    said = " ".join(words)
    postal = bool(_POSTAL_SAID.search(said))
    if postal or _COUNTER_SAID.search(said):
        return postal and not _POSTAL_NEG.search(said)
    if bare:
        core = " ".join(w for w in words if w not in _POSTAL_FILLER)
        if core in _POSTAL_YES_BARE:
            return True
        if core in _POSTAL_NO_BARE:
            return False
    if current in ("yes", "no") and _POSTAL_DOI_Y.fullmatch(said):
        return current == "no"  # chỉ hai lựa chọn: "đổi ý" là chọn cái còn lại
    return None


def liz_postal_by_text(conv: dict, proc: dict | None, message: str, *, typed: bool = False) -> Intent | None:
    """Câu gõ / nói trả lời hoặc ĐỔI Ý câu hỏi ô VNPost (đã tích ô cam kết, chưa nộp) → lệnh liz_postal như bấm nút
    Có / Không; None = câu không nói về việc đó, để bộ phân loại chung lo. "Có" / "Không" trơn chỉ nhận khi đang chờ trả
    lời và là câu GÕ (lời nói ngắn có thể là tạp âm qua ASR — để lớp cách nói xét). Đang hỏi ô người nhận mà câu không
    đổi câu trả lời (vd địa chỉ có chữ "bưu điện") thì để vòng hỏi hiểu."""
    st = conv.get("field_review") or {}
    current = str(st.get("liz_postal") or "")
    if (current not in ("asked", "yes", "no") or conv.get("state") != "done" or not st.get("liz_commit_ok")
            or _submitted(conv) or not liz_commit_self(conv, proc)):
        return None
    words = re.findall(r"[a-z0-9]+", fold(message))
    if not words or len(words) > _POSTAL_MAX_WORDS or _POSTAL_QUESTION.search(" ".join(words)):
        return None
    post = _postal_choice(words, current, bare=typed and liz_postal_waiting(conv, proc))
    if post is None or (field_review.asking(conv) and post == (current == "yes")):
        return None
    return Intent("action", "liz_postal", {"post": post})


def _liz_postal_action(proc: dict, conv: dict, post: bool) -> dict | None:
    """Lệnh gạt ô VNPost. fillRecipient=False: tích xong không điền hộ khối người nhận, công dân tự điền (user 13/11) —
    extension chỉ trả các ô người nhận còn trống để trợ lý kể tên."""
    key = "postal" if post else "counter"
    action = _liz_page_action(proc, guided.select_result_method_action(proc, key), key, conv)
    if not action:
        return None
    conv["result_method"] = key
    return {**action, "fillRecipient": False}


def _liz_postal_reply(conv: dict, proc: dict, post: bool):
    """Công dân trả lời câu hỏi ô VNPost. Có → trợ lý tích ô (câu dặn điền khối người nhận nói khi extension báo lại);
    Không → nhấn Lưu và nộp hồ sơ (ô đã lỡ tích theo lần trả lời trước thì bỏ tích)."""
    from app.channels.handfree.chat import flow

    if _submitted(conv):
        return flow.Reply()
    st = _liz_commit_st(conv)
    before = st.get("liz_postal")
    st["liz_postal"] = "yes" if post else "no"
    _liz_refresh_go(conv)
    if post:
        r = flow.Reply()
        action = _liz_postal_action(proc, conv, True)
        r.actions = [action] if action else []
        return r
    r = flow.Reply(*_v2_say(vi.LIZ_POSTAL_NO, required_note=_liz_required_note(st)))
    r.chips = [_submit_cta()]
    if before == "yes":
        action = _liz_postal_action(proc, conv, False)
        r.actions = [action] if action else []
    else:
        conv["result_method"] = "counter"
    return r


async def _liz_recipient_ask_reply(conv: dict, proc: dict):
    """Vừa tích ô VNPost: mở luôn vòng hỏi từng ô còn trống (như nút "Bổ sung các thông tin còn thiếu") — trợ lý hỏi
    Tên / Số điện thoại / Địa chỉ người nhận, Đơn vị hành chính…; công dân nói hoặc gõ ("tên người nhận: …"), LLM của
    vòng bổ sung hiểu rồi extension điền đúng ô. Câu mở đầu đã nói cách làm → bỏ câu giới thiệu chung của vòng hỏi."""
    from app.channels.handfree.chat import flow

    started = await field_review.handle(conv, proc, Intent("action", "field_review_start", {}))
    st = _liz_commit_st(conv)
    st["intro"] = False
    st["loop_started_now"] = True  # finalize không dừng vòng vừa mở trong lượt result_method_report
    r = flow.Reply(*_v2_say(vi.LIZ_POSTAL_YES_ASK))
    r.actions = list((started or flow.Reply()).actions)
    return r


async def _liz_postal_report_reply(conv: dict, proc: dict, payload: dict):
    """Extension báo đã gạt ô VNPost theo câu trả lời. Có: trợ lý hỏi lần lượt ô người nhận còn trống (vòng bổ sung),
    extension không có vòng bổ sung thì kể tên ô + dặn chọn cách thanh toán lệ phí; Không: đã nói ở lượt trả lời, chỉ
    lên tiếng khi bỏ tích không được."""
    from app.channels.handfree.chat import flow

    st = _liz_commit_st(conv)
    post = st.get("liz_postal") == "yes"
    if str(payload.get("method") or "") != ("postal" if post else "counter"):
        return flow.Reply()  # báo muộn của câu trả lời trước (công dân vừa đổi ý)
    if not payload.get("ok"):
        r = flow.Reply(*_v2_say(vi.LIZ_POSTAL_FAILED if post else vi.LIZ_POSTAL_UNTICK_FAILED))
    elif not post:
        return flow.Reply()
    elif field_review.active(conv, proc) and not st.get("running") and _missing_labels(payload):
        return await _liz_recipient_ask_reply(conv, proc)
    else:
        missing = _missing_labels(payload)
        filled = [str(x).strip() for x in (payload.get("filled") or []) if str(x).strip()]
        if not missing and filled:
            r = flow.Reply(*_v2_say(vi.LIZ_POSTAL_YES_FILLED))  # extension bản cũ tự điền theo người nộp
        else:
            r = flow.Reply(*_v2_say(vi.LIZ_POSTAL_YES,
                                    missing=", ".join(missing) if missing else vi.LIZ_POSTAL_RECIPIENT_DEFAULT))
    r.chips = [_submit_cta()]
    return r


def _liz_commit_tick_reply(proc: dict):
    """Công dân bấm nút cam "Tích ô cam kết" → extension tích ô trên trang rồi báo liz_commit_report (source "tick")."""
    from app.channels.handfree.chat import flow

    r = flow.Reply()
    r.actions = [{"type": "liz_commit_tick", "commitLabel": field_review.liz_commit_label(proc)}]
    return r


def _liz_commit_wait_reply(conv: dict, proc: dict, template: dict):
    """Ô cam kết chưa được tích: dặn, theo dõi lại ô, nút cam "Tích ô cam kết"."""
    from app.channels.handfree.chat import flow

    st = _liz_commit_st(conv)
    st["liz_commit_ok"] = False
    st["liz_commit_asked"] = True
    _liz_refresh_go(conv)
    r = flow.Reply(*_v2_say(template, commit=field_review.liz_commit_label(proc)))
    r.actions = [field_review.liz_commit_watch_action(proc)]
    r.chips = [_liz_commit_chip()]
    return r


def _liz_commit_check_reply(proc: dict):
    """Nhờ extension đọc ô cam kết (công dân nói lúc đang chờ tích / nút "Tôi đã tích ô cam kết" của bản trước còn trên
    màn hình) → liz_commit_report."""
    from app.channels.handfree.chat import flow

    r = flow.Reply()
    r.actions = [{"type": "liz_commit_check", "commitLabel": field_review.liz_commit_label(proc)}]
    return r


def _liz_commit_report_reply(conv: dict, proc: dict, payload: dict):
    """Extension báo trạng thái ô cam kết. `source`: "watch" = đọc lúc bắt đầu theo dõi (chỉ báo khi đã tích sẵn),
    "change" = công dân vừa tích / bỏ tích trên trang, "tick" = trợ lý vừa tích theo nút cam, "manual" = công dân nói
    "tích rồi"."""
    from app.channels.handfree.chat import flow

    st = _liz_commit_st(conv)
    source = str(payload.get("source") or "manual")
    checked = payload.get("checked") is True
    if source in ("manual", "tick") and payload.get("found") is False:
        # Cổng đổi chữ ô cam kết → không chặn công dân: tự tích rồi nộp (vẫn hỏi ô VNPost nếu chưa hỏi).
        st["liz_commit_ok"] = True
        _liz_refresh_go(conv)
        commit = field_review.liz_commit_label(proc)
        if _liz_postal_answered(st):
            r = flow.Reply(*_v2_say(vi.LIZ_COMMIT_NOT_FOUND, commit=commit))
            r.chips = [_submit_cta()]
            return r
        st["liz_postal"] = "asked"
        r = flow.Reply(*_v2_say(vi.LIZ_COMMIT_NOT_FOUND_POSTAL, commit=commit))
        r.chips = _liz_postal_chips()
        return r
    if checked:
        if st.get("liz_commit_ok") and source == "change":
            return flow.Reply()
        if not st.get("liz_commit_asked") and source not in ("manual", "tick"):
            return flow.Reply()  # tích trước khi trợ lý dặn (còn đang đính) → nói khi tới lượt
        return _liz_commit_ok_reply(conv, proc)
    if source == "tick":
        return _liz_commit_wait_reply(conv, proc, vi.LIZ_COMMIT_TICK_FAILED)
    if source == "manual":
        return _liz_commit_wait_reply(conv, proc, vi.LIZ_COMMIT_NOT_TICKED)
    if source == "change" and st.get("liz_commit_ok"):
        return _liz_commit_wait_reply(conv, proc, vi.LIZ_COMMIT_UNTICKED)
    return flow.Reply()


async def _handle_liz_commit(conv: dict, proc: dict, intent: Intent):
    """Chặng tích ô cam kết của cổng liz (công dân tự tích). None = không phải lượt của chặng này."""
    from app.channels.handfree.chat import flow

    if not liz_commit_self(conv, proc):
        return None
    if intent.kind == "action" and intent.value == "liz_commit_report":
        if _submitted(conv):
            return flow.Reply()
        return _liz_commit_report_reply(conv, proc, intent.payload or {})
    if intent.kind == "action" and intent.value == "liz_commit_tick":
        return _liz_commit_tick_reply(proc)
    if intent.kind == "action" and intent.value == "liz_commit_done":
        return _liz_commit_check_reply(proc)
    if intent.kind == "action" and intent.value == "liz_postal":
        return _liz_postal_reply(conv, proc, (intent.payload or {}).get("post") is True)
    if (intent.kind == "action" and intent.value == "result_method_report" and conv.get("state") == "done"
            and _liz_postal_answered(conv.get("field_review") or {})):
        if _submitted(conv):
            return flow.Reply()
        return await _liz_postal_report_reply(conv, proc, intent.payload or {})
    if liz_postal_waiting(conv, proc):
        # Đang chờ trả lời ô VNPost: "có" / "không đồng ý" nói hoặc gõ → trả lời câu đó; câu khác không rõ → hỏi lại.
        if intent.kind in ("confirm", "deny"):
            return _liz_postal_reply(conv, proc, intent.kind == "confirm")
        if intent.kind == "unknown":
            r = flow.Reply(*_v2_say(vi.LIZ_POSTAL_REASK))
            r.chips = _liz_postal_chips()
            return r
    st = conv.get("field_review") or {}
    waiting = (conv.get("state") == "done" and st.get("liz_commit_asked") and not st.get("liz_commit_ok")
               and not st.get("running") and not _submitted(conv))
    if waiting and intent.kind not in {"event", "action"}:
        # Đang chờ tích mà công dân nói / gõ (thường là "tích rồi") → đọc ô trên trang rồi trả lời theo đó.
        return _liz_commit_check_reply(proc)
    if intent.kind == "action" and intent.value == "tpm_result_method" and conv.get("state") == "done":
        # Nút "Tiếp tục" của luồng cũ còn trên màn hình → không tích hộ, đi theo chặng tự tích.
        if st.get("liz_commit_ok"):
            return _liz_commit_ok_reply(conv, proc)
        return _liz_commit_wait_reply(conv, proc, vi.LIZ_COMMIT_REMIND)
    return None


def _liz_result_step_reply(conv: dict, proc: dict):
    """Cổng liz bấm Tiếp tục: tích ô cam kết + giữ cách nhận đang chọn (mặc định không qua bưu điện), hỏi có nhận qua
    bưu điện không. Bấm lại sau khi đã chọn bưu điện thì không được bỏ tích ô VNPost."""
    from app.channels.handfree.chat import flow

    key = conv.get("result_method") or str((guided.default_result_method(proc) or {}).get("key") or "")
    card, actions = _result_card_action(conv, proc, key)
    conv.setdefault("field_review", {})["liz_result_step"] = True
    r = flow.Reply(*_v2_say(vi.LIZ_RESULT_ASK))
    r.cards = [card]
    r.actions = actions
    r.chips = [_submit_cta()]
    return r


def _result_step_reply(conv: dict, proc: dict):
    """Chọn sẵn cách đầu (cổng cũng để sẵn cách này) rồi hiện thẻ 3 cách để công dân đổi."""
    from app.channels.handfree.chat import flow

    if liz(proc):
        return _liz_result_step_reply(conv, proc)
    method = guided.default_result_method(proc) or {}
    card, actions = _result_card_action(conv, proc, str(method.get("key") or ""))
    r = flow.Reply(*flow._fmt(vi.TPM_RESULT_PICK, label=str(method.get("label") or ""),
                              note=vi.TPM_SUBMIT_HINT))
    r.cards = [card]
    r.actions = actions
    r.chips = [_submit_cta()]
    return r


def _pick_result_method_reply(conv: dict, proc: dict, payload: dict):
    from app.channels.handfree.chat import flow

    key = str(payload.get("method") or "")
    if not guided.result_method(proc, key):
        return flow.Reply()
    card, actions = _result_card_action(conv, proc, key)
    r = flow.Reply()
    r.cards = [card]
    r.actions = actions
    r.chips = [_submit_cta()]
    return r


def _result_method_report_reply(conv: dict, proc: dict, payload: dict):
    """FE báo đã chọn trên ô "Hình thức nhận kết quả"; bưu điện thì kèm ô đã điền theo người yêu
    cầu trên tờ khai (`filled`) và ô còn trống (`missing`)."""
    from app.channels.handfree.chat import flow

    key = str(payload.get("method") or conv.get("result_method") or "")
    method = guided.result_method(proc, key) or {}
    label = str(method.get("label") or "")
    if not payload.get("ok"):
        r = flow.Reply(*flow._fmt(vi.TPM_RESULT_FAILED, label=label))
    elif liz(proc) and payload.get("commit") is False:
        # Nút nộp của cổng liz chỉ mở sau khi tích ô cam kết → báo trước mọi chuyện khác.
        r = flow.Reply(*_v2_say(vi.LIZ_COMMIT_FAILED, label=label))
    else:
        missing = _missing_labels(payload)
        filled = [str(x).strip() for x in (payload.get("filled") or []) if str(x).strip()]
        if filled:
            missing_text = flow._join_owner_labels(missing)
            r = flow.Reply(*flow._fmt(
                vi.TPM_RESULT_RECIPIENT_PARTIAL if missing else vi.TPM_RESULT_RECIPIENT_FILLED,
                note=vi.TPM_SUBMIT_HINT, label=label, filled_note=flow._join_owner_labels(filled),
                missing_note=missing_text, missing_tts=missing_text,
            ))
        elif missing:
            text = flow._join_owner_labels(missing)
            r = flow.Reply(*flow._fmt(vi.GUIDED_RESULT_MISSING, note=vi.TPM_SUBMIT_HINT,
                                      label=label, missing_note=text, missing_tts=text))
        elif method.get("needsInput"):
            r = flow.Reply(*flow._fmt(vi.GUIDED_RESULT_NEEDS_INPUT, note=vi.TPM_SUBMIT_HINT,
                                      label=label))
        else:
            r = flow.Reply(*flow._fmt(vi.GUIDED_RESULT_PICKED, note=vi.TPM_SUBMIT_HINT, label=label))
    # Gắn lại thẻ ở lượt CÓ CHỮ: lượt bấm chọn là Reply rỗng nên không vào last_reply.
    r.cards = [guided.result_methods_card(proc, key)]
    r.chips = [_submit_cta()]
    if liz(proc) and payload.get("ok") and _missing_labels(payload):
        # Ô người nhận không có nguồn trên tờ khai (vd số điện thoại) → hỏi từng ô; hỏi xong hiện lại nút nộp.
        conv.setdefault("field_review", {})["chips"] = [_submit_cta()]
        r.chips = [*field_review.start_chips(conv, proc, [_submit_cta()]), _submit_cta()]
    return r


def _submit_report_reply(conv: dict, proc: dict, payload: dict):
    """FE soát ô bắt buộc trước khi bấm; thiếu thì không bấm và trả danh sách ô thiếu."""
    from app.channels.handfree.chat import flow

    if payload.get("ok"):
        # Cú bấm đã vào đường đếm hồ sơ (submit_clicked → thẻ đánh giá); nói thêm là chen giữa thẻ.
        return flow.Reply()
    if liz_commit_self(conv, proc) and payload.get("commit") is False:
        # Công dân tự tích ô cam kết: extension thấy ô chưa tích thì không bấm → dặn tích, chỉ vào ô.
        return _liz_commit_wait_reply(conv, proc, vi.LIZ_SUBMIT_NEED_COMMIT)
    missing = _missing_labels(payload)
    message = str(payload.get("message") or "").strip()
    if missing:
        text = flow._join_owner_labels(missing[:8])
        r = flow.Reply(*flow._fmt(vi.TPM_SUBMIT_MISSING, missing_note=text, missing_tts=text))
        r.chips = [*field_review.start_chips(conv, proc, _final_chips(proc, conv)), _submit_cta()]
        return r
    if message:
        r = flow.Reply(*flow._fmt(vi.TPM_SUBMIT_BLOCKED, portal_message=message))
    else:
        r = flow.Reply(*flow._fmt(vi.TPM_SUBMIT_STUCK))
    r.chips = [_submit_cta()]
    return r


async def handle(conv: dict, proc: dict, intent: Intent):
    """Lượt ở chặng đính kèm / sau đính kèm. Trả None để state machine cũ xử lý tiếp."""
    from app.channels.handfree.chat import flow

    state = conv.get("state")
    payload = intent.payload or {}
    commit_reply = await _handle_liz_commit(conv, proc, intent)
    if commit_reply is not None:
        return commit_reply
    if auto_flow(conv):
        if _submitted(conv) and intent.kind not in {"event", "action"}:
            return None  # đã nộp: câu tự do để luồng chung sau nộp lo, không nhắc nút nộp nữa
        auto_reply = await _handle_auto(conv, proc, intent)
        if auto_reply is not None:
            return auto_reply
    if intent.kind == "action" and intent.value in {"tpm_attach", "request_attach"}:
        r = await _request_attach(conv)
        if _v2(conv, proc) and conv.get("state") == "attaching":
            # "Đính kèm lại": thẻ một bước; tệp → dòng nói ở khung kết quả đính kèm.
            actions = [steps_action(vi.FLOW2_STEPS[2:]), *r.actions]
            if any(a.get("type") == "attach_plan" for a in r.actions):
                r = flow.Reply()
            r.actions = actions
        return r

    if state == "attaching":
        if intent.kind == "event" and intent.value == "attach_ready":
            # Kế hoạch về sớm trong lúc công dân còn rà form: giữ đó, chờ nút đính kèm.
            if not conv.get("tpm_attach_requested"):
                return flow.Reply()
            if _v2(conv, proc):
                # Thẻ tiến trình đang ở bước "Đính kèm": chỉ phát lệnh đính, tệp → dòng nói ở khung kết quả đính kèm.
                planned = await flow._handle_attaching(conv, intent)
                r = flow.Reply()
                r.actions = planned.actions
                return r
            return None
        if intent.kind == "event" and intent.value == "page_status":
            # Một trang duy nhất — không có "sang bước đính kèm" để watcher tự kích hoạt.
            return flow.Reply()
        if intent.kind == "event" and intent.value == "pipeline_error":
            conv["attachment_plan_started"] = False
            r = flow.Reply(*flow._fmt(vi.ATTACH_PIPELINE_ERROR,
                                      error=conv.get("pipeline_error") or "không rõ"))
            r.chips = [{"label": "🔁 Thử lập kế hoạch lại", "send": "__action:tpm_attach", "solid": True}]
            return r
        if intent.kind == "action" and intent.value == "attach_report":
            # Đường cũ lo phần sổ sách (khóa action, trace, state); câu và nút theo trang một trang.
            r = await flow._handle_attaching(conv, intent)
            # Thẻ kết quả theo từng tệp (supportsAttachFileReport); nút đính lại của trang một trang giữ như cũ.
            files = attach_files.parse(conv, payload)
            if conv.get("attach_done"):
                return attach_files.apply(_attach_done_reply(conv, payload), files, hint=vi.ATTACH_FILES_HINT_AGAIN)
            if conv.get("attach_action_in_progress"):
                return r  # report trễ của lượt cũ — đường cũ đã bỏ qua
            errors = [str(e) for e in (payload.get("errors") or []) if e]
            r = flow.Reply(*flow._fmt(vi.TPM_ATTACH_NONE,
                                      error_note=f": *{errors[0]}*" if errors and not files else ""))
            r.chips = [_retry_attach_chip(), flow._supplement_documents_chip()]
            if _v2(conv, proc):
                r.actions = [steps_action(active=2, failed=True)]
            return attach_files.apply(r, files)
        return None

    if state == "done":
        if intent.kind == "action" and intent.value == "tpm_result_method":
            return _result_step_reply(conv, proc)
        if intent.kind == "action" and intent.value == "pick_result_method":
            return _pick_result_method_reply(conv, proc, payload)
        if intent.kind == "action" and intent.value == "result_method_report":
            return _result_method_report_reply(conv, proc, payload)
        if intent.kind == "action" and intent.value == "tpm_submit":
            r = flow.Reply()
            r.actions = [_liz_page_action(proc, guided.submit_action(proc), conv=conv)]
            return r
        if intent.kind == "action" and intent.value == "guided_submit_report":
            return _submit_report_reply(conv, proc, payload)
        if intent.kind not in {"event", "action"}:
            r = flow.Reply(*flow._fmt(vi.TPM_DONE_REMIND))
            r.chips = ([_submit_cta()] if conv.get("result_method")
                       else [flow._supplement_documents_chip(), _result_cta()])
            return r
    return None


async def _handle_auto(conv: dict, proc: dict, intent: Intent):
    """Phần riêng của luồng tự động ở chặng đính kèm / sau đính kèm. None = đi tiếp như cũ."""
    from app.channels.handfree.chat import flow

    state = conv.get("state")
    if _submitted(conv):
        # Đã nộp: kế hoạch / kết quả đính về muộn chỉ cập nhật sổ sách, không chen câu hay nút
        # vào sau phiếu đánh giá. Còn lại (đánh giá, đăng xuất) để luồng chung lo.
        if intent.kind == "event" and intent.value in {"attach_ready", "pipeline_error", "page_status"}:
            return flow.Reply()
        if intent.kind == "action" and intent.value == "attach_report":
            await flow._handle_attaching(conv, intent)
            return flow.Reply()
    if intent.kind == "action" and intent.value == "refill":
        conv["tpm_auto_attach"] = False
        conv["docs_target"] = "declaration"  # trang một trang: điền lại luôn đúng chỗ
        running = conv.get("pipeline_status") == "running"
        r = await flow._restart_declaration_pipeline(conv)
        if _v2(conv, proc) and not running and conv.get("pipeline_status") == "running":
            r = flow.Reply(*_v2_say(vi.FLOW2_REFILL))
            r.actions = [steps_action(vi.FLOW2_STEPS[:2])]
        return r
    if intent.kind == "action" and intent.value == "add_documents":
        if conv.get("submitted_completed"):
            return flow.Reply(*flow._fmt(vi.ATTACH_SUPPLEMENT_AFTER_SUBMIT))
        conv["tpm_auto_attach"] = True  # nút chốt to = điền & đính kèm lại
        r = await flow._start_documents_adjustment(
            conv, "declaration",
            finish_action=ADJUST_BOTH_LABEL.removeprefix("✅ "),
            finish_detail=("tôi sẽ điền lại tờ khai rồi đính kèm lại; chỉ cần làm một việc thì "
                           "công dân bấm nút nhỏ tương ứng"),
        )
        if conv.get("supplementing_documents") and r.chips:
            r.chips = [*r.chips, *adjust_choice_chips()]
        return r
    if state == "done" and intent.kind not in {"event", "action"}:
        r = flow.Reply(*flow._fmt(vi.TPM_DONE_REMIND))
        r.chips = field_review.next_chips(conv, proc, _final_chips(proc, conv))
        return r
    return None


async def adjust_done(conv: dict, payload: dict):
    """Nút nhỏ khi điều chỉnh giấy tờ: chốt phiên rồi CHỈ điền lại hoặc CHỈ đính kèm lại."""
    from app.channels.handfree.chat import flow

    then = str(payload.get("then") or "")
    sid = str(conv.get("upload_session_id") or "")
    if then not in {"declaration", "attachment"} or not conv.get("supplementing_documents") or not sid:
        return flow.Reply()
    conv["documents_adjustment_target"] = then
    conv["docs_target"] = then
    conv["tpm_auto_attach"] = then == "attachment"
    await flow.upload_service.complete_session(sid)
    # Trang một trang luôn đúng chỗ cho cả điền lẫn đính — không cần đọc trang.
    return await flow._docs_complete(conv, {})


def on_submitted(conv: dict):
    """Lưới đỡ khi cú bấm nộp bị lọt: cổng hiện toast "Gửi hồ sơ thành công" (trang không chuyển
    sang màn kết quả). Ở bước nào cũng sang phần sau nộp: phiếu đánh giá → đăng xuất.
    Đồng hồ tự đăng xuất KHÔNG chạy ở đây — nó là bước nối sau khi đánh giá xong."""
    from datetime import datetime, timezone

    from app.channels.handfree.chat import flow

    conv["submitted_completed"] = True
    conv["state"] = "done"
    if not conv.get("submit_clicked_at"):
        # Cú bấm lọt → mốc nộp lấy từ toast (nguồn "text" như đường dò chữ cũ).
        conv["submit_clicked_at"] = datetime.now(timezone.utc)
        conv["submit_clicked_source"] = "text"
        conv["submit_click_id"] = ""
    if conv.get("rating") or conv.get("awaiting_rating") or conv.get("submitted_logout_decision"):
        return flow.Reply()  # cú bấm đã dựng phiếu / đã hiện nút đăng xuất
    conv["submitted_logout_decision"] = "pending"
    if flow._supports_rating(conv) and flow.dossier_has_real_work(conv):
        conv["awaiting_rating"] = True
        _, tts = flow._fmt(vi.RATE_INVITE)
        r = flow.Reply("", tts)
        r.cards = [flow._rating_card()]  # không kèm đồng hồ: nó chạy khi đánh giá xong
        return r
    return flow._logout_choice_reply()
