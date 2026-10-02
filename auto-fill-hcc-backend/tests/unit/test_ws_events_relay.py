"""Sự kiện WS phải tới được kết nối nằm ở worker uvicorn khác (chạy nhiều worker)."""
from collections import OrderedDict

import pytest
from pymongo.errors import PyMongoError

from app.upload_session import ws as ws_mod


class FakeWs:
    def __init__(self, fail: bool = False):
        self.sent: list[dict] = []
        self.fail = fail

    async def send_json(self, payload: dict) -> None:
        if self.fail:
            raise RuntimeError("client rớt")
        self.sent.append(payload)


class FakeColl:
    def __init__(self, fail: bool = False):
        self.docs: list[dict] = []
        self.fail = fail

    async def insert_one(self, doc: dict):
        if self.fail:
            raise PyMongoError("mongo down")
        doc = {**doc, "_id": len(self.docs) + 1}
        self.docs.append(doc)


@pytest.fixture
def coll(monkeypatch):
    fake = FakeColl()
    monkeypatch.setattr(ws_mod, "get_db", lambda: {ws_mod.EVENTS_COLLECTION: fake})
    monkeypatch.setattr(ws_mod, "_SUBS", {})
    return fake


async def test_broadcast_giao_ngay_cho_ws_cung_worker_va_ghi_ws_events(coll):
    local = FakeWs()
    ws_mod._SUBS["s1"] = {local}

    await ws_mod.broadcast("s1", {"type": "files_added", "received": 2})

    assert local.sent == [{"type": "files_added", "received": 2}]
    assert len(coll.docs) == 1
    doc = coll.docs[0]
    assert doc["sid"] == "s1"
    assert doc["payload"] == {"type": "files_added", "received": 2}
    assert doc["origin"] == ws_mod._WORKER_ID


async def test_su_kien_worker_1_toi_ws_dang_o_worker_2(coll, monkeypatch):
    # Worker 1: request upload phát sự kiện, nhưng không giữ WS nào của sid.
    await ws_mod.broadcast("s1", {"type": "complete"})
    event = coll.docs[0]

    # Worker 2: giữ WS của sid, đọc được sự kiện từ ws_events.
    monkeypatch.setattr(ws_mod, "_WORKER_ID", "worker-2")
    remote = FakeWs()
    ws_mod._SUBS["s1"] = {remote}

    assert await ws_mod.handle_relayed_event(event, OrderedDict()) is True
    assert remote.sent == [{"type": "complete"}]


async def test_relay_bo_qua_su_kien_cua_chinh_minh_sid_la_va_ban_trung(coll):
    local = FakeWs()
    ws_mod._SUBS["s1"] = {local}
    seen: OrderedDict = OrderedDict()

    own = {"_id": 1, "sid": "s1", "payload": {"type": "x"}, "origin": ws_mod._WORKER_ID}
    other_sid = {"_id": 2, "sid": "khac", "payload": {"type": "x"}, "origin": "worker-9"}
    remote = {"_id": 3, "sid": "s1", "payload": {"type": "progress"}, "origin": "worker-9"}

    assert await ws_mod.handle_relayed_event(own, seen) is False
    assert await ws_mod.handle_relayed_event(other_sid, seen) is False
    assert await ws_mod.handle_relayed_event(remote, seen) is True
    # Mở lại cursor đọc lùi → gặp lại cùng _id, không giao lần hai.
    assert await ws_mod.handle_relayed_event(remote, seen) is False
    assert local.sent == [{"type": "progress"}]


async def test_mat_mongo_van_giao_cho_ws_cung_worker(monkeypatch):
    monkeypatch.setattr(ws_mod, "get_db", lambda: {ws_mod.EVENTS_COLLECTION: FakeColl(fail=True)})
    local = FakeWs()
    monkeypatch.setattr(ws_mod, "_SUBS", {"s1": {local}})

    await ws_mod.broadcast("s1", {"type": "session_opened"})

    assert local.sent == [{"type": "session_opened"}]


async def test_ws_rot_thi_bi_don_khoi_registry(coll):
    alive, dead = FakeWs(), FakeWs(fail=True)
    ws_mod._SUBS["s1"] = {alive, dead}

    await ws_mod.broadcast("s1", {"type": "files_added"})

    assert ws_mod._SUBS["s1"] == {alive}
