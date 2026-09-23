"""Compact-agent process pipeline [Lào Cai] tổ chức kinh tế nhận chuyển nhượng QSDĐ dự án (1.115681)."""

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
    )
    # options mang formContext (họ tên + số căn cước cổng prefill từ tài khoản định danh) — mapper cần
    # nó để biết AI đang đi nộp: người đại diện của tổ chức hay người được ủy quyền của đơn vị khác.
    # Hai trường hợp đó điền ô "Tên cơ quan/tổ chức" của khối người nộp bằng HAI pháp nhân khác nhau.
    result["fields"], warnings = mapper.enrich(result["fields"], options)
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    return result
