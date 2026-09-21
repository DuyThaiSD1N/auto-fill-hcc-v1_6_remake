"""Lazy attachment entrypoint cho [Lào Cai] Chuyển mục đích sử dụng đất cấp phường/xã (1.115679)."""


async def plan(files, options=None, session=None):
    from app.pipelines.chuyen_md_sd_dat_phuong_xa_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
