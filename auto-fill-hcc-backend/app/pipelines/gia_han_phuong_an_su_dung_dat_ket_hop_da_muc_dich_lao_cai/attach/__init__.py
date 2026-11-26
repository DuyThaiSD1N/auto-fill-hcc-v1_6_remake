"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] gia hạn phương án sử dụng đất kết hợp (1.115683)."""


async def plan(files, options=None, session=None):
    from app.pipelines.gia_han_phuong_an_su_dung_dat_ket_hop_da_muc_dich_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
