"""Kế hoạch đính kèm rỗng có lý do (planner cố ý không xếp tệp nào) → một câu, không phát lệnh đính rỗng."""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import flow, store, tracing
from app.channels.handfree.chat.intents import Intent


@pytest.fixture(autouse=True)
def _no_io(monkeypatch):
    monkeypatch.setattr(tracing, "set_report", AsyncMock())


def _conv(**extra):
    conv = store.new_conversation()
    conv.update({"procedure_key": "trich-luc-ks", "state": "attaching", "upload_session_id": "s1",
                 "docs_target": "attachment", "attach_plan": [], "tpm_attach_requested": True, **extra})
    return conv


async def test_ke_hoach_rong_co_ly_do_thi_chi_noi_mot_cau():
    conv = _conv(attach_errors=["Không có giấy ủy quyền — đã bỏ qua 1 tệp."])
    reply = await flow.handle_turn(conv, Intent("event", "attach_ready", {}))
    assert reply.actions == []
    assert reply.display_md.count("Không có giấy ủy quyền — đã bỏ qua 1 tệp.") == 1
    assert "Đã xếp xong" not in reply.display_md and "đang đính" not in reply.display_md
    assert [c["send"] for c in reply.chips] == ["__action:add_documents"]
    assert conv["state"] == "done" and not conv.get("attach_done")


async def test_ke_hoach_rong_khong_ly_do_giu_hanh_vi_cu():
    conv = _conv(attach_errors=[])
    reply = await flow.handle_turn(conv, Intent("event", "attach_ready", {}))
    assert any(a.get("type") == "attach_plan" for a in reply.actions)


async def test_luong_2_trang_mot_trang_giu_cau_bao_va_chot_the_tien_trinh():
    from app.channels.handfree.chat import tu_phap_moi

    caps = {"supportsFieldReview": True, "supportsFieldReviewSurvey": True, "supportsFlowV2": True}
    conv = _conv(attach_errors=["Không có giấy ủy quyền — đã bỏ qua 1 tệp."], client_capabilities=caps)
    assert tu_phap_moi._v2(conv, flow.get_procedure("trich-luc-ks")), "cấu hình test phải vào nhánh luồng 2"
    reply = await flow.handle_turn(conv, Intent("event", "attach_ready", {}))
    assert "Không có giấy ủy quyền — đã bỏ qua 1 tệp." in reply.display_md
    assert reply.actions[0] == {"type": "pipeline_steps", "active": 2, "failed": True}
    assert [a["type"] for a in reply.actions[1:]] == ["trail_message"], "khung kết luận sau câu lý do"
    assert "__action:add_documents" in [c["send"] for c in reply.chips]


_CAPS_V2 = {"supportsTuPhapMoi": True, "supportsTpmAutoFlow": True, "supportsFieldReview": True,
            "supportsFieldReviewSurvey": True, "supportsFlowV2": True}
_REVIEW = {"filled": 6, "optional": 4, "required": 3}


@pytest.mark.parametrize("lang", ["vi", "hmong"])
async def test_luong_2_ke_hoach_rong_ve_truoc_bao_dien_van_co_ket_luan(lang):
    """Kế hoạch (rỗng có lý do) lập xong TRƯỚC khi extension báo điền xong: trước đây chỉ lấy actions của phần đính kèm
    (rỗng) → mất câu lý do + khung kết luận, thẻ tiến trình quay mãi ở bước Đính kèm, không còn nút nào."""
    conv = _conv(state="filling", pipeline_status="attach_ready", attachment_plan_started=True,
                 attach_errors=["Không có giấy ủy quyền — đã bỏ qua 1 tệp."], client_capabilities=_CAPS_V2,
                 docs_target="declaration", lang=lang, fields=[])
    reply = await flow.handle_turn(conv, Intent("action", "fill_report", {"filled": 6, "notFound": [], "review": _REVIEW}),
                                   {"formKind": "surveyjs", "wizardStep": 0, "attachmentTarget": False})
    steps = [a for a in reply.actions if a.get("type") == "pipeline_steps"]
    assert steps == [{"type": "pipeline_steps", "active": 2, "failed": True}]
    trails = [a["md"] for a in reply.actions if a.get("type") == "trail_message"]
    assert len(trails) == 2 and "Không có giấy ủy quyền" in trails[0]
    sends = [c["send"] for c in reply.chips]
    assert "__action:field_review_start" in sends and "__action:add_documents" in sends
    assert conv["state"] == "done"
    if lang == "hmong":
        assert reply.tts_lang == "hmong" and "Daim foos tseem tshuav 3 lub thawv" in reply.tts_text


async def test_luong_tu_dong_gop_bao_dien_va_dinh_kem_giu_nut_dieu_chinh_giay_to():
    from app.channels.handfree.chat import tu_phap_moi

    conv = _conv(state="filling", pipeline_status="attach_ready",
                 attach_errors=["Không có giấy ủy quyền — đã bỏ qua 1 tệp."])
    rep = {"filled": 6, "notFound": []}
    reply = await tu_phap_moi._auto_fill_report_reply(conv, rep, flow.get_procedure("trich-luc-ks"))
    assert "Không có giấy ủy quyền — đã bỏ qua 1 tệp." in reply.display_md
    assert [c["send"] for c in reply.chips] == ["__action:add_documents"]
