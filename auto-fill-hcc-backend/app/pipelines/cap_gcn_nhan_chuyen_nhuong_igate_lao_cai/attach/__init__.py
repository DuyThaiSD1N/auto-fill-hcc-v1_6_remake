"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] cấp GCN cho người nhận chuyển nhượng trong dự án BĐS (1.115667)."""


async def plan(files, options=None, session=None):
    from app.pipelines.cap_gcn_nhan_chuyen_nhuong_igate_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
