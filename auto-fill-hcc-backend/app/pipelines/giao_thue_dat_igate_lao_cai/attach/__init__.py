"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] giao đất, cho thuê đất (1.115650)."""


async def plan(files, options=None, session=None):
    from app.pipelines.giao_thue_dat_igate_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
