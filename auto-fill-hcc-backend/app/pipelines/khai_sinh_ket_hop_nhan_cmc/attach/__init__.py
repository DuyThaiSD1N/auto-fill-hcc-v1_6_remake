"""Attachment entrypoint for the combined civil-status procedure."""


async def plan(files, options=None, session=None):
    from app.pipelines.khai_sinh_ket_hop_nhan_cmc.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]

