"""Khóa ghép ổn định hai trải nghiệm vào cùng dòng báo cáo đơn vị."""
import unicodedata

from app.core.errors import AppError
from app.locations.catalog import canonical_location
from app.reports.procedure_meta import ma_thu_tuc


def fold(value: str | None) -> str:
    raw = str(value or "").replace("Đ", "D").replace("đ", "d")
    return " ".join(
        "".join(
            char
            for char in unicodedata.normalize("NFD", raw)
            if unicodedata.category(char) != "Mn"
        ).casefold().split()
    )


def province_name(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        canonical, _ = canonical_location(raw, None)
        return canonical or raw
    except AppError:
        return raw


def unit_key(province: str | None, ward: str | None) -> str:
    """Gộp nhiều tài khoản cùng xã/phường vào một dòng báo cáo hành chính."""
    return f"{fold(province_name(province))}::{fold(ward)}"


def canonical_procedure_id(key: str, entry: dict | None) -> str:
    code = ma_thu_tuc(entry)
    return f"tthc:{code}" if code and code != "—" else f"key:{key}"
