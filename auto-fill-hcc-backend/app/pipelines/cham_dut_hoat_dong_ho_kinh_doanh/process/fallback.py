"""Bù các mốc tất định mà LLM đôi khi bỏ sót trong hồ sơ chấm dứt HKD."""

from __future__ import annotations

import re
from typing import Any


_EMPTY = (None, "", {}, [])


def _as_dict(raw_fields: Any) -> dict[str, Any]:
    if isinstance(raw_fields, dict):
        return dict(raw_fields)
    if isinstance(raw_fields, list):
        return {
            item.get("name"): item.get("value")
            for item in raw_fields
            if isinstance(item, dict) and item.get("name")
        }
    return {}


def _match(text: str, pattern: str) -> str:
    found = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    return " ".join((found.group(1) if found else "").split()).strip(" :-/")


def _address(text: str) -> dict[str, str] | None:
    found = re.search(
        r"(?:Nơi thường trú|Nơi cư trú)\s*/\s*Place of residence\s*:\s*(.+?)"
        r"(?=\n\s*(?:Có giá trị|Date of expiry|Đặc điểm nhân dạng|Personal identification|Ngày, tháng, năm))",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not found:
        return None
    lines = [" ".join(line.split()).strip(" ,") for line in found.group(1).splitlines() if line.strip()]
    if not lines:
        return None

    region = [part.strip() for part in lines[-1].split(",") if part.strip()]
    if len(lines) > 1 and len(region) >= 2:
        detail = ", ".join(lines[:-1])
        commune = region[0]
        province = region[-1]
    else:
        parts = [part.strip() for part in lines[0].split(",") if part.strip()]
        province = parts[-1] if parts else ""
        commune = parts[-3] if len(parts) >= 3 else (parts[0] if len(parts) == 2 else "")
        detail = ", ".join(parts[:-3] if len(parts) >= 3 else [])
    return {
        "quocGia": "Việt Nam",
        "tinh": province,
        "xa": commune,
        "diaChi": detail,
    }


def _physical_cccd(text: str) -> dict[str, Any] | None:
    if not re.search(r"CĂN CƯỚC CÔNG DÂN|Citizen Identity Card|THẺ CĂN CƯỚC", text, re.IGNORECASE):
        return None
    identity = re.sub(r"\D", "", _match(text, r"(?:Số\s*/\s*No\.?|Số)\s*:\s*([0-9 ]{9,20})"))
    name = _match(text, r"(?:Họ và tên\s*/\s*Full name|Họ và tên|Full name)\s*:?\s*\n?([^\n]+)")
    if not identity or not name:
        return None
    issued_dates = re.findall(
        r"Ngày, tháng, năm(?:\s*/\s*Date, month, year)?\s*:\s*(\d{1,2}/\d{1,2}/\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    person: dict[str, Any] = {
        "hoTen": name,
        "soDinhDanh": identity,
        "ngaySinh": _match(text, r"Ngày sinh\s*/\s*Date of birth\s*:\s*(\d{1,2}/\d{1,2}/\d{4})"),
        "gioiTinh": _match(text, r"Giới tính\s*/\s*Sex\s*:\s*([^\n]+?)(?:\s+Quốc tịch|\s+Nationality|$)"),
        "ngayCap": issued_dates[-1] if issued_dates else "",
        "noiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        "diaChi": _address(text),
    }
    return {key: value for key, value in person.items() if value not in _EMPTY}


def apply_ocr_fallback(raw_fields: Any, documents: list[dict]) -> dict[str, Any]:
    """Chỉ bù nhãn rõ trên thẻ vật lý/Thông báo; không tự gán CCCD thành người nộp."""
    fields = _as_dict(raw_fields)
    texts = [str(item.get("text") or "") for item in documents]

    if fields.get("HoKinhDoanh_MaSo") in _EMPTY:
        for text in texts:
            value = re.sub(r"\D", "", _match(text, r"Mã số hộ kinh doanh\s*:\s*([0-9 .-]{6,})"))
            if value:
                fields["HoKinhDoanh_MaSo"] = value
                break

    existing = fields.get("Cccd_DanhSach") if isinstance(fields.get("Cccd_DanhSach"), list) else []
    cards = [dict(item) for item in existing if isinstance(item, dict)]
    seen = {re.sub(r"\D", "", str(item.get("soDinhDanh") or "")) for item in cards}
    for text in texts:
        card = _physical_cccd(text)
        identity = re.sub(r"\D", "", str((card or {}).get("soDinhDanh") or ""))
        if card and identity not in seen:
            cards.append(card)
            seen.add(identity)
    if cards:
        fields["Cccd_DanhSach"] = cards
    return fields
