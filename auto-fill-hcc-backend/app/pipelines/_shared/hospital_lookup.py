"""Tra cuu phuong/xa + tinh cua co so y te tu ten benh vien/phong kham.

Cach dung:
    from app.pipelines._shared.hospital_lookup import lookup_hospital

    area = lookup_hospital("Bệnh viện Đa khoa tỉnh Lâm Đồng")
    # -> {"xa": "Phường Cam Ly - Đà Lạt", "tinh": "Tỉnh Lâm Đồng"}

    area = lookup_hospital("BV da khoa lam dong")   # fold, khong phan biet dau
    # -> {"xa": "Phường Cam Ly - Đà Lạt", "tinh": "Tỉnh Lâm Đồng"}

Cach them tinh moi:
    Tao file JSON ten bv_<ten_tinh>.json trong thu muc _shared/data_bv/.
    Module tu load tat ca file bv_*.json luc khoi dong.

Cau truc moi entry JSON:
    {
        "ten":  "Bệnh viện Đa khoa tỉnh Lâm Đồng",
        "xa":   "Phường Cam Ly - Đà Lạt",
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
from functools import lru_cache
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


# Tu chung chung cua ten co so y te + don vi hanh chinh: chuoi tra chi con cac tu nay thi khong du
# de nhan ra benh vien nao.
_GENERIC_WORDS = re.compile(
    r"\b(benh vien|da khoa|trung tam y te|tram y te|phong kham|nha ho sinh|khu vuc|tinh|thanh pho|"
    r"huyen|quan|thi xa|phuong|xa|so|co so|tp)\b"
)


def _province_key(tinh: Optional[str]) -> str:
    """"Tỉnh Lâm Đồng" / "Lâm Đồng" -> "lam dong"."""
    return re.sub(r"^(tinh|thanh pho|tp)\s+", "", re.sub(r"[^a-z0-9]+", " ", _fold(tinh)).strip())


@lru_cache(maxsize=1)
def _old_to_new_province() -> dict[str, str]:
    """Khoa tinh cu (truoc 1/7/2025) -> khoa tinh hien hanh: "quang binh" -> "quang tri"."""
    try:
        from app.pipelines._shared.area_remap import _TINH_ONLY
    except Exception:  # noqa: BLE001
        return {}
    return {_province_key(cu): _province_key(moi) for cu, moi in _TINH_ONLY.items()}


def _current_province_key(tinh: Optional[str]) -> str:
    """Khoa tinh HIEN HANH cua tinh ghi tren giay; tinh cu quy ve tinh moi. Khong nhan ra -> ""."""
    key = _province_key(tinh)
    if not key:
        return ""
    try:
        from app.pipelines._shared.area_remap import canonical_province
        name = canonical_province(tinh)
    except Exception:  # noqa: BLE001
        name = None
    return _province_key(name) if name else _old_to_new_province().get(key, "")


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

def lookup_hospital(name: Optional[str], tinh: Optional[str] = None) -> Optional[dict]:
    """Tra cuu xa + tinh tu ten co so y te.

    Tra ve {"xa": ..., "tinh": ...} neu tim thay, None neu khong.

    So khop theo thu tu uu tien:
      1. Khop chinh xac (fold bang nhau).
      2. Khop mo rong: ten lookup nam trong ten bang HOAC ten bang nam trong ten lookup
         (xu ly truong hop OCR thieu/thua chu). Lay entry khop ngan nhat (it nham nhat).
      3. Khop theo tu rieng cua ten (giay ghi tat). `tinh` (neu co) phai trung tinh cua benh vien.
    `tinh` nhan ra duoc (ke ca tinh cu, vd "Quang Binh" -> Quang Tri) thi buoc 1-3 chi so voi benh vien
    cua tinh do: nhieu ten trung giua cac tinh ("Benh vien Da khoa Bac Thang Long" o Luc Ngan lan Dong
    Anh, "Benh vien Phu san" tron, "Benh vien Xay dung" o Ha Noi lan Viet Tri).
    """
    if not name:
        return None

    needle = _normalize(name)
    if not needle:
        return None

    current = _current_province_key(tinh)
    hospitals = [h for h in _HOSPITALS if _province_key(h["tinh"]) == current] if current else _HOSPITALS

    # Buoc 1: chinh xac
    for h in hospitals:
        if h["ten_folded"] == needle:
            return {"xa": h["xa"], "tinh": h["tinh"]}

    # Buoc 2: ten_bang nam tron trong needle (giay ghi them so nha/duong/tinh sau ten benh vien,
    # vd "Benh vien da khoa tinh Lam Dong So 01 Pham Ngoc Thach"). Lay ten DAI nhat = cu the nhat
    # ("... so 2", "... co so 2" thang ten goc).
    padded = f" {needle} "
    contained = [h for h in hospitals if f" {h['ten_folded']} " in padded]
    if contained:
        best = max(contained, key=lambda h: len(h["ten_folded"]))
        return {"xa": best["xa"], "tinh": best["tinh"]}

    # Buoc 3: needle nam trong ten_bang (OCR lay thieu chu). Needle chi gom tu chung chung
    # ("benh vien da khoa tinh") khop qua nhieu noi → bo. Lay entry ngan nhat (it nham nhat).
    if not _GENERIC_WORDS.sub(" ", needle).strip():
        return None
    candidates = [h for h in hospitals if f" {needle} " in f" {h['ten_folded']} "]
    if candidates:
        best = min(candidates, key=lambda h: len(h["ten_folded"]))
        return {"xa": best["xa"], "tinh": best["tinh"]}

    # Buoc 4: giay ghi tat ten benh vien ("Benh vien Hoan My", "BV Hoan My - TP Da Lat" cho "Benh vien
    # Da khoa Hoan My Da Lat"): moi tu rieng cua needle deu co trong ten bang. Ten tat de trung chuoi
    # benh vien cung ten o tinh khac (Hoan My co o nhieu tinh) → biet tinh thi phai cung tinh, va chi
    # nhan khi khop DUNG MOT benh vien.
    words = set(_GENERIC_WORDS.sub(" ", needle).split())
    province = current or _province_key(tinh)
    matches = [
        h for h in hospitals
        if words <= set(h["ten_folded"].split()) and (not province or _province_key(h["tinh"]) == province)
    ]
    if len(matches) != 1:
        return None
    return {"xa": matches[0]["xa"], "tinh": matches[0]["tinh"]}


def hospital_area(area: Optional[dict]) -> Optional[dict]:
    """Noi sinh la co so y te CO trong bang → xa/phuong lay theo bang, ke ca khi giay da ghi xa khac.

    To khai viet tay hay bi OCR doc sai ten xa (vd "Phuong Can Lu"), con ten benh vien thi doc dung;
    biet benh vien la biet dung xa. Tinh chi bu khi giay bo trong. Khong nhan ra benh vien → giu nguyen.
    """
    if not isinstance(area, dict):
        return area
    hospital = lookup_hospital(
        area.get("diaChi") or area.get("dia_chi") or area.get("diachi"),
        area.get("tinh"),
    )
    if not hospital:
        return area
    return {**area, "xa": hospital["xa"], "tinh": area.get("tinh") or hospital["tinh"]}


def reload() -> None:
    """Reload tat ca file JSON (dung khi hot-reload trong development)."""
    _HOSPITALS.clear()
    _old_to_new_province.cache_clear()
    _load_hospital_files()
