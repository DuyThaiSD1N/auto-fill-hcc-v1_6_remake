"""API quản lý tài khoản — toàn bộ gác require_admin."""
from typing import Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import JSONResponse, Response

from app.core.deps import require_admin
from app.core.errors import AppError
from app.reports.router import _content_disposition
from app.users import access_log, export_excel, import_excel, password_import, service
from app.users.schemas import AccountExportRequest, PasswordSet, Role, UserCreate, UserUpdate

router = APIRouter(prefix="/api/v1/users", tags=["users"])

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
# Phản hồi chứa mật khẩu: không cho trình duyệt/proxy lưu đệm.
_NO_STORE = {"Cache-Control": "no-store"}


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


@router.get("/parents")
async def list_parent_accounts(_admin: dict = Depends(require_admin)):
    """HCC xã chọn được làm cha của tổ dân phố (đủ cả danh sách — ô chọn tự lọc phía FE)."""
    return {"items": await service.list_parent_accounts()}


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


@router.get("/password-import/template")
async def password_import_template(_admin: dict = Depends(require_admin)):
    return Response(
        content=password_import.template_bytes(),
        media_type=_XLSX,
        headers={"Content-Disposition": 'attachment; filename="mau-nap-mat-khau.xlsx"'},
    )


@router.post("/password-import")
async def import_passwords(
    file: UploadFile = File(...),
    apply: bool = Query(False),
    admin: dict = Depends(require_admin),
):
    """apply=false: chỉ so với mật khẩu đang dùng. apply=true: so lại rồi lưu dòng khớp."""
    content = await file.read(import_excel.MAX_BYTES + 1)
    if len(content) > import_excel.MAX_BYTES:
        raise AppError("IMPORT_FILE_TOO_LARGE", "File quá 2MB.", 413)
    result = await password_import.run(content, apply=apply)
    if apply:
        await access_log.record(
            "import_passwords", admin, stored=result["summary"].get("stored", 0),
        )
    return result


@router.get("/export/options")
async def export_options(_admin: dict = Depends(require_admin)):
    return await export_excel.options()


@router.post("/export")
async def export_accounts(body: AccountExportRequest, admin: dict = Depends(require_admin)):
    data, filename, count, province = await export_excel.export(body.province)
    await access_log.record("export_accounts", admin, province=province, count=count)
    return Response(
        content=data,
        media_type=_XLSX,
        headers={"Content-Disposition": _content_disposition(filename), **_NO_STORE},
    )


@router.post("/{user_id}/password")
async def set_password(user_id: str, body: PasswordSet, admin: dict = Depends(require_admin)):
    result = await service.set_password(user_id, body.password)
    await access_log.record(
        "set_password", admin, target_id=result["id"], target_username=result["username"],
    )
    return result


@router.post("/{user_id}/password/reveal")
async def reveal_password(user_id: str, admin: dict = Depends(require_admin)):
    """POST (không phải GET) để mật khẩu không nằm trong URL/log truy cập hay bộ đệm."""
    result, target = await service.reveal_password(user_id)
    await access_log.record(
        "reveal_password", admin, target_id=str(target["_id"]),
        target_username=target.get("username"), stored=result["stored"],
    )
    return JSONResponse(result, headers=_NO_STORE)


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
