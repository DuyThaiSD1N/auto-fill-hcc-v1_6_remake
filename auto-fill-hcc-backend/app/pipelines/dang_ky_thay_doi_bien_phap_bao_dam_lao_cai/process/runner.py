"""Compact-agent process pipeline cho thủ tục đăng ký thay đổi biện pháp bảo đảm Lào Cai (1.011442)."""

from app.pipelines._shared.compact_agent import runner

from . import mapper
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    result = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        # Hồ sơ thế chấp nhiều người/nhiều giấy: danh sách ứng viên + mô tả nội dung thay đổi vượt mức
        # 1800 token mặc định → JSON bị cắt giữa chừng, mất trắng cả kết quả.
        max_tokens=3200,
    )
    result["fields"], warnings = mapper.enrich(result["fields"], options)
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    return result
