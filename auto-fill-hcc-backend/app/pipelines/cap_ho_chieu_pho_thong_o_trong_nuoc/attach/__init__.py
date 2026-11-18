"""Lazy attachment entrypoint cho Cấp hộ chiếu phổ thông ở trong nước (1.001456)."""


async def plan(files, options=None, session=None):
    from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
