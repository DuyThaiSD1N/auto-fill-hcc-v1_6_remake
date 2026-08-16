"""Compact agent process pipeline cho "Thực hiện, điều chỉnh, thôi hưởng trợ cấp xã hội hàng tháng,
hỗ trợ kinh phí chăm sóc, nuôi dưỡng hàng tháng"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.tro_cap_xa_hoi_hang_thang.process import mapper
from app.pipelines.tro_cap_xa_hoi_hang_thang.process.prompt import EXTRA_RULES
from app.pipelines.tro_cap_xa_hoi_hang_thang.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Giữ chữ ký pipeline chung nhưng không truyền formContext/options của FE xuống compact runner.
    _ = options
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
    )
    # Thủ tục này xác định người nộp từ block "Thông tin người khai thay" trên tờ khai; không dùng
    # nhân thân tài khoản/formContext do FE gửi kèm request chung.
    mapped_fields, warnings = mapper.enrich(res["fields"])
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
