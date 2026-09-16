"""Lazy attachment entrypoint cho [Lào Cai] cấp GCN cho người nhận chuyển nhượng trong dự án BĐS (1.115667)."""


async def plan(files, options=None, session=None):
    from app.pipelines.cap_GCN_nhan_chuyen_nhuong.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
