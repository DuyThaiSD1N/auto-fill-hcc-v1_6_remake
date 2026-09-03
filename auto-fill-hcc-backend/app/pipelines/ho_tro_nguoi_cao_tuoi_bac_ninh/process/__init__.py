"""Trích xuất thông tin người cao tuổi cho khối ủy quyền Bắc Ninh."""

from app.pipelines._shared.compact_agent import runner

from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS
from .mapper import enrich


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    result = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
    )
    result["fields"] = enrich(result.get("fields", []))
    return result
