"""Normalize don vi hanh chinh cu -> moi theo cac dot sap nhap.

Cach dung:
    from app.pipelines._shared.area_remap import remap_area

    area = {"quocGia": "Viet Nam", "tinh": "Binh Thuan", "xa": "Ham Kiem", "diaChi": "To 3"}
    area = remap_area(area)
    # -> {"quocGia": "Viet Nam", "tinh": "Lam Dong", "xa": "Xa Ham Kiem", "diaChi": "To 3"}

Cach them tinh moi:
    Tao file JSON ten remap_<ten_tinh>.json trong cung thu muc _shared/data/.
    Module tu load tat ca file remap_*.json luc khoi dong.

Cau truc moi entry JSON:
    {
        "tinh_cu":  "Binh Thuan",
        "xa_cu":    "Ham Kiem",
        "tinh_moi": "Lam Dong",
        "xa_moi":   "Xa Ham Kiem",
        "ghi_chu":  "..."
    }

Luu y ambiguous:
    Mot so don vi cung ten ton tai o nhieu huyen trong cung tinh cu.
    Nhung entry nay duoc danh dau "ambiguous": true trong JSON --
    module se BO QUA chung khi tra cuu, tranh mapping sai.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Load tat ca file remap_*.json trong thu muc data/
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent / "data"

# Lookup dict: (fold(tinh_cu), fold(xa_cu)) -> {"tinh": ..., "xa": ...}
_REMAP: dict[tuple[str, str], dict[str, str]] = {}


def _fold(text: str) -> str:
    """Bo dau, lowercase, chuan hoa khoang trang -- dung de so sanh key."""
    t = unicodedata.normalize("NFD", str(text or ""))
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    t = t.replace("\u0110", "D").replace("\u0111", "d")
    # Bo tien to loai don vi truoc khi fold (xa/phuong/thi tran/tt)
    t = re.sub(r"^(xa|phuong|thi tran|tt\.?)\s+", "", t, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip().lower()


def _load_remap_files() -> None:
    """Load tat ca remap_*.json va build lookup dict."""
    if not _DATA_DIR.exists():
        return
    for json_file in sorted(_DATA_DIR.glob("remap_*.json")):
        try:
            with open(json_file, encoding="utf-8-sig") as f:
                entries: list[dict] = json.load(f)
        except Exception as e:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).warning("area_remap: cannot load %s -- %s", json_file, e)
            continue

        for entry in entries:
            # Bo qua entry ambiguous
            if entry.get("ambiguous"):
                continue
            tinh_cu = entry.get("tinh_cu") or ""
            xa_cu   = entry.get("xa_cu") or ""
            if not tinh_cu or not xa_cu:
                continue
            key = (_fold(tinh_cu), _fold(xa_cu))
            # Uu tien entry dau tien, khong ghi de
            if key not in _REMAP:
                _REMAP[key] = {
                    "tinh": entry.get("tinh_moi") or tinh_cu,
                    "xa":   entry.get("xa_moi")   or xa_cu,
                }


_load_remap_files()  # chay 1 lan luc import


# ---------------------------------------------------------------------------
# Bang: thanh pho/thi xa thuoc tinh -> ten tinh chinh thuc
# LLM doi khi tra "tinh" = ten thanh pho thuoc tinh (vd "Da Lat") thay vi ten tinh ("Lam Dong").
# Bang nay normalize truoc khi lookup remap xa.
# ---------------------------------------------------------------------------
_CITY_TO_PROVINCE: dict[str, str] = {
    # Lâm Đồng
    "da lat":        "Lâm Đồng",
    "bao loc":       "Lâm Đồng",
    # Đắk Lắk
    "buon ma thuot": "Đắk Lắk",
    "buon ho":       "Đắk Lắk",
    # Đắk Nông
    "gia nghia":     "Đắk Nông",
    # Bình Thuận
    "phan thiet":    "Bình Thuận",
    "la gi":         "Bình Thuận",
    # Quảng Nam
    "tam ky":        "Quảng Nam",
    "hoi an":        "Quảng Nam",
    # Quảng Trị
    "dong ha":       "Quảng Trị",
    "quang tri":     "Quảng Trị",   # thị xã Quảng Trị cũ
    # Thừa Thiên Huế (nay là TP Huế trực thuộc TW)
    "hue":           "Huế",
    # Bắc Ninh
    "bac ninh":      "Bắc Ninh",
    "tu son":        "Bắc Ninh",
    # Bắc Giang
    "bac giang":     "Bắc Giang",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def remap_area(area: Optional[dict]) -> Optional[dict]:
    """Nhan object dia chi {quocGia, tinh, xa, diaChi}, tra ve da normalize.

    Buoc 1: neu "tinh" la thanh pho/thi xa thuoc tinh (vd "Da Lat") -> doi sang ten tinh (vd "Lam Dong").
    Buoc 2: neu (tinh, xa) co trong bang sap nhap -> thay bang ten don vi moi.
    Neu khong co entry nao -> giu nguyen (pass-through).
    """
    if not area or not isinstance(area, dict):
        return area

    tinh_raw: str = area.get("tinh") or ""
    xa_raw:   str = area.get("xa")   or ""

    if not tinh_raw and not xa_raw:
        return area

    # Buoc 1: normalize thanh pho thuoc tinh -> ten tinh
    tinh_normalized = _CITY_TO_PROVINCE.get(_fold(tinh_raw))
    if tinh_normalized:
        area = {**area, "tinh": tinh_normalized}
        tinh_raw = tinh_normalized

    # Buoc 2: lookup bang sap nhap (tinh, xa)
    key = (_fold(tinh_raw), _fold(xa_raw))
    mapping = _REMAP.get(key)
    if mapping:
        return {**area, "tinh": mapping["tinh"], "xa": mapping["xa"]}

    return area


def reload() -> None:
    """Reload tat ca file JSON (dung khi hot-reload trong development)."""
    _REMAP.clear()
    _load_remap_files()
