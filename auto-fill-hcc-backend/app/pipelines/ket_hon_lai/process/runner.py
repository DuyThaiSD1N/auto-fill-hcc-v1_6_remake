"""Compact agent process pipeline cho "Đăng ký lại kết hôn"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.ket_hon_lai.process import mapper
from app.pipelines.ket_hon_lai.process.prompt import EXTRA_RULES
from app.pipelines.ket_hon_lai.process.schema import (
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
    )
    res["fields"] = mapper.enrich(res["fields"], options)
    return res
