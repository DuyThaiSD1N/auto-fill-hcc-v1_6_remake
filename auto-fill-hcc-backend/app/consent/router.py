"""API ghi nhận chấp thuận xử lý dữ liệu cá nhân (PDPL).

POST /api/v1/consent (require_auth) — extension gọi khi người dùng bấm "Đồng ý": lưu bản ghi +
file PDF bằng chứng. Chỉ khi trả 200 thì extension mới coi phiên là ĐÃ đồng ý (bằng chứng chắc
chắn đã lưu). Mỗi phiên đồng ý 1 lần → 1 bản ghi.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.consent import store
from app.core.deps import require_auth
from app.core.errors import AppError

router = APIRouter(prefix="/api/v1/consent", tags=["consent"])


class ConsentReq(BaseModel):
    logId: str
    version: str
    procedure: str | None = None
    procedureLabel: str | None = None
    statements: list[str] = []
    optimize: bool = False       # người dùng ĐỒNG Ý (tùy chọn) cho lưu data lần xử lý để tối ưu hệ thống
    at: str | None = None       # thời điểm hiển thị phía client (chuỗi, để đối chiếu với giờ máy chủ)
    # Chủ thể dữ liệu = tài khoản VNeID đang đăng nhập trên cổng (extension đọc từ header trang).
    # CCCD None khi cổng không lộ số định danh → consent gắn theo mã phiên; tên chỉ để đối chiếu.
    principalCccd: str | None = None
    principalName: str | None = None


@router.post("")
async def create_consent(body: ConsentReq, user: dict = Depends(require_auth)):
    if not body.logId:
        raise AppError("BAD_CONSENT", "Thiếu mã nhật ký chấp thuận.", 400)
    result = await store.save_consent(
        log_id=body.logId, user=user, procedure=body.procedure,
        procedure_label=body.procedureLabel, version=body.version,
        statements=body.statements, optimize=body.optimize, at=body.at,
        principal_cccd=body.principalCccd, principal_name=body.principalName,
    )
    return {"ok": True, **result}
