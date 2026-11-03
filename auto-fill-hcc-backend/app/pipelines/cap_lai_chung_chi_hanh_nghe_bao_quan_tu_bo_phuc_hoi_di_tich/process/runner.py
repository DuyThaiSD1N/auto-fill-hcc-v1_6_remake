"""Compact agent process pipeline cho "Thủ tục cấp lại Chứng chỉ hành nghề bảo quản, tu bổ, phục hồi di tích"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_lai_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.process import mapper
from app.pipelines.cap_lai_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.process.prompt import EXTRA_RULES
from app.pipelines.cap_lai_chung_chi_hanh_nghe_bao_quan_tu_bo_phuc_hoi_di_tich.process.schema import (
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
        # Đơn Mẫu 51 chép nguyên văn trình độ + bảng quá trình hoạt động (nhiều công trình) như bản cấp mới.
        max_tokens=2400,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
