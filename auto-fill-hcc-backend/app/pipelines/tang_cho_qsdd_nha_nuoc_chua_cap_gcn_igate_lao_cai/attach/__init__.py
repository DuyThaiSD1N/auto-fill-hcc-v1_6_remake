"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] tặng cho quyền sử dụng đất mở rộng đường giao thông (1.115690)."""


async def plan(files, options=None, session=None):
    from app.pipelines.tang_cho_qsdd_nha_nuoc_chua_cap_gcn_igate_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
