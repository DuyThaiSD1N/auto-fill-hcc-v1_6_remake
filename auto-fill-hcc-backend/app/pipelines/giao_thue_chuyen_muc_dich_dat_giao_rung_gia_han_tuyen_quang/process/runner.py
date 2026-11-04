"""Compact-agent process pipeline cho form 1 của thủ tục giao đất, cho thuê đất, chuyển mục đích (Tuyên Quang).

Trợ lý người dân: công dân chọn quy trình VBDLIS ở hộp thoại "Chọn trường hợp giải quyết" → registry trợ lý
(caseOptions) gửi ``options.quyTrinh = "vbdlis"`` → chạy form 2. Auto Fill không gửi khóa này (tự nhận diện key -vbdlis).
"""

from app.pipelines._shared.compact_agent import runner

from . import mapper
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    if str((options or {}).get("quyTrinh") or "") == "vbdlis":
        from ..process_vbdlis.runner import run as run_vbdlis

        return await run_vbdlis(files_by_role, options)
    result = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
    )
    result["fields"], warnings = mapper.enrich(result["fields"], options)
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    return result
