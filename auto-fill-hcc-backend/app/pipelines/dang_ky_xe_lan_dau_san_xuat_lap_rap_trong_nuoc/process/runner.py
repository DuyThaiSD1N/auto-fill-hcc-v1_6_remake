"""Compact agent pipeline cho thủ tục 1.012575 (Cổng DVC Bộ Công an)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.process import mapper
from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.process.schema import (
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
        options=options,
    )
    res["fields"], warnings = mapper.enrich(res["fields"], options)
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
