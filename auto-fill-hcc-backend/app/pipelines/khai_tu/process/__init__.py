"""Lazy process entrypoint for khai-tu."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.khai_tu.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
