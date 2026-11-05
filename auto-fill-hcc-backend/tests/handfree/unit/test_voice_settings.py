"""Cấu hình giọng nói trên web quản trị (voice/store.py, voice/admin_router.py) và cách ws_tts / voice/config dùng nó.

Thứ tự ưu tiên: cán bộ chọn (cài đặt tài khoản) → mặc định trong DB → env. Bảng trống = env (deploy chưa cấu hình chạy y
như cũ). Giọng bị máy chủ giọng từ chối → giọng dự phòng ở env, không mất tiếng. Bản extension cũ vẫn nhận danh mục
giọng cũ và âm thanh 16000 Hz.
"""
import asyncio
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from websockets.exceptions import ConnectionClosedOK

from app.channels.handfree.voice import admin_router, catalog, router, store, ws_tts
from app.core.deps import require_admin, require_auth
from app.core.errors import AppError, app_error_handler


class _Cursor:
    def __init__(self, docs):
        self.docs = docs

    async def to_list(self, length=None):
        return list(self.docs)


class _Coll:
    def __init__(self):
        self.docs: dict[str, dict] = {}

    async def find_one(self, flt):
        doc = self.docs.get(flt["_id"])
        return dict(doc) if doc else None

    async def update_one(self, flt, update, upsert=False):
        self.docs.setdefault(flt["_id"], {"_id": flt["_id"]}).update(update["$set"])

    def find(self, flt):
        return _Cursor([dict(d) for d in self.docs.values()])

    async def insert_one(self, doc):
        from pymongo.errors import DuplicateKeyError
        if doc["_id"] in self.docs:
            raise DuplicateKeyError("dup")
        self.docs[doc["_id"]] = dict(doc)

    async def find_one_and_update(self, flt, update, return_document=None):
        if flt["_id"] not in self.docs:
            return None
        self.docs[flt["_id"]].update(update["$set"])
        return dict(self.docs[flt["_id"]])

    async def delete_one(self, flt):
        class _Res:
            deleted_count = 1 if self.docs.pop(flt["_id"], None) else 0
        return _Res()


class _Db(dict):
    def __missing__(self, key):
        self[key] = _Coll()
        return self[key]


@pytest.fixture()
def db(monkeypatch):
    fake = _Db()
    monkeypatch.setattr(store, "get_db", lambda: fake)
    monkeypatch.setattr(store.settings, "tts_ws_url", "wss://tts.example")
    monkeypatch.setattr(store.settings, "tts_api_key", "key")
    monkeypatch.setattr(store.settings, "tts_tempo", 0.95)
    monkeypatch.setattr(store.settings, "tts_voice", "phuongnhi-north")
    monkeypatch.setattr(store.settings, "asr_grpc_uri", "asr:9112")
    monkeypatch.setattr(store.settings, "asr_speech_timeout", 1.8)
    store.clear_cache()
    yield fake
    store.clear_cache()


def _admin_client():
    app = FastAPI()
    app.include_router(admin_router.router)
    app.add_exception_handler(AppError, app_error_handler)
    app.dependency_overrides[require_admin] = lambda: {"id": "a1", "role": "admin"}
    return TestClient(app)


# ── Thứ tự ưu tiên ──

async def test_bang_trong_dung_env(db):
    assert (await store.tts())["defaultTempo"] == 0.95 and (await store.tts())["wsUrl"] == "wss://tts.example"
    assert (await store.asr())["speechTimeout"] == 1.8
    assert await store.voices_for("vi") == []


async def test_db_de_env_theo_tung_khoa(db):
    await store.update_tts({"defaultTempo": 1.1})
    await store.update_asr({"speechTimeout": 2.5})
    tts = await store.tts()
    assert tts["defaultTempo"] == 1.1 and tts["wsUrl"] == "wss://tts.example", "khoá chưa sửa vẫn lấy env"
    assert (await store.asr())["speechTimeout"] == 2.5


async def test_mongo_loi_van_chay_bang_env(monkeypatch):
    def _boom():
        raise RuntimeError("mongo down")
    monkeypatch.setattr(store, "get_db", _boom)
    store.clear_cache()
    assert (await store.tts())["wsUrl"] == store.settings.tts_ws_url
    assert await store.list_voices() == []
    store.clear_cache()


