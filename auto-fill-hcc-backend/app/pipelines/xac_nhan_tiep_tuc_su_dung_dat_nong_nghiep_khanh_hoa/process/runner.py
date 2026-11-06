"""Compact-agent process pipeline cho xác nhận tiếp tục sử dụng đất nông nghiệp — Khánh Hòa (1.013947).

LLM trả facts theo NGƯỜI (người thứ nhất / thứ hai đứng Đơn, bên được ủy quyền); mapper phân vai người nộp / chủ hồ sơ
theo file mapping và sinh field Form.io ba khối.

`apply_printed_names`: Đơn Mẫu 09 viết tay (scan có khi xoay ngang) hay bị OCR đọc lệch dấu tên ("Lê Cương" thay vì "Lê
Cường"), còn OCR trang bìa Giấy chứng nhận khổ A3 có khi hỏng hẳn. Tên IN trên Phiếu đo đạc ("3. Tên người sử dụng đất…:
A - B") / Giấy chứng nhận ("Ông: A", "Bà: B") khớp tên LLM trả khi bỏ dấu → lấy đúng chữ in.
"""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_doi_gcn_khanh_hoa.process.runner import _as_dict
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.mapper import _fold

from . import mapper
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS

_PRINTED_NAME_LINES = (
    re.compile(r"Tên\s+người\s+sử\s+dụng\s+đất[^:\n]*:\s*([^\n]+)", re.IGNORECASE),
    re.compile(r"^\s*(?:Ông|Bà)\s*:\s*([^\n,]+)", re.MULTILINE),
)
_NAME_SPLIT = re.compile(r"\s+[-–]\s+|;|,|\s+và\s+", re.IGNORECASE)


def _printed_names(text: str) -> list[str]:
    names: list[str] = []
    for pattern in _PRINTED_NAME_LINES:
        for match in pattern.finditer(text):
            for part in _NAME_SPLIT.split(match.group(1)):
                name = " ".join(part.split()).strip(" .:")
                if 2 <= len(name.split()) <= 6 and name[:1].isupper() and not any(ch.isdigit() for ch in name):
                    names.append(name)
    return names


def apply_printed_names(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    printed = _printed_names("\n".join(document.get("text") or "" for document in documents))
    for key in ("NSD1_HoTen", "NSD2_HoTen"):
        value = fields.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        for name in printed:
            # Chỉ sửa khi khác DẤU (cùng chữ cái): tên khác hẳn là người khác, giữ nguyên.
            if _fold(name) == _fold(value) and name != value:
                fields[key] = name
                break
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
        compact_field_fallback=apply_printed_names,
    )
    result["fields"], warnings = mapper.enrich(result["fields"], options)
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    return result
