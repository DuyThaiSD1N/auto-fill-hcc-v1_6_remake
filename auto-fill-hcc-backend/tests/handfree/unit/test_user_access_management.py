from bson import ObjectId
import pytest

from app.auth.access_control import MAINTENANCE_MESSAGE
from app.core.errors import AppError
from app.users import service
from app.users.schemas import UserUpdate


class _Users:
    def __init__(self, user: dict):
        self.user = user
        self.update_doc = None

    async def find_one(self, query):
        return self.user if query.get("_id") == self.user["_id"] else None

    async def find_one_and_update(self, query, update, return_document):
        if query.get("_id") != self.user["_id"]:
            return None
        self.update_doc = update
        self.user.update(update.get("$set", {}))
        for field in update.get("$unset", {}):
            self.user.pop(field, None)
        return dict(self.user)


class _RefreshTokens:
    def __init__(self):
        self.calls = []

    async def update_many(self, query, update):
        self.calls.append((query, update))
        return type("Result", (), {"modified_count": 2})()


class _Db:
    def __init__(self, user: dict):
        self.users = _Users(user)
        self.refresh_tokens = _RefreshTokens()


def _user(*, disabled: bool = False) -> dict:
    user = {
        "_id": ObjectId(),
        "username": "hccnghiahung",
        "role": "commune",
        "access_disabled": disabled,
    }
    if disabled:
        user["access_disabled_reason"] = MAINTENANCE_MESSAGE
        user["access_disabled_at"] = service._now()
    return user


@pytest.mark.asyncio
async def test_admin_can_disable_account_and_revoke_refresh_tokens(monkeypatch):
    target = _user()
    db = _Db(target)
    monkeypatch.setattr(service, "get_db", lambda: db)

    result = await service.update_user(
        str(target["_id"]),
        UserUpdate(access_disabled=True),
        str(ObjectId()),
    )

    assert result["access_disabled"] is True
    assert target["access_disabled_reason"] == MAINTENANCE_MESSAGE
    assert db.refresh_tokens.calls[0][0] == {
        "user_id": str(target["_id"]),
        "revoked_at": None,
    }


@pytest.mark.asyncio
async def test_admin_can_enable_account_and_remove_maintenance_metadata(monkeypatch):
    target = _user(disabled=True)
    db = _Db(target)
    monkeypatch.setattr(service, "get_db", lambda: db)

    result = await service.update_user(
        str(target["_id"]),
        UserUpdate(access_disabled=False),
        str(ObjectId()),
    )

    assert result["access_disabled"] is False
    assert "access_disabled_reason" not in target
    assert "access_disabled_at" not in target
    assert db.refresh_tokens.calls == []


@pytest.mark.asyncio
async def test_admin_cannot_disable_own_account(monkeypatch):
    target = _user()
    db = _Db(target)
    monkeypatch.setattr(service, "get_db", lambda: db)

    with pytest.raises(AppError) as error:
        await service.update_user(
            str(target["_id"]),
            UserUpdate(access_disabled=True),
            str(target["_id"]),
        )

    assert error.value.error == "CANNOT_DISABLE_SELF"
    assert db.users.update_doc is None

