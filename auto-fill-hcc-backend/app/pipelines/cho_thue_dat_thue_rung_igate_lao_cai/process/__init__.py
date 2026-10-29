"""Process pipeline cho [Lào Cai - cổng iGate mới] giao đất/cho thuê đất, giao rừng/cho thuê rừng (1.115678)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.cho_thue_dat_thue_rung_igate_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
