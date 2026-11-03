"""Lazy attachment entrypoint cho Hỗ trợ chi phí mai táng người dân tộc thiểu số Lai Châu (2.002862)."""


async def plan(files, options=None, session=None):
    from app.pipelines.ho_tro_mai_tang_dan_toc_thieu_so_lai_chau.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
