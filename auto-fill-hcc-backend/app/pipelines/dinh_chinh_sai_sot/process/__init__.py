"""Process pipeline for Đính chính sai sót."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dinh_chinh_sai_sot.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
