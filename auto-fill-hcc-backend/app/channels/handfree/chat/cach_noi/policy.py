"""Bảng chính sách: (bước × cách nói × bộ đếm) → câu trả lời. Tất định, không LLM.

Thay cho "đáy hàm" của các handler từng phát lại nguyên câu của bước cho mọi câu không hiểu. Ở đây:
- vô nghĩa / không rõ: 3 nấc — nhắc việc nói được → đưa nút → bảo bấm tay / nhờ cán bộ và tạm không tự mở mic;
- ngoài luồng: từ chối lịch sự một lần, sau chỉ nhắc bước;
- đi tiếp / quay lại / làm lại / huỷ: nghĩa cố định theo bước; việc xoá dữ liệu bằng lời phải xác nhận; đi tiếp / quay lại
  nghe chưa chắc (độ chắc "vua") → hỏi "có phải … không?" kèm đúng nút, không bấm;
- xác nhận / từ chối trống (không có câu hỏi treo): nhắc việc của bước, không bấm gì.
Chỉ tiếng Việt: chế độ Mông đi luồng cũ (câu thoại chưa có bản dịch). Mọi câu qua flow._fmt(vi.CN_*).
"""
from app.channels.handfree.chat import guided_steps as guided
from app.channels.handfree.chat import intents, script_vi as vi, step_back
from app.channels.handfree.chat.cach_noi import KHONG_RO, KIND, LAM_LAI_SENDS, LOI, forward_button, lop1
from app.channels.handfree.chat.intents import Intent

DEM_KEY = "cach_noi_dem"          # {"khong_hieu": n, "ngoai_luong": n} — về 0 khi có cú bấm / câu hiểu được
MIC_KEY = "cn_mic_nghi"           # nấc 3: không tự mở mic sau câu trả lời tới khi công dân bấm nút
THONG_KE_KEY = "cach_noi_thong_ke"
MAX_KHONG_HIEU = 3
MAX_NUT_GOI_Y = 3

# Bước có câu hỏi treo thật sự: "ừ" / "không" trống mang nghĩa trong handler → không chặn.
PENDING_STATES = frozenset({"greet", "confirm_procedure", "consent", "choose_variant", "choose_mae_dialog",
                            "choosing_attach_mode", "ask_doc_method"})
# Bước → nhóm câu nhắc (CN_NHAC_BUOC).
_NHOM = {
    "greet": "chao", "confirm_procedure": "chao", "choose_variant": "chon_truong_hop",
    "choose_mae_dialog": "chon_truong_hop", "guide_login": "dang_nhap", "consent": "dong_y",
    "ask_doc_method": "cach_gui", "qr_waiting": "gui_giay", "collecting_docs": "gui_giay",
    "choosing_attach_mode": "che_do_dinh", "owner_filling": "dang_dien", "filling": "dang_dien",
    "owner_waiting_next": "chu_ho_so", "reviewing": "ke_khai_xong", "attaching": "dinh_kem", "done": "dinh_kem",
}
_HOI_LAI = frozenset({lop1.VO_NGHIA, KHONG_RO, LOI})


def enabled(conv: dict) -> bool:
    return (conv.get("lang") or "vi") == "vi"


def reset(conv: dict) -> None:
    conv.pop(DEM_KEY, None)
    conv.pop(MIC_KEY, None)


def finalize(conv: dict, intent: Intent, reply) -> None:
    """Cuối mỗi lượt: cú bấm tay (lệnh máy không phải sự kiện nền) đưa bộ đếm về 0; đang nghỉ mic thì bỏ lệnh tự mở."""
    payload = intent.payload or {}
    if intent.kind == "action" and not payload.get("_voice"):
        reset(conv)
    if conv.get(MIC_KEY) and reply is not None:
        reply.actions = [a for a in reply.actions if not (isinstance(a, dict) and a.get("type") == "listen_after_tts")]


def _dem(conv: dict, key: str) -> int:
    dem = conv.setdefault(DEM_KEY, {})
    dem[key] = int(dem.get(key) or 0) + 1
    tk = conv.setdefault(THONG_KE_KEY, {})
    tk[key] = int(tk.get(key) or 0) + 1
    return dem[key]


def _proc(conv: dict) -> dict:
    from app.channels.handfree.procedure_registry import get_procedure
    return get_procedure(conv.get("procedure_key") or "") or {}


