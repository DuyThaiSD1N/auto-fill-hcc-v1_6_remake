"""Compact agent process pipeline for "Đăng ký tham dự kiểm tra kết quả tập sự hành nghề công chứng"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_tham_du_kiem_tra_ket_qua_tap_su_hanh_nghe_cong_chung.process import mapper
from app.pipelines.dang_ky_tham_du_kiem_tra_ket_qua_tap_su_hanh_nghe_cong_chung.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_tham_du_kiem_tra_ket_qua_tap_su_hanh_nghe_cong_chung.process.schema import (
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
    res["fields"], warnings = mapper.enrich(res["fields"], options)
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
