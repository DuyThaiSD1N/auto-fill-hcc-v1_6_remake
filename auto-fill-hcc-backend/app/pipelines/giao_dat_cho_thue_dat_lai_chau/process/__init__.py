"""Process pipeline cho Giao đất, cho thuê đất — Lai Châu (1.115577)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.giao_dat_cho_thue_dat_lai_chau.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
