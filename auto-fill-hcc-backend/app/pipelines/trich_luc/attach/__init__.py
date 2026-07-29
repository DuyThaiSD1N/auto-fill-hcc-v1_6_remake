"""Lazy attachment entrypoint for trich-luc-ks."""


async def plan(files, options=None, session=None):
    from app.pipelines.trich_luc.attach.planner import plan as _plan

    return await _plan(files, options, session)


async def plan_trich_luc_attachments(files, options=None, session=None):
    from app.pipelines.trich_luc.attach.planner import plan_trich_luc_attachments as _plan

    return await _plan(files, options, session)


__all__ = ["plan", "plan_trich_luc_attachments"]
