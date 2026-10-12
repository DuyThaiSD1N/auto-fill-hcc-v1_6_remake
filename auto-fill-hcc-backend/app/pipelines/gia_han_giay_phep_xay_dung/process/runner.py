"""Compact agent process pipeline cho "Gia hạn giấy phép xây dựng" (mã 1.013227, cổng Bộ Xây dựng dvc.moc)."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.gia_han_giay_phep_xay_dung.process import mapper
from app.pipelines.gia_han_giay_phep_xay_dung.process.prompt import EXTRA_RULES
from app.pipelines.gia_han_giay_phep_xay_dung.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
    OCR_MAX_PAGES,
)
from app.services.pdf_utils import trim_files_for_classify


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Chỉ OCR vài trang đầu mỗi PDF (xem OCR_MAX_PAGES) — GPXD kèm bản vẽ có thể dài hàng chục trang.
    trimmed = {role: trim_files_for_classify(files or [], OCR_MAX_PAGES) for role, files in files_by_role.items()}
    res = await runner.run(
        trimmed,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        max_tokens=1800,
    )
    # Đính kèm ocr_text để mapper suy giới tính từ xưng hô Ông/Bà khi giấy tờ không ghi rõ.
    enrich_options = dict(options or {})
    enrich_options["_ocr_text"] = res.get("ocr_text", "")
    mapped_fields, warnings = mapper.enrich(res["fields"], enrich_options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
