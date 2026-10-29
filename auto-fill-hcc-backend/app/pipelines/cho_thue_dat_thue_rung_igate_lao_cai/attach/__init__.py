"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] giao đất/cho thuê đất, giao rừng/cho thuê rừng (1.115678)."""


async def plan(files, options=None, session=None):
    from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
