"""Lazy attachment entrypoint cho Giao đất, cho thuê đất — Lai Châu (1.115577)."""


async def plan(files, options=None, session=None):
    from app.pipelines.giao_dat_cho_thue_dat_lai_chau.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
