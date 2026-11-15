"""API cho extension hỏi kết quả điền đợt 2 của một lượt process."""
from fastapi import APIRouter, Depends

from app.core.deps import require_auth
from app.second_pass import service

router = APIRouter(prefix="/api/v1/process", tags=["process"])


@router.get("/{request_id}/second-pass")
async def get_second_pass(request_id: str, user: dict = Depends(require_auth)):
    # Chỉ tài khoản đã gửi lượt process đó mới đọc được; lượt của tài khoản khác trả như không có.
    return await service.result(request_id, user["id"])
