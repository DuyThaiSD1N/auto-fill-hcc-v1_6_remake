"""Compact agent pipeline cho thủ tục 2.001485 (Cổng DVC Bộ Công an)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.thu_hoi_chung_nhan_dang_ky_bien_so_xe_cap_tinh.process import mapper
from app.pipelines.thu_hoi_chung_nhan_dang_ky_bien_so_xe_cap_tinh.process.prompt import EXTRA_RULES
from app.pipelines.thu_hoi_chung_nhan_dang_ky_bien_so_xe_cap_tinh.process.schema import (
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
