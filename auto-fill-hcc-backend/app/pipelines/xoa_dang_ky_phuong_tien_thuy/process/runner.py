"""Compact agent process pipeline cho "Xóa đăng ký phương tiện thủy nội địa".

MỘT subject = CHỦ PHƯƠNG TIỆN (đối tượng đề nghị xóa đăng ký), điền vào Block 1 của cổng. Không tách vai
người nộp riêng (cổng dùng Block 1 làm khối khai chính; xem mapper)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.xoa_dang_ky_phuong_tien_thuy.process import mapper
from app.pipelines.xoa_dang_ky_phuong_tien_thuy.process.prompt import EXTRA_RULES
from app.pipelines.xoa_dang_ky_phuong_tien_thuy.process.schema import (
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
