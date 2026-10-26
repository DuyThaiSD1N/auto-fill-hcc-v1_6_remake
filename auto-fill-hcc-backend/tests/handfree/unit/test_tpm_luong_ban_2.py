"""Trang nộp một trang — luồng bản 2 (extension khai supportsFlowV2).

Mỗi khung một việc: nhận tệp → thẻ tiến trình 3 bước (cập nhật tại chỗ theo mốc thật) → kết quả điền → kết quả đính
kèm → kết luận. Nút đi tiếp (chọn hình thức nhận kết quả, nộp) chỉ hiện khi tờ khai đủ ô bắt buộc — kể cả khi công
dân tự gõ thẳng trên cổng (extension đếm lại và báo __event:field_review_status)."""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import field_review, flow, guided_steps, pipeline_runner, store, tracing
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import tu_phap_moi as tpm
from app.channels.handfree.chat.intents import Intent

KEY = "xac-nhan-tinh-trang-hon-nhan"
CAPS = {"supportsTuPhapMoi": True, "supportsTpmAutoFlow": True, "supportsPageBoundDocsComplete": True,
        "supportsAttachmentContext": True, "supportsRating": True,
        "supportsFieldReview": True, "supportsFieldReviewSurvey": True, "supportsFlowV2": True}
PAGE = {"formKind": "surveyjs", "wizardStep": 0, "attachmentTarget": False}
MISSING = {"filled": 13, "optional": 0, "required": 4}
FULL = {"filled": 17, "optional": 0, "required": 0}
SMALL = ["__action:add_documents", "__action:refill", "__action:tpm_attach"]
NEXT = ["__action:tpm_result_method", "__action:tpm_submit"]
PLAN = [{"fileName": "cccd.pdf", "slotName": "Trường hợp đã có vợ"}]


@pytest.fixture(autouse=True)
def spawned(monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: calls.append(coro))
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a, **k: ("run_attach", a))
    monkeypatch.setattr(pipeline_runner, "run_process", lambda *a, **k: ("run_process", a))
    monkeypatch.setattr(tracing, "set_report", AsyncMock())
    monkeypatch.setattr(flow.conv_store, "save", AsyncMock())
    return calls


def _conv(state: str, caps: dict = CAPS, **extra) -> dict:
    conv = store.new_conversation()
    conv.update({
        "procedure_key": KEY, "state": state, "client_capabilities": dict(caps),
        "auth_user": {"id": "u1", "tinh": "Tỉnh A", "xa": "Xã B"},
        "upload_session_id": "s1", "docs_target": "declaration",
        "fields": [{"name": "a", "value": "1"}, {"name": "b", "value": "2", "default": True}],
    })
    conv.update(extra)
    return conv


async def _turn(conv, kind, value, payload=None):
    return await flow.handle_turn(conv, Intent(kind, value, payload or {}), PAGE)


def _sends(reply) -> list[str]:
    return [chip["send"] for chip in reply.chips]


def _trails(reply) -> list[str]:
    return [a["md"] for a in reply.actions if a.get("type") == "trail_message"]


def _steps(reply) -> list[dict]:
    return [a for a in reply.actions if a.get("type") == "pipeline_steps"]


async def _filled_and_attached(review=MISSING, errors=(), attached=1):
    conv = _conv("filling", pipeline_status="running", attachment_plan_started=True)
    await _turn(conv, "action", "fill_report", {"filled": 20, "notFound": [], "review": review})
    conv.update(attach_plan=PLAN, attach_action_in_progress=True)
    reply = await _turn(conv, "action", "attach_report",
                        {"attached": attached, "skipped": 0, "errors": list(errors)})
    return conv, reply


def _default_label() -> str:
    return guided_steps.default_result_method(flow.get_procedure(KEY))["label"]


# ── Gate ──

def test_router_nhan_co_luong_ban_2():
    from app.channels.handfree.chat.router import _clean_client_capabilities

    assert _clean_client_capabilities({"supportsFlowV2": True})["supportsFlowV2"] is True
    assert _clean_client_capabilities({})["supportsFlowV2"] is False


def test_thieu_co_hoac_tieng_mong_thi_giu_luong_cu():
    proc = flow.get_procedure(KEY)
    assert field_review.flow_v2(_conv("done"), proc)
    assert not field_review.flow_v2(_conv("done", {k: v for k, v in CAPS.items() if k != "supportsFlowV2"}), proc)
    assert not field_review.flow_v2(_conv("done", lang="hmong"), proc)
    # Tư pháp form cũ có vòng bổ sung ô (kết hôn) cũng vào luồng bản 2; thủ tục chưa có vòng bổ sung ô thì không.
    assert field_review.flow_v2(_conv("done", procedure_key="ket-hon"), flow.get_procedure("ket-hon"))
    assert not field_review.flow_v2(_conv("done", procedure_key="dang-ky-nuoi-con-nuoi-trong-nuoc"),
                                    flow.get_procedure("dang-ky-nuoi-con-nuoi-trong-nuoc"))


