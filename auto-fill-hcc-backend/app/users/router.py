"""API quản lý tài khoản — toàn bộ gác require_admin."""
from fastapi import APIRouter, Depends, Query

from app.core.deps import require_admin
from app.users import service
from app.users.schemas import Role, UserCreate, UserUpdate

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("")
async def list_users(
    _admin: dict = Depends(require_admin),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    role: Role | None = Query(None),
):
    res = await service.list_users(skip=(page - 1) * pageSize, limit=pageSize, role=role)
    return {**res, "page": page, "pageSize": pageSize}


@router.post("")
async def create_user(body: UserCreate, _admin: dict = Depends(require_admin)):
    return await service.create_user(body)


@router.patch("/{user_id}")
async def update_user(user_id: str, body: UserUpdate, admin: dict = Depends(require_admin)):
    return await service.update_user(user_id, body, admin["id"])


@router.delete("/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    await service.delete_user(user_id, admin["id"])
    return {"ok": True}
