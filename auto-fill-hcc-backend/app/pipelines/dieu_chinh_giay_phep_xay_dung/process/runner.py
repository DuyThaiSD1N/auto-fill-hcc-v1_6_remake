"""Compact agent process pipeline cho "Cấp điều chỉnh giấy phép xây dựng" (cổng Bộ Xây dựng dvc.moc)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dieu_chinh_giay_phep_xay_dung.process import mapper
from app.pipelines.dieu_chinh_giay_phep_xay_dung.process.prompt import EXTRA_RULES
from app.pipelines.dieu_chinh_giay_phep_xay_dung.process.schema import (
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
        max_tokens=1600,
    )
    # Đính kèm ocr_text để mapper suy giới tính từ xưng hô Ông/Bà khi giấy tờ không ghi rõ.
    enrich_options = dict(options or {})
    enrich_options["_ocr_text"] = res.get("ocr_text", "")
    mapped_fields, warnings = mapper.enrich(res["fields"], enrich_options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
