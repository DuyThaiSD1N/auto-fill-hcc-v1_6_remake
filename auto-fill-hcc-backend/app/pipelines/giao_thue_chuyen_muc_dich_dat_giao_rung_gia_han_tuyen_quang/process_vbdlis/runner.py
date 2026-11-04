"""Compact-agent process pipeline cho form 2 (quy trình VBDLIS) của thủ tục giao đất, cho thuê đất (Tuyên Quang)."""

from app.pipelines._shared.compact_agent import runner

from ..process.prompt import EXTRA_RULES
from ..process.schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS
from . import mapper


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    result = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
    )
    result["fields"], warnings = mapper.enrich(result["fields"], options)
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    return result
