"""Lazy attachment entrypoint for [Bắc Ninh] Cấp đổi Giấy chứng nhận QSDĐ."""


async def plan(files, options=None, session=None):
    from app.pipelines.cap_doi_gcn_bac_ninh.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
