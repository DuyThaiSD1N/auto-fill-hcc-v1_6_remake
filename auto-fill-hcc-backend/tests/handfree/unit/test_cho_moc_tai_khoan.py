"""Thủ tục tư pháp form cũ: chờ tờ khai đổ xong dữ liệu tài khoản (khối người yêu cầu) rồi mới chạy lượt trích ở bước
Kê khai — mốc tài khoản là căn cứ phân vai người yêu cầu (bản thân / cha / mẹ / người khác)."""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import flow, pipeline_runner, store, tracing
from app.channels.handfree.chat.intents import Intent

CAPS = {"supportsFieldReview": True, "supportsFlowV2": True, "supportsAccountAnchorWait": True,
        "supportsPageBoundDocsComplete": True}
PAGE = {"formKind": "legacy", "wizardStep": 2}


@pytest.fixture(autouse=True)
def _no_io(monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: calls.append(coro))
    monkeypatch.setattr(pipeline_runner, "run_process", lambda *a, **k: ("run_process", a))
    monkeypatch.setattr(tracing, "set_report", AsyncMock())
    monkeypatch.setattr(flow.conv_store, "save", AsyncMock())
    monkeypatch.setattr(flow.upload_service, "progress_of",
                        AsyncMock(return_value={"received": 2, "total": 2, "files_count": 2}))
    return calls


def _conv(state, key="khai-sinh-dang-ky-lai", caps=CAPS, **extra):
    conv = store.new_conversation()
    conv.update({"procedure_key": key, "state": state, "client_capabilities": dict(caps),
                 "auth_user": {"id": "u1"}, "upload_session_id": "s1", "docs_target": ""})
    conv.update(extra)
    return conv


async def _page(conv, tai_khoan):
    return await flow.handle_turn(conv, Intent("event", "page_status", {**PAGE, "taiKhoan": tai_khoan}), PAGE)


async def test_sang_ke_khai_cho_khoi_nguoi_yeu_cau_co_du_lieu_roi_moi_chay(_no_io):
    conv = _conv("owner_waiting_next")
    waiting = await _page(conv, "cho")
    assert not _no_io and not conv.get("main_processing_started") and waiting.display_md == ""
    await _page(conv, "co")
    assert [c[0] for c in _no_io] == ["run_process"] and conv["main_processing_started"]


async def test_cho_qua_lau_thi_van_chay(_no_io):
    conv = _conv("owner_waiting_next")
    await _page(conv, "cho")
    await _page(conv, "khong")
    assert [c[0] for c in _no_io] == ["run_process"]


@pytest.mark.parametrize("caps,key", [
    ({k: v for k, v in CAPS.items() if k != "supportsAccountAnchorWait"}, "khai-sinh-dang-ky-lai"),  # bản cũ
    (CAPS, "trich-luc-ks"),  # không phải thủ tục tư pháp form cũ
])
async def test_ban_cu_hoac_thu_tuc_khac_chay_ngay(_no_io, caps, key):
    conv = _conv("owner_waiting_next", caps=caps, key=key)
    await _page(conv, "cho")
    assert [c[0] for c in _no_io] == ["run_process"]


async def test_da_dua_du_o_ke_khai_khi_to_khai_chua_co_tai_khoan_thi_cho_watcher(_no_io):
    conv = _conv("collecting_docs")
    reply = await flow._docs_complete(conv, {**PAGE, "pageContextCaptured": True, "taiKhoan": "cho"})
    assert not _no_io and conv["state"] == "owner_waiting_next" and reply.display_md
    await _page(conv, "co")
    assert [c[0] for c in _no_io] == ["run_process"]
