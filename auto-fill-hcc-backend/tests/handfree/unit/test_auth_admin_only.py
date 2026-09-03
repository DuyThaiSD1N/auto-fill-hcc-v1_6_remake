"""Login adminOnly (trang quản lý): tài khoản không phải admin bị CHẶN ngay tại login —
không cấp token (chốt 2026-08-07: chỉ admin vào FE quản trị, role khác chỉ dùng extension)."""
import pytest
from bson import ObjectId

from app.auth import service
from app.core.errors import AppError
from app.core.security import hash_password


class _FakeColl:
    def __init__(self, user):
        self._user = user
        self.updated = False

    async def find_one(self, q):
        return self._user if q.get("username") == self._user["username"] else None

    async def update_one(self, *_a, **_k):
        self.updated = True

    async def insert_one(self, *_a, **_k):
        return None


class _FakeDb:
    def __init__(self, user):
        self.users = _FakeColl(user)
        self.refresh_tokens = _FakeColl(user)


def _user(role):
    return {"_id": ObjectId(), "username": "phuongx", "name": "Phường X",
            "role": role, "password_hash": hash_password("matkhau123")}


@pytest.mark.asyncio
async def test_admin_only_chan_tai_khoan_thuong(monkeypatch):
    monkeypatch.setattr(service, "get_db", lambda: _FakeDb(_user("user")))
    with pytest.raises(AppError) as e:
        await service.login("phuongx", "matkhau123", admin_only=True)
    assert e.value.error == "NOT_ADMIN" and e.value.code == 403

    # Cùng tài khoản, login KHÔNG kèm cờ (đường extension) → vẫn cấp token bình thường.
    res = await service.login("phuongx", "matkhau123")
    assert res["accessToken"] and res["user"]["role"] == "user"


@pytest.mark.asyncio
async def test_admin_only_cho_admin_qua(monkeypatch):
    monkeypatch.setattr(service, "get_db", lambda: _FakeDb(_user("admin")))
    res = await service.login("phuongx", "matkhau123", admin_only=True)
    assert res["user"]["role"] == "admin" and res["accessToken"]


@pytest.mark.asyncio
async def test_super_admin_only_phan_biet_voi_admin_only(monkeypatch):
    monkeypatch.setattr(service, "get_db", lambda: _FakeDb(_user("super_admin")))

    res = await service.login("phuongx", "matkhau123", super_admin_only=True)
    assert res["user"]["role"] == "super_admin" and res["accessToken"]

    with pytest.raises(AppError) as error:
        await service.login("phuongx", "matkhau123", admin_only=True)
    assert error.value.error == "NOT_ADMIN"


@pytest.mark.asyncio
async def test_super_admin_only_chan_admin_thuong(monkeypatch):
    monkeypatch.setattr(service, "get_db", lambda: _FakeDb(_user("admin")))
    with pytest.raises(AppError) as error:
        await service.login("phuongx", "matkhau123", super_admin_only=True)
    assert error.value.error == "NOT_SUPER_ADMIN" and error.value.code == 403
