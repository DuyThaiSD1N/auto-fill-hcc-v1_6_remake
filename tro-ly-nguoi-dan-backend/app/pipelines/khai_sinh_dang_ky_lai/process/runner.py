"""Compact agent process pipeline for "Đăng ký lại khai sinh"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.khai_sinh_dang_ky_lai.process import mapper, reason
from app.pipelines.khai_sinh_dang_ky_lai.process.prompt import EXTRA_RULES
from app.pipelines.khai_sinh_dang_ky_lai.process.schema import (
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
        context_builder=reason.build_context,
    )
    # Reasoning đã chốt vai trò theo người. Lọc trước mapper để không biến field
    # bị gán nhầm người thành field UI hợp lệ.
    reasoning_context = res.get("reasoning_context") or ""
    res["fields"] = reason.sanitize_extracted_fields(res["fields"], reasoning_context)
    # Truyen reasoning_context de mapper biet cha/me nao da duoc xac dinh la da chet
    enrich_options = {**(options or {}), "_reasoning_context": reasoning_context}
    res["fields"] = mapper.enrich(res["fields"], enrich_options)
    return res
