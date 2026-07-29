"""Lazy process entrypoint for dang-ky-kinh-doanh."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_kinh_doanh.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
