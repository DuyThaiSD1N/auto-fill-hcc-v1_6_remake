"""Compact-agent process pipeline cho thủ tục đăng ký biến động chuyển nhượng, thừa kế, tặng cho Khánh Hòa (1.013831).

Đơn Mẫu 18 viết tay ghi địa chỉ dạng "Đường A - Tổ dân phố B - phường Nam Nha Trang - Tỉnh Khánh Hòa"; LLM có thể áp
nhầm quy tắc CCCD (cụm sát trước tỉnh là cấp huyện) rồi lấy tên tổ dân phố làm phường. Dùng lại bước bù phường từ Đơn
của pipeline cấp đổi GCN Khánh Hòa (cùng cổng, cùng mẫu Đơn): phường LLM trả không có trong danh mục tỉnh mà Đơn ghi rõ
"phường/xã X" hợp lệ thì lấy X.
"""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.cap_doi_gcn_khanh_hoa.process.runner import (
    _DON_TITLE,
    _WARD_IN_TEXT,
    _as_dict,
    _don_ward,
    _fix_person_ward,
)
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.mapper import _fold

from . import mapper
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS

_PROVINCE = "Khánh Hòa"
_TOA_LAC = re.compile(r"tọa\s+lạc\s+tại\s*:?\s*", re.IGNORECASE)
_TOA_LAC_END = re.compile(r"\.(?:\s|$)|\n\s*(?:có\s+nhu\s+cầu|III\.|IV\.)", re.IGNORECASE)


def _don_parcel_address(text: str) -> str | None:
    """Cụm "tọa lạc tại …" trong mục II của Đơn (địa danh hiện hành do người dân ghi) — nguồn đầu tiên của địa chỉ
    thửa đất theo file mapping; LLM hay chọn lẫn tờ khai hoặc tự ghép. Chỉ nhận khi cụm có phường/xã."""
    title = _DON_TITLE.search(text)
    if not title:
        return None
    match = _TOA_LAC.search(text, title.end(), title.end() + 4000)
    if not match:
        return None
    rest = text[match.end():match.end() + 300]
    end = _TOA_LAC_END.search(rest)
    address = " ".join((rest[:end.start()] if end else rest).split()).strip(" ,;:-")
    return address if address and _WARD_IN_TEXT.search(address) else None


def apply_printed_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    text = "\n".join(document.get("text") or "" for document in documents)
    parcel_address = _don_parcel_address(text)
    if parcel_address:
        fields["ThuaDat_DiaChiDayDu"] = parcel_address
    don_ward = _don_ward(text, _PROVINCE)
    if don_ward:
        _fix_person_ward(fields, "ChuHoSo_DiaChi", don_ward, _PROVINCE)
        applicant = fields.get("NguoiNop_HoTen")
        # Địa chỉ ở Đơn là của chủ hồ sơ: chỉ sửa khối người nộp khi đó cũng là chủ hồ sơ.
        if not applicant or _fold(applicant) == _fold(fields.get("ChuHoSo_HoTen")):
            _fix_person_ward(fields, "NguoiNop_DiaChi", don_ward, _PROVINCE)
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
