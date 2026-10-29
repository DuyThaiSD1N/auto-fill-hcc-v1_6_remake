"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] tổ chức kinh tế nhận chuyển nhượng QSDĐ dự án (1.115681)."""


async def plan(files, options=None, session=None):
    from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhuong_igate_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
