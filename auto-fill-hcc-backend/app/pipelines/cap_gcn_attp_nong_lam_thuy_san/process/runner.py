"""Compact process runner cho cấp GCN ATTP nông, lâm, thủy sản."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_gcn_attp_nong_lam_thuy_san.process import mapper
from app.pipelines.cap_gcn_attp_nong_lam_thuy_san.process.prompt import EXTRA_RULES
from app.pipelines.cap_gcn_attp_nong_lam_thuy_san.process.schema import (
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
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
