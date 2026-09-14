"""Lazy attachment entrypoint for xac-nhan-thong-tin-ho-tich."""


async def plan(files, options=None, session=None):
    from app.pipelines.xac_nhan_thong_tin_ho_tich.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
