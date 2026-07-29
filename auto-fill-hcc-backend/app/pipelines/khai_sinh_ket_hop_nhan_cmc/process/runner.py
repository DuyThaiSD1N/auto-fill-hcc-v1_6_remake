"""Run one of the two eForms using an explicit DOM-derived form variant."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.khai_sinh_ket_hop_nhan_cmc.process import mapper
from app.pipelines.khai_sinh_ket_hop_nhan_cmc.process.prompt import EXTRA_RULES
from app.pipelines.khai_sinh_ket_hop_nhan_cmc.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


def _variant(options: dict | None) -> str:
    options = options or {}
    context = options.get("formContext") or {}
    variant = str(context.get("formVariant") or "").strip()
    signature = {str(name) for name in (context.get("formSignature") or [])}
    expected = {
        mapper.BIRTH_VARIANT: {"HoTenKS", "HoTenMeKS", "HoTenChaKS"},
        mapper.RECOGNITION_VARIANT: {"HotenA", "hotenB", "loaiXacNhan"},
    }.get(variant, set())
    return variant if expected and expected <= signature else ""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    variant = _variant(options)
    if variant not in mapper.VALID_VARIANTS:
        return {
            "fields": [],
            "extracted": {"documents": []},
            "errors": ["Không xác định được biểu mẫu khai sinh hay nhận cha, mẹ, con đang mở."],
            "stats": {"ocr_latency_ms": 0, "llm_latency_ms": 0, "total_latency_ms": 0},
        }

    result = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        max_tokens=2400,
    )
    source_fields = result["fields"]
    warning = mapper.child_name_warning(source_fields)
    if warning:
        result.setdefault("errors", []).append(warning)
    result["fields"] = mapper.enrich(source_fields, variant, options)
    result.setdefault("extracted", {})["formVariant"] = variant
    return result
