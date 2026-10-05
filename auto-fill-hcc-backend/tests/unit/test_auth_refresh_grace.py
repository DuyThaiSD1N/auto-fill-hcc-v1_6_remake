"""Làm mới token: tranh chấp xoay vòng không được đá cán bộ ra; mọi lần làm mới/thất bại có nhật ký.

Nhiều nơi trên CÙNG một máy làm mới bằng cùng một refresh token (nhiều tab mở panel, tab tách
chứng thực, background gửi mốc nộp, đọc giọng nói lúc đang chat). BE xoay vòng: token cũ bị thu hồi
ngay → bên đến sau bị 401 → extension xoá token → cán bộ thấy màn đăng nhập giữa lúc làm hồ sơ.
"""
from datetime import datetime, timedelta, timezone

import mongomock
import pytest
from bson import ObjectId

from app.auth import service
from app.core.errors import AppError
from app.core.security import create_refresh_token, hash_password, token_hash


class _AsyncColl:
    def __init__(self, coll):
        self._c = coll

    async def find_one(self, *a, **kw):
        return self._c.find_one(*a, **kw)

    async def insert_one(self, *a, **kw):
        return self._c.insert_one(*a, **kw)

    async def update_one(self, *a, **kw):
        return self._c.update_one(*a, **kw)


class _Db:
    def __init__(self):
        raw = mongomock.MongoClient().db
        self.raw = raw
        self.users = _AsyncColl(raw.users)
        self.refresh_tokens = _AsyncColl(raw.refresh_tokens)
        self.auth_events = _AsyncColl(raw.auth_events)


@pytest.fixture()
def db(monkeypatch):
    fake = _Db()
    monkeypatch.setattr(service, "get_db", lambda: fake)
    return fake


def _user(db, **extra):
    uid = ObjectId()
    db.raw.users.insert_one({"_id": uid, "username": "hccvuninh", "password_hash": hash_password("mk123456"),
                             "role": "commune", **extra})
    return str(uid)


def _stored_refresh(db, uid, **extra):
    token = create_refresh_token(uid)
    db.raw.refresh_tokens.insert_one({"user_id": uid, "token_hash": token_hash(token), "revoked_at": None,
                                      "expires_at": datetime.now(timezone.utc) + timedelta(days=30), **extra})
    return token


def _events(db, event=None):
    return [e for e in db.raw.auth_events.find() if event is None or e["event"] == event]


async def test_hai_noi_cung_lam_moi_bang_mot_token_deu_duoc_cap(db):
    uid = _user(db)
    token = _stored_refresh(db, uid)
    first = await service.refresh(token, "chrome", ip="1.2.3.4")
    second = await service.refresh(token, "chrome")   # tab khác / background, chậm hơn một nhịp
    assert first["accessToken"] and second["accessToken"]
    assert first["refreshToken"] != second["refreshToken"]
    assert [e["event"] for e in _events(db)] == ["refresh", "refresh_grace"]


async def test_dung_lai_token_xoay_vong_qua_an_han_bi_tu_choi(db):
    uid = _user(db)
    old = datetime.now(timezone.utc) - timedelta(minutes=5)
    token = _stored_refresh(db, uid, revoked_at=old, revoked_reason="rotated")
    with pytest.raises(AppError) as exc:
        await service.refresh(token)
    assert exc.value.code == 401
    assert _events(db, "refresh_fail")[0]["reason"] == "rotated_reuse"


async def test_token_thu_hoi_do_khoa_xoa_tai_khoan_khong_co_an_han(db):
    """Thu hồi do admin (khoá/xoá) không mang lý do "rotated" — không được cho qua dù vừa xong."""
    uid = _user(db)
    token = _stored_refresh(db, uid, revoked_at=datetime.now(timezone.utc))
    with pytest.raises(AppError):
        await service.refresh(token)
    assert _events(db, "refresh_fail")[0]["reason"] == "revoked"


async def test_token_khong_ton_tai_ghi_ly_do(db):
    """Vd gọi nhầm sang server khác (database khác) — trước đây không có dấu vết nào."""
    uid = _user(db)
    token = create_refresh_token(uid)
    with pytest.raises(AppError):
        await service.refresh(token, "chrome", ip="5.6.7.8")
    ev = _events(db, "refresh_fail")[0]
    assert ev["reason"] == "not_found" and ev["user_id"] == uid and ev["ip"] == "5.6.7.8"


async def test_dang_nhap_va_dang_nhap_sai_co_nhat_ky(db):
    _user(db)
    await service.login("hccvuninh", "mk123456", "chrome", ip="1.1.1.1")
    with pytest.raises(AppError):
        await service.login("hccvuninh", "sai", "chrome")
    assert [(e["event"], e.get("reason")) for e in _events(db)] == [("login", None), ("login_fail", "invalid_credentials")]


async def test_lam_moi_danh_dau_ly_do_xoay_vong(db):
    uid = _user(db)
    token = _stored_refresh(db, uid)
    await service.refresh(token)
    assert db.raw.refresh_tokens.find_one({"token_hash": token_hash(token)})["revoked_reason"] == "rotated"
