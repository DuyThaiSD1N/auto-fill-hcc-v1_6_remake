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

# Lookup dict chinh: (fold(tinh_cu), fold(xa_cu)) -> {"tinh": ..., "xa": ...}
_REMAP: dict[tuple[str, str], dict[str, str]] = {}

# Lookup dict phu: chi bo dau thanh (giu nguyen chu cai co/khong co mu),
# de bat bien the OCR nham dau (Ha Man / Ha Man / Ha Mau deu map ve Ha Man).
# Key: (fold_base(tinh_cu), fold_base(xa_cu)) -> list[{"tinh":..,"xa":..}]
# Neu co nhieu entry khop (dong am khac nghia) -> lay entry dau (uu tien file truoc).
_REMAP_BASE: dict[tuple[str, str], dict[str, str]] = {}


def _fold(text: str) -> str:
    """Bo dau, lowercase, chuan hoa khoang trang -- dung de so sanh key."""
    t = unicodedata.normalize("NFD", str(text or ""))
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    t = t.replace("\u0110", "D").replace("\u0111", "d")
    # Bo tien to loai don vi truoc khi fold (xa/phuong/thi tran/tt)
    t = re.sub(r"^(xa|phuong|thi tran|tt\.?)\s+", "", t, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip().lower()


def _fold_base(text: str) -> str:
    """Bo toan bo dau va chu mu (a/â/ă -> a, o/ô/ơ -> o, u/ư -> u...).

    Dung lam secondary key de bat OCR nham dau thanh hoac nham mu nguyen am.
    Vi du: 'Ha Man' / 'Ha Man' / 'Ha Mau' / 'Ha Man' deu cho ra 'ha man'.
    """
    t = unicodedata.normalize("NFD", str(text or ""))
    # Giu chi ky tu ASCII + so
    t = "".join(ch for ch in t if ord(ch) < 128)
    t = t.replace("D", "D").replace("d", "d")
    t = re.sub(r"^(xa|phuong|thi tran|tt\.?)\s+", "", t, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip().lower()


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


def _s(value) -> str:
    """Normalize scalar input to a stripped string."""
    return str(value or "").strip()


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
            mapping = {
                "tinh": entry.get("tinh_moi") or tinh_cu,
                "xa":   entry.get("xa_moi")   or xa_cu,
            }
            # Index chinh (fold bao gom dau thanh, bo mu nguyen am)
            key = (_fold(tinh_cu), _fold(xa_cu))
            if key not in _REMAP:
                _REMAP[key] = mapping
            # Index phu (fold ASCII thuan, bo ca mu nguyen am)
            key_base = (_fold_base(tinh_cu), _fold_base(xa_cu))
            if key_base not in _REMAP_BASE:
                _REMAP_BASE[key_base] = mapping


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
        key = (tinh_folded, folded)
        mapping = _REMAP.get(key)
        if mapping and len(folded) > best_len:
            best_original = original
            best_mapping = mapping
            best_len = len(folded)

    return (best_original, best_mapping) if best_mapping else None


def remap_area(area: Optional[dict]) -> Optional[dict]:
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

    tinh_raw: str = _s(area.get("tinh") or area.get("tỉnh"))
    xa_raw: str = _s(area.get("xa") or area.get("xã") or area.get("phuong") or area.get("phường"))
    dia_raw: str = _s(area.get("diaChi") or area.get("dia_chi") or area.get("diachi"))

    # Keep normalized aliases in the outgoing object.
    area = {**area, "tinh": tinh_raw, "xa": xa_raw, "diaChi": dia_raw}

    if not tinh_raw and not xa_raw:
        return area

    # Chặn viết tắt tỉnh (LA, LD, LĐ, L.D...) → xóa xa để tránh điền sai.
    if tinh_raw:
        letters_only = re.sub(r"[^a-z0-9]", "", _fold(tinh_raw))
        if len(letters_only) <= 2:
            return {**area, "xa": ""}

    # Mở rộng viết tắt phường/xã trước khi lookup: P9 → Phường 9, X5 → Xã 5
    if xa_raw:
        xa_expanded = _expand_abbrev(xa_raw)
        if xa_expanded != xa_raw:
            area = {**area, "xa": xa_expanded}
            xa_raw = xa_expanded

    # Buoc 1: normalize thanh pho thuoc tinh -> ten tinh
    tinh_normalized = _CITY_TO_PROVINCE.get(_fold(tinh_raw))
    if tinh_normalized:
        area = {**area, "tinh": tinh_normalized}
        tinh_raw = tinh_normalized

    tinh_folded = _fold(tinh_raw)

    # Buoc 2: lookup bang sap nhap (tinh, xa) -- index chinh
    key = (tinh_folded, _fold(xa_raw))
    mapping = _REMAP.get(key)
    if mapping:
        return {**area, "tinh": mapping["tinh"], "xa": mapping["xa"]}

    # Buoc 2b: fallback -- so sanh khong dau (bat bien the OCR nham dau thanh/mu nguyen am)
    # Vi du: "Ha Man" (sai dau) map duoc vao "Ha Man" (dung) hay "Ha Man" (ca hai cung fold base = "ha man")
    key_base = (_fold_base(tinh_raw), _fold_base(xa_raw))
    mapping_base = _REMAP_BASE.get(key_base)
    if mapping_base:
        return {**area, "tinh": mapping_base["tinh"], "xa": mapping_base["xa"]}

    # Buoc 3: fallback A — thu dung diaChi lam xa
    if dia_raw and xa_raw:
        key_dia = (tinh_folded, _fold(dia_raw))
        mapping_dia = _REMAP.get(key_dia)
        if mapping_dia:
            return {
                **area,
                "tinh": mapping_dia["tinh"],
                "xa": mapping_dia["xa"],
                "diaChi": xa_raw,
            }

    # Buoc 4: fallback B — scan token trong xa hoac diaChi
    # Uu tien scan trong xa truoc (co the la chuoi gop "thon - xa")
    # LUU Y: chi boc ten xa (matched_original), KHONG remap sang ten moi (matched_mapping["xa"])
    # De cho mapper pipeline xu ly remap sau.
    for scan_src, keep_as_detail in ((xa_raw, True), (dia_raw, False)):
        if not scan_src:
            continue
        result = _scan_for_xa(scan_src, tinh_folded)
        if result:
            matched_original, matched_mapping = result
            if keep_as_detail:
                # xa goc (khong remap), diaChi = toan bo chuoi goc lam chi tiet
                return {
                    **area,
                    "tinh": tinh_raw,  # giu nguyen tinh (khong remap)
                    "xa": matched_original,  # giu ten xa ban dau, khong chang sang ten moi
                    "diaChi": scan_src,  # giu nguyen toan bo chuoi goc lam chi tiet
                }
            else:
                # diaChi chua xa hop le. Boc chi tiet dung tru ten xa + huyen.
                # neu diaChi co dang "chi_tiet, xa, huyen" (3+ phan) thi phan truoc xa la chi tiet.
                detail = xa_raw  # mac dinh: xa_raw la chi tiet (thuong rong)
                if dia_raw:
                    parts_d = [p.strip() for p in dia_raw.split(",") if p.strip()]
                    # Tim vi tri phan khop voi xa duoc chon trong chuoi diaChi
                    xa_folded = _fold(matched_original)
                    for i, part in enumerate(parts_d):
                        if _fold(part) == xa_folded and i > 0:
                            # Cac phan truoc vi tri xa la chi tiet
                            detail = ", ".join(parts_d[:i])
                            break
                return {
                    **area,
                    "tinh": tinh_raw,  # giu nguyen tinh
                    "xa": matched_original,  # giu ten xa ban dau, khong chang
                    "diaChi": detail,
                }

    # Buoc 5: fallback C — khi xa trong va diaChi co dang "ten_xa, ten_huyen[, ...]"
    # hoac "chi_tiet, ten_xa, ten_huyen" (3 phan).
    # LLM doi khi dua ca cum "xa, huyen" vao diaChi ma de xa rong.
    if not xa_raw and dia_raw:
        parts = [p.strip() for p in dia_raw.split(",") if p.strip()]

        # Some OCR/LLM outputs repeat province in diaChi. Drop trailing province token first,
        # then parse [detail, xa, huyen] or [xa, huyen].
        if len(parts) >= 2 and _fold(parts[-1]) == tinh_folded:
            parts = parts[:-1]

        xa_candidate = ""
        detail_candidate = ""

        if len(parts) == 1:
            # Chi co 1 phan -> co the chinh la xa (vd "Ha Man")
            xa_candidate = parts[0]
            detail_candidate = ""
        elif len(parts) == 2:
            # 2 phan: [xa, huyen] -> phan dau la xa, phan sau la huyen (bo)
            # vd "Ha Man, Thuan Thanh" -> xa="Ha Man"
            xa_candidate = parts[0]
            detail_candidate = ""
        elif len(parts) >= 3:
            # 3+ phan: [chi_tiet, xa, huyen, ...] -> phan thu 2 la xa, phan dau la chi tiet
            # vd "Man Xa Tay, Ha Man, Thuan Thanh" -> xa="Ha Man", diaChi="Man Xa Tay"
            # vd "Xom 3, Ban Ma, Muong Cha"         -> xa="Ban Ma", diaChi="Xom 3"
            xa_candidate = parts[1]
            detail_candidate = parts[0]

        if xa_candidate:
            # BOC xa tu diaChi ma KHONG remap — de mapper pipeline xu ly remap (sau normalization).
            # Vi: LLM/OCR da tra ten xa, chi can tach ra khoi diaChi, khong tu dong chang sang ten moi.
            # Vi du: "Ha Man" se giu lai "Ha Man", khong tuc dung "Phuong Song Lieu" (ten sau sap nhap).
            return {**area, "xa": xa_candidate, "diaChi": detail_candidate}

    return area


def reload() -> None:
    """Reload tat ca file JSON (dung khi hot-reload trong development)."""
    _REMAP.clear()
    _REMAP_BASE.clear()
    _load_remap_files()
