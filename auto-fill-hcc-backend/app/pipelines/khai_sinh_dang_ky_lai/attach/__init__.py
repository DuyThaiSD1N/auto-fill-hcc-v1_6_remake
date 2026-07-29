"""Đính kèm bước 3 cho thủ tục đăng ký lại khai sinh."""


async def plan(files, options=None, session=None):
    from app.pipelines.khai_sinh_dang_ky_lai.attach.planner import plan as _plan

    return await _plan(files, options, session)


async def plan_dang_ky_lai_khai_sinh_attachments(files, options=None, session=None):
    from app.pipelines.khai_sinh_dang_ky_lai.attach.planner import (
        plan_dang_ky_lai_khai_sinh_attachments as _plan,
    )

    return await _plan(files, options, session)


__all__ = ["plan", "plan_dang_ky_lai_khai_sinh_attachments"]
