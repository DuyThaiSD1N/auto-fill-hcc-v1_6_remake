"""Compact agent process pipeline cho [Lâm Đồng] chuyển mục đích/chuyển hình thức/gia hạn/điều chỉnh
thời hạn sử dụng đất (1.116365)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.chuyen_muc_dich_su_dung_dat_lam_dong.process import mapper
from app.pipelines.chuyen_muc_dich_su_dung_dat_lam_dong.process.prompt import EXTRA_RULES
from app.pipelines.chuyen_muc_dich_su_dung_dat_lam_dong.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Người nộp/đại diện được quyết định TẤT ĐỊNH bằng CÓ hay KHÔNG có Giấy ủy quyền (xem prompt) —
    # KHÔNG tiêm formContext (mỏ neo tài khoản) vào prompt, giống các thủ tục Lâm Đồng khác.
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        max_tokens=1400,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
