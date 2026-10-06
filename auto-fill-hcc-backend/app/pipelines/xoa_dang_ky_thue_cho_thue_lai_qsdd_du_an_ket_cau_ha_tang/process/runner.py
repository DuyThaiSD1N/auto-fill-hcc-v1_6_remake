"""Compact agent process pipeline cho "Xóa đăng ký thuê, cho thuê lại QSDĐ trong dự án xây dựng kinh doanh kết
cấu hạ tầng" — cổng DVC Đà Nẵng.

HAI vai: CHỦ HỒ SƠ (người đứng Đơn Mẫu 18) và NGƯỜI NỘP (mặc định tự nộp). Xem mapper."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.xoa_dang_ky_thue_cho_thue_lai_qsdd_du_an_ket_cau_ha_tang.process import mapper
from app.pipelines.xoa_dang_ky_thue_cho_thue_lai_qsdd_du_an_ket_cau_ha_tang.process.prompt import EXTRA_RULES
from app.pipelines.xoa_dang_ky_thue_cho_thue_lai_qsdd_du_an_ket_cau_ha_tang.process.schema import (
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
