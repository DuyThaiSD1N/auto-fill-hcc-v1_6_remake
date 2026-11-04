"""Compact agent process pipeline cho "Thủ tục tổ chức biểu diễn nghệ thuật"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.to_chuc_bieu_dien_nghe_thuat.process import mapper
from app.pipelines.to_chuc_bieu_dien_nghe_thuat.process.prompt import EXTRA_RULES
from app.pipelines.to_chuc_bieu_dien_nghe_thuat.process.schema import (
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
        # Văn bản đề nghị chép nguyên văn nhiều mục (thời gian, địa điểm, tài liệu kèm theo) + bản kịch bản.
        max_tokens=2000,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
