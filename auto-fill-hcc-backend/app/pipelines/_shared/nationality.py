"""Chuẩn hóa tên quốc tịch OCR → tên chính thức khớp option dropdown cổng dịch vụ công."""

from __future__ import annotations
import re
import unicodedata


def _fold(text: str) -> str:
    t = unicodedata.normalize("NFD", str(text or ""))
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", t.replace("Đ", "D").replace("đ", "d")).strip().lower()


_MAP: dict[str, str] = {
    "viet nam": "Việt Nam",
    "vietnam": "Việt Nam",
    "vn": "Việt Nam",
    # Trung Quốc
    "trung quoc": "Trung Quốc",
    "cong hoa nhan dan trung hoa": "Trung Quốc",
    "cong hoa nhan dan trung quoc": "Trung Quốc",
    "trung hoa": "Trung Quốc",
    "china": "Trung Quốc",
    "chinese": "Trung Quốc",
    "prc": "Trung Quốc",
    # Lào
    "lao": "Lào",
    "nuoc cong hoa dan chu nhan dan lao": "Lào",
    "laos": "Lào",
    # Campuchia
    "campuchia": "Campuchia",
    "cambodia": "Campuchia",
    "vuong quoc campuchia": "Campuchia",
    # Hàn Quốc
    "han quoc": "Hàn Quốc",
    "korea": "Hàn Quốc",
    "south korea": "Hàn Quốc",
    # Nhật Bản
    "nhat ban": "Nhật Bản",
    "japan": "Nhật Bản",
    # Đài Loan
    "dai loan": "Đài Loan",
    "taiwan": "Đài Loan",
    # Mỹ
    "my": "Hoa Kỳ",
    "hoa ky": "Hoa Kỳ",
    "usa": "Hoa Kỳ",
    "united states": "Hoa Kỳ",
    # Pháp
    "phap": "Pháp",
    "france": "Pháp",
    # Đức
    "duc": "Đức",
    "germany": "Đức",
    # Úc
    "uc": "Úc",
    "australia": "Úc",
    # Anh
    "anh": "Anh",
    "united kingdom": "Anh",
    "uk": "Anh",
    # Canada
    "canada": "Canada",
    # Nga
    "nga": "Nga",
    "russia": "Nga",
    # Thái Lan
    "thai lan": "Thái Lan",
    "thailand": "Thái Lan",
    # Myanmar
    "myanmar": "Myanmar",
    # Philippines
    "philippines": "Philippines",
    # Indonesia
    "indonesia": "Indonesia",
    # Malaysia
    "malaysia": "Malaysia",
    # Singapore
    "singapore": "Singapore",
    # Ấn Độ
    "an do": "Ấn Độ",
    "india": "Ấn Độ",
}


def normalize_nationality(raw: str | None, default: str = "Việt Nam") -> str:
    """Chuẩn hóa tên quốc tịch OCR → tên chính thức.

    Trả default ("Việt Nam") khi raw rỗng hoặc không nhận ra.
    """
    if not raw or not str(raw).strip():
        return default
    key = _fold(raw)
    # Exact match trước
    mapped = _MAP.get(key)
    if mapped:
        return mapped
    # Partial match: "cong hoa nhan dan trung hoa" chứa "trung hoa"
    for k, v in _MAP.items():
        if k in key or key in k:
            return v
    return str(raw).strip()
