"""Compact agent process pipeline cho "Đăng ký, cấp GCN cho người nhận chuyển nhượng trong dự án bất động
sản" (cổng DVC Đà Nẵng, 1.012787).

HAI vai: CHỦ HỒ SƠ (bên nhận chuyển nhượng) và NGƯỜI NỘP (tự nộp hoặc được ủy quyền). Xem mapper."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bat_dong_san.process import mapper
from app.pipelines.dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bat_dong_san.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bat_dong_san.process.schema import (
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
