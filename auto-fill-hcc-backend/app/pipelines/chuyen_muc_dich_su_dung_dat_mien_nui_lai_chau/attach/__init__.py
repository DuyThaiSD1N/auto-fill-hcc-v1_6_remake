"""Lazy attachment entrypoint cho Chuyển mục đích sử dụng đất (xã miền núi, biên giới...) — Lai Châu (1.115578)."""


async def plan(files, options=None, session=None):
    from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
