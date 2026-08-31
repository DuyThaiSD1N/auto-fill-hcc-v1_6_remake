"""Lazy attachment entrypoint for thanh-lap-cong-ty-tnhh-hai-thanh-vien."""


async def plan(files, options=None, session=None):
    from app.pipelines.thanh_lap_ctythnn_2_nguoi.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
