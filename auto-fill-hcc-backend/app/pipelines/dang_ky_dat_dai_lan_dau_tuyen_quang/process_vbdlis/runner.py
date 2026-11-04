"""Process pipeline cho form quy trình VBDLIS của đăng ký đất đai lần đầu (Tuyên Quang): cùng facts với form "5 bước"."""

from ..process.runner import extract
from . import mapper


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    result = await extract(files_by_role, options)
    result["fields"], warnings = mapper.enrich(result["fields"], options)
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    return result
