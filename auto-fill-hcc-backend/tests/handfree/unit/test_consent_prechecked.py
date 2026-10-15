"""Thẻ xin phép tích sẵn 2 ô cam kết: biên bản ghi rõ ô được tích sẵn (prechecked)."""
from unittest.mock import AsyncMock

from app.channels.handfree.chat import flow, store
from app.channels.handfree.chat.intents import Intent


def _conv():
    conv = store.new_conversation()
    conv.update({"state": "consent", "procedure_key": "ket-hon"})
    return conv


async def _consent(monkeypatch, payload):
    persist = AsyncMock()
    monkeypatch.setattr(flow.consent_log, "persist", persist)
    await flow.handle_turn(_conv(), Intent("action", "consent", payload))
    return persist.await_args.args[0]


async def test_the_moi_tich_san_thi_bien_ban_ghi_prechecked(monkeypatch):
    entry = await _consent(monkeypatch, {"accepted": True, "checks": [True, True], "prechecked": True})
    assert entry["accepted"] is True and entry["method"] == "chip" and entry["prechecked"] is True


async def test_extension_cu_khong_gui_thi_ghi_false(monkeypatch):
    entry = await _consent(monkeypatch, {"accepted": True, "checks": [True, True]})
    assert entry["prechecked"] is False
