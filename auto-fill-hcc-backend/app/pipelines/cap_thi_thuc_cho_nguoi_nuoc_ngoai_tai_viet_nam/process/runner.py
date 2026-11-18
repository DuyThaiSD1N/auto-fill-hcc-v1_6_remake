"""Compact agent pipeline cho thủ tục 1.001194 (Cổng DVC Bộ Công an)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.process import mapper
from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.process.prompt import EXTRA_RULES
from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.process.schema import (
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
        compact_field_fallback=mapper.ocr_fallback,
        options=options,
    )
    res["fields"], warnings = mapper.enrich(res["fields"], options)
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
