"""Compact-agent process pipeline cho đăng ký tài sản gắn liền với thửa đất đã cấp GCN — Khánh Hòa (1.013995).

Dùng lại bước bù tất định của cấp đổi GCN Khánh Hòa (cùng cổng, cùng mẫu Đơn 18): số thửa/số tờ khi mọi chỗ in cùng một
số, phường thường trú ghi rõ "phường X" trên Đơn khi phường LLM trả không có trong danh mục tỉnh. Thêm: mục "Nội dung
biến động" của Đơn LLM bỏ sót thì chép thẳng từ chữ OCR (giữ xuống dòng, dừng trước câu cam đoan / "Người viết đơn").
"""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_doi_gcn_khanh_hoa.process.runner import _DON_TITLE
from app.pipelines.cap_doi_gcn_khanh_hoa.process.runner import apply_printed_fallback as _cap_doi_fallback

from . import mapper
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS

_REQUEST_HEAD = re.compile(r"nội\s+dung\s+biến\s+động\s*:?", re.IGNORECASE)
_REQUEST_END = re.compile(r"\n\s*(?:tôi\s+)?cam\s+đoan|\n\s*người\s+viết\s+đơn", re.IGNORECASE)
_REQUEST_MAX = 1200


def _don_request(text: str) -> str | None:
    """Mục "Nội dung biến động" của Đơn, nguyên văn; chỉ tìm sau tiêu đề Đơn (giấy khác không có mục này)."""
    title = _DON_TITLE.search(text)
    head = _REQUEST_HEAD.search(text, title.end()) if title else None
    if not head:
        return None
    rest = text[head.end():head.end() + _REQUEST_MAX]
    end = _REQUEST_END.search(rest)
    lines = [" ".join(line.split()) for line in (rest[:end.start()] if end else rest).splitlines()]
    request = "\n".join(line for line in lines if line.strip(" .…"))
    return request or None


def apply_printed_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _cap_doi_fallback(raw_fields, documents)
    if not str(fields.get("Don_NoiDungBienDong") or "").strip():
        request = _don_request("\n".join(document.get("text") or "" for document in documents))
        if request:
            fields["Don_NoiDungBienDong"] = request
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
