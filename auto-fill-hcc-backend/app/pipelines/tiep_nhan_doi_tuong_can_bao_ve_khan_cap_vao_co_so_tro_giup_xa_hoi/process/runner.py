"""Compact agent process pipeline cho "Tiếp nhận đối tượng cần bảo vệ khẩn cấp vào cơ sở trợ giúp xã hội".

``run_with`` dùng chung cho 1.116907 (tiếp nhận đối tượng bảo trợ xã hội có hoàn cảnh đặc biệt khó khăn): cùng form,
cùng Tờ khai Mẫu số 04, chỉ khác prompt thủ tục và nhóm đối tượng bắt buộc trong Ghi chú."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.process import mapper
from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.process.prompt import EXTRA_RULES
from app.pipelines.tiep_nhan_doi_tuong_can_bao_ve_khan_cap_vao_co_so_tro_giup_xa_hoi.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def run_with(
    files_by_role: dict[str, list[dict]], options: dict, *, extra_rules: str, required_group: str | None,
) -> dict:
    # LLM chỉ trích người giám hộ + đối tượng từ giấy tờ; mốc tài khoản (formContext) chỉ dùng ở mapper để chọn
    # người nộp, không đưa vào prompt.
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=extra_rules,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options, required_group)
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


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    return await run_with(files_by_role, options, extra_rules=EXTRA_RULES, required_group=mapper.EMERGENCY_GROUP)
