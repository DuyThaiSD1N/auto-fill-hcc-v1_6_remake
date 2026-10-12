"""Compact agent process pipeline cho "Thông báo phát triển nguồn điện mặt trời mái nhà tự sản xuất, tự tiêu thụ"
(cổng Bộ Công Thương). Xem mapper: chọn panel Cá nhân/Tổ chức, khối tài khoản theo mốc đăng nhập."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.thong_bao_phat_trien_nguon_dien_mat_troi_mai_nha.process import mapper
from app.pipelines.thong_bao_phat_trien_nguon_dien_mat_troi_mai_nha.process.prompt import EXTRA_RULES
from app.pipelines.thong_bao_phat_trien_nguon_dien_mat_troi_mai_nha.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
    OCR_MAX_PAGES,
)
from app.services.pdf_utils import trim_files_for_classify


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    # Chỉ OCR vài trang đầu mỗi PDF (xem OCR_MAX_PAGES): mọi field nằm ở Thông báo / trang đầu bản vẽ.
    trimmed = {role: trim_files_for_classify(files or [], OCR_MAX_PAGES) for role, files in files_by_role.items()}
    res = await runner.run(
        trimmed,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