def _nhom(conv: dict, proc: dict, page_context: dict | None) -> str:
    state = conv.get("state", "greet")
    if state == "done" and conv.get("submitted_completed"):
        return "sau_nop"
    if state in ("collecting_docs", "qr_waiting") and conv.get("supplementing_documents"):
        return "dieu_chinh_giay"
    if state == "guide_login" and _owner_cta_showing(conv, proc):
        return "chu_ho_so"   # chủ hồ sơ đã điền xong, đang mời bấm sang Kê khai (state vẫn là guide_login)
    if state in ("attaching", "done"):
        from app.channels.handfree.chat import flow
        step = flow._docs_page_context(page_context)["wizardStep"] if page_context else 0
        if step and step == flow._wizard_step(proc, "resultStep", 4):
            return "nhan_ket_qua"
    return _NHOM.get(state, "chao")


def _xem_truoc(conv: dict) -> bool:
    """Bản xem trước tờ khai đang mở: chỉ còn hai việc (Sửa lại tờ khai / Xác nhận sang Thành phần hồ sơ)."""
    return conv.get("state") == "reviewing" and bool((conv.get("field_review") or {}).get("preview_open"))


def _xem_truoc_hoi(conv: dict):
    return _with_chips(_say(vi.CN_XEM_TRUOC_HOI), conv)


def _owner_cta_showing(conv: dict, proc: dict) -> bool:
    from app.channels.handfree.chat import field_review
    return field_review.owner_cta_showing(conv, proc)


def _nhac(conv: dict, proc: dict, page_context: dict | None) -> dict:
    return vi.CN_NHAC_BUOC[_nhom(conv, proc, page_context)]


def _options(conv: dict) -> tuple[list[str], list[dict]]:
    items = intents.voice_buttons(conv, conv.get("state", "greet"))
    labels = [i["label"] for i in items if i.get("label")]
    chips = [dict(i["chip"]) for i in items if isinstance(i.get("chip"), dict)]
    return labels, chips


def _visible(conv: dict, sends) -> dict | None:
    items = intents.voice_buttons(conv, conv.get("state", "greet"))
    for send in sends:
        for item in items:
            if item.get("send") == send:
                return item
    return None


def _forward(conv: dict) -> dict | None:
    return forward_button(intents.voice_buttons(conv, conv.get("state", "greet")))


def _say(tpl: dict, nhac: dict | None = None, **kw):
    from app.channels.handfree.chat.flow import Reply, _fmt
    if nhac is not None:
        kw.setdefault("nhac_md", nhac["md"])
        kw.setdefault("nhac_tts", nhac["tts"])
    return Reply(*_fmt(tpl, **kw))


def _with_chips(reply, conv: dict, chips: list[dict] | None = None):
    reply.chips = chips if chips is not None else _options(conv)[1]
    return reply


async def _run(conv: dict, intent: Intent, page_context: dict | None, meta: dict):
    """Chạy một lệnh thay cho câu nói — qua handle_turn để giữ cả xác nhận lệnh xoá lẫn đường bấm hộ của extension."""
    from app.channels.handfree.chat import flow
    intent.payload = {**(intent.payload or {}), **{k: meta[k] for k in ("_voice", "cach_noi", "do_chac", "llm_calls")
                                                  if k in meta}}
    return await flow.handle_turn(conv, intent, page_context)


# ── Điểm vào ─────────────────────────────────────────────────────────────────────────────────────────────────────────
async def intercept(conv: dict, intent: Intent, page_context: dict | None):
    """Reply cho nhãn chỉ-chính-sách và cho xác nhận / từ chối trống; None = để flow xử lý như cũ."""
    if not enabled(conv):
        return None
    payload = intent.payload or {}
    state = conv.get("state", "greet")
    if intent.kind == KIND:
        return await _label(conv, intent, state, page_context)
    if intent.kind == "unknown" and payload.get("cach_noi") in _HOI_LAI:
        if state in PENDING_STATES and state != "confirm_procedure":
            return None   # màn chào / câu hỏi có thẻ: handler tự nói "chưa nhận ra" + dựng lại thẻ
        if _xem_truoc(conv) and _dem(conv, "khong_hieu") < MAX_KHONG_HIEU:
            return _xem_truoc_hoi(conv)   # đang xem trước: hỏi thẳng hai việc thay vì "chưa hiểu" chung chung
        return _khong_hieu(conv)
    if intent.kind in ("confirm", "deny") and payload.get("_voice") and state not in PENDING_STATES:
        proc = _proc(conv)
        return await (_confirm_tron if intent.kind == "confirm" else _deny_tron)(conv, proc, page_context, payload)
    return None


