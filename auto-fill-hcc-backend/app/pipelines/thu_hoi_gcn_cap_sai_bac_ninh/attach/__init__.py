"""Lazy attachment entrypoint for [Bắc Ninh] Thu hồi GCN cấp sai & cấp lại."""


async def plan(files, options=None, session=None):
    from app.pipelines.thu_hoi_gcn_cap_sai_bac_ninh.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
