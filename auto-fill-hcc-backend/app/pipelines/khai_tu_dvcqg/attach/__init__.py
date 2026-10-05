"""Lazy attachment entrypoint for khai-tu-dvcqg."""


async def plan(files, options=None, session=None):
    from app.pipelines.khai_tu_dvcqg.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
