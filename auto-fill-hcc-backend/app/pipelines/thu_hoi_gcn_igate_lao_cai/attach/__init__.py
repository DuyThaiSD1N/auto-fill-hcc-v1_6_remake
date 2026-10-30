"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] thu hồi GCN cấp lần đầu không đúng quy định (1.115687)."""


async def plan(files, options=None, session=None):
    from app.pipelines.thu_hoi_gcn_igate_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
