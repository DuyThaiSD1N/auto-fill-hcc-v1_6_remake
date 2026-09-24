"""Compact agent process pipeline cho "Cấp bổ sung xe tập lái, cấp lại Giấy phép xe tập lái"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_bo_sung_xe_tap_lai_cap_lai_giay_phep_xe_tap_lai.process import mapper
from app.pipelines.cap_bo_sung_xe_tap_lai_cap_lai_giay_phep_xe_tap_lai.process.prompt import EXTRA_RULES
from app.pipelines.cap_bo_sung_xe_tap_lai_cap_lai_giay_phep_xe_tap_lai.process.schema import (
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
        # Bảng xe có thể nhiều dòng × ~11 cột → cần nhiều token hơn mặc định 1800.
        max_tokens=3600,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
