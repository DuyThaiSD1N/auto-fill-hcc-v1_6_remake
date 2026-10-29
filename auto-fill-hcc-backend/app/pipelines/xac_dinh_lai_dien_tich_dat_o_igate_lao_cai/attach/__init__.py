"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] xác định lại diện tích đất ở (1.115685)."""


async def plan(files, options=None, session=None):
    from app.pipelines.xac_dinh_lai_dien_tich_dat_o_igate_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
