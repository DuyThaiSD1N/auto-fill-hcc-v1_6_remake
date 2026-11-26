"""Compact agent process pipeline cho Khánh Hòa - tính hoặc tính lại tiền sử dụng đất theo NĐ 50/2026/NĐ-CP (1.115148)."""

from app.pipelines._shared.compact_agent import runner

from . import mapper
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Không tiêm formContext (tài khoản đăng nhập) vào prompt; mapper dùng formContext TẤT ĐỊNH để biết có giữ khối người
    # nộp cổng đổ sẵn hay phải trả các ô thiếu về trống.
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
