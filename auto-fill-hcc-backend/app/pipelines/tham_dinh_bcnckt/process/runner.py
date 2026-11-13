"""Compact agent process pipeline cho "Thẩm định BCNCKT đầu tư xây dựng" (cổng DVC Bộ Xây dựng).

Người nộp (CCCD, occ0) + chủ đầu tư + dự án + quy hoạch/phê duyệt (containers) + năng lực nhà thầu
(+2 datagrid bộ môn). Xem mapper.

`drop_contractor_contacts` chặn tất định một lỗi LLM: nhiều Tờ trình KHÔNG ghi trụ sở/điện thoại chủ đầu tư, chỉ ghi
"Địa chỉ / Điện thoại" của từng nhà thầu ở mục "Hồ sơ năng lực của các nhà thầu" → LLM lấy địa chỉ + SĐT nhà thầu tư
vấn thiết kế đầu tiên điền vào Thông tin doanh nghiệp / chủ đầu tư. Giá trị chỉ có trong khối nhà thầu thì bỏ.

Cùng bước đó bù MST chủ đầu tư: Tờ trình kiểu này không có dòng "Mã số thuế" cạnh tên chủ đầu tư, chỉ ghi "Giấy chứng
nhận đăng ký doanh nghiệp số …" ở mục "Văn bản pháp lý" → LLM lúc lấy lúc bỏ. Lấy số GCN đầu tiên NGOÀI khối nhà thầu;
số GCN chỉ có trong khối nhà thầu thì không nhận làm MST chủ đầu tư."""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.tham_dinh_bcnckt.process import mapper
from app.pipelines.tham_dinh_bcnckt.process.prompt import EXTRA_RULES
from app.pipelines.tham_dinh_bcnckt.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)

# Đầu mục thông tin nhà thầu: "3. Hồ sơ năng lực của các nhà thầu", "IV.3 Năng lực nhà thầu"…
_NANG_LUC_NHA_THAU = re.compile(r"năng\s+lực\s+(?:của\s+)?(?:các\s+)?nhà\s+thầu", re.IGNORECASE)
_CONTACT_LINE = re.compile(r"\b(địa\s*chỉ|điện\s*thoại|đt|tel|fax)\s*[:：]\s*([^\n]+)", re.IGNORECASE)
_LEGAL_FORM = re.compile(
    r"\b(tong cong ty|cong ty|co phan|cp|tnhh|trach nhiem huu han|mtv|mot thanh vien|hai thanh vien tro len)\b"
)
_OWNER_WINDOW = 300  # số ký tự nhìn ngược từ dòng "Địa chỉ:" để tìm tên đơn vị sở hữu dòng đó.
# "Giấy chứng nhận đăng ký doanh nghiệp số: 4200…", "Mã số doanh nghiệp: …", "Mã số thuế …" — 10 số, chi nhánh 10-3.
_TAX_LINE = re.compile(
    r"(?:đăng\s*ký\s*doanh\s*nghiệp|mã\s*số\s*(?:doanh\s*nghiệp|thuế))\s*(?:số)?\s*[:：]?\s*"
    r"(\d[\d .]{8,14}\d(?:\s*-\s*\d{3})?)",
    re.IGNORECASE,
)


def _compact(value) -> str:
    return re.sub(r"[^a-z0-9]", "", mapper._fold(value))


def _core_name(value) -> str:
    """Tên tổ chức bỏ loại hình ("Công ty CP", "TNHH"…): "Công Ty Cổ phần X" và "Công ty CP X" cùng một lõi."""
    return re.sub(r"[^a-z0-9]", "", _LEGAL_FORM.sub(" ", mapper._fold(value)))


def _phones(text: str) -> set[str]:
    out = set()
    for chunk in re.split(r"[,;/]|\s[-–]\s", text):
        digits = re.sub(r"\D", "", chunk)
        if 9 <= len(digits) <= 11:
            out.add(digits)
    return out


def _tax_code(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw)
    return digits if len(digits) in (10, 13) else None


