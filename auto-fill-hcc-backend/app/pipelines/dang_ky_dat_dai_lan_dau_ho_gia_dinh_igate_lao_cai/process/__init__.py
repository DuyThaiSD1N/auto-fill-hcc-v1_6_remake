"""Process pipeline cho [Lào Cai - cổng iGate mới] đăng ký đất đai, cấp GCN lần đầu hộ gia đình, cá nhân (1.115689)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_dat_dai_lan_dau_ho_gia_dinh_igate_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
