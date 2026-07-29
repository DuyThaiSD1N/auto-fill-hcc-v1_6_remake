"""Lazy attachment entrypoint for thay-doi-cai-chinh-ho-tich."""


async def plan(files, options=None, session=None):
    from app.pipelines.thay_doi_ho_tich.attach.planner import plan as _plan

    return await _plan(files, options, session)


async def plan_thay_doi_ho_tich_attachments(files, options=None, session=None):
    from app.pipelines.thay_doi_ho_tich.attach.planner import plan_thay_doi_ho_tich_attachments as _plan

    return await _plan(files, options, session)


__all__ = ["plan", "plan_thay_doi_ho_tich_attachments"]
