"""Lazy attachment entrypoint cho [Lai Châu] Đăng ký đất đai, cấp GCN lần đầu."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_dat_dai_tai_san.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
