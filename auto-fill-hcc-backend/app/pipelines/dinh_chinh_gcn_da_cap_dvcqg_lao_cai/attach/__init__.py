"""Lazy attachment entrypoint cho [Lào Cai] đính chính Giấy chứng nhận đã cấp (1.012790)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dinh_chinh_gcn_da_cap_dvcqg_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
