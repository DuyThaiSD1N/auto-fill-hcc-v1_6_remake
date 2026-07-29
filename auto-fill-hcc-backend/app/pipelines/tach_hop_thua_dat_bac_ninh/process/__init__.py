"""Process pipeline for [Bắc Ninh] Tách thửa đất/hợp thửa đất."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.tach_hop_thua_dat_bac_ninh.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
