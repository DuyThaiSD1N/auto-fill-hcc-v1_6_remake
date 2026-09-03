import pytest
from pydantic import ValidationError

from app.core.deps import require_admin, require_trace_reader
from app.core.errors import AppError
from app.users.schemas import UserCreate


@pytest.mark.asyncio
async def test_super_admin_only_gets_trace_reader_permission():
    user = {"id": "monitor", "role": "super_admin"}
    assert await require_trace_reader(user) is user

    with pytest.raises(AppError) as error:
        await require_admin(user)
    assert error.value.error == "FORBIDDEN"


@pytest.mark.asyncio
async def test_normal_admin_keeps_trace_reader_permission():
    user = {"id": "admin", "role": "admin"}
    assert await require_trace_reader(user) is user
    assert await require_admin(user) is user


@pytest.mark.asyncio
async def test_regular_user_cannot_read_trace():
    with pytest.raises(AppError) as error:
        await require_trace_reader({"id": "ward", "role": "commune"})
    assert error.value.error == "FORBIDDEN"


def test_public_user_schema_cannot_create_super_admin():
    with pytest.raises(ValidationError):
        UserCreate(username="monitor", password="matkhau123", role="super_admin")
