from bson import ObjectId
from fastapi import FastAPI
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
import pytest

from app.auth import service
from app.auth.access_control import (
    MAINTENANCE_ERROR,
    MAINTENANCE_MESSAGE,
    ensure_account_available,
)
from app.core import deps
from app.core.errors import AppError, app_error_handler
from app.core.security import hash_password
from scripts import set_account_access


class _Collection:
    def __init__(self, result):
        self.result = result
        self.writes = 0

    async def find_one(self, _query):
        return self.result

    async def update_one(self, *_args, **_kwargs):
        self.writes += 1

    async def update_many(self, *_args, **_kwargs):
        self.writes += 1
        return type("Result", (), {"modified_count": 2})()

    async def insert_one(self, *_args, **_kwargs):
        self.writes += 1


class _Db:
    def __init__(self, user):
        self.users = _Collection(user)
        self.refresh_tokens = _Collection({"_id": ObjectId(), "revoked_at": None})


def _disabled_user():
    return {
        "_id": ObjectId(),
        "username": "hccnghiahung",
        "password_hash": hash_password("matkhau123"),
        "access_disabled": True,
    }


@pytest.mark.asyncio
async def test_disabled_account_cannot_login_and_gets_exact_message(monkeypatch):
    db = _Db(_disabled_user())
    monkeypatch.setattr(service, "get_db", lambda: db)

    with pytest.raises(AppError) as error:
        await service.login("hccnghiahung", "matkhau123")

    assert error.value.error == MAINTENANCE_ERROR
    assert error.value.code == 401
    assert error.value.message == MAINTENANCE_MESSAGE
    assert db.refresh_tokens.writes == 0


@pytest.mark.asyncio
async def test_disabled_account_current_access_token_is_blocked(monkeypatch):
    user = _disabled_user()
    db = _Db(user)
    monkeypatch.setattr(deps, "get_db", lambda: db)
    monkeypatch.setattr(deps, "decode_access_token", lambda _: {
        "type": "access",
        "sub": str(user["_id"]),
    })

    with pytest.raises(AppError) as error:
        await deps.require_auth(HTTPAuthorizationCredentials(scheme="Bearer", credentials="token"))

    assert error.value.error == MAINTENANCE_ERROR
    assert error.value.code == 401
    assert error.value.message == MAINTENANCE_MESSAGE


@pytest.mark.asyncio
async def test_off_command_marks_user_and_revokes_refresh_tokens(monkeypatch):
    db = _Db(_disabled_user())
    monkeypatch.setattr(set_account_access, "get_db", lambda: db)

    result = await set_account_access.set_account_access(" HCCNGHIAHUNG ", disabled=True)

    assert result == {"username": "hccnghiahung", "disabled": True, "revoked": 2}
    assert db.users.writes == 1
    assert db.refresh_tokens.writes == 1


@pytest.mark.asyncio
async def test_disabled_account_cannot_refresh(monkeypatch):
    user = _disabled_user()
    db = _Db(user)
    monkeypatch.setattr(service, "get_db", lambda: db)
    monkeypatch.setattr(service, "decode_refresh_token", lambda _: {
        "type": "refresh",
        "sub": str(user["_id"]),
    })

    with pytest.raises(AppError) as error:
        await service.refresh("refresh-token")

    assert error.value.error == MAINTENANCE_ERROR
    assert error.value.code == 401
    assert error.value.message == MAINTENANCE_MESSAGE
    assert db.refresh_tokens.writes == 0


def test_maintenance_http_response_supports_installed_extension():
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)

    @app.get("/protected")
    async def protected():
        ensure_account_available(_disabled_user())

    response = TestClient(app).get("/protected")

    assert response.status_code == 401
    assert response.json() == {
        "error": MAINTENANCE_ERROR,
        "message": MAINTENANCE_MESSAGE,
        "code": 401,
        "detail": MAINTENANCE_MESSAGE,
    }
