"""Lazy attachment entrypoint for dang-ky-kinh-doanh."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_kinh_doanh.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
