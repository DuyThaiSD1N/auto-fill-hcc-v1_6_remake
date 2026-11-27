"""Compact-agent process pipeline cho tách thửa hoặc hợp thửa đất (1.012784) — cổng iGate Ninh Bình.

`apply_printed_fallback` bù tất định số thửa/số tờ GỐC khi LLM bỏ sót: Giấy chứng nhận ("Thửa đất số: 16; tờ bản đồ số:
118"), Đơn ("Tách thửa đất số: 16 tờ bản đồ số: 118") cùng in một số thì lấy số đó. Thửa mới sau tách ghi "thửa 16-1"
(không có chữ "đất số") nên không lẫn vào; hai số khác nhau (hợp thửa) thì để LLM/cán bộ quyết.
"""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_doi_gcn_khanh_hoa.process.runner import _SO_THUA, _SO_TO, _as_dict

from . import mapper
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS


def apply_printed_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    text = "\n".join(document.get("text") or "" for document in documents)
    for name, pattern in (("ThuaDat_SoThua", _SO_THUA), ("ThuaDat_SoTo", _SO_TO)):
        if fields.get(name) not in (None, "", {}, []):
            continue
        numbers = {match.lstrip("0") or "0" for match in pattern.findall(text)}
        if len(numbers) == 1:
            fields[name] = next(iter(numbers))
    return fields


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    result = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        compact_field_fallback=apply_printed_fallback,
    )
    result["fields"], warnings = mapper.enrich(result["fields"], options)
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    return result
