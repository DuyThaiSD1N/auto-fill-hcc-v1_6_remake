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
from functools import lru_cache
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Load tat ca file remap_*.json trong thu muc data/
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent / "data"

# Lookup dict: (fold(tinh_cu), fold(xa_cu)) -> {"tinh": ..., "xa": ...}
_REMAP: dict[tuple[str, str], dict[str, str]] = {}

# Lookup d\u1ef1 ph\u00f2ng: (fold(tinh_cu), fold(xa_cu) \u0111\u00e3 B\u1ece H\u1ebeT kho\u1ea3ng tr\u1eafng) -> {"tinh": ..., "xa": ...}.
# OCR/LLM \u0111\u00f4i khi tr\u1ea3 t\u00ean x\u00e3 vi\u1ebft d\u00ednh li\u1ec1n (vd "langbiang" thay v\u00ec "Lang Biang") -> exact-fold
# lookup \u1edf _REMAP tr\u01b0\u1ee3t v\u00ec c\u00f2n kho\u1ea3ng tr\u1eafng kh\u00e1c nhau. Bang nay khop bat chap khoang trang.
_REMAP_NOSPACE: dict[tuple[str, str], dict[str, str]] = {}

# Lookup CH\u1ec8 THEO T\u1ec8NH: fold(tinh_cu) -> tinh_moi. D\u00f9ng khi x\u00e3 kh\u00f4ng kh\u1edbp \u0111\u01b0\u1ee3c entry n\u00e0o (t\u00ean
# \u0111\u1ecdc sai/kh\u00f4ng c\u00f3 trong b\u1ea3ng) NH\u01afNG t\u1ec9nh c\u0169 \u0111\u00e3 bi\u1ebft ch\u1eafc \u0111\u1ed5i t\u00ean qua s\u00e1p nh\u1eadp -- v\u1eabn \u0111i\u1ec1n \u0111\u00fang
# t\u1ec9nh m\u1edbi, kh\u00f4ng gi\u1eef t\u1ec9nh c\u0169 (ch\u1eafc ch\u1eafn kh\u00f4ng c\u00f2n trong danh m\u1ee5c hi\u1ec7n h\u00e0nh -> ch\u1ecdn dropdown s\u1ebd
# l\u1ed7i). Ch\u1ec9 c\u00f3 entry cho t\u1ec9nh TH\u1ef0C S\u1ef0 xu\u1ea5t hi\u1ec7n trong b\u1ea3ng remap (\u0111\u00e3 \u0111\u1ed5i t\u00ean); t\u1ec9nh ch\u01b0a t\u1eebng \u0111\u1ed5i
# th\u00ec kh\u00f4ng c\u00f3 \u1edf \u0111\u00e2y -> h\u00e0nh vi gi\u1eef nguy\u00ean nh\u01b0 c\u0169, kh\u00f4ng \u0111\u1ee5ng v\u00e0o x\u00e3 h\u1ee3p l\u1ec7 ch\u01b0a c\u1ea7n remap.
_TINH_ONLY: dict[str, str] = {}


