"""Nhật ký sự kiện hồ sơ (`dossiers.events`): đánh giá rút gọn, lựa chọn đăng xuất, kết quả xóa phiên từng cổng."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.deps import require_auth
from app.dossiers import repo
from app.dossiers.router import router as dossiers_router


class _Coll:
    def __init__(self, doc):
        self.doc = doc
        self.updates = []

    async def find_one(self, query, _projection=None):
        if self.doc is None or any(self.doc.get(k) != v for k, v in query.items()):
            return None
        return self.doc

    async def update_one(self, query, update):
        self.updates.append((query, update))
        if self.doc is not None and all(self.doc.get(k) == v for k, v in query.items()):
            self.doc.update(update.get("$set", {}))
            for key, value in update.get("$push", {}).items():
                self.doc.setdefault(key, []).append(value)


class _Db:
    def __init__(self, doc):
        self.dossiers = _Coll(doc)


@pytest.fixture()
def db(monkeypatch):
    fake = _Db({"_id": "d1", "user_id": "u1"})
    monkeypatch.setattr(repo, "get_db", lambda: fake)
    return fake


async def test_danh_gia_chi_ghi_su_kien_khi_doi_muc(db):
    await repo.save_rating(dossier_id="d1", level=4)
    await repo.save_rating(dossier_id="d1", level=4, reasons=["Nhanh"], note="tốt")  # bước 2 cùng mức
    await repo.save_rating(dossier_id="d1", level=5)
    events = db.dossiers.doc["events"]
    assert [(e["type"], e["level"]) for e in events] == [("rating", 4), ("rating", 5)]
    assert "reasons" not in events[0] and db.dossiers.doc["rating"]["level"] == 5


async def test_bo_qua_danh_gia_la_mot_su_kien(db):
    await repo.save_rating(dossier_id="d1", level=None, skipped=True)
    assert db.dossiers.doc["events"][0]["skipped"] is True


async def test_ho_so_chua_co_thi_khong_ghi(db):
    db.dossiers.doc = None
    await repo.save_rating(dossier_id="d1", level=3)
    assert db.dossiers.updates == []


async def test_loai_su_kien_la_bi_bo_qua(db):
    await repo.add_event("d1", "xoa_ho_so")
    assert "events" not in db.dossiers.doc


@pytest.fixture()
def client(monkeypatch):
    calls = []

    async def fake_add_event(dossier_id, event_type, data=None, *, owner_user_id=None):
        calls.append((dossier_id, event_type, data, owner_user_id))

    import app.dossiers.router as module
    monkeypatch.setattr(module.dossiers_repo, "add_event", fake_add_event)
    app = FastAPI()
    app.include_router(dossiers_router)
    app.dependency_overrides[require_auth] = lambda: {"id": "u1"}
    return TestClient(app), calls


def test_ket_qua_xoa_phien_tung_cong_tu_tinh_ok(client):
    c, calls = client
    body = {"dossierId": "d1", "type": "logout_result", "portals": [
        {"host": "dichvucong.gov.vn", "found": 5, "removed": 5, "left": 0},
        {"host": "DichVuCong.BacNinh.gov.vn", "found": 7, "removed": 6, "left": 1},
    ]}
    assert c.post("/api/v1/dossiers/event", json=body).status_code == 200
    (dossier_id, event_type, data, owner) = calls[0]
    assert (dossier_id, event_type, owner) == ("d1", "logout_result", "u1")
    assert [(p["host"], p["ok"]) for p in data["portals"]] == [
        ("dichvucong.gov.vn", True), ("dichvucong.bacninh.gov.vn", False)]


def test_het_2_phut_va_loai_la(client):
    c, calls = client
    assert c.post("/api/v1/dossiers/event", json={"dossierId": "d1", "type": "logout_timeout"}).status_code == 200
    assert calls[0][1:3] == ("logout_timeout", {})
    assert c.post("/api/v1/dossiers/event", json={"dossierId": "d1", "type": "logout_choice"}).status_code == 422
