import re

import mongomock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.archive.config import archive_settings
from app.core.deps import require_auth
from app.core.errors import AppError, app_error_handler
from app.form_snapshots import relay
from app.form_snapshots.router import router
from app.form_snapshots.step_rules import PORTAL_STEP, form_snapshot_config
from app.procedures.portal_submit import PORTAL_SUBMIT

USER = {"id": "u1", "username": "hccx", "name": "Xã X"}
BODY = {
    "snapshotId": "snap-0001", "requestId": "req_abc", "kind": "step", "trigger": "tiep tuc",
    "host": "dvc.moc.gov.vn", "path": "/vi/padsvc/apply-online/x", "at": 1_761_450_000_000, "extVersion": "1.25",
    "fields": [{"name": "data[hoTen]", "comp": "dom-input", "value": "A", "label": "Họ và tên", "pos": 412},
               {"name": "DiaChi", "comp": "x-select-area", "value": {"tinh": "T", "xa": "X"}}],
}


class _AsyncColl:
    def __init__(self, coll):
        self._c = coll

    async def find_one(self, *a, **kw):
        return self._c.find_one(*a, **kw)

    async def insert_one(self, doc):
        return self._c.insert_one(doc)


class _Db:
    def __init__(self):
        self.raw = mongomock.MongoClient(tz_aware=True).db

    def __getattr__(self, name):
        return _AsyncColl(self.raw[name])


@pytest.fixture()
def db(monkeypatch):
    fake = _Db()
    monkeypatch.setattr(relay, "get_db", lambda: fake)
    monkeypatch.setattr(archive_settings, "vault_url", "http://vault.test")
    return fake


@pytest.fixture()
def client(db, monkeypatch):
    sent: list[dict] = []

    async def fake_relay(bundle):
        sent.append(bundle)

    monkeypatch.setattr(relay, "relay", fake_relay)
    app = FastAPI()

    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(router)
    app.dependency_overrides[require_auth] = lambda: USER
    return TestClient(app), sent


def test_chi_nhan_luot_cua_chinh_tai_khoan(client, db):
    c, sent = client
    db.raw.process_requests.insert_one({"request_id": "req_abc", "user_id": "u2", "procedure": "p"})
    assert c.post("/api/v1/form-snapshots", json=BODY).status_code == 404
    assert sent == []


def test_chuyen_sang_kho_kem_request_id(client, db):
    c, sent = client
    db.raw.process_requests.insert_one({"request_id": "req_abc", "user_id": "u1", "procedure": "khai-sinh",
                                        "experience": "handfree", "options": {"conversation_id": "cv1"}})
    assert c.post("/api/v1/form-snapshots", json=BODY).status_code == 200
    (bundle,) = sent
    assert bundle["type"] == "form_snapshot" and bundle["request_id"] == "req_abc"
    assert bundle["procedure"] == "khai-sinh" and bundle["conversation_id"] == "cv1"
    assert bundle["unit"]["user_id"] == "u1"
    assert bundle["snapshot"]["kind"] == "step" and bundle["snapshot"]["extVersion"] == "1.25"
    assert bundle["snapshot"]["fields"][1]["value"] == {"tinh": "T", "xa": "X"}
    assert bundle["snapshot"]["fields"][0]["label"] == "Họ và tên" and bundle["snapshot"]["fields"][0]["pos"] == 412
    assert bundle["created_at"].startswith("2025-10-26")


def test_tu_choi_gia_tri_qua_dai(client, db):
    c, _ = client
    body = {**BODY, "fields": [{"name": "x", "value": "a" * 5000}]}
    assert c.post("/api/v1/form-snapshots", json=body).status_code == 422


class _Vault:
    def __init__(self, fail):
        self.fail, self.bundles = fail, []

    async def send(self, bundle, files):
        if self.fail:
            raise ConnectionError("vault không phản hồi")
        self.bundles.append(bundle)


async def test_kho_loi_thi_giu_tam_cho_archiver(db, monkeypatch):
    monkeypatch.setattr(relay, "_client", _Vault(fail=True))
    await relay.relay({"id": "snap-1", "type": "form_snapshot"})
    await relay.relay({"id": "snap-1", "type": "form_snapshot"})
    assert db.raw.form_snapshots.count_documents({}) == 1


async def test_kho_nhan_thi_khong_luu_gi(db, monkeypatch):
    vault = _Vault(fail=False)
    monkeypatch.setattr(relay, "_client", vault)
    await relay.relay({"id": "snap-1", "type": "form_snapshot"})
    assert len(vault.bundles) == 1 and db.raw.form_snapshots.count_documents({}) == 0


async def test_khong_bat_kho_thi_luu_cho_monitor(db, monkeypatch):
    monkeypatch.setattr(archive_settings, "vault_url", "")
    vault = _Vault(fail=False)
    monkeypatch.setattr(relay, "_client", vault)
    await relay.relay({"id": "snap-1", "type": "form_snapshot"})
    assert vault.bundles == [] and db.raw.form_snapshots.count_documents({}) == 1


def test_luat_buoc_hop_le():
    for host, rules in PORTAL_STEP.items():
        assert isinstance(rules, list) and rules, host
        for rule in rules:
            assert rule.get("urlPattern"), host
            re.compile(rule["urlPattern"])
            assert rule.get("buttonIds") or rule.get("buttonText") or rule.get("buttonSelector"), host


def test_formio_khong_khop_theo_nhan_tiep_tuc():
    formio = [h for h, r in PORTAL_SUBMIT.items() if r.get("buttonSelector") == 'button[form="captchaForm"]']
    assert len(formio) == 10
    for host in formio:
        (rule,) = PORTAL_STEP[host]
        assert "buttonText" not in rule and "-0" in rule["buttonSelector"]


def test_cau_hinh_gui_kem_lenh_dien():
    cfg = form_snapshot_config("req_x")
    assert cfg["requestId"] == "req_x" and cfg["stepRules"] is PORTAL_STEP
