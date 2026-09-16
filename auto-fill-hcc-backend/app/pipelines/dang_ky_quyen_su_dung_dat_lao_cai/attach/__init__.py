"""Lazy attachment entrypoint cho [Lào Cai] Đăng ký biến động quyền sử dụng đất (1.115668)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
