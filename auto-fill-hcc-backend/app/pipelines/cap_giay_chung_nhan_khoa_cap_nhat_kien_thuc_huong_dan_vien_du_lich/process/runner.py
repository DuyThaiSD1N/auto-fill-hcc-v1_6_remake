"""Compact agent process pipeline cho "Thủ tục cấp Giấy chứng nhận khóa cập nhật kiến thức cho hướng dẫn viên du lịch"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_giay_chung_nhan_khoa_cap_nhat_kien_thuc_huong_dan_vien_du_lich.process import mapper
from app.pipelines.cap_giay_chung_nhan_khoa_cap_nhat_kien_thuc_huong_dan_vien_du_lich.process.prompt import (
    EXTRA_RULES,
)
from app.pipelines.cap_giay_chung_nhan_khoa_cap_nhat_kien_thuc_huong_dan_vien_du_lich.process.schema import (
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
        # Đơn Mẫu 06 một trang, một người; CCCD/thẻ HDV (nếu có) chỉ góp vài fact đối chiếu.
        max_tokens=1400,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
