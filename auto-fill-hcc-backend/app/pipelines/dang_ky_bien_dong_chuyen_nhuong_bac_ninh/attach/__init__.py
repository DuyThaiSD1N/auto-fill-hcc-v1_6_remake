"""Lazy attachment entrypoint for [Bắc Ninh] Đăng ký biến động QSDĐ (chuyển nhượng/thừa kế/tặng cho)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_bac_ninh.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
