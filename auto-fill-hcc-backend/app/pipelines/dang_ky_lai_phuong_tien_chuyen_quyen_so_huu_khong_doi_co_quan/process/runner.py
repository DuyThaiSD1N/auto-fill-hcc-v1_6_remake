"""Compact agent process pipeline cho "Đăng ký lại phương tiện ... chuyển quyền sở hữu" (1.004002).

HAI vai: CHỦ PHƯƠNG TIỆN MỚI (bên mua / bên nhận — tổ chức hoặc cá nhân, đứng tên Đơn Mẫu 07) và NGƯỜI NỘP (người
đại diện theo pháp luật của chủ mới, hoặc chính chủ mới nếu là cá nhân). Chủ CŨ (bên bán, chủ trên GCN đăng ký cũ)
chỉ dùng để ghép lý do đăng ký lại."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_lai_phuong_tien_chuyen_quyen_so_huu_khong_doi_co_quan.process import mapper
from app.pipelines.dang_ky_lai_phuong_tien_chuyen_quyen_so_huu_khong_doi_co_quan.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_lai_phuong_tien_chuyen_quyen_so_huu_khong_doi_co_quan.process.schema import (
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
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
