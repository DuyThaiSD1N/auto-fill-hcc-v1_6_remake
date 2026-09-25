"""Compact agent process pipeline cho "Thủ tục tiếp nhận hồ sơ thông báo sản phẩm quảng cáo trên bảng quảng
cáo, băng-rôn" (Bộ VHTTDL)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.thong_bao_san_pham_quang_cao_bang_ron.process import mapper
from app.pipelines.thong_bao_san_pham_quang_cao_bang_ron.process.prompt import EXTRA_RULES
from app.pipelines.thong_bao_san_pham_quang_cao_bang_ron.process.schema import (
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
