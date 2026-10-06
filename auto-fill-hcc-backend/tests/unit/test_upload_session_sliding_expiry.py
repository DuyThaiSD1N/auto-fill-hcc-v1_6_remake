"""Mã QR tải ảnh của Auto Fill: còn dùng thì không hết hạn, bỏ không 30 phút thì tự hết.

Trước đây hạn cố định 30 phút từ lúc TẠO mã → cán bộ mở QR từ hồ sơ trước rồi làm tiếp là panel báo
"Phiên tải ảnh đã hết hạn" giữa chừng.
"""
from datetime import datetime, timedelta, timezone

import mongomock
import pytest

from app.config import settings
from app.upload_session import store


class _AsyncColl:
    def __init__(self, coll):
        self._c = coll

    async def update_one(self, *a, **kw):
        return self._c.update_one(*a, **kw)


class _Db:
    def __init__(self):
        self.raw = mongomock.MongoClient().db
        self.upload_sessions = _AsyncColl(self.raw.upload_sessions)


@pytest.fixture()
def db(monkeypatch):
    fake = _Db()
    monkeypatch.setattr(store, "get_db", lambda: fake)
    return fake


def _expiry(db, sid):
    exp = db.raw.upload_sessions.find_one({"_id": sid})["expires_at"]
    return exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)


def _insert(db, experience, minutes_left):
    sess = {"_id": f"HS-{experience}", "experience": experience,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=minutes_left)}
    db.raw.upload_sessions.insert_one(sess)
    return sess["_id"]


async def test_dang_dung_thi_gia_han_du_30_phut_tu_luc_do(db):
    sid = _insert(db, "autofill", minutes_left=2)          # sắp hết vì mở từ 28 phút trước
    await store.extend_autofill_expiry(sid)
    left = _expiry(db, sid) - datetime.now(timezone.utc)
    assert timedelta(minutes=settings.upload_session_ttl_minutes - 1) < left \
        <= timedelta(minutes=settings.upload_session_ttl_minutes)


async def test_hoi_lien_tuc_khong_ghi_db_moi_luot(db):
    sid = _insert(db, "autofill", minutes_left=settings.upload_session_ttl_minutes)  # vừa gia hạn
    before = _expiry(db, sid)
    await store.extend_autofill_expiry(sid)
    assert _expiry(db, sid) == before, "hạn chỉ vừa đặt — chưa cần ghi lại"


async def test_phien_handfree_khong_dung_toi(db):
    sid = _insert(db, "handfree", minutes_left=5)
    before = _expiry(db, sid)
    await store.extend_autofill_expiry(sid)
    assert _expiry(db, sid) == before


def test_router_gia_han_o_ca_ba_cho_dung_phien():
    import inspect
    from app.upload_session import router
    for fn in (router.get_session, router.get_file, router.upload_files):
        assert "extend_autofill_expiry(sid)" in inspect.getsource(fn), fn.__name__
