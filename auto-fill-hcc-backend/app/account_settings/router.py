"""API cài đặt theo tài khoản cho extension (Auto Fill + handfree).

Endpoint mới hoàn toàn — bản extension cũ trên chợ không gọi nên không bị ảnh hưởng.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.account_settings import service
from app.core.deps import require_auth

router = APIRouter(prefix="/api/v1/account/settings", tags=["account-settings"])


class AccountSettingsUpdate(BaseModel):
    # Khoá lạ bỏ qua: extension bản mới hơn BE có thể gửi khoá BE chưa biết.
    model_config = ConfigDict(extra="ignore")

    renameAttachmentFiles: bool | None = None
    submitterFromDeclaration: bool | None = None


@router.get("")
async def get_settings(user: dict = Depends(require_auth)):
    return service.resolve(user)


@router.patch("")
async def update_settings(body: AccountSettingsUpdate, user: dict = Depends(require_auth)):
    return await service.update(user, body.model_dump(exclude_none=True))