def _fold(text: str) -> str:
    """Bo dau, lowercase, chuan hoa khoang trang -- dung de so sanh key."""
    t = unicodedata.normalize("NFD", str(text or ""))
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    t = t.replace("\u0110", "D").replace("\u0111", "d")
    # Bo tien to loai don vi truoc khi fold (xa/phuong/thi tran/tt)
    t = re.sub(r"^(xa|phuong|thi tran|tt\.?)\s+", "", t, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip().lower()


def _fold_nospace(text: str) -> str:
    """_fold() roi bo luon khoang trang -- dung de khop ten xa viet dinh lien (vd "langbiang")."""
    return _fold(text).replace(" ", "")


def _expand_abbrev(text: str) -> str:
    """Mo rong viet tat phuong/xa truoc khi lookup.

    P9 / P.9 / P 9 → Phường 9
    X5 / X.5       → Xã 5
    Giu nguyen neu khong khop mau viet tat.
    """
    t = text.strip()
    # P<so> hoac P.<so> hoac P <so> (ca hoa lan thuong)
    m = re.fullmatch(r"[Pp]\.?\s*(\d+)", t)
    if m:
        return f"Phường {m.group(1)}"
    # X<so> hoac X.<so>
    m = re.fullmatch(r"[Xx]\.?\s*(\d+)", t)
    if m:
        return f"Xã {m.group(1)}"
    return t


def _load_remap_files() -> None:
    """Load tat ca remap_*.json va build lookup dict."""
    if not _DATA_DIR.exists():
        return
    
    # Track duplicate keys to mark as ambiguous
    _duplicate_tracker: dict[tuple[str, str], list[dict]] = {}
    
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
            mapping = {
                "tinh": entry.get("tinh_moi") or tinh_cu,
                "xa":   entry.get("xa_moi")   or xa_cu,
            }
            
            # Track all entries for this key to detect duplicates
            if key not in _duplicate_tracker:
                _duplicate_tracker[key] = []
            _duplicate_tracker[key].append(mapping)
    
    # Only add entries that are NOT duplicates (or are marked ambiguous)
    for key, mappings in _duplicate_tracker.items():
        # If there are multiple different mappings for the same key, skip them all (ambiguous)
        unique_mappings = {(m["tinh"], m["xa"]) for m in mappings}
        if len(unique_mappings) > 1:
            # Multiple different destinations for same source -> ambiguous, skip
            import logging
            logging.getLogger(__name__).info(
                "area_remap: skipping ambiguous entry %s -> %s (multiple mappings found)",
                key, unique_mappings
            )
            continue
        
        # Single mapping or all duplicates point to same destination -> safe to use
        mapping = mappings[0]
        _REMAP[key] = mapping
        
        tinh_cu_folded, xa_cu_folded = key
        key_nospace = (tinh_cu_folded, xa_cu_folded.replace(" ", ""))
        if key_nospace not in _REMAP_NOSPACE:
            _REMAP_NOSPACE[key_nospace] = mapping
        
        if tinh_cu_folded not in _TINH_ONLY:
            _TINH_ONLY[tinh_cu_folded] = mapping["tinh"]


_load_remap_files()  # chay 1 lan luc import


# ---------------------------------------------------------------------------
# Bang tra ten xa/phuong HIEN HANH (khong can remap) da bo khoang trang -- dung khi
# OCR/LLM tra ten xa dinh lien nhung do CHINH LA ten xa MOI (khong nam trong bang remap
# o tren, vi khong bi doi ten qua sap nhap). Vd "langbiang" (tinh "Lam Dong") -> "Phường
# Lang Biang - Đà Lạt". Xay dung tu danh muc hanh chinh hien hanh (app.locations.catalog).
# ---------------------------------------------------------------------------
_CURRENT_WARD_NOSPACE: dict[tuple[str, str], str] = {}


def _build_current_ward_index() -> None:
    try:
        from app.locations.catalog import PROVINCES, WARDS_BY_SLUG
    except Exception as e:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning(
            "area_remap: khong nap duoc danh muc hanh chinh hien hanh -- %s", e
        )
        return
    for province in PROVINCES:
        communes = WARDS_BY_SLUG.get(province["slug"], {}).get("communes") or []
        for ward_full_name in communes:
            # Ten day du, vd "Phường Lang Biang - Đà Lạt" -> bo khoang trang toan bo.
            full_nospace = _fold_nospace(ward_full_name)
            # Phan "loi" truoc hau to "- <thanh pho>" (mot so phuong sau sap nhap co hau to
            # nay), vd "lang biang" tu "Phường Lang Biang - Đà Lạt" -> van khop duoc khi
            # OCR/LLM chi doc "langbiang", khong doc hau to thanh pho.
            core_nospace = _fold(ward_full_name).split(" - ")[0].strip().replace(" ", "")
            for tinh_key in (_fold(province["text"]), _fold(province["name"])):
                for nospace_key in (full_nospace, core_nospace):
                    key = (tinh_key, nospace_key)
                    if key not in _CURRENT_WARD_NOSPACE:
                        _CURRENT_WARD_NOSPACE[key] = ward_full_name


_build_current_ward_index()  # chay 1 lan luc import


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
    # Thừa Thiên Huế → Thành phố Huế trực thuộc TW (từ 01/01/2026)
    "thua thien hue": "Huế",
    "hue":            "Huế",
    "thanh pho hue":  "Huế",
    # Bắc Ninh
    "bac ninh":      "Bắc Ninh",
    "tu son":        "Bắc Ninh",
    # Bắc Giang
    "bac giang":     "Bắc Giang",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _scan_for_xa(text: str, tinh_folded: str) -> Optional[dict]:
    """Scan tung token trong chuoi text de tim xa/phuong hop le trong bang remap.

    Dung khi LLM/OCR gop nhieu cap dia chi vao 1 truong, vi du:
        "Tu Tra - Don Duong"  (thon - xa)
        "Suoi Thong C, Don Duong"  (thon, xa)
        "Rl Lon Tu Tra"  (thon xa viet lien)

    Uu tien token dai nhat khop bang (tranh nham token con).
    """
    if not text:
        return None
    # Tach theo dau phan cach pho bien
    separators = re.compile(r"[\s,;/\-–—]+")
    raw_tokens = [t.strip() for t in separators.split(text) if t.strip()]
    if not raw_tokens:
        return None

    # Thu ghep 1, 2, 3 token lien tiep (de bat ten xa nhieu chu, vd "Nam Ban", "Ka Do")
    candidates: list[tuple[str, str]] = []  # (original_text, folded)
    for length in (3, 2, 1):
        for i in range(len(raw_tokens) - length + 1):
            chunk = " ".join(raw_tokens[i:i + length])
            candidates.append((chunk, _fold(chunk)))

    best_original = None
    best_mapping = None
    best_len = 0
    for original, folded in candidates:
        # Token số đơn lẻ trong địa chỉ thường là số nhà/ngõ (vd "Cò/1 Đồng Tâm"),
        # không đủ chứng cứ để coi là tên phường/xã. Cụm có nhãn "Phường 1" vẫn
        # được giữ vì original còn chứa tiền tố đơn vị hành chính.
        if folded.isdigit() and original.strip() == folded:
            continue
        key = (tinh_folded, folded)
        mapping = _REMAP.get(key) or _REMAP_NOSPACE.get((tinh_folded, folded.replace(" ", "")))
        if mapping and len(folded) > best_len:
            best_original = original
            best_mapping = mapping
            best_len = len(folded)

    return (best_original, best_mapping) if best_mapping else None


@lru_cache(maxsize=1024)
def _remap_area_cached(
    tinh: str,
    xa: str,
    dia_chi: str,
    allow_diachi_fallback: bool,
) -> tuple[str, str, str]:
    """Cached version of remap logic. Returns (tinh_moi, xa_moi, dia_chi_moi)."""
    # Chặn viết tắt tỉnh (LA, LD, LĐ, L.D...) → xóa xa để tránh điền sai.
    if tinh:
        letters_only = re.sub(r"[^a-z0-9]", "", _fold(tinh))
        if len(letters_only) <= 2:
            return (tinh, "", dia_chi)

    # Mở rộng viết tắt phường/xã trước khi lookup: P9 → Phường 9, X5 → Xã 5
    xa_expanded = _expand_abbrev(xa) if xa else xa

    # Khi xa đã có nhãn hành chính rõ, diaChi chỉ là chi tiết địa chỉ.
    xa_has_admin_label = bool(re.match(r"^\s*(xã|phường|thị trấn|tt\.?)\b", xa_expanded, flags=re.IGNORECASE)) if xa_expanded else False

    # Buoc 1: normalize thanh pho thuoc tinh -> ten tinh
    tinh_for_lookup = re.sub(
        r"^\s*(tp|thanh pho|thi xa|tx|city of)\.?\s+",
        "",
        _fold(tinh),
        flags=re.IGNORECASE,
    ).strip() if tinh else ""
    
    tinh_normalized = _CITY_TO_PROVINCE.get(tinh_for_lookup) or _CITY_TO_PROVINCE.get(_fold(tinh)) if tinh else None
    if tinh_normalized:
        tinh = tinh_normalized

    tinh_folded = _fold(tinh)

    # Buoc 2: lookup bang sap nhap (tinh, xa)
    key = (tinh_folded, _fold(xa_expanded))
    mapping = _REMAP.get(key)
    if not mapping and xa_expanded and " " not in xa_expanded.strip():
        # Ten xa THUC SU viet dinh lien khong dau cach (vd "langbiang" thay vi "Lang Biang") ->
        # khop bat chap khoang trang. CHI ap dung khi khong co khoang trang, tranh dong nham ten
        # da co khoang trang dung nhung khac cach viet (vd hau to "- <thanh pho>") vao mot xa khac.
        mapping = _REMAP_NOSPACE.get((tinh_folded, _fold_nospace(xa_expanded)))
    if mapping:
        return (mapping["tinh"], mapping["xa"], dia_chi)

    # Buoc 2b: ten xa co the DA LA ten hien hanh (khong doi qua sap nhap, khong nam trong
    # bang remap) nhung OCR/LLM tra dinh lien khong dau cach (vd "langbiang") -> tra ve dung
    # ten co khoang trang chuan tu danh muc hien hanh. CHI kich hoat khi xa_expanded THUC SU
    # la MOT TU dinh lien (khong co khoang trang) -- ten da co khoang trang dung (vd "Phường
    # Xuân Hương", thieu hau to "- Đà Lạt") KHONG duoc dong qua "core" cua phuong khac.
    if xa_expanded and " " not in xa_expanded.strip():
        current_ward = _CURRENT_WARD_NOSPACE.get((tinh_folded, _fold_nospace(xa_expanded)))
        if current_ward:
            return (tinh, current_ward, dia_chi)

    # Buoc 2c: xa khong khop duoc entry nao, nhung TINH CU DA BIET CHAC doi ten qua sap nhap (co
    # trong bang remap) -> van dien dung TINH MOI (tinh cu chac chan khong con trong danh muc hien
    # hanh, giu nguyen se khong chon duoc tren cong), con XA thi BO TRONG de can bo tu chon (khong
    # du can cu de giu nguyen ten xa cu, vi ca tinh do da to chuc lai). Tinh nao CHUA TUNG doi ten
    # thi khong co trong _TINH_ONLY -> roi xuong cac nhanh cu, khong dung den xa hop le chua remap.
    tinh_only_moi = _TINH_ONLY.get(tinh_folded)
    if tinh_only_moi and _fold(tinh_only_moi) != tinh_folded:
        return (tinh_only_moi, "", dia_chi)

    if xa_has_admin_label:
        return (tinh, xa_expanded, dia_chi)

    # MẶC ĐỊNH TẮT fallback
    if not allow_diachi_fallback:
        return (tinh, xa_expanded, dia_chi)

    # Buoc 3: fallback A — thu dung diaChi lam xa
    if dia_chi and xa_expanded:
        key_dia = (tinh_folded, _fold(dia_chi))
        mapping_dia = _REMAP.get(key_dia)
        if mapping_dia:
            return (mapping_dia["tinh"], mapping_dia["xa"], xa_expanded)

    # Buoc 4: fallback B — scan token trong xa hoac diaChi
    for scan_src, keep_as_detail in ((xa_expanded, True), (dia_chi, False)):
        if not scan_src:
            continue
        result = _scan_for_xa(scan_src, tinh_folded)
        if result:
            matched_original, matched_mapping = result
            if keep_as_detail:
                return (matched_mapping["tinh"], matched_mapping["xa"], scan_src)
            else:
                return (matched_mapping["tinh"], matched_mapping["xa"], xa_expanded)

    return (tinh, xa_expanded, dia_chi)


def remap_area(area: Optional[dict], allow_diachi_fallback: bool = False) -> Optional[dict]:
    """Nhan object dia chi {quocGia, tinh, xa, diaChi}, tra ve da normalize.

    Buoc 1: neu "tinh" la thanh pho/thi xa thuoc tinh (vd "Da Lat") -> doi sang ten tinh (vd "Lam Dong").
    Buoc 2: neu (tinh, xa) co trong bang sap nhap -> thay bang ten don vi moi.
    Buoc 3 (fallback A): neu xa khong khop, thu dung diaChi lam xa de lookup.
    Buoc 4 (fallback B): scan tung token trong xa hoac diaChi de tim xa hop le.
    Neu tinh la viet tat qua ngan (< 3 ky tu: LA, LD, LĐ...) -> xoa xa tranh dien sai.
    Neu khong co entry nao -> giu nguyen (pass-through).
    """
    if not area or not isinstance(area, dict):
        return area

    tinh_raw: str = area.get("tinh") or ""
    xa_raw:   str = area.get("xa")   or ""
    dia_raw:  str = area.get("diaChi") or ""

    if not tinh_raw and not xa_raw:
        return area

    # Sử dụng cached function để tính toán
    tinh_moi, xa_moi, dia_moi = _remap_area_cached(
        tinh_raw,
        xa_raw,
        dia_raw,
        allow_diachi_fallback,
    )

    return {**area, "tinh": tinh_moi, "xa": xa_moi, "diaChi": dia_moi}


def reload() -> None:
    """Reload tat ca file JSON (dung khi hot-reload trong development)."""
    _REMAP.clear()
    _REMAP_NOSPACE.clear()
    _TINH_ONLY.clear()
    _load_remap_files()
    _CURRENT_WARD_NOSPACE.clear()
    _build_current_ward_index()
    # Clear cache khi reload data
    _remap_area_cached.cache_clear()