# ── Khung 1 + thẻ tiến trình ──

def test_nhan_tep_khong_hua_so_giay_va_dung_the_3_buoc():
    conv = _conv("filling")
    old = flow.Reply(*flow._fmt(vi.DOCS_COMPLETE_NEXT_STEP, files_count=1))
    reply = tpm.docs_received_reply(conv, flow.get_procedure(KEY), old, 1, all_received=True)
    assert reply.display_md.startswith("✓ Đã nhận **1 tệp**.")
    assert "giây" not in reply.display_md + reply.tts_text
    assert "điền tờ khai và đính kèm" in reply.display_md
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 0, "steps": list(vi.FLOW2_STEPS)}]


def test_du_lieu_dien_ve_thi_im_lang_the_sang_buoc_dien_va_tat_chu_giai_cu():
    conv = _conv("filling")
    reply = flow._fill_fields_reply(conv)
    assert reply.display_md == "" and reply.tts_text == ""
    assert reply.actions[0] == {"type": "pipeline_steps", "active": 1}
    fill = reply.actions[1]
    assert fill["type"] == "fill_fields" and fill["noLegend"] is True and fill["fieldReview"]["noAsk"]


# ── Khung 3: kết quả điền ──

async def test_ket_qua_dien_chi_mot_con_so_la_so_o_xanh_tren_cong():
    conv = _conv("filling", pipeline_status="running", attachment_plan_started=True)
    reply = await _turn(conv, "action", "fill_report", {"filled": 20, "notFound": ["Nơi cấp"], "review": MISSING})
    assert reply.display_md.startswith("🟩 Em đã điền **13 ô** vào tờ khai.")
    assert "20" not in reply.display_md
    assert "🟨 **1 ô** em điền mặc định" in reply.display_md
    assert "⚠️ **1 ô** chưa khớp được trên tờ khai: Nơi cấp." in reply.display_md
    assert reply.tts_text.startswith("Dạ em đã điền 13 ô vào tờ khai.")
    # Đang đính kèm: chưa kết luận, chưa có nút.
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 2}]
    assert not reply.chips and not _trails(reply)
    assert "Hình thức nhận kết quả" not in reply.display_md


async def test_ke_hoach_san_thi_phat_lenh_dinh_khong_noi_da_xep_xong():
    conv = _conv("filling", pipeline_status="attach_ready", attachment_plan_started=True, attach_plan=PLAN)
    reply = await _turn(conv, "action", "fill_report", {"filled": 20, "notFound": [], "review": MISSING})
    assert [a["type"] for a in reply.actions] == ["pipeline_steps", "attach_plan"]
    assert "Đã xếp xong" not in reply.display_md


async def test_ke_hoach_ve_sau_thi_chi_phat_lenh_dinh():
    conv = _conv("filling", pipeline_status="running", attachment_plan_started=True)
    await _turn(conv, "action", "fill_report", {"filled": 20, "notFound": [], "review": MISSING})
    conv.update(pipeline_status="attach_ready", attach_plan=PLAN)
    reply = await _turn(conv, "event", "attach_ready")
    assert reply.display_md == "" and reply.tts_text == ""
    assert [a["type"] for a in reply.actions] == ["attach_plan"]


# ── Khung 4 + 5: kết quả đính kèm, kết luận ──

async def test_con_o_bat_buoc_thi_chi_moi_bo_sung_chua_co_nut_di_tiep():
    conv, reply = await _filled_and_attached(MISSING)
    assert reply.display_md.startswith("📎 Em đã đính kèm **1 tệp**:")
    assert "cccd.pdf" in reply.display_md and "rà soát lại các tệp đã đính" in reply.display_md
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 2, "done": True}]
    (trail,) = _trails(reply)
    assert "🟥 **4 ô bắt buộc** · 🟧 **0 ô không bắt buộc** còn trống." in trail
    assert "tự điền thẳng vào tờ khai, hoặc bấm **Bổ sung các thông tin còn thiếu**" in trail
    assert "Hình thức nhận kết quả" not in reply.display_md + trail
    assert _sends(reply) == ["__action:field_review_start", *SMALL]
    assert "Tờ khai còn 4 ô bắt buộc" in reply.tts_text


