"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] điều chỉnh quyết định giao đất, cho thuê đất (1.115652)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dieu_chinh_giao_dat_igate_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
