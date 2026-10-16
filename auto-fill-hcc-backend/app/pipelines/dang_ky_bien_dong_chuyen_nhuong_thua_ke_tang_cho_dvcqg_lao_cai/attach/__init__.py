"""Lazy attachment entrypoint cho [Lào Cai] đăng ký biến động chuyển nhượng, thừa kế, tặng cho (1.013831)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_dvcqg_lao_cai.attach.planner import (
        plan as _plan,
    )

    return await _plan(files, options, session)


__all__ = ["plan"]
