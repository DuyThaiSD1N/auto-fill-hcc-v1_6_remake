"""Lazy attachment entrypoint cho [Lào Cai] diện tích tăng thêm do thay đổi ranh giới (1.115693)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi.attach.planner import (
        plan as _plan,
    )

    return await _plan(files, options, session)


__all__ = ["plan"]
