"""Lazy attachment entrypoint for [Bắc Ninh] Giao/thuê/chuyển mục đích SDĐ."""


async def plan(files, options=None, session=None):
    from app.pipelines.giao_thue_chuyen_muc_dich_dat_bac_ninh.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
