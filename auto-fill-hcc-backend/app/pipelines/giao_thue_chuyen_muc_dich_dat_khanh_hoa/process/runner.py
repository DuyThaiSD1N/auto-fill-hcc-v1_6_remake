"""Compact-agent process pipeline cho thủ tục giao đất, cho thuê đất, chuyển mục đích sử dụng đất Khánh Hòa (1.013949).

Đơn Mẫu 06 thường viết tay: OCR chữ ký/chữ số tay hay sai mà LLM vẫn bám theo Đơn dù bản in có giá trị đúng. Sau bước
LLM, `apply_printed_fallback` đọc tất định hai mẫu in ổn định trong giấy ủy quyền/Giấy chứng nhận để sửa lại.
"""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner

from . import mapper
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS

# "Bằng giấy này, tôi ủy quyền cho:\nÔng : NGUYỄN VĂN A - Sinh ngày: …" — chỉ cá nhân (có Ông/Bà), bỏ qua tổ chức.
_UY_QUYEN_CHO = re.compile(
    r"(?:ủy|uỷ)\s+quyền\s+cho\s*:?\s*(?:Ông\s*/\s*Bà|Ông|Bà)\s*:?\s*([^\n\-–,:;()]{3,60}?)\s*(?:[-–,;(]|\n|Sinh\b|$)",
    re.IGNORECASE,
)
# "c) Diện tích: 262,4m²" (GCN), "diện tích: 262,4 m²" (giấy ủy quyền). Có dấu ":" ngay sau "Diện tích" nên không
# trúng "Diện tích xây dựng:", "Diện tích sàn:".
_DIEN_TICH = re.compile(r"diện\s+tích\s*:\s*(\d+(?:[.,]\d+)?)\s*m", re.IGNORECASE)
_DIEN_TICH_DAT_TRONG_CAU = re.compile(r"(diện\s+tích\s+đất\s*:?\s*)(\d+(?:[.,]\d+)?)(\s*m)", re.IGNORECASE)


def _as_dict(raw_fields) -> dict:
    if isinstance(raw_fields, dict):
        return dict(raw_fields)
    if isinstance(raw_fields, list):
        return {
            item.get("name"): item.get("value")
            for item in raw_fields
            if isinstance(item, dict) and item.get("name") and item.get("value") not in (None, "", {}, [])
        }
    return {}


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", str(text or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn").replace("đ", "d").replace("Đ", "D")
    return " ".join(text.lower().split())


def _looks_like_person_name(text: str) -> bool:
    words = text.split()
    return 2 <= len(words) <= 6 and all(word.isalpha() for word in words)


def apply_printed_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    text = "\n".join(document.get("text") or "" for document in documents)

    names: dict[str, str] = {}
    for match in _UY_QUYEN_CHO.finditer(text):
        name = " ".join(match.group(1).split())
        if _looks_like_person_name(name):
            names.setdefault(_fold(name), name)
    # Đúng MỘT cá nhân được ủy quyền in trong hồ sơ -> tên in thắng bản LLM đọc (hay lấy theo chữ ký tay trên Đơn).
    if len(names) == 1:
        fields["UyQuyen_HoTenNguoiDuocUyQuyen"] = next(iter(names.values()))

    areas = {value.replace(".", ",") for value in _DIEN_TICH.findall(text)}
    content = fields.get("Don_NoiDungDeNghi")
    # Mọi bản in cùng một diện tích thửa -> số viết tay đọc lệch trong câu nội dung yêu cầu được sửa theo bản in.
    if len(areas) == 1 and isinstance(content, str):
        area = next(iter(areas))
        fields["Don_NoiDungDeNghi"] = _DIEN_TICH_DAT_TRONG_CAU.sub(
            lambda m: f"{m.group(1)}{area}{m.group(3)}", content, count=1
        )
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
