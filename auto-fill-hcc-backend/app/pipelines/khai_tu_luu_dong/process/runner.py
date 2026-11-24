"""Pipeline đăng ký khai tử lưu động (1.000419): trích compact → mapper ra ô eForm khai tử (cùng mẫu 2053)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.khai_tu_dang_ky_lai.process.runner import _requester_hint
from app.pipelines.khai_tu_nuoc_ngoai.process.runner import _compact_field_fallback

from . import mapper
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES + _requester_hint(options),
        # Số định danh khớp số in trên thẻ trong hồ sơ → nhân thân theo thẻ (chung với khai tử có yếu tố nước ngoài).
        compact_field_fallback=_compact_field_fallback,
        options=options,
    )
    res["fields"] = mapper.enrich(res["fields"], options)
    return res
