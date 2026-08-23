"""Xác thực server-to-server riêng cho API batch."""
from __future__ import annotations

import hmac

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.core.errors import AppError


_bearer = HTTPBearer(auto_error=False)


async def require_batch_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    configured = settings.batch_api_secret.strip()
    if not configured:
        raise AppError(
            "BATCH_AUTH_NOT_CONFIGURED",
            "API batch chưa được cấu hình khóa truy cập.",
            503,
        )
    supplied = credentials.credentials if credentials else ""
    if not supplied or not hmac.compare_digest(supplied, configured):
        raise AppError("INVALID_BATCH_SECRET", "Khóa truy cập batch không hợp lệ.", 401)
    return {"client": "batch-service"}
