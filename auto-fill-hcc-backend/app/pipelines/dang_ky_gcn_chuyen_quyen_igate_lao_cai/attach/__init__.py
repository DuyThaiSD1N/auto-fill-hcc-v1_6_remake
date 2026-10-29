"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] đăng ký, cấp GCN khi đã chuyển quyền trước 01/8/2024 (1.115666)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_gcn_chuyen_quyen_igate_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
