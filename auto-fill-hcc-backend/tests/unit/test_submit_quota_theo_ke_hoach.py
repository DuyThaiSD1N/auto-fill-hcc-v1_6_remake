"""Hồ sơ Auto Fill chỉ nhận số lần nộp bằng số hồ sơ mà lượt đính kèm cuối tạo ra.

Khóa sống theo tab tới lượt điền/đính kèm sau → tab còn giữ khóa mà cán bộ làm tay hồ sơ khác thì cú
bấm nộp vẫn báo về khóa cũ (bản extension cũ trên chợ không tự chặn). Cú bấm vượt hạn không ghi, không
dời mốc nộp → "thời gian làm" không cộng quãng làm tay.
"""
from datetime import datetime, timedelta, timezone

import mongomock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.deps import require_auth
from app.core.errors import AppError, app_error_handler
from app.dossiers import repo
from app.dossiers.router import router as dossiers_router

_T0 = datetime(2026, 11, 18, 7, 10, tzinfo=timezone.utc)
USER = {"id": "u1", "username": "hccx", "name": "UBND X", "role": "commune"}


class _AsyncColl:
    def __init__(self, coll):
        self._c = coll

    async def update_one(self, *a, **kw):
        return self._c.update_one(*a, **kw)

    async def find_one(self, *a, **kw):
        return self._c.find_one(*a, **kw)


class _AsyncDb:
    def __init__(self):
        raw = mongomock.MongoClient().db
        self.dossiers = _AsyncColl(raw.dossiers)
        self.traces = _AsyncColl(raw.traces)


@pytest.fixture()
def db(monkeypatch):
    fake = _AsyncDb()
    monkeypatch.setattr(repo, "get_db", lambda: fake)
    return fake


@pytest.fixture()
def client():
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(dossiers_router)
    app.dependency_overrides[require_auth] = lambda: USER
    return TestClient(app)


def _dossier(db):
    db.dossiers._c.insert_one({"_id": "d1", "user_id": "u1", "experience": "autofill", "started_at": _T0})


def _attach_trace(db, n, at=_T0):
    db.traces._c.insert_one({"dossier_id": "d1", "kind": "attach", "created_at": at,
                             "dossier_ids": [f"r:{i}" for i in range(1, n + 1)]})


def _click(client, i, minutes):
    at = _T0 + timedelta(minutes=minutes)
    res = client.post("/api/v1/dossiers/submit-click", json={
        "dossierId": "d1", "portalHost": "h", "clickId": f"c{i}", "source": "click",
        "clickedAt": int(at.timestamp() * 1000),
    })
    assert res.status_code == 200


def _doc(db):
    return db.dossiers._c.find_one({"_id": "d1"})


@pytest.fixture(autouse=True)
def _now(monkeypatch):
    # Giờ bấm của test nằm trong quá khứ xa → client_clicked_at coi là đồng hồ máy sai; dùng giờ test làm "bây giờ".
    monkeypatch.setattr(repo, "client_clicked_at",
                        lambda ms: datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc))


def test_mot_ho_so_sau_cu_bam_chi_con_mot(db, client):
    _dossier(db)
    _attach_trace(db, 1)
    for i, minutes in enumerate((1, 2, 4, 52, 63, 67)):
        _click(client, i, minutes)
    doc = _doc(db)
    assert doc["submit_count"] == 1 and len(doc["submit_events"]) == 1
    assert repo._utc(doc["submit_clicked_at"]) == _T0 + timedelta(minutes=1)
    assert repo._serialize(doc)["durationMs"] == 60_000


def test_tach_ba_tab_ba_cu_bam_giu_ca_ba(db, client):
    _dossier(db)
    _attach_trace(db, 3)
    for i in range(3):
        _click(client, i, i + 1)
    _click(client, 9, 50)  # cú thứ 4: vượt số hồ sơ đã tách
    assert _doc(db)["submit_count"] == 3


def test_chi_dien_khong_dinh_kem_nhan_mot(db, client):
    _dossier(db)
    _click(client, 0, 1)
    _click(client, 1, 30)
    assert _doc(db)["submit_count"] == 1


def test_lay_luot_dinh_kem_cuoi(db, client):
    _dossier(db)
    _attach_trace(db, 1, at=_T0)
    _attach_trace(db, 2, at=_T0 + timedelta(minutes=1))
    for i in range(3):
        _click(client, i, i + 2)
    assert _doc(db)["submit_count"] == 2
