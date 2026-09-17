"""Process pipeline cho [Lào Cai] Chuyển mục đích sử dụng đất (1.115651)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
