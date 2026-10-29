"""Process pipeline cho [Lào Cai - cổng iGate mới] điều chỉnh quyết định giao đất, cho thuê đất (1.115652)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dieu_chinh_giao_dat_igate_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
