"""Compact-agent process pipeline cho thủ tục cấp đổi Giấy chứng nhận Khánh Hòa (1.012783).

`apply_printed_fallback` bù tất định hai chỗ LLM hay trượt:
- Số thửa/số tờ in ở mục II.1 của Giấy chứng nhận và lặp lại ở đầu Trang bổ sung ("Thửa đất số: …  Tờ bản đồ số: …").
  LLM đọc bản quét dài (trang bìa + sơ đồ + bảng tọa độ) đôi khi bỏ sót: bù khi mọi chỗ in cùng một số.
- Phường/xã nơi thường trú: dòng "c) Địa chỉ" của Đơn ghi "Tổ dân phố A, Hòn B phường Nam Nha Trang"; LLM áp nhầm quy
  tắc CCCD (cụm sát trước tỉnh là cấp huyện, bỏ) -> coi "Nam Nha Trang" là thành phố cũ, lấy tên tổ dân phố làm phường.
  Phường LLM trả không có trong danh mục tỉnh mà Đơn ghi rõ "phường/xã X" hợp lệ thì lấy X.
"""

import re

from app.pipelines._shared.area_remap import canonical_ward
from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.mapper import _area, _fold

from . import mapper
from .prompt import EXTRA_RULES
from .schema import ALIASES, ALLOWED, COMPACT_COMP_BY_NAME, FIELDS

_SO_THUA = re.compile(r"thửa\s+đất\s+số\s*:?\s*(\d{1,6})\b", re.IGNORECASE)
_SO_TO = re.compile(r"tờ\s+bản\s+đồ\s+số\s*:?\s*(\d{1,4})\b", re.IGNORECASE)
# Đơn đăng ký biến động mục 1/I, hai bố cục: "c) Địa chỉ(2):\n<địa chỉ>\nd) Điện thoại…" và Mẫu 18 mới "- Địa chỉ(4):
# <địa chỉ> - phường X - Tỉnh Y\n- Mã số thuế…". Chỉ xét đoạn từ tiêu đề Đơn tới "Nội dung biến động": khối chữ ký số
# ("Địa chỉ: CƠ QUAN …") và "Địa chỉ" của giấy khác (tờ khai, hợp đồng) không lẫn vào.
_DON_TITLE = re.compile(r"đơn\s+đăng\s+ký\s+biến\s+động", re.IGNORECASE)
_DON_END = re.compile(r"nội\s+dung\s+biến\s+động", re.IGNORECASE)
_DON_DIA_CHI = re.compile(
    r"Địa\s*chỉ[^\n:]*:\s*(.+?)(?=\n\s*(?:-\s*)?(?:d\)|mã\s+số\s+thuế|điện\s+thoại)|\Z)", re.IGNORECASE | re.DOTALL
)
_WARD_IN_TEXT = re.compile(r"\b(phường|xã|đặc\s+khu)\s+([^\n,;()]+)", re.IGNORECASE)
_PROVINCE_TAIL = re.compile(r"\s+(?:tỉnh|thành\s+phố|tp\.?)\s.*$", re.IGNORECASE)


def _don_ward(text: str, province: str) -> str | None:
    """Phường/xã ghi rõ (có tiền tố) ở dòng địa chỉ người sử dụng đất trên Đơn, đã chuẩn theo danh mục tỉnh; không có/
    không hợp lệ -> None."""
    title = _DON_TITLE.search(text)
    if not title:
        return None
    end = _DON_END.search(text, title.end())
    block = text[title.end():end.start() if end else title.end() + 1500]
    for match in _DON_DIA_CHI.finditer(block):
        wards = _WARD_IN_TEXT.findall(match.group(1))
        if not wards:
            continue  # "Địa chỉ: CƠ QUAN …" của khối chữ ký số
        kind, name = wards[-1]
        name = re.split(r"\s+[-–]\s*", _PROVINCE_TAIL.sub("", name))[0].strip(" .:-")
        return canonical_ward(province, f"{kind} {name}") if name else None
    return None


def _fix_person_ward(fields: dict, name: str, don_ward: str, province: str) -> None:
    value = fields.get(name)
    if not isinstance(value, dict):
        return
    remapped = _area(value)
    tinh = (remapped or {}).get("tinh") or province
    if _fold(tinh) != _fold(province):
        return  # người ở tỉnh khác: Đơn của thủ tục Khánh Hòa không đủ căn cứ sửa
    if remapped and canonical_ward(tinh, remapped.get("xa")):
        return  # phường LLM trả (sau remap tên cũ) đã hợp lệ: giữ thứ tự nguồn CCCD -> Đơn
    fields[name] = {**value, "tinh": value.get("tinh") or province, "xa": don_ward}


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


def apply_printed_fallback(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    text = "\n".join(document.get("text") or "" for document in documents)
    for name, pattern in (("ThuaDat_SoThua", _SO_THUA), ("ThuaDat_SoTo", _SO_TO)):
        if fields.get(name) not in (None, "", {}, []):
            continue
        numbers = {match.lstrip("0") or "0" for match in pattern.findall(text)}
        # Chỉ bù khi mọi chỗ in cùng một số; hai số khác nhau (tách thửa, bản đồ cũ/mới) thì để LLM/cán bộ quyết.
        if len(numbers) == 1:
            fields[name] = next(iter(numbers))

    don_ward = _don_ward(text, mapper.PORTAL_PROVINCE)
    if don_ward:
        _fix_person_ward(fields, "ChuHoSo_DiaChi", don_ward, mapper.PORTAL_PROVINCE)
        applicant = fields.get("NguoiNop_HoTen")
        # Địa chỉ ở Đơn là của chủ hồ sơ: chỉ sửa khối người nộp khi đó cũng là chủ hồ sơ.
        if not applicant or _fold(applicant) == _fold(fields.get("ChuHoSo_HoTen")):
            _fix_person_ward(fields, "NguoiNop_DiaChi", don_ward, mapper.PORTAL_PROVINCE)
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
