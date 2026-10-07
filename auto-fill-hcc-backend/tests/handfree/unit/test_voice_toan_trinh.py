"""Tương tác giọng nói toàn trình — test offline (LLM giả lập).

Bốn lỗi thật tại quầy (ảnh chụp): nói đổi phường → bot lặp câu cũ; nói "làm cho người khác" → bot
lặp câu cũ; nói "tôi đồng ý tất cả" ở thẻ xin phép → bot nhắc tích ô; nói "quét bằng điện thoại" ở
bước chủ hồ sơ → bot im lặng. Đo chất lượng thật bằng LLM: tests/handfree/eval/eval_step_intents.py.
"""
import json
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import flow, intents, store
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import Intent
from app.channels.handfree.chat.place_picker import agent as place_agent

BN = {"province": "Thành phố Bắc Ninh", "province_slug": "bacninh", "ward": "Phường Phương Liễu"}


def _conv(state="greet", procedure="khai-sinh-dang-ky-thuong", caps=None):
    c = store.new_conversation(location=dict(BN))
    c["auth_user"] = {"province_slug": "bacninh"}
    c["state"] = state
    c["procedure_key"] = procedure
    c["client_capabilities"] = caps or {}
    return c


def _stub(monkeypatch, target, reply):
    async def fake(messages, **_kw):
        return reply if isinstance(reply, str) else json.dumps(reply, ensure_ascii=False)
    monkeypatch.setattr(target, "llm_chat", fake)


# ── Xin phép: "đồng ý" mọi cách nói ───────────────────────────────────────────────────────

@pytest.mark.parametrize("intent", [Intent("confirm"), Intent("action", "consent_agree")])
async def test_dong_y_bang_loi_o_buoc_xin_phep(monkeypatch, intent):
    monkeypatch.setattr(flow.consent_log, "persist", AsyncMock())
    conv = _conv("consent")
    r = await flow.handle_turn(conv, intent)
    assert conv["consent"]["accepted"] is True
    assert {"type": "consent_verbal", "accepted": True} in r.actions  # thẻ trên màn hình tự tích


async def test_tu_choi_bang_loi_o_buoc_xin_phep(monkeypatch):
    monkeypatch.setattr(flow.consent_log, "persist", AsyncMock())
    conv = _conv("consent")
    r = await flow.handle_turn(conv, Intent("deny"))
    assert conv["consent"]["accepted"] is False
    assert {"type": "consent_verbal", "accepted": False} in r.actions


# ── Bước xác nhận: sửa nơi làm / đối tượng bằng lời ───────────────────────────────────────

async def test_noi_doi_phuong_thi_ap_va_hoi_xac_nhan_lai(monkeypatch):
    conv = _conv("confirm_procedure")
    r = await flow.handle_turn(conv, Intent("action", "set_place", {"ward": "Phường Song Liễu"}))
    assert conv["location"]["ward"] == "Phường Song Liễu"
    assert conv["state"] == "confirm_procedure"
    assert "Phường Song Liễu" in r.display_md and r.tts_text  # bong bóng mới, có đọc


async def test_noi_lam_cho_nguoi_khac_thi_doi_doi_tuong():
    # Câu xác nhận có nêu đối tượng ở màn chọn-thủ-tục-trước (extension hiện tại khai cờ này).
    conv = _conv("confirm_procedure", caps={"supportsProcedureFirst": True})
    r = await flow.handle_turn(conv, Intent("action", "set_place", {"subject": "other_person"}))
    assert conv["execution_subject"] == "other_person"
    assert "cho người khác" in r.display_md


async def test_doi_tinh_ma_chua_neu_xa_thi_bo_xa_cu():
    conv = _conv("confirm_procedure")
    await flow.handle_turn(conv, Intent("action", "set_place", {"province_slug": "hanoi"}))
    assert conv["location"]["province_slug"] == "hanoi" and conv["location"]["ward"] == ""


async def test_xa_chua_chac_thi_goi_y_de_chon():
    conv = _conv("confirm_procedure")
    r = await flow.handle_turn(conv, Intent("action", "set_place", {
        "ward_candidates": ["Phường Phương Liễu", "Phường Song Liễu"]}))
    assert conv["location"]["ward"] == "Phường Phương Liễu"  # chưa đổi
    assert [json.loads(c["send"].split(":", 2)[2])["ward"] for c in r.chips] == [
        "Phường Phương Liễu", "Phường Song Liễu"]


