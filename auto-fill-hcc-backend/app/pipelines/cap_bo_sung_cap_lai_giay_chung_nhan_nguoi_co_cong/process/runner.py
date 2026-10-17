"""Compact agent process pipeline cho "Cấp bổ sung hoặc cấp lại giấy chứng nhận người có công" (1.010814)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_bo_sung_cap_lai_giay_chung_nhan_nguoi_co_cong.process import mapper
from app.pipelines.cap_bo_sung_cap_lai_giay_chung_nhan_nguoi_co_cong.process.prompt import EXTRA_RULES
from app.pipelines.cap_bo_sung_cap_lai_giay_chung_nhan_nguoi_co_cong.process.schema import (
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
