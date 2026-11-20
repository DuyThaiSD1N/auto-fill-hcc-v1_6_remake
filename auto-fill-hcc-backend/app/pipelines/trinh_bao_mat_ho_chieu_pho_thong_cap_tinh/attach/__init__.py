"""Lazy attachment entrypoint cho Trình báo mất hộ chiếu phổ thông (thực hiện tại cấp tỉnh) (1.001445)."""


async def plan(files, options=None, session=None):
    from app.pipelines.trinh_bao_mat_ho_chieu_pho_thong_cap_tinh.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
