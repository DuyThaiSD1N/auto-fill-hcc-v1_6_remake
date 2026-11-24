"""Lazy attachment entrypoint cho Đăng ký xe lần đầu trực tuyến toàn trình đối với xe sản xuất lắp ráp trong nước
(1.012575)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