async def test_chon_giong(db):
    await store.create_voice({"voiceId": "thanhtruc-south", "name": "Thanh Trúc", "gender": "nu", "region": "nam",
                              "ethnicity": "", "sampleRate": 24000, "enabled": True})
    await store.create_voice({"voiceId": "xi", "name": "Cô Xi", "gender": "nu", "region": "", "ethnicity": "H'Mông",
                              "sampleRate": 16000, "enabled": True})
    await store.create_voice({"voiceId": "tat", "name": "Tắt", "gender": "", "region": "", "ethnicity": "",
                              "sampleRate": 16000, "enabled": False})
    assert (await store.resolve_voice("vi", "thanhtruc-south"))["voiceId"] == "thanhtruc-south"
    assert (await store.resolve_voice("vi", "xi"))["voiceId"] == "phuongnhi-north", "giọng Mông không dùng cho tiếng Việt"
    assert (await store.resolve_voice("vi", "tat"))["voiceId"] == "phuongnhi-north", "giọng đã tắt → dự phòng"
    assert (await store.resolve_voice("vi", "bom-tuy-y"))["voiceId"] == "phuongnhi-north"
    assert [v["voiceId"] for v in await store.voices_for("hmong")] == ["xi"]


async def test_bang_trong_van_nhan_giong_danh_muc_cu(db):
    """Bản extension cũ chọn giọng từ danh mục cũ — chưa nhập bảng thì vẫn dùng được."""
    legacy = catalog.voices_for("hmong")[0]["id"]
    assert (await store.resolve_voice("hmong", legacy))["voiceId"] == legacy


# ── API quản trị ──

def test_api_quan_tri_them_sua_xoa_giong(db):
    c = _admin_client()
    r = c.post("/api/v1/admin/voice/voices", json={"voiceId": "ngocanh-central", "name": "Ngọc Anh", "gender": "nu",
                                                    "region": "trung"})
    assert r.status_code == 200 and r.json()["sampleRate"] == 16000, "Hz mặc định 16000"
    assert c.post("/api/v1/admin/voice/voices", json={"voiceId": "ngocanh-central", "name": "X"}).status_code == 409
    assert c.patch("/api/v1/admin/voice/voices/ngocanh-central", json={"sampleRate": 24000}).json()["sampleRate"] == 24000
    assert c.patch("/api/v1/admin/voice/voices/ngocanh-central", json={"sampleRate": 44100}).status_code == 422
    assert c.patch("/api/v1/admin/voice/voices/khong-co", json={"name": "A"}).status_code == 404
    assert [v["voiceId"] for v in c.get("/api/v1/admin/voice/voices").json()["voices"]] == ["ngocanh-central"]
    assert c.delete("/api/v1/admin/voice/voices/ngocanh-central").json() == {"ok": True}


def test_api_quan_tri_cau_hinh_khong_lo_khoa(db):
    c = _admin_client()
    got = c.get("/api/v1/admin/voice/settings").json()
    assert got["tts"]["apiKeyConfigured"] is True and "key" not in json.dumps(got["tts"]).replace("apiKey", "")
    assert got["tts"]["fallbackVoiceVi"] == "phuongnhi-north"
    assert c.put("/api/v1/admin/voice/settings/tts", json={"defaultTempo": 1.5}).status_code == 422, \
        "mặc định phải nằm trong khoảng min–max (0.8–1.3)"
    assert c.put("/api/v1/admin/voice/settings/tts", json={"wsUrl": "http://x"}).status_code == 422
    r = c.put("/api/v1/admin/voice/settings/asr", json={"silenceTimeout": 8, "speechMax": 40})
    assert r.status_code == 200 and r.json()["asr"]["silenceTimeout"] == 8


def test_api_quan_tri_chi_admin():
    app = FastAPI()
    app.include_router(admin_router.router)
    app.add_exception_handler(AppError, app_error_handler)
    app.dependency_overrides[require_auth] = lambda: {"id": "u1", "role": "commune"}
    assert TestClient(app).get("/api/v1/admin/voice/settings").status_code == 403


def test_dia_chi_danh_sach_giong_cua_may_chu():
    assert admin_router._provider_voices_url("wss://sockettts.magicvoice.vn") == "https://sockettts.magicvoice.vn/voices"
    assert admin_router._provider_voices_url("ws://10.0.0.1:8767/x") == "http://10.0.0.1:8767/voices"


# ── voice/config ──

def test_voice_config_giu_danh_muc_cu_cho_ban_tren_cho(db):
    asyncio.run(store.create_voice({"voiceId": "thanhtruc-south", "name": "Thanh Trúc", "gender": "nu", "region": "nam",
                                    "ethnicity": "", "sampleRate": 16000, "enabled": True}))
    app = FastAPI()
    app.include_router(router.router)
    app.dependency_overrides[require_auth] = lambda: {"id": "u1"}
    data = TestClient(app).get("/api/v1/voice/config").json()
    assert data["voices"]["vi"] == catalog.voices_for("vi"), "khoá cũ không đổi — bản cũ vẽ mỗi giọng một nút"
    assert [v["id"] for v in data["voiceOptions"]["vi"]] == ["thanhtruc-south"]
    assert data["tempo"] == {"default": 0.95, "min": 0.8, "max": 1.3}


