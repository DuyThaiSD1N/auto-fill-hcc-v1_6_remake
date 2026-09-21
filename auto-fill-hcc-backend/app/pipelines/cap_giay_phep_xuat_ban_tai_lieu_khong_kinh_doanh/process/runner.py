"""Compact agent process pipeline cho "Cấp giấy phép xuất bản tài liệu không kinh doanh"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_giay_phep_xuat_ban_tai_lieu_khong_kinh_doanh.process import mapper
from app.pipelines.cap_giay_phep_xuat_ban_tai_lieu_khong_kinh_doanh.process.prompt import EXTRA_RULES
from app.pipelines.cap_giay_phep_xuat_ban_tai_lieu_khong_kinh_doanh.process.schema import (
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
        # Đơn Mẫu 04 có tóm tắt nội dung + mục đích xuất bản dài, cộng 3 khối nhân thân/doanh nghiệp.
        max_tokens=2200,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