async def _label(conv: dict, intent: Intent, state: str, page_context: dict | None):
    label, meta = intent.value, intent.payload or {}
    proc = _proc(conv)
    if label == lop1.XA_GIAO:
        return _with_chips(_say(vi.CN_XA_GIAO, _nhac(conv, proc, page_context)), conv)
    if state in PENDING_STATES and label == lop1.LAM_LAI:
        return None   # câu hỏi có thẻ đang treo: handler hỏi lại thẻ đó, không có gì để "làm lại"
    if label == lop1.NGOAI_LUONG:
        n = _dem(conv, "ngoai_luong")
        return _with_chips(_say(vi.CN_NGOAI_LUONG_1 if n == 1 else vi.CN_NGOAI_LUONG_2, _nhac(conv, proc, page_context)),
                           conv)
    if _xem_truoc(conv) and label in (lop1.KHONG_BIET, lop1.LAM_LAI):
        return _xem_truoc_hoi(conv)   # làm lại / không biết lúc xem trước: chỉ có hai việc để chọn
    if label == lop1.KHONG_BIET:
        return _with_chips(_say(vi.CN_KHONG_BIET, _nhac(conv, proc, page_context)), conv)
    if label == lop1.DI_TIEP:
        return await _di_tiep(conv, proc, page_context, meta)
    if label == lop1.QUAY_LAI:
        return await _quay_lai(conv, proc, page_context, meta)
    if label == lop1.LAM_LAI:
        _, chips = _options(conv)
        lam_lai = [c for c in chips if c.get("send") in LAM_LAI_SENDS]
        return _with_chips(_say(vi.CN_LAM_LAI_CHON), conv, lam_lai or chips)
    return None


def _khong_hieu(conv: dict):
    from app.channels.handfree.chat import flow
    n = _dem(conv, "khong_hieu")
    if n == 1:
        return flow.not_understood_reply(conv)
    labels, chips = _options(conv)
    if n == 2:
        if labels:
            r = _say(vi.CN_KHONG_HIEU_2, options_md=" · ".join(f"**{x}**" for x in labels[:MAX_NUT_GOI_Y]),
                     options_tts=", ".join(labels[:MAX_NUT_GOI_Y]))
        else:
            r = _say(vi.CN_KHONG_HIEU_2_KHONG_NUT)
        return _with_chips(r, conv, chips[:MAX_NUT_GOI_Y] or chips)
    conv[MIC_KEY] = True
    return _with_chips(_say(vi.CN_KHONG_HIEU_3), conv, chips[:MAX_NUT_GOI_Y] or chips)


async def _confirm_tron(conv: dict, proc: dict, page_context: dict | None, meta: dict):
    state = conv.get("state", "greet")
    if state == "done" and conv.get("submitted_logout_decision") == "pending":
        from app.channels.handfree.chat import flow
        r = _say(vi.CN_LOGOUT_HOI)
        r.chips = flow._logout_choice_reply(arm_timer=False).chips
        return r
    if state == "filling" or state == "owner_filling":
        return None   # handler trấn an "đang đọc giấy tờ"
    # Trợ lý vừa mời kiểm tra rồi bấm nút đi tiếp (chủ hồ sơ đã điền; bản xem trước đang mở): "đúng rồi" = bấm nút đó.
    if (state == "owner_waiting_next" or (state == "guide_login" and _owner_cta_showing(conv, proc))
            or (state == "reviewing" and (conv.get("field_review") or {}).get("preview_open"))):
        item = _forward(conv)
        if item:
            picked = intents._button_intent(item)
            if picked is not None:
                return await _run(conv, picked, page_context, meta)
    return _with_chips(_say(vi.CN_XAC_NHAN_TRON, _nhac(conv, proc, page_context)), conv)


async def _deny_tron(conv: dict, proc: dict, page_context: dict | None, meta: dict):
    if conv.get("state") in ("filling", "owner_filling"):
        return None
    if _xem_truoc(conv):
        return _xem_truoc_hoi(conv)   # "không" lúc xem trước: chưa rõ là sửa hay chưa xác nhận → hỏi hai việc
    return _with_chips(_say(vi.CN_TU_CHOI_TRON, _nhac(conv, proc, page_context)), conv)