# ── ws_tts ──

def test_toc_do_ep_vao_khoang_quan_tri():
    cfg = {"defaultTempo": 0.95, "tempoMin": 0.8, "tempoMax": 1.3}
    assert ws_tts._tempo("2", {}, cfg) == 1.3
    assert ws_tts._tempo("", {"ttsTempo": 1.1}, cfg) == 1.1, "không gửi query thì lấy cài đặt tài khoản"
    assert ws_tts._tempo(None, {}, cfg) == 0.95


class _Upstream:
    def __init__(self, frames, wait_texts=0):
        self.sent: list[str] = []
        self.frames = list(frames)
        self.wait_texts = wait_texts

    async def send(self, text):
        self.sent.append(text)

    async def recv(self):
        while len(self.sent) < 1 + self.wait_texts:  # frame cấu hình + số câu cần chờ
            await asyncio.sleep(0.01)
        if not self.frames:
            raise ConnectionClosedOK(None, None)
        return self.frames.pop(0)

    async def close(self):
        pass


class _ClientWs:
    def __init__(self, texts):
        self.inbox = [{"type": "websocket.receive", "text": t} for t in texts]
        self.out: list = []

    async def accept(self, subprotocol=None):
        pass

    async def receive(self):
        if self.inbox:
            return self.inbox.pop(0)
        await asyncio.sleep(3600)

    async def send_json(self, data):
        self.out.append(data)

    async def send_text(self, text):
        self.out.append(json.loads(text))

    async def close(self):
        pass


async def test_giong_bi_may_chu_tu_choi_thi_doi_giong_du_phong(db, monkeypatch):
    await store.create_voice({"voiceId": "hong-nguyen-v1", "name": "Hồng", "gender": "nu", "region": "",
                              "ethnicity": "", "sampleRate": 24000, "enabled": True})
    bad = _Upstream(['{"error": "Invalid voice_id"}'], wait_texts=2)
    good = _Upstream(['{"audio": "AAAA", "sample_rate": 16000}', '{"isFinal": true, "audio": null}'])
    conns = iter([bad, good])

    async def _connect(url, open_timeout=None):
        return next(conns)

    async def _auth(ws):
        return {"id": "u1", "account_settings": {}}, None

    monkeypatch.setattr(ws_tts.websockets, "connect", _connect)
    monkeypatch.setattr(ws_tts, "authenticate_voice_websocket", _auth)
    client = _ClientWs(['{"text": "Xin chào"}', '{"text": ""}'])
    await asyncio.wait_for(ws_tts.ws_tts(client, lang="vi", voice="hong-nguyen-v1", tempo="", sr=""), timeout=5)

    assert json.loads(bad.sent[0])["voice_settings"]["voiceId"] == "hong-nguyen-v1"
    retry = json.loads(good.sent[0])["voice_settings"]
    assert retry["voiceId"] == "phuongnhi-north", "đổi sang giọng dự phòng ở env"
    assert retry["resample_rate"] == 16000, "bản không khai sr=1 luôn nhận 16000 Hz"
    assert good.sent[1:] == ['{"text": "Xin chào"}', '{"text": ""}'], "chữ đã nhận được gửi lại đủ, đúng thứ tự"
    assert {"error": "Invalid voice_id"} not in client.out
    assert any(m.get("audio") for m in client.out if isinstance(m, dict))


async def test_ban_moi_nhan_tan_so_rieng_cua_giong(db, monkeypatch):
    await store.create_voice({"voiceId": "thanhtruc-south", "name": "Thanh Trúc", "gender": "nu", "region": "nam",
                              "ethnicity": "", "sampleRate": 24000, "enabled": True})
    up = _Upstream(['{"isFinal": true, "audio": null}'])

    async def _connect(url, open_timeout=None):
        return up

    async def _auth(ws):
        return {"id": "u1", "account_settings": {"ttsVoiceVi": "thanhtruc-south", "ttsTempo": 1.2}}, None

    monkeypatch.setattr(ws_tts.websockets, "connect", _connect)
    monkeypatch.setattr(ws_tts, "authenticate_voice_websocket", _auth)
    await asyncio.wait_for(ws_tts.ws_tts(_ClientWs([]), lang="vi", voice="", tempo="", sr="1"), timeout=5)
    cfg = json.loads(up.sent[0])["voice_settings"]
    assert cfg["voiceId"] == "thanhtruc-south" and cfg["tempo"] == 1.2 and cfg["resample_rate"] == 24000
