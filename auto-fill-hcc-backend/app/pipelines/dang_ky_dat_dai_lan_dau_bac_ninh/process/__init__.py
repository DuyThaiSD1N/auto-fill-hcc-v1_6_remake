"""Process pipeline for [Bắc Ninh] Đăng ký đất đai, cấp GCN lần đầu."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_dat_dai_lan_dau_bac_ninh.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
