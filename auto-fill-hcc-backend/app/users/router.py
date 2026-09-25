"""API quản lý tài khoản — toàn bộ gác require_admin."""
from typing import Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response

from app.core.deps import require_admin
from app.core.errors import AppError
from app.users import import_excel, service
from app.users.schemas import Role, UserCreate, UserUpdate

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("")
async def list_users(
    _admin: dict = Depends(require_admin),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    role: Role | None = Query(None),
    q: str | None = Query(None, max_length=100),
    tinh: str | None = Query(None, max_length=100),
    status: Literal["all", "active", "disabled", "deleted"] = Query("all"),
):
    res = await service.list_users(
        skip=(page - 1) * pageSize,
        limit=pageSize,
        role=role,
        keyword=q,
        tinh=tinh,
        status=status,
    )
    return {**res, "page": page, "pageSize": pageSize}


@router.post("")
async def create_user(body: UserCreate, _admin: dict = Depends(require_admin)):
    return await service.create_user(body)


@router.get("/import/template")
async def import_template(_admin: dict = Depends(require_admin)):
    return Response(
        content=import_excel.template_bytes(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="mau-tao-tai-khoan.xlsx"'},
    )


@router.post("/import")
async def import_users(
    file: UploadFile = File(...),
    apply: bool = Query(False),
    _admin: dict = Depends(require_admin),
):
    """apply=false: chỉ kiểm, trả bảng xem trước. apply=true: kiểm lại rồi tạo."""
    # Đọc thừa 1 byte để biết file có vượt giới hạn không mà không phải nạp cả file lớn.
    content = await file.read(import_excel.MAX_BYTES + 1)
    if len(content) > import_excel.MAX_BYTES:
        raise AppError("IMPORT_FILE_TOO_LARGE", "File quá 2MB.", 413)
    return await import_excel.run(content, apply=apply)


@router.patch("/{user_id}")
async def update_user(user_id: str, body: UserUpdate, admin: dict = Depends(require_admin)):
    return await service.update_user(user_id, body, admin["id"])


@router.delete("/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    """Xóa MỀM: chỉ đóng dấu users.deleted_at, document vẫn còn nguyên trong Mongo."""
    await service.delete_user(user_id, admin["id"])
    return {"ok": True}


@router.post("/{user_id}/restore")
async def restore_user(user_id: str, _admin: dict = Depends(require_admin)):
    return await service.restore_user(user_id)
