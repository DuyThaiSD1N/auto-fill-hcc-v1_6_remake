"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] đăng ký biến động do chia, tách, hợp nhất, sáp nhập tổ chức (1.115670)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_bien_dong_chia_tach_to_chuc_igate_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
