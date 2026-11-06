"""Compact agent process pipeline cho "Tuyên Quang - Đăng ký mua, thuê mua, thuê nhà ở xã hội…" (cổng DVC Bộ Xây dựng).

Người kê khai là chủ hồ sơ và là người nộp. PDF gộp lớn OCR song song theo phần như các thủ tục đất đai Tuyên Quang."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_bien_dong_thoa_thuan_thanh_vien_ho_gia_dinh_da_nang.process.runner import (
    _ocr_split_large_pdfs,
)
from app.pipelines.dang_ky_nha_o_xa_hoi_tuyen_quang.process import mapper
from app.pipelines.dang_ky_nha_o_xa_hoi_tuyen_quang.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_nha_o_xa_hoi_tuyen_quang.process.schema import (
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
        ocr_fn=_ocr_split_large_pdfs,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options, ocr_text=res.get("ocr_text"))
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