async def test_khong_nghe_ra_gi_thi_hoi_lai_kem_card():
    conv = _conv("confirm_procedure")
    r = await flow.handle_turn(conv, Intent("action", "set_place", {}))
    assert r.display_md.startswith(vi.PLACE_NOT_HEARD["md"][:20])
    assert r.cards and r.cards[0]["kind"] == "location_picker"


async def test_khong_phai_kem_noi_khac_la_sua_khong_phai_tu_choi(monkeypatch):
    """Bộ phân loại trả change_place → agent nơi làm, KHÔNG reset thủ tục."""
    _stub(monkeypatch, intents, {"kind": "state_action", "value": "change_place"})
    _stub(monkeypatch, place_agent, {"province_name": "", "ward_name": "Song Liễu", "subject": None})
    conv = _conv("confirm_procedure")
    i = await intents.resolve("không phải, tôi muốn làm ở phường song liễu", "confirm_procedure", conv)
    assert (i.kind, i.value, i.payload["ward"]) == ("action", "set_place", "Phường Song Liễu")


def test_khop_ten_xa_chi_chon_thang_khi_trung_tron_ten():
    wards = ["Phường Phương Liễu", "Phường Song Liễu", "Xã Tam Tiến", "Phường Tam Tiến"]
    assert place_agent._match_ward("song lieu", wards) == ("Phường Song Liễu", [])
    assert place_agent._match_ward("Phường Song Liễu", wards) == ("Phường Song Liễu", [])
    assert place_agent._match_ward("Liễu", wards) == ("", ["Phường Phương Liễu", "Phường Song Liễu"])
    assert place_agent._match_ward("Tam Tiến", wards) == ("", ["Xã Tam Tiến", "Phường Tam Tiến"])
    assert place_agent._match_ward("Xã Tam Tiến", wards) == ("Xã Tam Tiến", [])
    assert place_agent._match_ward("", wards) == ("", [])


# ── Nút nào đang hiện thì nói được nút đó ─────────────────────────────────────────────────

def test_luu_nut_cua_luot_bot_gom_ca_nut_tren_card():
    conv = _conv("consent")
    r = flow.Reply("x")
    r.chips = [{"label": "Xem lại", "send": "__action:show_consent"},
               {"label": "Xoá", "send": "__action:delete_data"}]
    r.cards = [{"kind": "consent"}]
    flow.update_voice_options(conv, r)
    sends = [i["send"] for i in conv["voice_options"]["items"]]
    assert sends == ["__action:show_consent", "__action:consent_agree", "__action:consent_decline"]
    assert "__action:delete_data" not in sends  # xoá dữ liệu chỉ bấm tay


def test_luot_chi_co_chu_giu_nut_cung_buoc_bo_nut_khi_sang_buoc_khac():
    conv = _conv("qr_waiting")
    r = flow.Reply("x")
    r.chips = [{"label": "Hiện lại mã QR", "send": "__action:reshow_qr"}]
    flow.update_voice_options(conv, r)
    flow.update_voice_options(conv, flow.Reply("Đã nhận 1 tệp"))
    assert conv["voice_options"]["items"]
    conv["state"] = "filling"
    flow.update_voice_options(conv, flow.Reply("Đang điền"))
    assert conv["voice_options"] is None


def test_khong_noi_thay_nut_nop_ho_so():
    conv = _conv("done")
    r = flow.Reply("x")
    r.chips = [{"label": "Gửi hồ sơ", "send": "__action:guided_submit"},
               {"label": "Nhận bản giấy", "send": '__action:pick_result_method:{"method":"paper"}'}]
    flow.update_voice_options(conv, r)
    assert [i["label"] for i in conv["voice_options"]["items"]] == ["Nhận bản giấy"]


