"""Compact-agent process pipeline cho thủ tục đính chính GCN Ninh Bình."""

from app.pipelines._shared.compact_agent import runner

from . import mapper
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS


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
