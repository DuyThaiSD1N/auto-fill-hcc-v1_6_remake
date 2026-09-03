"""Compact agent process pipeline cho "Thẩm định BCNCKT đầu tư xây dựng" (cổng DVC Bộ Xây dựng).

Người nộp (CCCD, occ0) + chủ đầu tư + dự án + quy hoạch/phê duyệt (containers) + năng lực nhà thầu
(+2 datagrid bộ môn). Xem mapper."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.tham_dinh_bcnckt.process import mapper
from app.pipelines.tham_dinh_bcnckt.process.prompt import EXTRA_RULES
from app.pipelines.tham_dinh_bcnckt.process.schema import (
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
