"""Lazy attachment entrypoint cho Đăng ký mẫu con dấu mới (2.001428)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_mau_con_dau.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
