"""Compact agent process pipeline cho "Cấp giấy phép chặt hạ, dịch chuyển cây xanh" (cổng DVC Bộ Xây dựng).

Chủ hồ sơ (người đề nghị) là chủ thể chính; người nộp có thể khác (nộp thay). Xem mapper."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_giay_phep_chat_ha_cay_xanh.process import mapper
from app.pipelines.cap_giay_phep_chat_ha_cay_xanh.process.prompt import EXTRA_RULES
from app.pipelines.cap_giay_phep_chat_ha_cay_xanh.process.schema import (
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
