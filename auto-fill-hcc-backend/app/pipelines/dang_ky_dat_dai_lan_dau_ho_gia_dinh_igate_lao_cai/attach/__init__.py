"""Lazy attachment entrypoint cho [Lào Cai - cổng iGate mới] đăng ký đất đai, cấp GCN lần đầu hộ gia đình, cá nhân (1.115689)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_dat_dai_lan_dau_ho_gia_dinh_igate_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
