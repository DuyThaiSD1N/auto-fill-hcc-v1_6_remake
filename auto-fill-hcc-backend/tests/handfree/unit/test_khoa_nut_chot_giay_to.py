"""Chốt giấy tờ tự động (chọn tệp từ máy / điện thoại báo xong) cũng phải khoá nút "Đã đưa đủ" như bấm tay."""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import flow, pipeline_runner, store, tracing
from app.channels.handfree.chat.intents import Intent

LOCKS = [{"type": "chip_used", "send": s}
         for s in ("__action:docs_done", "__action:pick_files_again", "__action:reshow_qr")]
PAGE = {"pageContextCaptured": True, "wizardStep": 2, "formKind": "legacy", "declarationTarget": True}


@pytest.fixture(autouse=True)
def _no_io(monkeypatch):
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: coro.close())
    monkeypatch.setattr(tracing, "set_report", AsyncMock())
    monkeypatch.setattr(flow.upload_service, "complete_session", AsyncMock())
    monkeypatch.setattr(flow.upload_service, "progress_of",
                        AsyncMock(return_value={"received": 1, "total": 2, "files_count": 1}))


def _conv() -> dict:
    conv = store.new_conversation()
    conv.update({"procedure_key": "ket-hon", "state": "collecting_docs", "doc_method": "scan",
                 "upload_session_id": "s1", "client_capabilities": {"supportsPageBoundDocsComplete": True}})
    return conv


async def test_tu_chot_sau_khi_chon_tep_thi_khoa_nut_da_dua_du():
    conv = _conv()
    r = await flow.handle_turn(conv, Intent("action", "docs_done", PAGE), PAGE)
    assert conv["pipeline_status"] == "running"
    assert all(lock in r.actions for lock in LOCKS)


async def test_dien_thoai_bao_xong_cung_khoa_nut():
    conv = _conv()
    r = await flow.handle_turn(conv, Intent("event", "docs_complete", PAGE), PAGE)
    assert all(lock in r.actions for lock in LOCKS)


async def test_chua_chot_duoc_thi_khong_khoa_nut_moi():
    conv = _conv()
    page = {"pageContextCaptured": True}  # chưa nhận ra trang → trả lại nút chốt mới
    r = await flow.handle_turn(conv, Intent("action", "docs_done", page), page)
    assert any(c.get("send") == "__action:docs_done" for c in r.chips)
    assert not any(a.get("type") == "chip_used" for a in r.actions)
