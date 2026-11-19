"""Lazy attachment entrypoint cho Trình báo mất hộ chiếu phổ thông (thực hiện tại cấp xã) (1.010386)."""


async def plan(files, options=None, session=None):
    from app.pipelines.trinh_bao_mat_ho_chieu_pho_thong_cap_xa.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
