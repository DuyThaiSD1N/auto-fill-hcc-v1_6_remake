"""Lazy attachment entrypoint for [Bắc Ninh] Tách thửa đất/hợp thửa đất."""


async def plan(files, options=None, session=None):
    from app.pipelines.tach_hop_thua_dat_bac_ninh.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
