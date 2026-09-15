"""Lazy attachment entrypoint for [Bắc Ninh] Đăng ký biến động QSDĐ (1.115468)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_bien_dong_dat_dai_bac_ninh.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
