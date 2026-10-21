"""Lazy attachment entrypoint for [Bắc Ninh] Đăng ký biến động QSDĐ (1.115468) và bản thỏa thuận (1.115470)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_bien_dong_dat_dai_bac_ninh.attach.planner import plan as _plan

    return await _plan(files, options, session)


async def plan_thoa_thuan(files, options=None, session=None):
    """1.115470 — cùng planner, catalog/prompt riêng (18 thành phần khác 1.115468)."""
    from app.pipelines.dang_ky_bien_dong_dat_dai_bac_ninh.attach.catalog import MA_THOA_THUAN
    from app.pipelines.dang_ky_bien_dong_dat_dai_bac_ninh.attach.planner import plan as _plan

    return await _plan(files, options, session, ma=MA_THOA_THUAN)


__all__ = ["plan", "plan_thoa_thuan"]
