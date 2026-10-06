"""Compact agent process pipeline cho "Xác định lại diện tích đất ở (GCN cấp trước 01/7/2004)" — cổng
DVC Đà Nẵng.

HAI vai: CHỦ HỒ SƠ (người đứng Đơn) và NGƯỜI NỘP (mặc định tự nộp) + panel thửa đất. Xem mapper."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.xac_dinh_lai_dien_tich_dat_o_gcn_truoc_2004.process import mapper
from app.pipelines.xac_dinh_lai_dien_tich_dat_o_gcn_truoc_2004.process.prompt import EXTRA_RULES
from app.pipelines.xac_dinh_lai_dien_tich_dat_o_gcn_truoc_2004.process.schema import (
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
