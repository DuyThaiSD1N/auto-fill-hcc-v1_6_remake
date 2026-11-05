"""API cài đặt theo tài khoản cho extension (Auto Fill + handfree).

Endpoint mới hoàn toàn — bản extension cũ trên chợ không gọi nên không bị ảnh hưởng.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.account_settings import service
from app.core.deps import require_auth

router = APIRouter(prefix="/api/v1/account/settings", tags=["account-settings"])


class AccountSettingsUpdate(BaseModel):
    # Khoá lạ bỏ qua: extension bản mới hơn BE có thể gửi khoá BE chưa biết.
    model_config = ConfigDict(extra="ignore")

    renameAttachmentFiles: bool | None = None
    submitterFromDeclaration: bool | None = None
    fontScale: float | None = Field(default=None, ge=0.9, le=1.3)
    # Rỗng = về giọng mặc định. Tốc độ ép tiếp vào khoảng quản trị cho phép lúc đọc (ws_tts).
    ttsVoiceVi: str | None = Field(default=None, max_length=80, pattern=r"^[A-Za-z0-9._-]*$")
    ttsVoiceHmong: str | None = Field(default=None, max_length=80, pattern=r"^[A-Za-z0-9._-]*$")
    ttsTempo: float | None = Field(default=None, ge=0.5, le=2.0)


@router.get("")
async def get_settings(user: dict = Depends(require_auth)):
    return service.resolve(user)


@router.patch("")
async def update_settings(body: AccountSettingsUpdate, user: dict = Depends(require_auth)):
    return await service.update(user, body.model_dump(exclude_none=True))
