"""Pipeline đăng ký khai tử (Cổng DVC quốc gia mới): phân vai → trích → mapper."""

import re

from app.pipelines._shared.compact_agent import runner

from . import mapper, reason
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS

# Khối người mất trên tờ khai bắt đầu sau câu "Đề nghị cơ quan đăng ký khai tử cho người có tên dưới đây".
_TO_KHAI_NGUOI_MAT = re.compile(r"đề\s*nghị\s+cơ\s+quan\s+đăng\s+ký\s+khai\s+tử", re.IGNORECASE)
# "Giới tính: (2) Nam Dân tộc: (2) Kinh Quốc tịch: (2) Việt Nam" — dân tộc thường chung dòng với giới tính.
_DAN_TOC = re.compile(r"dân\s*tộc\s*[:：]\s*(?:\(\d+\)\s*)?(.+?)(?=\s+quốc\s*tịch|\s+nơi\s|\s*\(\d+\)|\n|$)",
                      re.IGNORECASE)


def _dan_toc_to_khai(documents: list[dict]) -> str:
    """Dân tộc ghi trong khối người mất của tờ khai; không thấy tờ khai thì rỗng."""
    for doc in documents or []:
        text = str(doc.get("text") or "")
        anchor = _TO_KHAI_NGUOI_MAT.search(text)
        if not anchor:
            continue
        # Chỉ xét vài dòng đầu khối người mất, tránh lấy nhầm dòng của giấy khác ghép sau.
        block = "\n".join(text[anchor.end():].splitlines()[:8])
        found = _DAN_TOC.search(block)
        value = found.group(1).strip(" .,:;-") if found else ""
        if value and not re.fullmatch(r"[.…\s]*", value):
            return value
    return ""


def _compact_field_fallback(raw_fields, documents: list[dict]):
    """LLM hay bỏ sót dân tộc khi nó nằm giữa dòng giới tính / quốc tịch → đọc thẳng từ tờ khai."""
    if isinstance(raw_fields, dict):
        if not raw_fields.get("NguoiMat_DanToc"):
            value = _dan_toc_to_khai(documents)
            if value:
                raw_fields["NguoiMat_DanToc"] = value
    elif isinstance(raw_fields, list):
        if not any(isinstance(f, dict) and f.get("name") == "NguoiMat_DanToc" and f.get("value")
                   for f in raw_fields):
            value = _dan_toc_to_khai(documents)
            if value:
                raw_fields.append({"name": "NguoiMat_DanToc", "value": value})
    return raw_fields


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    result = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=_compact_field_fallback,
        options=options,
        context_builder=reason.build_context,
    )
    enrich_options = {**(options or {}), "_reasoning_context": result.get("reasoning_context") or ""}
    result["fields"], warnings = mapper.enrich(result["fields"], enrich_options)
    if warnings:
        result.setdefault("errors", []).extend(warnings)
    return result
