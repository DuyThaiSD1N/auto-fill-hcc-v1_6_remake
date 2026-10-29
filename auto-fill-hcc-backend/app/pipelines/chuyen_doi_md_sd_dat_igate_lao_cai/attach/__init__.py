"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] Chuyển mục đích sử dụng đất (1.115651)."""


async def plan(files, options=None, session=None):
    from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