async def _di_tiep(conv: dict, proc: dict, page_context: dict | None, meta: dict):
    from app.channels.handfree.chat import field_review, flow
    state = conv.get("state", "greet")
    if state in ("greet", "confirm_procedure", "consent", "ask_doc_method", "choose_variant", "choose_mae_dialog",
                 "choosing_attach_mode") and not (state == "ask_doc_method" and conv.get("supplementing_documents")):
        if state == "confirm_procedure" and meta.get("do_chac") == "cao":
            return await _run(conv, Intent("confirm"), page_context, meta)
        return _with_chips(_say(vi.CN_DI_TIEP_KHONG_CO, _nhac(conv, proc, page_context)), conv)
    if state in ("filling", "owner_filling"):
        return _say(vi.STILL_READING_DOCUMENTS)
    if state in ("ask_doc_method", "collecting_docs", "qr_waiting") and conv.get("supplementing_documents"):
        # Đang điều chỉnh giấy tờ mà "đi tiếp" = không điều chỉnh nữa: về bước đang dở (tờ khai giữ nguyên) rồi làm việc
        # đi tiếp của chính bước đó (Xem trước / sang Thành phần hồ sơ…). Chốt điều chỉnh (điền lại) chỉ khi nói rõ.
        lead = await flow._cancel_documents_adjustment(conv)
        flow.update_voice_options(conv, lead)
        r = await _di_tiep(conv, proc, page_context, meta)
        r.display_md = "\n\n".join(x for x in (lead.display_md, r.display_md) if x)
        r.tts_text = " ".join(x for x in (lead.tts_text, r.tts_text) if x)
        return r
    if meta.get("do_chac") != "cao":
        # Nghe chưa chắc là muốn đi tiếp (câu bỏ lửng, lẫn nhiễu): nêu đúng nút đi tiếp của bước và hỏi, không bấm.
        send = "__action:docs_done" if state in ("collecting_docs", "qr_waiting") else (_forward(conv) or {}).get("send", "")
        if send.startswith("__action:"):
            return voice_confirm(conv, send, hoi=vi.CN_DI_TIEP_HOI)
        return _with_chips(_say(vi.CN_DI_TIEP_KHONG_CO, _nhac(conv, proc, page_context)), conv)
    if state in ("collecting_docs", "qr_waiting"):
        send = "__action:docs_done"
        item = _visible(conv, (send, "__event:docs_complete"))
        picked = intents._button_intent(item) if item else Intent("action", "docs_done")
        return await _run(conv, picked, page_context, meta)
    item = _forward(conv)
    if item:
        picked = intents._button_intent(item)
        if picked is not None:
            return await _run(conv, picked, page_context, meta)
    if state == "reviewing" and field_review.flow_v2(conv, proc):
        required = ((conv.get("field_review") or {}).get("stats") or {}).get("required") or 0
        if required:
            r = _say(vi.CN_DI_TIEP_THIEU_O, required=required)
            r.chips = [field_review._start_chip(), field_review._preview_chip()]
            return r
        return await _run(conv, Intent("action", "field_review_preview"), page_context, meta)
    if state in ("attaching", "done") and proc.get("wizard") and guided.result_flow_enabled(conv, proc):
        step = flow._docs_page_context(page_context)["wizardStep"] if page_context else 0
        if step == flow._wizard_step(proc, "attachmentStep", 3):
            return flow._voice_step_reply(conv, proc, Intent("action", "guided_next", {"phase": guided.ATTACHMENT,
                                                                                        "voice": True}))
        if step == flow._wizard_step(proc, "resultStep", 4):
            return flow._voice_step_reply(conv, proc, Intent("action", "voice_submit_hint"))
    return _with_chips(_say(vi.CN_DI_TIEP_KHONG_CO, _nhac(conv, proc, page_context)), conv)


async def _quay_lai(conv: dict, proc: dict, page_context: dict | None, meta: dict):
    chac = meta.get("do_chac") == "cao"
    if _xem_truoc(conv):
        # "quay lại" lúc xem trước = về tờ khai (đóng xem trước), không phải lùi bước trên cổng (về chủ hồ sơ).
        item = _visible(conv, ("__action:field_review_preview_close",))
        picked = intents._button_intent(item) if item else Intent("action", "field_review_preview_close")
        return await _run(conv, picked, page_context, meta)
    if step_back.enabled(conv, proc) and conv.get("state") in ("reviewing", "attaching", "done"):
        send = "__action:step_back"
        return await _run(conv, Intent("action", "step_back"), page_context, meta) if chac \
            else voice_confirm(conv, send, hoi=vi.CN_QUAY_LAI_HOI)
    item = next((it for it in intents.voice_buttons(conv, conv.get("state", "greet"))
                 if (it.get("chip") or {}).get("tone") == "back"), None)
    if item:
        if not chac and str(item.get("send") or "").startswith("__action:"):
            return voice_confirm(conv, item["send"], hoi=vi.CN_QUAY_LAI_HOI)
        picked = intents._button_intent(item)
        if picked is not None:
            return await _run(conv, picked, page_context, meta)
    return _with_chips(_say(vi.CN_QUAY_LAI_KHONG_CO, _nhac(conv, proc, page_context)), conv)


