"""Ảnh chụp giá trị form sau khi điền (fill), khi cán bộ sửa (edit) và lúc rời bước kê khai (step).

Không lưu ở server chính: chuyển thẳng sang kho Spark, kho không nhận thì giữ tạm trong
`form_snapshots` cho archiver gửi lại và xoá trong `archive_after_minutes`.
"""
from fastapi import APIRouter, BackgroundTasks, Depends

from app.core.deps import require_auth
from app.core.errors import AppError
from app.form_snapshots import relay
from app.form_snapshots.schemas import FormSnapshotReq

router = APIRouter(prefix="/api/v1/form-snapshots", tags=["form-snapshots"])


@router.post("")
async def create_snapshot(body: FormSnapshotReq, background: BackgroundTasks,
                          user: dict = Depends(require_auth)):
    preq = await relay.owned_request(body.requestId, str(user.get("id") or ""))
    if not preq:
        raise AppError("REQUEST_NOT_FOUND", "Không tìm thấy lượt điền", 404)
    background.add_task(relay.relay, relay.build_bundle(body, user, preq))
    return {"ok": True}
