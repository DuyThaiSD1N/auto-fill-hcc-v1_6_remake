"""Lazy attachment entrypoint cho [Lào Cai] thửa đất có diện tích tăng thêm (1.115694)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dk_giay_cn_thua_dat_dien_tich_tang_them.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
