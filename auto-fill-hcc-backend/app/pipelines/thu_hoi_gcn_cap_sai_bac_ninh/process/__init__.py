"""Process pipeline for [Bắc Ninh] Thu hồi GCN cấp sai & cấp lại."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.thu_hoi_gcn_cap_sai_bac_ninh.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
