"""Compact agent pipeline cho "[Bắc Ninh] Đính chính GCN có sai sót".

TÁCH theo purpose (chọn TRƯỚC khi gọi LLM để mỗi lần trích gọn, không lẫn người):
- "registration_form" (mặc định): Đơn Mẫu 18 + người nhận kết quả.
- "authorized_person": nhân thân MỘT người = bên ủy quyền (chủ hồ sơ) → khối doiTuongKhac*.
"""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dinh_chinh_sai_sot_bac_ninh.process import mapper
from app.pipelines.dinh_chinh_sai_sot_bac_ninh.process.fallback import (
    apply_authorized_fallback,
    apply_ocr_fallback,
)
from app.pipelines.dinh_chinh_sai_sot_bac_ninh.process.prompt import EXTRA_RULES, RULES_UYQUYEN
from app.pipelines.dinh_chinh_sai_sot_bac_ninh.process.schema import (
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
