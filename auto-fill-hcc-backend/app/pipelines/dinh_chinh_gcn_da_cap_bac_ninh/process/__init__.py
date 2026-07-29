"""Process pipeline for [Bắc Ninh] Cấp đổi Giấy chứng nhận QSDĐ."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dinh_chinh_gcn_da_cap_bac_ninh.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
