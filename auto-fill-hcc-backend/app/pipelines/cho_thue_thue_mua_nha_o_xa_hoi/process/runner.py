"""Compact agent process pipeline cho "Cho thuê, cho thuê mua nhà ở xã hội…" (cổng DVC Bộ Xây dựng).

Nhân thân + đơn đăng ký thuê/thuê mua NOXH (occurrence Phần I/III, datagrid thành viên). Xem mapper."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.process import mapper
from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.process.prompt import EXTRA_RULES
from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.process.schema import (
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
