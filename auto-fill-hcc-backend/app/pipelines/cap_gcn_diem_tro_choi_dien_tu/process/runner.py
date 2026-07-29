"""Compact agent process pipeline cho "Cấp GCN đủ điều kiện điểm trò chơi điện tử công cộng"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_gcn_diem_tro_choi_dien_tu.process import mapper
from app.pipelines.cap_gcn_diem_tro_choi_dien_tu.process.prompt import EXTRA_RULES
from app.pipelines.cap_gcn_diem_tro_choi_dien_tu.process.schema import (
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
        max_tokens=1100,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
