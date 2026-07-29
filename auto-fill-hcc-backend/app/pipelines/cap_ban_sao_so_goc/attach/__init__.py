"""Lazy attachment entrypoint for cap-ban-sao-so-goc."""


async def plan(files, options=None, session=None):
    from app.pipelines.cap_ban_sao_so_goc.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
