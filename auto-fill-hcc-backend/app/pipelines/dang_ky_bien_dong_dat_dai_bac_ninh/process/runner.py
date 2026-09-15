"""Compact agent pipeline "[Bắc Ninh] Đăng ký biến động QSDĐ" (1.115468).

TÁCH theo purpose: lần "authorized_person" chỉ trích nhân thân 1 người (schema gọn); lần
"registration_form" trích chủ hồ sơ + đồng sử dụng + nghiệp vụ.
"""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_bien_dong_dat_dai_bac_ninh.process import mapper, prompt, schema


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    purpose = str((options or {}).get("purpose") or "registration_form")
    if purpose == "authorized_person":
        fields, allowed, comp, rules = (
            schema.FIELDS_UYQUYEN, schema.ALLOWED_UYQUYEN, schema.COMPACT_COMP_UYQUYEN, prompt.RULES_UYQUYEN,
        )
    else:
        fields, allowed, comp, rules = (
            schema.FIELDS_DON, schema.ALLOWED_DON, schema.COMPACT_COMP_DON, prompt.RULES_DON,
        )

    res = await runner.run(
        files_by_role,
        fields=fields,
        allowed=allowed,
        comp_by_name=comp,
        aliases=schema.ALIASES,
        extra_rules=rules,
    )
    mapped, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
