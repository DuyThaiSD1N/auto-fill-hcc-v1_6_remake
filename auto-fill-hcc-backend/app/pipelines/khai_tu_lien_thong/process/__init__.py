"""Lazy process entrypoint for khai-tu-lien-thong."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.khai_tu_lien_thong.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
