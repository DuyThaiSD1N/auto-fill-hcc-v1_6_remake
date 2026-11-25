"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] giao đất ở không đấu giá (1.115684)."""


async def plan(files, options=None, session=None):
    from app.pipelines.giao_dat_o_khong_dau_gia_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
