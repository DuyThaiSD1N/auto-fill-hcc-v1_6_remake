"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] đính chính Giấy chứng nhận đã cấp (1.115686)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dinh_chinh_gcn_da_cap_igate_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
