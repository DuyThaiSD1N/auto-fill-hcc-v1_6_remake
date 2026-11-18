"""Compact agent process pipeline cho "Cấp GCN đủ điều kiện kinh doanh dược (Sở Y tế)".

HAI vai: CHỦ HỒ SƠ (người đại diện theo pháp luật) và NGƯỜI NỘP (tài khoản đăng nhập). Mốc người nộp dùng chung với thủ
tục cấp lại / điều chỉnh cùng cổng (chỉ nhận đoạn văn bản có dấu hiệu thẻ căn cước, dò theo TỪNG TRANG vì hồ sơ hay
là một PDF gộp). Cài đặt "Lấy người nộp theo tờ khai" bật → bỏ mốc tài khoản: người nộp = chủ hồ sơ."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.process import mapper
from app.pipelines.cap_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.process.prompt import EXTRA_RULES
from app.pipelines.cap_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)
from app.pipelines.cap_lai_dieu_chinh_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.process.runner import (
    _submitter_context as _account_submitter_context,
)


async def _submitter_context(documents: list[dict], options: dict) -> str:
    # Cài đặt "Lấy người nộp theo tờ khai": không neo CCCD tài khoản, LLM chỉ trích chủ hồ sơ như tự nộp.
    if str((options or {}).get("submitterMode") or "") == mapper.OWNER_AS_SUBMITTER:
        return ""
    return await _account_submitter_context(documents, options)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        context_builder=_submitter_context,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
