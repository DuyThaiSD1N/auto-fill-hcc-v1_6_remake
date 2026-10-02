"""Compact agent process pipeline cho "Đăng ký hoạt động khuyến mại mang tính may rủi trên địa bàn 01 tỉnh"
(cổng Bộ Công Thương). Xem mapper: occurrence tài khoản/tờ khai, khối tài khoản theo mốc đăng nhập."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_khuyen_mai_may_rui.process import mapper
from app.pipelines.dang_ky_khuyen_mai_may_rui.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_khuyen_mai_may_rui.process.schema import (
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
