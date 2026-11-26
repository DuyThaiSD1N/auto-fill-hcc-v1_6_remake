"""Pipeline đăng ký khai tử có yếu tố nước ngoài (1.001766): trích compact → mapper ra ô eForm khai tử 2053."""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.khai_tu_dang_ky_lai.process.runner import (
    _apply_identity_facts,
    _cccd_front_facts,
    _cccd_issue_facts,
    _digits,
    _fields_dict,
    _ocr_text,
    _requester_hint,
)

from . import mapper
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS


def _is_card_number(value) -> bool:
    """Chỉ số CMND 9 / CCCD 12 chữ số mới dò mặt thẻ; số hộ chiếu (có chữ cái) bỏ qua để không cắt mất chữ."""
    text = str(value or "").strip().replace(" ", "")
    return text.isdigit() and len(text) in (9, 12)


def _compact_field_fallback(raw_fields, documents: list[dict]):
    """Số định danh (agent trích hoặc chép từ tờ khai) khớp số in trên một thẻ trong hồ sơ → nhân thân theo thẻ."""
    fields = _fields_dict(raw_fields)
    text = _ocr_text(documents)
    if not fields or not text:
        return raw_fields
    for prefix, declared in (("Requester", "ToKhai_NguoiYeuCau"), ("Deceased", "ToKhai_NguoiChet")):
        for id_number in (fields.get(f"{prefix}_IdNumber"), fields.get(f"{declared}_SoDinhDanh")):
            if not _is_card_number(id_number):
                continue
            facts = {**_cccd_front_facts(text, id_number), **_cccd_issue_facts(text, id_number)}
            if not facts:
                continue
            fields[f"{prefix}_IdNumber"] = _digits(id_number)
            _apply_identity_facts(fields, prefix, facts)
            if prefix == "Requester" and facts.get("birthDate"):
                fields["Requester_BirthDate"] = facts["birthDate"]
            break
    return fields


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES + _requester_hint(options),
        compact_field_fallback=_compact_field_fallback,
        options=options,
    )
    res["fields"] = mapper.enrich(res["fields"], options)
    return res
