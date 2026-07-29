"""Compact agent pipeline cho "[Bắc Ninh] Đăng ký đất đai, cấp GCN lần đầu"."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_dat_dai_lan_dau_bac_ninh.process import mapper
from app.pipelines.dang_ky_dat_dai_lan_dau_bac_ninh.process.fallback import apply_ocr_fallback
from app.pipelines.dang_ky_dat_dai_lan_dau_bac_ninh.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_dat_dai_lan_dau_bac_ninh.process.schema import (
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
        compact_field_fallback=apply_ocr_fallback,
    )
    res["fields"] = mapper.enrich(res["fields"])
    return res
