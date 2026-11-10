"""Nói lại lời cổng nháy ở toast cảnh báo / lỗi (chat/portal_alert.py)."""
import pytest

from app.channels.handfree.chat import flow, router, store, tracing
from app.channels.handfree.chat.intents import Intent, resolve_deterministic

CAPS = {"supportsFieldReview": True, "supportsFlowV2": True, "supportsPortalAlert": True}
TOAST = "Vui lòng điền đầy đủ thông tin vào tờ khai"


@pytest.fixture(autouse=True)
def _no_io(monkeypatch):
    async def _noop(*a, **k):
        return None
    monkeypatch.setattr(tracing, "set_report", _noop)


def _conv(caps=CAPS, **extra) -> dict:
    conv = store.new_conversation()
    conv.update({"procedure_key": "ket-hon", "state": "reviewing", "client_capabilities": dict(caps)})
    conv.update(extra)
    return conv


def _alert(text=TOAST) -> Intent:
    intent = resolve_deterministic(f'__event:portal_alert:{{"text": "{text}"}}')
    assert intent == Intent("event", "portal_alert", {"text": text})
    return intent


async def test_noi_lai_nguyen_loi_cong_khong_doi_buoc():
    conv = _conv()
    reply = await flow.handle_turn(conv, _alert())
    assert f"Cổng báo: **{TOAST}**" in reply.display_md
    assert reply.tts_text.startswith(f"Cổng báo: {TOAST}.")
    assert not reply.actions and conv["state"] == "reviewing"


async def test_extension_cu_khong_khai_capability_thi_im_lang():
    conv = _conv(caps={k: v for k, v in CAPS.items() if k != "supportsPortalAlert"})
    reply = await flow.handle_turn(conv, _alert())
    assert not reply.display_md and not reply.tts_text


@pytest.mark.parametrize("extra", [{"state": "filling"}, {"state": "greet"}, {"attach_action_in_progress": True},
                                   {"lang": "hmong"}])
async def test_im_lang_khi_tro_ly_dang_tu_dien_dinh_hoac_tieng_mong(extra):
    reply = await flow.handle_turn(_conv(**extra), _alert())
    assert not reply.display_md and not reply.tts_text


async def test_loi_cong_dai_bi_cat_gon():
    reply = await flow.handle_turn(_conv(), _alert("x " * 300))
    assert len(reply.display_md) < 300


def test_whitelist_capability():
    assert router._clean_client_capabilities({"supportsPortalAlert": True})["supportsPortalAlert"] is True
    assert router._clean_client_capabilities({})["supportsPortalAlert"] is False
