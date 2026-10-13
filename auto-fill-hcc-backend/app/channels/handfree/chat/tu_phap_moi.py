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
"""

import re

from app.channels.handfree.chat import guided_steps as guided
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import Intent

PROFILE = "tu-phap-moi"
CAPABILITY = "supportsTuPhapMoi"
# Luồng TỰ ĐỘNG: điền xong tự đính kèm, nút nộp/đổi cách nhận hiện ngay, nộp (bấm trên trang, bấm
# nút trong khung chat, hoặc lưới đỡ toast "Gửi hồ sơ thành công") ở bước nào cũng sang phần sau
# nộp. Extension cũ không khai cờ này → đi nguyên luồng bấm-từng-chặng bên dưới.
AUTO_CAPABILITY = "supportsTpmAutoFlow"
ADJUST_BOTH_LABEL = "✅ Đủ giấy tờ — điền & đính kèm lại"


def is_active(proc: dict | None) -> bool:
    return bool(proc and proc.get("flowProfile") == PROFILE)


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


def _final_chips() -> list[dict]:
    """Sau khi điền + đính: 3 nút sửa nhỏ, 2 nút đi tiếp to (cách nhận kết quả, nộp)."""
    from app.channels.handfree.chat import flow

    return [
        flow._supplement_documents_chip(),
        {"label": "🔁 Điền lại", "send": "__action:refill"},
        {"label": "📎 Đính kèm lại", "send": "__action:tpm_attach"},
        _result_cta(),
        _submit_cta(),
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


async def _auto_fill_report_reply(conv: dict, rep: dict, proc: dict):
    from app.channels.handfree.chat import flow, tracing

    await tracing.set_report(conv.get("trace_request_id"), "autofill", rep)
    missing = rep["notFound"]
    missing_note = f"\n\n⚠️ **{len(missing)} ô chưa khớp được**: {', '.join(missing[:8])}" if missing else ""
    flow._clear_documents_adjustment(conv)
    if conv.get("tpm_auto_attach") is False:
        # "Điền lại" / "Đã đủ giấy tờ - Điền lại tờ khai": giấy tờ trên trang giữ nguyên.
        conv["tpm_auto_attach"] = True
        conv["state"] = "done"
        r = flow.Reply(*flow._fmt(vi.FILL_REPORT_REVIEW, filled=rep["filled"],
                                  missing_note=missing_note, note=vi.TPM_SUBMIT_HINT))
        r.chips = _final_chips()
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
        return r
    if not (conv.get("attachment_plan_started") and conv.get("pipeline_status") == "running"):
        _spawn_attach_planner(conv)  # chưa chạy (phiên cũ) hoặc lượt lập kế hoạch vừa lỗi
    return flow.Reply(*flow._fmt(vi.FILL_REPORT_REVIEW, filled=rep["filled"],
                                 missing_note=missing_note, note=vi.TPM_AUTO_ATTACH_WAIT))


async def fill_report_reply(conv: dict, rep: dict):
    """Điền xong: lập kế hoạch đính kèm ở nền, chờ công dân rà form rồi bấm nút đính kèm."""
    from app.channels.handfree.chat import flow, tracing

    if auto_flow(conv):
        proc = flow.get_procedure(conv.get("procedure_key") or "") or {}
        return await _auto_fill_report_reply(conv, rep, proc)

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
    if conv.get("pipeline_status") == "attach_ready" and conv.get("attach_plan"):
        return await flow._handle_attaching(conv, Intent("event", "attach_ready"))
    if conv.get("pipeline_status") == "running" and conv.get("attachment_plan_started"):
        return flow.Reply(*flow._fmt(vi.TPM_ATTACH_WAIT_PLAN))
    # Chưa có kế hoạch hoặc lượt trước lỗi → lập lại trên chính phiên tệp hiện tại.
    _spawn_attach_planner(conv)
    return flow.Reply(*flow._fmt(vi.ATTACH_PLANNING))


def _auto_attach_done_reply(conv: dict, proc: dict, attached: int, skipped: int, errors: list[str]):
    from app.channels.handfree.chat import flow

    note, label = _default_result_note(proc)
    if errors:
        error_list = "\n".join(f"- {e}" for e in errors[:5])
        r = flow.Reply(*flow._fmt(vi.TPM_ATTACH_DONE_WITH_ERRORS, attached=attached,
                                  error_list=error_list, note=note, label=label))
    else:
        template = vi.TPM_AUTO_ALL_EXIST if attached == 0 and skipped > 0 else vi.TPM_AUTO_ATTACH_DONE
        r = flow.Reply(*flow._fmt(template, attached=attached, note=note, label=label))
    r.chips = _final_chips()
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


def _result_card_action(conv: dict, proc: dict, key: str) -> tuple[dict, list]:
    conv["result_method"] = key
    action = guided.select_result_method_action(proc, key)
    return guided.result_methods_card(proc, key), [action] if action else []


def _result_step_reply(conv: dict, proc: dict):
    """Chọn sẵn cách đầu (cổng cũng để sẵn cách này) rồi hiện thẻ 3 cách để công dân đổi."""
    from app.channels.handfree.chat import flow

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
    """FE báo đã chọn trên ô "Hình thức nhận kết quả"; bưu điện thì kèm ô còn trống."""
    from app.channels.handfree.chat import flow

    key = str(payload.get("method") or conv.get("result_method") or "")
    method = guided.result_method(proc, key) or {}
    label = str(method.get("label") or "")
    if not payload.get("ok"):
        r = flow.Reply(*flow._fmt(vi.TPM_RESULT_FAILED, label=label))
    else:
        missing = _missing_labels(payload)
        if missing:
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
    return r


def _submit_report_reply(payload: dict):
    """FE soát ô bắt buộc trước khi bấm; thiếu thì không bấm và trả danh sách ô thiếu."""
    from app.channels.handfree.chat import flow

    if payload.get("ok"):
        # Cú bấm đã vào đường đếm hồ sơ (submit_clicked → thẻ đánh giá); nói thêm là chen giữa thẻ.
        return flow.Reply()
    missing = _missing_labels(payload)
    message = str(payload.get("message") or "").strip()
    if missing:
        text = flow._join_owner_labels(missing[:8])
        r = flow.Reply(*flow._fmt(vi.TPM_SUBMIT_MISSING, missing_note=text, missing_tts=text))
    elif message:
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
    if auto_flow(conv):
        if _submitted(conv) and intent.kind not in {"event", "action"}:
            return None  # đã nộp: câu tự do để luồng chung sau nộp lo, không nhắc nút nộp nữa
        auto_reply = await _handle_auto(conv, proc, intent)
        if auto_reply is not None:
            return auto_reply
    if intent.kind == "action" and intent.value in {"tpm_attach", "request_attach"}:
        return await _request_attach(conv)

    if state == "attaching":
        if intent.kind == "event" and intent.value == "attach_ready":
            # Kế hoạch về sớm trong lúc công dân còn rà form: giữ đó, chờ nút đính kèm.
            return None if conv.get("tpm_attach_requested") else flow.Reply()
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
            if conv.get("attach_done"):
                return _attach_done_reply(conv, payload)
            if conv.get("attach_action_in_progress"):
                return r  # report trễ của lượt cũ — đường cũ đã bỏ qua
            errors = [str(e) for e in (payload.get("errors") or []) if e]
            r = flow.Reply(*flow._fmt(vi.TPM_ATTACH_NONE,
                                      error_note=f": *{errors[0]}*" if errors else ""))
            r.chips = [_retry_attach_chip(), flow._supplement_documents_chip()]
            return r
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
            r.actions = [guided.submit_action(proc)]
            return r
        if intent.kind == "action" and intent.value == "guided_submit_report":
            return _submit_report_reply(payload)
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
        return await flow._restart_declaration_pipeline(conv)
    if intent.kind == "action" and intent.value == "add_documents":
        if conv.get("submitted_completed"):
            return flow.Reply(*flow._fmt(vi.ATTACH_SUPPLEMENT_AFTER_SUBMIT))
        conv["tpm_auto_attach"] = True  # nút chốt to = điền & đính kèm lại
        r = await flow._start_documents_adjustment(
            conv, "declaration",
            finish_action=ADJUST_BOTH_LABEL.removeprefix("✅ "),
            finish_detail=("em sẽ điền lại tờ khai rồi đính kèm lại; chỉ cần làm một việc thì "
                           "công dân bấm nút nhỏ tương ứng"),
        )
        if conv.get("supplementing_documents") and r.chips:
            r.chips = [*r.chips, *adjust_choice_chips()]
        return r
    if state == "done" and intent.kind not in {"event", "action"}:
        r = flow.Reply(*flow._fmt(vi.TPM_DONE_REMIND))
        r.chips = _final_chips()
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