async def test_du_o_bat_buoc_thi_ket_luan_kem_hai_nut_di_tiep():
    conv, reply = await _filled_and_attached(FULL)
    (trail,) = _trails(reply)
    assert trail.startswith("✓ Công dân đã điền và đính kèm đủ các thông tin bắt buộc.")
    assert f"đang để **{_default_label()}**" in trail
    assert _sends(reply) == [*SMALL, *NEXT]


async def test_chi_con_o_khong_bat_buoc_thi_van_cho_di_tiep():
    conv, reply = await _filled_and_attached({"filled": 15, "optional": 2, "required": 0})
    (trail,) = _trails(reply)
    assert "còn **2 ô không bắt buộc** để trống" in trail
    assert _sends(reply) == ["__action:field_review_start", *SMALL, *NEXT]
    assert reply.chips[0]["solid"] is False


async def test_khong_dinh_duoc_tep_nao_thi_the_bao_loi_va_chua_ket_luan():
    conv, reply = await _filled_and_attached(FULL, errors=["Tệp cccd.pdf quá lớn"], attached=0)
    assert reply.display_md.startswith("⚠️ Chưa đính được tệp nào")
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 2, "failed": True}]
    assert not set(NEXT) & set(_sends(reply)) and not _trails(reply)


async def test_dinh_loi_mot_phan_thi_bao_loi_va_khong_khang_dinh_da_dinh_du():
    conv, reply = await _filled_and_attached(FULL, errors=["Tệp cccd.pdf quá lớn"])
    assert reply.display_md.startswith("⚠️ Em đính được **1 tệp**, còn lỗi:")
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 2, "failed": True}]
    (trail,) = _trails(reply)
    assert trail.startswith("✓ Công dân đã điền đủ các thông tin bắt buộc.")
    assert "__action:tpm_attach" in _sends(reply)


# ── Công dân tự gõ trên cổng ──

async def test_tu_go_den_khi_du_o_bat_buoc_thi_hien_nut_di_tiep_mot_lan():
    conv, _ = await _filled_and_attached(MISSING)
    assert conv["state"] == "done"
    quiet = await _turn(conv, "event", "field_review_status", {"stats": {"filled": 15, "optional": 0, "required": 2}})
    assert quiet.display_md == "" and not quiet.chips
    ready = await _turn(conv, "event", "field_review_status", {"stats": FULL})
    assert ready.display_md.startswith("✓ Công dân đã điền và đính kèm đủ các thông tin bắt buộc.")
    assert _sends(ready) == [*SMALL, *NEXT]
    again = await _turn(conv, "event", "field_review_status", {"stats": FULL})
    assert again.display_md == "" and not again.chips


async def test_dem_lai_trong_luc_dang_hoi_tung_o_thi_im_lang():
    conv, _ = await _filled_and_attached(MISSING)
    await _turn(conv, "action", "field_review_start")
    reply = await _turn(conv, "event", "field_review_status", {"stats": FULL})
    assert reply.display_md == "" and not reply.chips


async def test_chua_dinh_xong_thi_dem_lai_chua_ket_luan():
    conv = _conv("filling", pipeline_status="running", attachment_plan_started=True)
    await _turn(conv, "action", "fill_report", {"filled": 20, "notFound": [], "review": MISSING})
    reply = await _turn(conv, "event", "field_review_status", {"stats": FULL})
    assert reply.display_md == ""
    # Đính xong sau đó: kết luận dùng số đếm mới nhất.
    conv.update(attach_plan=PLAN, attach_action_in_progress=True)
    reply = await _turn(conv, "action", "attach_report", {"attached": 1, "skipped": 0, "errors": []})
    assert _sends(reply)[-2:] == NEXT


# ── Hỏi xong vòng bổ sung ──

async def test_hoi_xong_van_con_o_bat_buoc_thi_bao_so_o_chua_co_nut_di_tiep():
    conv, _ = await _filled_and_attached(MISSING)
    await _turn(conv, "action", "field_review_start")
    reply = await _turn(conv, "event", "field_review_focus",
                        {"field": None, "stats": {"filled": 15, "optional": 0, "required": 2}})
    assert reply.display_md.startswith("✓ Em đã hỏi hết các ô còn trống. Tờ khai còn **2 ô bắt buộc** công dân cần điền.")
    assert _sends(reply) == ["__action:field_review_start", *SMALL]


async def test_dung_hoi_ma_con_o_bat_buoc_cung_chua_co_nut_di_tiep():
    conv, _ = await _filled_and_attached(MISSING)
    await _turn(conv, "action", "field_review_start")
    reply = await _turn(conv, "action", "field_review_stop")
    assert reply.display_md.startswith("Dạ, em dừng hỏi. Tờ khai còn **4 ô bắt buộc**")
    assert not set(NEXT) & set(_sends(reply))


