"""Lazy attachment entrypoint for khai-tu."""


async def plan(files, options=None, session=None):
    from app.pipelines.khai_tu.attach.planner import plan as _plan

    return await _plan(files, options, session)


async def plan_khai_tu_attachments(files, options=None, session=None):
    from app.pipelines.khai_tu.attach.planner import plan_khai_tu_attachments as _plan

    return await _plan(files, options, session)


__all__ = ["plan", "plan_khai_tu_attachments"]
