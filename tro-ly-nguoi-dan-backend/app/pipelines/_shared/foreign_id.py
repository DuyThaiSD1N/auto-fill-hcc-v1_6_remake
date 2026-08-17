"""Lookup giấy tờ tùy thân nước ngoài từ file foreign_id_map.json.

Cách dùng:
    from app.pipelines._shared.foreign_id import normalize_nationality, normalize_id_type, normalize_foreign_tinh

    normalize_nationality("Cong hoa nhan dan Trung Hoa")  → "Trung Quốc"
    normalize_nationality(None)                            → "Việt Nam"   (default)
    normalize_id_type("Chung minh thu")                   → "Hộ chiếu (CMND nước ngoài)"
    normalize_foreign_tinh("Trung Quốc", "Van Nam")       → "Vân Nam"

Thêm quốc gia / loại giấy tờ mới: chỉ cần chỉnh file
    app/pipelines/_shared/data/foreign_id_map.json
không cần sửa code Python.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from functools import lru_cache

_DATA_FILE = Path(__file__).parent / "data" / "foreign_id_map.json"


@lru_cache(maxsize=1)
def _load() -> dict:
    """Load bảng mapping (cache sau lần đầu)."""
    try:
        return json.loads(_DATA_FILE.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return {}


def _fold(text: str) -> str:
    """Bỏ dấu, lowercase, chuẩn hoá khoảng trắng — dùng để so sánh key."""
    t = unicodedata.normalize("NFD", str(text or ""))
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", t.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _lookup(section: str, raw: str) -> str | None:
    """Tra bảng section (exact match trước, partial match sau)."""
    table: dict = _load().get(section, {})
    key = _fold(raw)
    # 1. Exact match
    if key in table:
        return table[key]
    # 2. Partial match: key chứa entry hoặc ngược lại
    for k, v in table.items():
        if k in key or key in k:
            return v
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_nationality(raw: str | None, default: str = "Việt Nam") -> str:
    """Chuẩn hóa tên quốc tịch OCR → tên chính thức trong dropdown.

    Trả default khi raw rỗng hoặc không nhận ra.
    """
    if not raw or not str(raw).strip():
        return default
    result = _lookup("quoc_tich", raw)
    return result if result else str(raw).strip()


def normalize_id_type(raw: str | None) -> str | None:
    """Chuẩn hóa loại giấy tờ tùy thân nước ngoài → tên trong dropdown.

    Trả None nếu không nhận ra (để pipeline tự xử lý).
    """
    if not raw or not str(raw).strip():
        return None
    return _lookup("loai_giay_to", raw)


def normalize_foreign_tinh(quoc_tich: str, tinh_raw: str | None) -> str | None:
    """Chuẩn hóa tên tỉnh/vùng của nước ngoài → tên hiển thị.

    Trả nguyên tinh_raw nếu không có trong bảng (giữ nguyên tên OCR).
    """
    if not tinh_raw:
        return tinh_raw
    tinh_table: dict = _load().get("tinh_nuoc_ngoai", {}).get(quoc_tich, {})
    key = _fold(tinh_raw)
    return tinh_table.get(key, tinh_raw)


def is_foreign(quoc_tich: str) -> bool:
    """Kiểm tra quốc tịch có phải nước ngoài (khác Việt Nam) không."""
    return _fold(quoc_tich) not in ("viet nam", "vietnam", "vn", "")


def reload() -> None:
    """Reload file JSON (dùng khi hot-reload trong development)."""
    _load.cache_clear()
