"""Process pipeline for [Bắc Ninh] Giao/thuê/chuyển mục đích SDĐ."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.giao_thue_chuyen_muc_dich_dat_bac_ninh.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
