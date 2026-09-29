"""Compact agent process pipeline cho "Thủ tục cấp thẻ hướng dẫn viên du lịch tại điểm" (Đà Nẵng)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_the_huong_dan_vien_du_lich_tai_diem_da_nang.process import mapper
from app.pipelines.cap_the_huong_dan_vien_du_lich_tai_diem_da_nang.process.prompt import EXTRA_RULES
from app.pipelines.cap_the_huong_dan_vien_du_lich_tai_diem_da_nang.process.schema import (
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
        # Đơn ngắn, chỉ một người; chứng chỉ/văn bằng/CCCD chỉ góp vài fact đối chiếu.
        max_tokens=1400,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
