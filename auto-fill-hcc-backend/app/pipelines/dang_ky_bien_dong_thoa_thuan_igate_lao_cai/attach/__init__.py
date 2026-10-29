"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] đăng ký biến động theo thỏa thuận, tài sản công, bản án (1.115671)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_bien_dong_thoa_thuan_igate_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