# ── Xác nhận trước việc xoá dữ liệu khi chọn bằng lời ────────────────────────────────────────────────────────────────
def confirm_needed(conv: dict, send: str) -> bool:
    """Nút / lệnh làm lại chọn BẰNG LỜI phải xác nhận; bấm tay không qua đây. Nộp hồ sơ do flow xử lý riêng."""
    if not enabled(conv):
        return False
    if send == "__action:docs_done":
        return bool(conv.get("supplementing_documents"))
    if send == "__action:new_procedure":
        return bool(conv.get("procedure_key")) and conv.get("state") not in ("greet", "confirm_procedure")
    return send in LAM_LAI_SENDS


def voice_confirm(conv: dict, send: str, hoi: dict | None = None):
    """Câu hỏi xác nhận + nút xác nhận (payload voiceConfirmed chạy thẳng) + nút giữ nguyên. Trạng thái chờ ghi vào
    conv["voice_submit_confirm"] (cùng khoá với xác nhận nộp để flow xử lý Có / Không một chỗ). `hoi`: mẫu câu hỏi
    riêng (đi tiếp / quay lại nghe chưa chắc); mặc định hỏi theo kiểu làm lại / huỷ kèm hậu quả."""
    from app.channels.handfree.chat import flow
    key = send.removeprefix("__action:")
    item = next((i for i in (conv.get("voice_options") or {}).get("items") or [] if i.get("send") == send), {})
    label = flow._chip_name(item.get("chip") or {}) or vi.CN_NHAN_LAM_LAI.get(key, key)
    if key == "docs_done":
        label = flow._chip_name({"label": flow._docs_done_label_for_conv(conv)})
    chip = {"label": label, "send": send, "solid": True}
    conv["voice_submit_confirm"] = {"send": send, "chip": chip, "kind": "lam_lai", "prev_chips": _prev_chips(conv)}
    hau_qua = vi.CN_HAU_QUA.get(key, vi.CN_HAU_QUA["khac"])
    tpl = hoi or (vi.CN_HUY_HOI if key == "new_procedure" else vi.CN_LAM_LAI_HOI)
    r = _say(tpl, label=label, hau_qua_md=hau_qua["md"], hau_qua_tts=hau_qua["tts"])
    r.chips = [{**chip, "label": f"✓ {label}", "send": send + flow._VOICE_CONFIRMED},
               {"label": vi.CN_GIU_NGUYEN_CHIP, "send": "__action:cn_giu_nguyen", "tone": "back"}]
    return r


def _prev_chips(conv: dict) -> list[dict]:
    """Nút của lượt TRƯỚC câu hỏi xác nhận (last_reply lúc này chưa bị câu hỏi đè) — để Không / Giữ nguyên trả lại đúng
    màn hình cũ, không trả lại chính nút "Không, giữ nguyên" (bấm mãi không thoát)."""
    return [dict(c) for c in (conv.get("last_reply") or {}).get("chips") or []
            if not str(c.get("send") or "").endswith(_confirmed_suffix()) and c.get("send") != "__action:cn_giu_nguyen"]


def keep_reply(conv: dict, pending: dict | None = None):
    """Công dân nói Không / bấm Giữ nguyên trước câu hỏi xác nhận làm lại: không làm gì, trả lại nút của lượt trước câu hỏi."""
    pending = pending if pending is not None else conv.pop("voice_submit_confirm", None) or {}
    conv.pop("voice_submit_confirm", None)
    r = _say(vi.CN_LAM_LAI_HUY)
    chips = pending.get("prev_chips")
    r.chips = [dict(c) for c in chips] if chips is not None else _prev_chips(conv)
    return r


def _confirmed_suffix() -> str:
    from app.channels.handfree.chat import flow
    return flow._VOICE_CONFIRMED