async def test_bo_phan_loai_chon_nut_ra_dung_lenh_cua_nut(monkeypatch):
    conv = _conv("owner_waiting_next")
    conv["voice_options"] = {"state": "owner_waiting_next", "items": [
        {"label": "Có, chứng thực luôn", "send": "__action:certify_identity:yes"},
        {"label": "Xong, sang bước đính kèm →", "send": "__action:guided_next", "phase": "owner"},
    ]}
    captured = {}

    async def fake(messages, **_kw):
        captured["system"] = messages[0]["content"]
        return '{"kind":"button","value":"2"}'
    monkeypatch.setattr(intents, "llm_chat", fake)
    i = await intents.resolve("xong rồi sang bước tiếp đi", "owner_waiting_next", conv)
    assert (i.kind, i.value) == ("action", "guided_next")
    assert i.payload["phase"] == "owner" and i.payload["_voice_button"] == "__action:guided_next"
    assert "[2] Xong, sang bước đính kèm →" in captured["system"]


async def test_so_nut_bia_thi_khong_chay_gi(monkeypatch):
    conv = _conv("qr_waiting")
    conv["voice_options"] = {"state": "qr_waiting", "items": [{"label": "A", "send": "__action:reshow_qr"}]}
    _stub(monkeypatch, intents, '{"kind":"button","value":"7"}')
    assert (await intents.resolve("abc", "qr_waiting", conv)).kind == "unknown"


async def test_nut_can_gom_du_lieu_tren_trang_thi_nho_extension_bam_ho():
    conv = _conv("collecting_docs", caps={"supportsVoiceChips": True})
    r = await flow.handle_turn(conv, Intent("action", "docs_done", {"_voice_button": "__action:docs_done"}))
    assert r.actions == [{"type": "press_chip", "send": "__action:docs_done"}]


async def test_extension_cu_chay_thang_lenh_va_khong_nhan_action_moi(monkeypatch):
    monkeypatch.setattr(flow.consent_log, "persist", AsyncMock())
    conv = _conv("consent")
    r = await flow.handle_turn(conv, Intent("action", "consent_agree",
                                            {"_voice_button": "__action:consent_agree"}))
    assert conv["consent"]["accepted"] is True
    assert not any(a.get("type") in ("press_chip", "chip_used") for a in r.actions)


# ── Không bao giờ im lặng ─────────────────────────────────────────────────────────────────

async def test_cau_noi_khong_ro_thi_noi_chua_hieu_kem_nut():
    conv = _conv("owner_waiting_next")
    conv["voice_options"] = {"state": "owner_waiting_next", "items": [
        {"label": "📷 Gửi lại giấy tờ", "send": "__action:resend_owner_docs",
         "chip": {"label": "📷 Gửi lại giấy tờ", "send": "__action:resend_owner_docs"}}]}
    r = await flow.handle_turn(conv, Intent("unknown", payload={"free_text": True}), free_text=True)
    assert "chưa hiểu" in r.display_md and "Gửi lại giấy tờ" in r.display_md
    assert r.chips == [{"label": "📷 Gửi lại giấy tờ", "send": "__action:resend_owner_docs"}]


async def test_su_kien_trang_im_lang_van_im_lang():
    conv = _conv("owner_waiting_next")
    r = await flow.handle_turn(conv, Intent("event", "page_status", {}))
    assert not r.display_md


# ── Bước chủ hồ sơ: lối thoát khi đọc giấy hỏng ───────────────────────────────────────────

async def test_loi_doc_chu_ho_so_co_nut_gui_lai_giay_to():
    conv = _conv("owner_filling")
    conv["pipeline_error"] = "Phiên không còn file nào."
    r = await flow.handle_turn(conv, Intent("event", "pipeline_error"))
    assert conv["state"] == "owner_waiting_next"
    assert r.chips == [{"label": vi.OWNER_RESEND_DOCS_CTA, "send": "__action:resend_owner_docs"}]


async def test_noi_quet_bang_dien_thoai_o_buoc_chu_ho_so_thi_mo_lai_qr(monkeypatch):
    monkeypatch.setattr(flow.upload_service, "create_for_conversation",
                        AsyncMock(return_value={"type": "show_qr", "sid": "new"}))
    conv = _conv("owner_waiting_next")
    conv["upload_session_id"] = "old"
    r = await flow.handle_turn(conv, Intent("pick_doc_method", "qr"), free_text=True)
    assert conv["state"] == "qr_waiting" and conv["owner_phase"] is True
    assert r.actions == [{"type": "show_qr", "sid": "new"}]
