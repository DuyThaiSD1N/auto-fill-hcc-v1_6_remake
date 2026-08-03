"""Compact-agent process pipeline cho thủ tục xóa đăng ký tàu cá."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.xoa_dang_ky_tau_ca.process import mapper
from app.pipelines.xoa_dang_ky_tau_ca.process.prompt import EXTRA_RULES
from app.pipelines.xoa_dang_ky_tau_ca.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


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
    mapped_fields, warnings = mapper.enrich(result["fields"], options)
    result["fields"] = mapped_fields
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    return result
