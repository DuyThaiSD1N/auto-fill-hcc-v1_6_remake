"""Process pipeline cho thủ tục hỗ trợ chi phí hỏa táng Bắc Ninh."""

from app.pipelines._shared.compact_agent import runner

from . import the_can_cuoc
from .mapper import enrich
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
        max_tokens=2600,
        llm_reuse="use" if str((options or {}).get("purpose") or "") == "authorized_person" else "save",
    )
    # Họ tên / ngày sinh theo bản sao CCCD in máy cùng số định danh (Đơn viết tay OCR hay đọc lệch chữ).
    mapped, warnings = enrich(the_can_cuoc.apply(result.get("fields", []), result.get("ocr_text") or ""), options)
    result["fields"] = mapped
    result.setdefault("errors", []).extend(warnings)
    return result
