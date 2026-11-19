"""Compact agent process pipeline cho [Lâm Đồng] tính hoặc tính lại tiền sử dụng đất theo NĐ 50/2026/NĐ-CP (1.115148)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.process import mapper
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.process.prompt import EXTRA_RULES
from app.pipelines.tinh_tien_su_dung_dat_nd_50_2026_lam_dong.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Không tiêm formContext (tài khoản đăng nhập) vào prompt như các thủ tục Lâm Đồng khác; mapper dùng formContext
    # TẤT ĐỊNH để biết tài khoản có phải chủ hồ sơ không (nộp thay mà hồ sơ không có giấy của người nộp).
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        max_tokens=1200,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
