"""Lazy attachment entrypoint cho Cấp lại Giấy chứng nhận do bị mất — Lai Châu (1.115557)."""


async def plan(files, options=None, session=None):
    from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_lai_chau.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
