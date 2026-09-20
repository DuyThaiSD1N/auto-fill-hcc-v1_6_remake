"""Lazy attachment entrypoint cho [Lào Cai] Thu hồi GCN cấp lần đầu không đúng quy định (1.115687)."""


async def plan(files, options=None, session=None):
    from app.pipelines.thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
