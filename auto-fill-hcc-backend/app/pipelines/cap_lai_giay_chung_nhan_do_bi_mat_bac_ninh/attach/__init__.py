"""Lazy attachment entrypoint for [Bắc Ninh] Cấp lại Giấy chứng nhận do bị mất."""


async def plan(files, options=None, session=None):
    from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
