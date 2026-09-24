"""Compact agent process pipeline cho "Cấp, cấp lại Phù hiệu cho xe ô tô … kinh doanh vận tải"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_lai_phu_hieu_xe_oto.process import mapper
from app.pipelines.cap_lai_phu_hieu_xe_oto.process.prompt import EXTRA_RULES
from app.pipelines.cap_lai_phu_hieu_xe_oto.process.schema import (
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
        # Đơn vị + GPKDVT + mảng xe ~17 khoá → cần nhiều token hơn mặc định 1800.
        max_tokens=3600,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options, ocr_text=res.get("ocr_text", ""))
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
