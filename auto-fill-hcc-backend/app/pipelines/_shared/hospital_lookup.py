"""Tra cuu phuong/xa + tinh cua co so y te tu ten benh vien/phong kham.

Cach dung:
    from app.pipelines._shared.hospital_lookup import lookup_hospital

    area = lookup_hospital("Bệnh viện Đa khoa tỉnh Lâm Đồng")
    # -> {"xa": "Phường Cam Ly", "tinh": "Tỉnh Lâm Đồng"}

    area = lookup_hospital("BV da khoa lam dong")   # fold, khong phan biet dau
    # -> {"xa": "Phường Cam Ly", "tinh": "Tỉnh Lâm Đồng"}

Cach them tinh moi:
    Tao file JSON ten bv_<ten_tinh>.json trong thu muc _shared/data_bv/.
    Module tu load tat ca file bv_*.json luc khoi dong.

Cau truc moi entry JSON:
    {
        "ten":  "Bệnh viện Đa khoa tỉnh Lâm Đồng",
        "xa":   "Phường Cam Ly",
        "tinh": "Tỉnh Lâm Đồng"
    }

Co che so khop:
    - Buoc 1 (chinh xac): fold(ten_lookup) == fold(ten_trong_bang) → khop 100%.
    - Buoc 2 (mo rong):   fold(ten_lookup) la CHUOI CON cua fold(ten_trong_bang)
      hoac nguoc lai → lay ket qua dau tien tim duoc (co the nhieu benh vien khop,
      uu tien entry ngan hon de tranh khop nham).
    Tra ve None neu khong tim thay.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Load tat ca file bv_*.json trong thu muc data_bv/
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent / "data_bv"

# Lookup list: [{"ten_folded": ..., "xa": ..., "tinh": ...}, ...]
_HOSPITALS: list[dict] = []


def _fold(text: str) -> str:
    """Bo dau, lowercase, chuan hoa khoang trang -- dung de so sanh."""
    t = unicodedata.normalize("NFD", str(text or ""))
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    t = t.replace("\u0110", "D").replace("\u0111", "d")
    return re.sub(r"\s+", " ", t).strip().lower()


# Viet tat hay gap tren Giay chung sinh / to khai (da fold). Thu tu quan trong: cum dai truoc cum ngan.
# "tttytkv" la loi go/OCR thua mot chu T cua "ttytkv" — van gap that tren ho so.
_ABBREVIATIONS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bt{2,3} ?yt ?kv\b"), "trung tam y te khu vuc"),
    (re.compile(r"\bt{2,3} ?yt\b"), "trung tam y te"),
    (re.compile(r"\bbv ?dk\b"), "benh vien da khoa"),
    (re.compile(r"\bpk ?dk\b"), "phong kham da khoa"),
    (re.compile(r"\bbv\b"), "benh vien"),
    (re.compile(r"\btyt\b"), "tram y te"),
    (re.compile(r"\bkv\b"), "khu vuc"),
]


def _normalize(text: str) -> str:
    """Fold + bo dau cau + mo rong viet tat: "TTYTKV Đơn Dương" == "Trung tâm Y tế khu vực Đơn Dương"."""
    t = re.sub(r"[^a-z0-9]+", " ", _fold(text)).strip()
    for pattern, full in _ABBREVIATIONS:
        t = pattern.sub(full, t)
    return t


def _load_hospital_files() -> None:
    """Load tat ca bv_*.json va build lookup list."""
    if not _DATA_DIR.exists():
        return
    for json_file in sorted(_DATA_DIR.glob("bv_*.json")):
        try:
            with open(json_file, encoding="utf-8-sig") as f:
                entries: list[dict] = json.load(f)
        except Exception as e:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).warning(
                "hospital_lookup: cannot load %s -- %s", json_file, e
            )
            continue

        for entry in entries:
            ten = entry.get("ten") or ""
            xa = entry.get("xa") or ""
            tinh = entry.get("tinh") or ""
            if not ten or not xa or not tinh:
                continue
            _HOSPITALS.append({
                "ten_folded": _normalize(ten),
                "xa": xa,
                "tinh": tinh,
            })


_load_hospital_files()  # chay 1 lan luc import


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lookup_hospital(name: Optional[str]) -> Optional[dict]:
    """Tra cuu xa + tinh tu ten co so y te.

    Tra ve {"xa": ..., "tinh": ...} neu tim thay, None neu khong.

    So khop theo thu tu uu tien:
      1. Khop chinh xac (fold bang nhau).
      2. Khop mo rong: ten lookup nam trong ten bang HOAC ten bang nam trong ten lookup
         (xu ly truong hop OCR thieu/thua chu). Lay entry khop ngan nhat (it nham nhat).
    """
    if not name:
        return None

    needle = _normalize(name)
    if not needle:
        return None

    # Buoc 1: chinh xac
    for h in _HOSPITALS:
        if h["ten_folded"] == needle:
            return {"xa": h["xa"], "tinh": h["tinh"]}

    # Buoc 2: mo rong (chuoi con)
    # Giu ca hai huong: needle ⊂ ten_bang (OCR lay du hon) va ten_bang ⊂ needle (OCR lay thieu)
    candidates: list[dict] = []
    for h in _HOSPITALS:
        if needle in h["ten_folded"] or h["ten_folded"] in needle:
            candidates.append(h)

    if not candidates:
        return None

    # Uu tien entry co ten ngan nhat (tranh khop qua rong, vd "benh vien" khop nhieu noi)
    best = min(candidates, key=lambda h: len(h["ten_folded"]))
    return {"xa": best["xa"], "tinh": best["tinh"]}


def reload() -> None:
    """Reload tat ca file JSON (dung khi hot-reload trong development)."""
    _HOSPITALS.clear()
    _load_hospital_files()