def _owned_by_investor(section: str, start: int, investor_core: str) -> bool:
    window = mapper._fold(section[max(0, start - _OWNER_WINDOW):start])
    owner = window[window.rfind("cong ty"):] if "cong ty" in window else window
    return bool(investor_core and investor_core in _core_name(owner))


def _contractor_contacts(documents: list[dict], investor: str) -> tuple[list[str], set[str], set[str], str]:
    """(địa chỉ nhà thầu dạng compact, SĐT nhà thầu, số GCN ĐKDN nhà thầu, đoạn văn bản NGOÀI khối nhà thầu). Dòng
    đứng sau tên chính chủ đầu tư (chủ đầu tư tự lập thiết kế) không tính là của nhà thầu."""
    investor_core = _core_name(investor)
    addresses: list[str] = []
    phones: set[str] = set()
    taxes: set[str] = set()
    outside: list[str] = []
    for document in documents:
        text = document.get("text") or ""
        heading = _NANG_LUC_NHA_THAU.search(text)
        if not heading:
            outside.append(text)
            continue
        outside.append(text[:heading.start()])
        section = text[heading.start():]
        for match in _CONTACT_LINE.finditer(section):
            if _owned_by_investor(section, match.start(), investor_core):
                continue
            label = mapper._fold(match.group(1))
            if label.startswith("dia"):
                address = _compact(match.group(2))
                if len(address) >= 6:
                    addresses.append(address)
            else:
                phones |= _phones(match.group(2))
        for match in _TAX_LINE.finditer(section):
            code = _tax_code(match.group(1))
            if code and not _owned_by_investor(section, match.start(), investor_core):
                taxes.add(code)
    return addresses, phones, taxes, "\n".join(outside)


def _investor_tax_codes(outside: str, investor: str) -> list[str]:
    """Số GCN ĐKDN / MST ngoài khối nhà thầu, theo thứ tự xuất hiện. Bỏ dòng ghi tên một công ty KHÁC chủ đầu tư."""
    investor_core = _core_name(investor)
    out: list[str] = []
    for match in _TAX_LINE.finditer(outside):
        code = _tax_code(match.group(1))
        if not code or code in out:
            continue
        line_start = outside.rfind("\n", 0, match.start()) + 1
        line_end = outside.find("\n", match.end())
        line = mapper._fold(outside[line_start:line_end if line_end >= 0 else len(outside)])
        if investor_core and "cong ty" in line and investor_core not in _core_name(line):
            continue
        out.append(code)
    return out


def _address_detail(value) -> str:
    if isinstance(value, dict):
        return _compact(value.get("chiTietDuoiXa") or value.get("diaChi") or value.get("chiTiet") or "")
    return _compact(value)


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


def drop_contractor_contacts(raw_fields, documents: list[dict]) -> dict:
    fields = _as_dict(raw_fields)
    investor = fields.get("ChuDauTu_Ten") or ""
    addresses, phones, contractor_taxes, outside = _contractor_contacts(documents, investor)

    detail = _address_detail(fields.get("ChuDauTu_DiaChi"))
    if len(detail) >= 6 and detail not in _compact(outside) and any(detail in a or a in detail for a in addresses):
        fields.pop("ChuDauTu_DiaChi", None)

    phone = mapper._phone(fields.get("ChuDauTu_DienThoai"))
    if phone and phone in phones and phone not in re.sub(r"[\s.]", "", outside):
        fields.pop("ChuDauTu_DienThoai", None)

    own_taxes = _investor_tax_codes(outside, investor)
    tax = mapper._digits(fields.get("ChuDauTu_MaSoThue"))
    if tax and tax in contractor_taxes and tax not in own_taxes:
        fields.pop("ChuDauTu_MaSoThue", None)
        tax = None
    if not tax and own_taxes:
        fields["ChuDauTu_MaSoThue"] = own_taxes[0]
    return fields


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
        compact_field_fallback=drop_contractor_contacts,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
