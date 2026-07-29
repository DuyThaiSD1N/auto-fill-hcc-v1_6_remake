"""Compact agent process pipeline cho "Cấp lại Bằng Tổ quốc ghi công"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_lai_to_quoc_ghi_cong.process import mapper
from app.pipelines.cap_lai_to_quoc_ghi_cong.process.prompt import EXTRA_RULES
from app.pipelines.cap_lai_to_quoc_ghi_cong.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
