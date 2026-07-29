"""Đính kèm bước 3 cho thủ tục đăng ký khai sinh thường."""


async def plan(files, options=None, session=None):
    from app.pipelines.khai_sinh_thuong.attach.planner import plan as _plan

    return await _plan(files, options, session)


async def plan_khai_sinh_thuong_attachments(files, options=None, session=None):
    from app.pipelines.khai_sinh_thuong.attach.planner import plan_khai_sinh_thuong_attachments as _plan

    return await _plan(files, options, session)


__all__ = ["plan", "plan_khai_sinh_thuong_attachments"]
