"""Sidebar nối lại kênh tiến trình (BE vừa khởi động lại): __event:pipeline_resync bù sự kiện đã lỡ và chạy lại tác
vụ nền đã chết theo lần khởi động lại — không để hội thoại đứng im ở "đang xử lý"."""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import flow, pipeline_runner, store, tracing
from app.channels.handfree.chat.intents import Intent


@pytest.fixture
def spawned(monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: calls.append(coro))
    for name in ("run_process", "run_owner_info", "run_attach", "run_business_registration"):
        monkeypatch.setattr(pipeline_runner, name, lambda *a, _n=name, **k: (_n, a))
    monkeypatch.setattr(tracing, "set_report", AsyncMock())
    return calls


def _beat(monkeypatch, kind="", alive=False):
    monkeypatch.setattr(pipeline_runner, "last_heartbeat", AsyncMock(return_value=(kind, alive)))


def _conv(state, **extra):
    conv = store.new_conversation()
    conv.update({"procedure_key": "ket-hon", "state": state, "upload_session_id": "s1",
                 "client_capabilities": {}, "auth_user": {"id": "u1"}})
    conv.update(extra)
    return conv


async def _resync(conv):
    return await flow.handle_turn(conv, Intent("event", "pipeline_resync", {}))


async def test_du_lieu_dien_da_xong_ma_chua_giao_thi_phat_lenh_dien_mot_lan(spawned, monkeypatch):
    _beat(monkeypatch)
    conv = _conv("filling", pipeline_status="fields_ready", fields_dispatched=False,
                 fields=[{"name": "a", "value": "1"}])
    reply = await _resync(conv)
    assert reply.actions and reply.actions[0]["type"] == "fill_fields"
    again = await _resync(conv)
    assert not again.actions and again.display_md == ""


async def test_dang_chay_va_tac_vu_con_nhip_tim_thi_im_lang(spawned, monkeypatch):
    _beat(monkeypatch, "process", alive=True)
    reply = await _resync(_conv("filling", pipeline_status="running"))
    assert reply.display_md == "" and not reply.actions and not spawned


async def test_tac_vu_dien_chet_theo_lan_khoi_dong_lai_thi_chay_lai(spawned, monkeypatch):
    _beat(monkeypatch, "process", alive=False)
    reply = await _resync(_conv("filling", pipeline_status="running"))
    assert reply.display_md == "" and [c[0] for c in spawned] == ["run_process"]


async def test_tac_vu_xep_dinh_kem_chet_thi_chay_lai_dung_tac_vu_do(spawned, monkeypatch):
    _beat(monkeypatch, "attach", alive=False)
    await _resync(_conv("attaching", pipeline_status="running", attachment_plan_started=True, attach_mode="split"))
    assert [c[0] for c in spawned] == ["run_attach"]
    assert spawned[0][1][3]["splitMode"] is True


async def test_chua_co_nhip_tim_nao_thi_doan_tac_vu_theo_buoc(spawned, monkeypatch):
    _beat(monkeypatch)
    await _resync(_conv("owner_filling", pipeline_status="running"))
    assert [c[0] for c in spawned] == ["run_owner_info"]


async def test_ke_hoach_dinh_kem_da_xong_ma_chua_phat_thi_phat(spawned, monkeypatch):
    _beat(monkeypatch)
    conv = _conv("attaching", pipeline_status="attach_ready", attach_plan=[{"fileName": "a.pdf"}],
                 attach_action_in_progress=False, docs_target="attachment")
    reply = await _resync(conv)
    assert any(a.get("type") == "attach_plan" for a in reply.actions)


async def test_khong_o_buoc_xu_ly_thi_im_lang(spawned, monkeypatch):
    _beat(monkeypatch)
    reply = await _resync(_conv("done", pipeline_status="attach_done"))
    assert reply.display_md == "" and not reply.actions and not spawned


class _FakeColl:
    def __init__(self):
        self.docs = {}

    async def update_one(self, flt, update, upsert=False):
        self.docs.setdefault(flt["_id"], {"_id": flt["_id"]}).update(update["$set"])

    async def delete_one(self, flt):
        doc = self.docs.get(flt["_id"])
        if doc and all(doc.get(k) == v for k, v in flt.items()):
            del self.docs[flt["_id"]]

    async def find_one(self, flt):
        return self.docs.get(flt["_id"])


async def test_tac_vu_ghi_nhip_tim_luc_chay_va_xoa_khi_xong(monkeypatch):
    import asyncio
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace

    coll = _FakeColl()
    monkeypatch.setattr(pipeline_runner, "get_db", lambda: SimpleNamespace(pipeline_heartbeats=coll))
    seen = {}

    @pipeline_runner._tracked("process")
    async def job(conv_id):
        await asyncio.sleep(0)
        seen["during"] = await pipeline_runner.last_heartbeat(conv_id)

    await job("c1")
    assert seen["during"] == ("process", True)
    assert await pipeline_runner.last_heartbeat("c1") == ("", False)
    # Tác vụ bị giết giữa chừng: bản ghi còn nhưng quá hạn → coi là chết, vẫn biết loại tác vụ để chạy lại.
    coll.docs["c2"] = {"_id": "c2", "kind": "attach", "at": datetime.now(timezone.utc) - timedelta(minutes=2)}
    assert await pipeline_runner.last_heartbeat("c2") == ("attach", False)
