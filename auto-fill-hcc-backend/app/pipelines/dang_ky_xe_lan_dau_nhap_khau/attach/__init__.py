"""Lazy attachment entrypoint cho Đăng ký xe lần đầu trực tuyến toàn trình đối với xe nhập khẩu (1.013066)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
