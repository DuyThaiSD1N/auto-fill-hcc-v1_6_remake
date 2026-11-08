"""Ảnh chụp giá trị form sau khi điền (fill), khi cán bộ sửa (edit) và lúc rời bước kê khai (step).

Không lưu ở server chính: chuyển thẳng sang kho Spark, kho không nhận thì giữ tạm trong
`form_snapshots` cho archiver gửi lại và xoá trong `archive_after_minutes`. Riêng hồ sơ handfree đang làm dở
thì bản mới nhất được giữ kèm bản ghi khôi phục (chat/resume/, hết hạn 30 phút) để điền lại đúng bản cán bộ sửa.
"""
from fastapi import APIRouter, BackgroundTasks, Depends

from app.channels.handfree.chat import resume
from app.core.deps import require_auth
from app.core.errors import AppError
from app.form_snapshots import relay
from app.form_snapshots.schemas import FormSnapshotReq

router = APIRouter(prefix="/api/v1/form-snapshots", tags=["form-snapshots"])


@router.post("")
async def create_snapshot(body: FormSnapshotReq, background: BackgroundTasks,
                          user: dict = Depends(require_auth)):
    user_id = str(user.get("id") or "")
    # Lượt điền của hồ sơ khôi phục trỏ về request cũ — có thể đã được archiver dọn, nên ghi bản khôi phục trước.
    kept = await resume.on_form_snapshot(user_id, body.requestId, body.kind, body.at,
                                         [f.model_dump(exclude_none=True) for f in body.fields])
    preq = await relay.owned_request(body.requestId, user_id)
    if not preq:
        if kept:
            return {"ok": True}
        raise AppError("REQUEST_NOT_FOUND", "Không tìm thấy lượt điền", 404)
    background.add_task(relay.relay, relay.build_bundle(body, user, preq))
    return {"ok": True}
