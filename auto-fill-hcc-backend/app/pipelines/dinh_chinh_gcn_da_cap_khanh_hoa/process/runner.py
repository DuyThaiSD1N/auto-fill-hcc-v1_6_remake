"""Compact-agent process pipeline cho thủ tục đính chính Giấy chứng nhận đã cấp Khánh Hòa (1.012790).

Bù tất định:
- Dùng chung với cấp đổi GCN Khánh Hòa (`apply_printed_fallback`): số thửa/số tờ khi mọi chỗ in cùng một số, và
  phường/xã nơi thường trú theo dòng "c) Địa chỉ" của Đơn (Mẫu 27 cùng bố cục mục 1 với Mẫu 18).
- GCN_NguoiSuDung: LLM hay chép tên ở Đơn mục 1a ("Ông A và vợ là bà B") thay vì tên in trên Giấy chứng nhận, làm cảnh
  báo Đơn/GCN lệch hồ sơ sai lý do. Lấy thẳng cụm "(Hộ) ông/bà: <tên>" ngay sau tiêu đề "I. Người sử dụng đất…" của
  GCN — trừ khi mục IV có dòng chuyển quyền (người sử dụng hiện tại là người nhận, để LLM đọc).
"""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_doi_gcn_khanh_hoa.process.runner import apply_printed_fallback

from . import mapper
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS

_GCN_SECTION_I = re.compile(r"I\s*[-.–]\s*Người\s+sử\s+dụng\s+đất[^\n]{0,80}?gắn\s+liền\s+với\s+đất", re.IGNORECASE)
_GCN_HOLDER = re.compile(
    r"((?:hộ\s+)?(?:ông|bà)\s*:\s*.+?)"
    r"(?=\s*(?:,\s*)?(?:năm\s+sinh|sinh\s+năm|sinh\s+ngày|số\s+cmnd|cmnd|cccd|số\s+định\s+danh|địa\s+chỉ|\n)|$)",
    re.IGNORECASE,
)
_TRANSFER = re.compile(r"chuyển\s+nhượng\s+cho|tặng\s+cho|thừa\s+kế|chuyển\s+quyền", re.IGNORECASE)
_SECTION_IV = re.compile(r"IV\s*[-.–]\s*Những\s+thay\s+đổi", re.IGNORECASE)


def gcn_holder(text: str) -> str | None:
    """Tên người in ở mục I của Giấy chứng nhận; mục IV có chuyển quyền hoặc không thấy mục I -> None."""
    section = _GCN_SECTION_I.search(text)
    if not section:
        return None
    later = _SECTION_IV.search(text, section.end())
    if later and _TRANSFER.search(text[later.end():later.end() + 3000]):
        return None
    match = _GCN_HOLDER.match(text[section.end():section.end() + 300].lstrip(" :\n"))
    if not match:
        return None
    holder = " ".join(match.group(1).split()).strip(" ,;.")
    return holder if len(holder) > 6 else None


def apply_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = apply_printed_fallback(raw_fields, documents)
    holder = gcn_holder("\n".join(document.get("text") or "" for document in documents))
    if holder:
        fields["GCN_NguoiSuDung"] = holder
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
        compact_field_fallback=apply_fallback,
    )
    result["fields"], warnings = mapper.enrich(result["fields"], options)
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    return result
