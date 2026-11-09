"""Lazy attachment entrypoint cho Đăng ký, cấp GCN đối với toàn bộ diện tích đất đang sử dụng — Lai Châu."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_cap_giay_chung_nhan_doi_voi_toan_bo_dien_tich_dat_lai_chau.attach.planner import (
        plan as _plan,
    )

    return await _plan(files, options, session)


__all__ = ["plan"]
