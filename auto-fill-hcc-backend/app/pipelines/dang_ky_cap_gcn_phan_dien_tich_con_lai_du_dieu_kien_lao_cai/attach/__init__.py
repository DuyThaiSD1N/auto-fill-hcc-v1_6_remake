"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] cấp GCN phần diện tích còn lại (1.115692)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_cap_gcn_phan_dien_tich_con_lai_du_dieu_kien_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
