"""Compact agent process pipeline cho "Cấp bản sao văn bằng, chứng chỉ từ sổ gốc" (cổng DVC Bộ GD&ĐT).

Chỉ trích nhân thân chủ văn bằng + nội dung kê khai; người nộp lấy từ tài khoản (formContext). Xem mapper."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_ban_sao_van_bang_so_goc.process import mapper
from app.pipelines.cap_ban_sao_van_bang_so_goc.process.prompt import EXTRA_RULES
from app.pipelines.cap_ban_sao_van_bang_so_goc.process.schema import (
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
    mapped_fields, warnings = mapper.enrich(res["fields"], options, ocr_text=res.get("ocr_text", ""))
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
