"""Đính kèm bước 3 cho thủ tục đăng ký khai sinh cho người đã có hồ sơ, giấy tờ cá nhân."""


async def plan(files, options=None, session=None):
    from app.pipelines.khai_sinh_co_ho_so.attach.planner import plan as _plan

    return await _plan(files, options, session)


async def plan_khai_sinh_co_ho_so_attachments(files, options=None, session=None):
    from app.pipelines.khai_sinh_co_ho_so.attach.planner import (
        plan_khai_sinh_co_ho_so_attachments as _plan,
    )

    return await _plan(files, options, session)


__all__ = ["plan", "plan_khai_sinh_co_ho_so_attachments"]
