"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] sử dụng đất kết hợp đa mục đích (1.115682)."""


async def plan(files, options=None, session=None):
    from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_igate_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
