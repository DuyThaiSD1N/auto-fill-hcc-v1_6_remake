"""Lazy attachment entrypoint cho Cấp thị thực cho người nước ngoài tại Việt Nam (1.001194)."""


async def plan(files, options=None, session=None):
    from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
