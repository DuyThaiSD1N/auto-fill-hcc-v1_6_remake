"""Compact agent process pipeline cho "Chấp thuận vị trí đấu nối tạm vào đường bộ đang khai thác".

Người nộp (Phần I) từ CCCD/tài khoản; đơn vị đề nghị + nội dung đơn (Phần II) từ Đơn đề nghị. Xem mapper."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.chap_thuan_dau_noi_tam.process import mapper
from app.pipelines.chap_thuan_dau_noi_tam.process.prompt import EXTRA_RULES
from app.pipelines.chap_thuan_dau_noi_tam.process.schema import (
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
