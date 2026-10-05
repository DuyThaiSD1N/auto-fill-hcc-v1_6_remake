from fastapi import APIRouter, Depends, Request

from app.auth import service
from app.auth.schemas import LoginReq, RefreshReq
from app.core.deps import require_auth

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    # Sau nginx: IP thật nằm ở X-Forwarded-For (phần tử đầu); chạy trực tiếp thì lấy socket.
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return (forwarded or (request.client.host if request.client else ""))[:64]


@router.post("/login")
async def login(body: LoginReq, request: Request):
    ua = request.headers.get("user-agent", "")[:200]
    return await service.login(
        body.username,
        body.password,
        ua,
        admin_only=body.adminOnly,
        super_admin_only=body.superAdminOnly,
        ip=_client_ip(request),
    )


@router.post("/refresh")
async def refresh(body: RefreshReq, request: Request):
    ua = request.headers.get("user-agent", "")[:200]
    return await service.refresh(body.refreshToken, ua, ip=_client_ip(request))


@router.get("/me")
async def me(user: dict = Depends(require_auth)):
    return {
        "id": user["id"],
        "username": user["username"],
        "name": user.get("name"),
        "role": user.get("role") or "user",
        "xa": user.get("xa"),
        "tinh": user.get("tinh"),
    }
