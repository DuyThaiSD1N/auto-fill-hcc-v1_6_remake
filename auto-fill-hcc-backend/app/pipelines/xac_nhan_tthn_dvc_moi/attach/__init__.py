"""Lazy attachment entrypoint for xac-nhan-tinh-trang-hon-nhan (Cổng DVC quốc gia mới)."""


async def plan(files, options=None, session=None):
    from app.pipelines.xac_nhan_tthn_dvc_moi.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
