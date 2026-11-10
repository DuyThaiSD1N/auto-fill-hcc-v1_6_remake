"""Quay lại bước trước trên wizard tư pháp (chat/step_back.py)."""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import flow, intents, pipeline_runner, step_back, store, tracing
from app.channels.handfree.chat.intents import Intent

PROC = "ket-hon"
CAPS = {"supportsFieldReview": True, "supportsFlowV2": True, "supportsPageBoundDocsComplete": True,
        "supportsStepBack": True}
FIELDS = [{"name": "HoTenBenNam", "comp": "raw", "value": "A"}, {"name": "HoTenBenNu", "comp": "raw", "value": "B"}]
PLAN = [{"target": "file", "componentName": "Giấy tờ tùy thân", "sourceFileIndexes": [0]}]


@pytest.fixture(autouse=True)
def _no_io(monkeypatch):
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: None)
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a, **k: None)
    monkeypatch.setattr(tracing, "set_report", AsyncMock())


def _conv(caps=CAPS, **extra) -> dict:
    conv = store.new_conversation()
    conv.update({"procedure_key": PROC, "state": "attaching", "client_capabilities": dict(caps),
                 "upload_session_id": "s1", "docs_target": "attachment", "auto_attach_after_fill": True,
                 "fields": list(FIELDS), "fill_report": {"filled": 40}, "portal_step": 3,
                 "attach_plan": list(PLAN)})
    conv.update(extra)
    return conv


async def _page(conv, step):
    page = {"formKind": "legacy" if step == 2 else "", "wizardStep": step}
    return await flow.handle_turn(conv, Intent("event", "page_status", page), page)


def _types(reply):
    return [a.get("type") for a in reply.actions]


async def test_extension_cu_khong_khai_capability_thi_lui_buoc_y_luong_cu():
    conv = _conv(caps={k: v for k, v in CAPS.items() if k != "supportsStepBack"})
    reply = await _page(conv, 2)
    assert "step_back_scan" not in _types(reply)
    assert conv["state"] == "attaching"


async def test_lui_ve_ke_khai_thi_kiem_to_khai():
    conv = _conv()
    reply = await _page(conv, 2)
    assert "Kê khai thông tin" in reply.display_md
    scan = next(a for a in reply.actions if a["type"] == "step_back_scan")
    assert scan["fieldReview"]["required"]
    assert conv["state"] == "attaching" and conv["step_back_trip"] is True


async def test_to_khai_bi_trong_thi_dien_lai_tu_du_lieu_da_doc():
    conv = _conv(portal_step=2, step_back_trip=True)
    reply = await flow.handle_turn(conv, Intent("event", "step_back_form", {"stats": {"filled": 0, "required": 12}}))
    fill = next(a for a in reply.actions if a["type"] == "fill_fields")
    assert [f["name"] for f in fill["fields"]] == ["HoTenBenNam", "HoTenBenNu"]
    assert conv["state"] == "filling"


async def test_to_khai_con_giu_va_du_o_bat_buoc_thi_nut_xem_truoc_va_bo_sung_o_khong_bat_buoc():
    conv = _conv(portal_step=2, step_back_trip=True)
    reply = await flow.handle_turn(conv, Intent("event", "step_back_form",
                                                {"stats": {"filled": 38, "required": 0, "optional": 3}}))
    assert "fill_fields" not in _types(reply)
    sends = [c.get("send") for c in reply.chips]
    assert "__action:field_review_preview" in sends and "__action:field_review_start" in sends
    assert conv["field_review"]["stats"]["optional"] == 3


async def test_to_khai_con_giu_het_o_trong_thi_khong_moi_bo_sung():
    conv = _conv(portal_step=2, step_back_trip=True)
    reply = await flow.handle_turn(conv, Intent("event", "step_back_form",
                                                {"stats": {"filled": 40, "required": 0, "optional": 0}}))
    sends = [c.get("send") for c in reply.chips]
    assert "__action:field_review_preview" in sends and "__action:field_review_start" not in sends


async def test_lui_ve_thanh_phan_ho_so_sau_khi_da_dinh_thi_co_nut_dinh_kem_lai():
    conv = _conv(portal_step=4, attach_done=True, state="done", milestones=["guided_result"])
    reply = await _page(conv, 3)
    assert "Thành phần hồ sơ" in reply.display_md
    assert any(c.get("send") == "__event:attach_ready" for c in reply.chips)
    assert conv["state"] == "attaching" and "guided_result" not in conv["milestones"]


async def test_di_lai_toi_thanh_phan_ho_so_da_dinh_thi_khong_dinh_lan_hai():
    conv = _conv(portal_step=2, attach_done=True, step_back_trip=True, docs_target="declaration")
    reply = await _page(conv, 3)
    assert "không đính lần nữa" in reply.display_md
    assert not any(a.get("type") in {"attach_plan", "attach_files"} for a in reply.actions)


async def test_noi_quay_lai_buoc_truoc_thi_bam_nut_quay_lai_cua_cong():
    conv = _conv()
    reply = await flow.handle_turn(conv, Intent("action", "step_back", {}))
    assert "guided_click_back" in _types(reply)
    failed = await flow.handle_turn(conv, Intent("event", "step_back_failed", {}))
    assert "Quay lại" in failed.display_md


def test_y_dinh_quay_lai_buoc_chi_mo_khi_extension_bam_duoc():
    on = [e["value"] for e in intents._state_entries("attaching", _conv())]
    off = [e["value"] for e in intents._state_entries(
        "attaching", _conv(caps={k: v for k, v in CAPS.items() if k != "supportsStepBack"}))]
    assert "step_back" in on and "step_back" not in off
    assert step_back.enabled(_conv(lang="hmong"), {"flowProfile": "tu-phap"}) is False
