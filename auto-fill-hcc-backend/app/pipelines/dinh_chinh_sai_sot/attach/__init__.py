"""Lazy attachment entrypoint cho [Lai Châu] Đính chính GCN có sai sót."""


async def plan(files, options=None, session=None):
    from app.pipelines.dinh_chinh_sai_sot.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