async def test_hoi_xong_du_o_bat_buoc_thi_hien_nut_di_tiep():
    conv, _ = await _filled_and_attached(MISSING)
    await _turn(conv, "action", "field_review_start")
    reply = await _turn(conv, "event", "field_review_focus", {"field": None, "stats": FULL})
    assert reply.display_md.startswith("✓ Công dân đã điền và đính kèm đủ các thông tin bắt buộc.")
    assert _sends(reply) == [*SMALL, *NEXT]
    # Đã báo đủ: đếm lại về sau không nói lần hai.
    again = await _turn(conv, "event", "field_review_status", {"stats": FULL})
    assert again.display_md == ""


async def test_cau_tu_do_khi_con_o_bat_buoc_khong_hien_nut_di_tiep():
    conv, _ = await _filled_and_attached(MISSING)
    reply = await _turn(conv, "free", "xong rồi")
    assert not set(NEXT) & set(_sends(reply))


# ── Điền lại ──

async def test_dien_lai_the_hai_buoc_roi_ket_luan_ngay():
    conv, _ = await _filled_and_attached(MISSING)
    conv["pipeline_status"] = "attach_done"
    reply = await _turn(conv, "action", "refill")
    assert reply.display_md == vi.FLOW2_REFILL["md"]
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 0, "steps": list(vi.FLOW2_STEPS[:2])}]
    reply = await _turn(conv, "action", "fill_report", {"filled": 20, "notFound": [], "review": FULL})
    assert reply.display_md.startswith("🟩 Em đã điền **17 ô**")
    assert _steps(reply) == [{"type": "pipeline_steps", "active": 2, "done": True}]
    (trail,) = _trails(reply)
    assert trail.startswith("✓ Công dân đã điền và đính kèm đủ")
    assert _sends(reply) == [*SMALL, *NEXT]


async def test_dinh_kem_lai_the_mot_buoc_va_phat_lenh_dinh():
    conv, _ = await _filled_and_attached(MISSING)
    conv.update(pipeline_status="attach_ready", attach_plan=PLAN, attach_action_in_progress=False)
    reply = await _turn(conv, "action", "tpm_attach")
    assert reply.display_md == ""
    assert [a["type"] for a in reply.actions] == ["pipeline_steps", "attach_plan"]
    assert reply.actions[0]["steps"] == [vi.FLOW2_STEPS[2]]


async def test_trang_mot_trang_het_o_bat_buoc_ma_doi_sang_buoc_tiep_thi_hien_nut_di_tiep(monkeypatch):
    from app.channels.handfree.chat.field_review import agent

    conv, _ = await _filled_and_attached(MISSING)
    await _turn(conv, "action", "field_review_start")
    field = {"key": "citizenField9__1", "name": "citizenField9", "role": "", "kind": "text", "label": "Ghi chú",
             "group": "", "section": "Thông tin người nộp", "required": False, "options": [], "value": ""}
    await _turn(conv, "event", "field_review_focus", {"field": field, "stats": {"filled": 17, "optional": 1, "required": 0}})
    monkeypatch.setattr(agent, "interpret", AsyncMock(return_value=agent.Answer("proceed")))
    reply = await _turn(conv, "action", "field_review_answer", {"text": "nộp luôn"})
    assert reply.display_md.startswith("✓ Công dân đã điền và đính kèm đủ các thông tin bắt buộc.")
    assert _sends(reply)[-2:] == NEXT


async def test_trang_mot_trang_hoi_o_khong_bat_buoc_kem_nut_chon_hinh_thuc_va_nop_khong_co_xem_truoc():
    conv, _ = await _filled_and_attached(MISSING)
    start = await _turn(conv, "action", "field_review_start")
    assert start.actions[0]["requiredFirst"] is True
    field = {"key": "citizenField9__1", "name": "citizenField9", "role": "", "kind": "text", "label": "Ghi chú",
             "group": "", "section": "Thông tin người nộp", "required": False, "options": [], "value": ""}
    reply = await _turn(conv, "event", "field_review_focus",
                        {"field": field, "stats": {"filled": 17, "optional": 1, "required": 0}})
    assert any("bấm **Chọn hình thức nhận kết quả** hoặc **Lưu và nộp hồ sơ**" in a.get("md", "")
               for a in reply.actions if a.get("type") == "lead_message")
    assert _sends(reply)[-2:] == NEXT
    assert not any(c.get("cta") for c in reply.chips)  # cỡ thường như các nút của câu hỏi
    assert "__action:field_review_preview" not in _sends(reply)
