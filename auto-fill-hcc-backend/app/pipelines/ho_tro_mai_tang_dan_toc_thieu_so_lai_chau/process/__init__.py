"""Process pipeline cho Hỗ trợ chi phí mai táng người dân tộc thiểu số Lai Châu (2.002862)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.ho_tro_mai_tang_dan_toc_thieu_so_lai_chau.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
