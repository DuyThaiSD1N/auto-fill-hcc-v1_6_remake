"""Lazy attachment entrypoint for [Bắc Ninh] Đính chính GCN có sai sót."""


async def plan(files, options=None, session=None):
    from app.pipelines.dinh_chinh_sai_sot_bac_ninh.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
