"""Compact agent process pipeline cho "Cấp Giấy chứng nhận đủ điều kiện ATTP" (cổng Bộ Công Thương).

Người nộp (tài khoản) + Cơ sở SXKD (chủ hồ sơ) + Đơn 01a + loại hình cơ sở. Xem mapper (occurrence I/IV)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_gcn_attp_cong_thuong.process import mapper
from app.pipelines.cap_gcn_attp_cong_thuong.process.prompt import EXTRA_RULES
from app.pipelines.cap_gcn_attp_cong_thuong.process.schema import (
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
