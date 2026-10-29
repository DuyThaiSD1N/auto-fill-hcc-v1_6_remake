"""Process pipeline cho [Lào Cai - cổng iGate mới] giao đất, cho thuê đất (1.115650)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.giao_thue_dat_igate_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
