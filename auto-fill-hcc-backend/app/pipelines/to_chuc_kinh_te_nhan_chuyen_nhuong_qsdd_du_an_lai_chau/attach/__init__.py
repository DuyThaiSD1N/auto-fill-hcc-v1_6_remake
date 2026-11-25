"""Lazy attachment entrypoint cho Tổ chức kinh tế nhận chuyển nhượng QSDĐ để thực hiện dự án — Lai Châu (1.115591)."""


async def plan(files, options=None, session=None):
    from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhuong_qsdd_du_an_lai_chau.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
