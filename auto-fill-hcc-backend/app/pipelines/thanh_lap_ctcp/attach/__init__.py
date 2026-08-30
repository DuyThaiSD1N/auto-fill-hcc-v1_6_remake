"""Lazy attachment entrypoint for thanh-lap-cong-ty-co-phan."""


async def plan(files, options=None, session=None):
    from app.pipelines.thanh_lap_ctcp.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
