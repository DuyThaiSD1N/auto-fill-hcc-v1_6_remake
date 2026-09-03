"""Compact agent process pipeline cho "Đính chính GCN đã cấp lần đầu có sai sót" (cổng DVC Đà Nẵng).

HAI vai: CHỦ HỒ SƠ (người đề nghị đính chính) và NGƯỜI NỘP (mặc định tự nộp; có thể ủy quyền). Xem mapper."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dinh_chinh_gcn_da_cap_da_nang.process import mapper
from app.pipelines.dinh_chinh_gcn_da_cap_da_nang.process.prompt import EXTRA_RULES
from app.pipelines.dinh_chinh_gcn_da_cap_da_nang.process.schema import (
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
