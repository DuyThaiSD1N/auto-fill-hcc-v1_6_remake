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
    # LLM chỉ trích người khai thay + đối tượng từ giấy tờ; mốc tài khoản (formContext) chỉ dùng ở mapper
    # để chọn người nộp, không đưa vào prompt.
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    if str((options or {}).get("submitterMode") or "") == "owner_as_submitter":
        # Họ tên + CCCD Phần I cổng khoá (disabled) theo tài khoản VNeID; người nộp theo tờ khai có thể là người
        # khác nên kèm enableInput để extension bỏ disabled trước khi ghi, cán bộ còn sửa được khi OCR sai.
        for field in mapped_fields:
            if field.get("name") in ("data[fullname]", "data[identityNumber]") and field.get("occurrence") in (None, 0):
                field["enableInput"] = True
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
