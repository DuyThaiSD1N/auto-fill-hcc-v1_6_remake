"""Process pipeline cho thủ tục mai táng phí dân công hỏa tuyến."""

from typing import Any


async def run(files_by_role: dict[str, list[dict]], options: dict[str, Any]) -> dict:
    from app.pipelines.mai_tang_dan_cong.process.runner import run as _run

    return await _run(files_by_role, options)

__all__ = ["run"]
