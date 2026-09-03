"""Process pipeline cho thủ tục đăng ký biện pháp bảo đảm Bắc Ninh (đơn Mẫu 01a + khối ủy quyền)."""

from app.pipelines._shared.compact_agent import runner

from .mapper import enrich
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
        max_tokens=3200,
    )
    result["fields"] = enrich(result.get("fields", []), options)
    return result
