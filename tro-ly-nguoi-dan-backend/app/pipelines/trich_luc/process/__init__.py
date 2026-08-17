"""Lazy process entrypoint for trich-luc-ks."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.trich_luc.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
