"""Compact agent pipeline cho "[Bắc Ninh] Cấp lại Giấy chứng nhận do bị mất".

TÁCH theo purpose (chọn TRƯỚC khi gọi LLM để mỗi lần trích gọn, không lẫn người):
- "registration_form" (mặc định): Đơn Mẫu 18 + số vào sổ / số phát hành GCN bị mất + người nhận kết quả.
- "authorized_person": nhân thân MỘT người = chủ hồ sơ (bên ủy quyền) → khối doiTuongKhac*.
"""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh.process import mapper
from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh.process.fallback import (
    apply_authorized_fallback,
    apply_ocr_fallback,
)
from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh.process.prompt import EXTRA_RULES, RULES_UYQUYEN
from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_bac_ninh.process.schema import (
    ALIASES,
    ALLOWED,
    ALLOWED_UYQUYEN,
    COMPACT_COMP_BY_NAME,
    COMPACT_COMP_UYQUYEN,
    FIELDS,
    FIELDS_UYQUYEN,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    if str((options or {}).get("purpose") or "registration_form") == "authorized_person":
        res = await runner.run(
            files_by_role,
            fields=FIELDS_UYQUYEN,
            allowed=ALLOWED_UYQUYEN,
            comp_by_name=COMPACT_COMP_UYQUYEN,
            aliases=ALIASES,
            extra_rules=RULES_UYQUYEN,
            compact_field_fallback=apply_authorized_fallback,
        )
        res["fields"], warnings = mapper.enrich_authorized(res["fields"])
        if warnings:
            res.setdefault("errors", []).extend(warnings)
        return res

    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=apply_ocr_fallback,
    )
    res["fields"] = mapper.enrich(res["fields"])
    return res
