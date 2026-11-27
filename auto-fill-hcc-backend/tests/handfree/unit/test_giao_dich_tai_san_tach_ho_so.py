"""Chứng thực giao dịch tài sản: cài đặt "tách hồ sơ" chỉ áp khi extension khai supportsRegistrySplitTabs;
extension cũ (chỉ đa tab cho bản sao/chữ ký) giữ luồng gộp như trước."""
import asyncio

from app.channels.handfree.chat import flow, pipeline_runner
from app.channels.handfree.chat.router import _clean_client_capabilities

KEY = "chung-thuc-giao-dich-tai-san"


def _conv(caps=None, **kw):
    base = {
        "_id": "t-gd-tach", "state": "collecting_docs", "history": [],
        "procedure_key": KEY, "upload_session_id": "", "docs_target": "attachment", "attach_mode": None,
        "attachment_preferences": {"attachMode": "split"}, "client_capabilities": caps or {},
    }
    base.update(kw)
    return base


def _capture_run_attach(monkeypatch):
    calls = {}

    async def fake_run_attach(conv_id, sid, key, options):
        calls["options"] = options

    async def one_file(_sid):
        return {"received": 1, "total": 1, "files_count": 1}

    monkeypatch.setattr(pipeline_runner, "run_attach", fake_run_attach)
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: asyncio.ensure_future(coro))
    monkeypatch.setattr(flow.upload_service, "progress_of", one_file)
    return calls


def test_router_giu_capability_moi():
    assert _clean_client_capabilities({"supportsRegistrySplitTabs": True})["supportsRegistrySplitTabs"] is True
    assert _clean_client_capabilities({"supportsRegistrySplitTabs": "true"})["supportsRegistrySplitTabs"] is False


async def test_extension_moi_tach_ho_so(monkeypatch):
    calls = _capture_run_attach(monkeypatch)
    conv = _conv({"supportsRegistrySplitTabs": True})
    await flow._docs_complete(conv, {"attachmentTarget": True})
    await asyncio.sleep(0)
    assert conv["attach_mode"] == "split" and calls["options"]["splitMode"] is True

    action = flow._attach_plan_action(conv, [{"fileIndex": 0}])
    assert action["mode"] == "split" and action["splitTabs"] is True


async def test_extension_cu_giu_luong_gop(monkeypatch):
    calls = _capture_run_attach(monkeypatch)
    conv = _conv()
    await flow._docs_complete(conv, {"attachmentTarget": True})
    await asyncio.sleep(0)
    assert not conv.get("attach_mode") and "splitMode" not in calls["options"]

    action = flow._attach_plan_action(conv, [{"fileIndex": 0}])
    assert action["mode"] == "merge" and "splitTabs" not in action


def test_ban_sao_khong_mang_co_split_tabs():
    conv = {"procedure_key": "chung-thuc-ban-sao", "attach_mode": "split", "upload_session_id": ""}
    assert "splitTabs" not in flow._attach_plan_action(conv, [])
