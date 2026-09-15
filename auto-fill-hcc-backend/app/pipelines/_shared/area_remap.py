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

# Lookup NGUOC: (fold_province(tinh MOI), fold_accent(xa CU)) -> ten xa MOI.
#
# Giay to cap/in LAI sau sap nhap 2025 mang TINH MOI, nhung dong dia chi tren do van con ten XA CU
# (vd CCCD: "Thon 5 Nghia Trung / Nghia Hung, Ninh Binh" -- "Nghia Trung" la xa cu thuoc tinh cu Nam
# Dinh). _REMAP key theo (tinh CU, xa cu) nen cap (tinh MOI, xa cu) tra truot hoan toan, dia chi roi
# xuong pass-through va tra ve mot ten xa KHONG CON trong danh muc -> dropdown Phuong/Xa tren cong
# bo trong. Bang nay vao dung khe do.
_REMAP_BY_NEW_PROVINCE: dict[tuple[str, str], str] = {}
# Cung mot ten xa cu, nhieu tinh cu khac nhau, cung don ve mot tinh moi nhung RA HAI xa moi khac
# nhau -> khong du can cu de chon, bo qua thay vi doan bua.
_REMAP_BY_NEW_PROVINCE_AMBIGUOUS: set[tuple[str, str]] = set()
# (tinh_moi, xa_cu, xa_moi) cua nhung entry da qua duoc vong loc ambiguous o _load_remap_files().
# Giu tam o day vi index nguoc can _fold_province(), ham do dinh nghia sau _load_remap_files().
_REMAP_SOURCE_ENTRIES: list[tuple[str, str, str]] = []

# Lookup 3 KHOA: (fold(tinh_cu), fold(xa_cu), fold_district(huyen_cu)) -> {"tinh": ..., "xa": ...}.
#
# Go dung cai nut ma canh gac "ambiguous" o _load_remap_files() danh phai bo tay: mot ten xa/phuong
# ton tai o NHIEU huyen trong cung mot tinh cu, moi cai di ve mot don vi moi khac nhau. Kinh dien
# nhat la phuong DANH SO -- "Phường 1" co o ca TP Da Lat cu (-> "Phường Xuân Hương - Đà Lạt") lan TP
# Bao Loc cu (-> "Phường 1 Bảo Lộc"). Chi co (tinh, xa) thi that su khong du can cu, nen bang 2 khoa
# BO QUA ca hai; nhung khi giay to CO ghi cap huyen thi cai nut do co loi giai chac chan.
#
# Bang nay nap TAT CA entry co "huyen_cu" -- KE CA nhung entry bi vong loc ambiguous gat di, vi day
# chinh la cho dung den chung. Khong co goi y huyen thi khong ai tra bang nay -> hanh vi cu giu nguyen.
_REMAP_BY_DISTRICT: dict[tuple[str, str, str], dict[str, str]] = {}


_UNIT_PREFIX_RE = re.compile(
    r"^\s*(xã|xa|phường|phuong|thị trấn|thi tran|tt)\.?\s+", re.IGNORECASE
)


def _fold(text: str) -> str:
    """Bo dau, lowercase, chuan hoa khoang trang -- dung de so sanh key.

    Tien to loai don vi phai cat TRUOC khi bo dau. Cat sau thi "Phuong Liet" (TEN THAT cua xa,
    bo dau ra "phuong liet") bi hieu la tien to "Phuong" + "Liet" -> key con moi "liet", trong khi
    ban day du "Phuong Phuong Liet" ra "phuong liet": hai ben khong bao gio gap nhau. Danh muc
    hien hanh co 9 xa dinh bay nay (Phuong Liet, Phuong Duc, Xa Dung, Phuong Son, Xa Phien...),
    va no con DE RA map mo GIA -- "Phuong Son" cut con "son" roi dung do voi entry khac.
    """
    t = _UNIT_PREFIX_RE.sub("", str(text or ""))
    t = unicodedata.normalize("NFD", t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    t = t.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", t).strip().lower()


def _fold_nospace(text: str) -> str:
    """_fold() roi bo luon khoang trang -- dung de khop ten xa viet dinh lien (vd "langbiang")."""
    return _fold(text).replace(" ", "")


def _fold_accent(text: str) -> str:
    """Nhu _fold() nhung GIU dau thanh -- chi bo qua VI TRI dat dau.

    _fold() bo het dau nen "Binh Thanh" (Thạnh) va "Binh Thanh" (Thành) trung key. Voi bang remap
    thi chap nhan duoc (co canh gac ambiguous khi trung dich), nhung TRA DANH MUC HIEN HANH thi
    khong: no se bien "Bình Thạnh" thanh "Xã Bình Thành" -- mot xa KHAC.

    Cach lam: tach chu cai goc va dau thanh cua tung tu, roi SAP XEP dau. Nho vay "Hòa" (kieu dat
    dau cu) va "Hoà" (kieu moi) van la MOT, con "Thạnh" (nang) va "Thành" (huyen) thi KHAC nhau.
    """
    raw = _UNIT_PREFIX_RE.sub("", str(text or "")).strip().lower()
    out: list[str] = []
    for word in re.split(r"\s+", raw):
        if not word:
            continue
        decomposed = unicodedata.normalize("NFD", word)
        base = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
        marks = sorted(ch for ch in decomposed if unicodedata.category(ch) == "Mn")
        base = base.replace("đ", "d")
        out.append(base + "".join(marks))
    return " ".join(out)


_DISTRICT_PREFIX_RE = re.compile(
    r"^(tp|thanh pho|tx|thi xa|q|quan|h|huyen|city of)\.?\s+", re.IGNORECASE
)


def _fold_district(text: str) -> str:
    """Fold ten cap huyen de so khop: bo tien to loai (TP/TX/Quan/Huyen) va duoi "cu".

    Giay to viet cap huyen du kieu: "Đà Lạt", "TP Đà Lạt", "Thành phố Đà Lạt", "TP. Đà Lạt cũ".
    Tat ca deu phai quy ve mot khoa, neu khong goi y huyen se tra truot dung luc can nhat.
    """
    folded = _fold(text)
    folded = _DISTRICT_PREFIX_RE.sub("", folded).strip()
    folded = re.sub(r"\s+cu$", "", folded).strip()
    return folded


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


# Ghi chu trong ngoac o cuoi xa_cu KHONG phai ten cap huyen: "(phan)", "(mot phan)", "(thi tran)"...
_XA_CU_NOTES = {"phan", "mot phan", "phan con lai", "thi tran", "phuong", "xa", "huyen", "quan", "cu"}
_XA_CU_DISTRICT_RE = re.compile(r"^(.*\S)\s*\(([^()]+)\)\s*$")


def _split_xa_cu_district(xa_cu: str) -> tuple[str, str]:
    """Tach cap huyen ma bang remap nhet vao ngoac sau ten xa cu.

    Nhieu file remap khong dung khoa "huyen_cu" ma viet "Tân Thành (huyện Bắc Sơn)",
    "Phường 1 (TP Bạc Liêu)", "Tân An (Tân Châu)". De nguyen chuoi do lam khoa thi khong giay to
    nao khop duoc -- ca bang 2 khoa lan 3 khoa -- va xa cu roi xuong pass-through: CCCD ghi
    "Tân Thành, Bắc Sơn, Lạng Sơn" ra "Tân Thành" (mot xa KHAC o Huu Lung) thay vi "Xã Nhất Hòa".

    Tra (ten xa, ten huyen). Ngoac chi la ghi chu ("(phần)", "(thị trấn)") thi giu nguyen xa_cu.
    """
    m = _XA_CU_DISTRICT_RE.match(xa_cu)
    if not m:
        return xa_cu, ""
    inner = m.group(2).split(",")[0].strip()  # "Châu Thành, KG" -> "Châu Thành"
    if not _fold_district(inner) or _fold(inner) in _XA_CU_NOTES:
        return xa_cu, ""
    return m.group(1), inner


def _load_remap_files() -> None:
    """Load tat ca remap_*.json va build lookup dict."""
    if not _DATA_DIR.exists():
        return
    
    # Track duplicate keys to mark as ambiguous
    _duplicate_tracker: dict[tuple[str, str], list[dict]] = {}
    _source_xa_cu: dict[tuple[str, str], str] = {}
    
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

            # Index 3 khoa nap TRUOC vong loc ambiguous: entry ghi ro huyen_cu thi cap
            # (tinh, xa, huyen) la duy nhat, khong con gi de nham. Trung khoa 3 -> du lieu mau
            # thuan, giu entry dau va bo qua phan sau thay vi ghi de am tham.
            # Huyen ghi trong ngoac ("Tân Thành (huyện Bắc Sơn)") CHI vao bang 3 khoa: ngoac do
            # co mat chinh vi ten xa trung, thieu goi y huyen thi van khong du can cu -> bang 2
            # khoa giu nguyen nhu cu.
            huyen_cu = entry.get("huyen_cu") or ""
            xa_cu_district = xa_cu
            if not huyen_cu:
                xa_cu_district, huyen_cu = _split_xa_cu_district(xa_cu)
            if huyen_cu:
                _REMAP_BY_DISTRICT.setdefault(
                    (key[0], _fold(xa_cu_district), _fold_district(huyen_cu)), mapping
                )
            
            # Track all entries for this key to detect duplicates
            if key not in _duplicate_tracker:
                _duplicate_tracker[key] = []
            _duplicate_tracker[key].append(mapping)
            # key da fold (mat dau) -- index nguoc can ten xa cu CON DAU de khong dong nham
            # "Thanh" (Thanh) voi "Thanh" (Thanh).
            _source_xa_cu.setdefault(key, xa_cu)
    
    # Only add entries that are NOT duplicates (or are marked ambiguous)
    for key, mappings in _duplicate_tracker.items():
        # If there are multiple different mappings for the same key, skip them all (ambiguous)
        unique_mappings = {(m["tinh"], m["xa"]) for m in mappings}
        if len(unique_mappings) > 1:
            # Xa cu tach ra nhieu don vi moi, NHUNG mot trong so do GIU NGUYEN ten cu ->
            # chon chinh no. Day la truong hop don vi bi cat bot dia gioi ma van giu ten:
            # giay to ghi "X" thi kha nang cao thuoc "X" moi, khong phai mieng cat sang ten
            # khac. Bo tay o day nghia la tra ve ten CU -- mot ten khong con trong danh muc,
            # dropdown Phuong/Xa se do. So sanh bang _fold_accent de "Thanh" (nang) khong
            # dong nham voi "Thanh" (huyen).
            xa_cu_goc = _source_xa_cu.get(key) or ""
            keepers = [m for m in mappings
                       if _fold_accent(m["xa"]) == _fold_accent(xa_cu_goc)]
            unique_keepers = {(m["tinh"], m["xa"]) for m in keepers}
            if len(unique_keepers) == 1:
                mappings = keepers[:1]
            else:
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

        xa_cu_goc = _source_xa_cu.get(key)
        if xa_cu_goc:
            _REMAP_SOURCE_ENTRIES.append((mapping["tinh"], xa_cu_goc, mapping["xa"]))


_load_remap_files()  # chay 1 lan luc import


# ---------------------------------------------------------------------------
# Bang tra ten xa/phuong HIEN HANH (khong can remap) da bo khoang trang -- dung khi
# OCR/LLM tra ten xa dinh lien nhung do CHINH LA ten xa MOI (khong nam trong bang remap
# o tren, vi khong bi doi ten qua sap nhap). Vd "langbiang" (tinh "Lam Dong") -> "Phường
# Lang Biang - Đà Lạt". Xay dung tu danh muc hanh chinh hien hanh (app.locations.catalog).
# ---------------------------------------------------------------------------
_CURRENT_WARD_NOSPACE: dict[tuple[str, str], str] = {}

# Bang tra ten xa/phuong HIEN HANH theo ten da fold (CON khoang trang, da bo tien to
# "Xa/Phuong/Thi tran"). Dung cho hai ca rat pho bien sau sap nhap 2025:
#   (a) Giay to ghi TINH CU nhung XA da la ten MOI ("Bac Giang" + "Xa Hiep Hoa").
#   (b) OCR/LLM tra TEN HUYEN CU lam xa -- ma xa moi lai LAY CHINH TEN HUYEN do
#       ("huyen Hiep Hoa" -> "Xa Hiep Hoa"). Bang remap chi co key theo XA cu nen tra truot.
# Ca hai truoc day deu roi xuong nhanh _TINH_ONLY va bi XOA TRANG o Xa/Phuong.
_CURRENT_WARD: dict[tuple[str, str], str] = {}
# Ten fold bi TRUNG trong cung mot tinh -> khong du can cu de chon, bo qua thay vi doan bua.
_CURRENT_WARD_AMBIGUOUS: set[tuple[str, str]] = set()


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
                # CHI index ten DAY DU. Khong index phan "loi" truoc hau to "- <thanh pho>":
                # lam vay se noi "Phuong Xuan Huong" (dung nhu option tren form) thanh "Phuong Xuan
                # Huong - Da Lat" -- da co test khoa hanh vi nay.
                for spaced_key in {_fold_accent(ward_full_name)}:
                    if not spaced_key:
                        continue
                    key = (tinh_key, spaced_key)
                    existing = _CURRENT_WARD.get(key)
                    if existing is None:
                        _CURRENT_WARD[key] = ward_full_name
                    elif existing != ward_full_name:
                        _CURRENT_WARD_AMBIGUOUS.add(key)


_build_current_ward_index()  # chay 1 lan luc import


# ---------------------------------------------------------------------------
# Tra NGUOC danh muc hien hanh: ten xa/phuong -> tinh dang so huu no.
#
# OCR chu viet tay tren to khai doc sai TEN TINH rat de: chi 34 tinh nhung chu viet tay thi
# "Bac Ninh" ra "lai ninh", "Bac Giang" ra "Ba Ria - Vung Tau". Cap (tinh sai, xa dung) khong
# chon duoc gi tren cong -- ca hai dropdown do. Ten xa nguoc lai rat dac trung: 2376/2745 ten
# xa chi ton tai o DUNG MOT tinh, nen khi cap khong hop le ma ten xa lai duy nhat toan quoc thi
# tinh moi la ve dang sai, khong phai xa.
# ---------------------------------------------------------------------------
# fold_accent(ten xa) -> (ten tinh khong tien to, ten xa day du trong danh muc)
_PROVINCE_BY_WARD: dict[str, tuple[str, str]] = {}
# Ten xa trung o nhieu tinh -> khong du can cu suy ra tinh, bo qua thay vi doan bua.
_WARD_NAME_AMBIGUOUS: set[str] = set()
# (fold(tinh), fold_accent(xa)) co that trong danh muc hien hanh.
_CURRENT_PAIRS: set[tuple[str, str]] = set()
# fold(ten tinh, ca dang "Tinh X" lan "X") -> ten tinh khong tien to.
_CURRENT_PROVINCES: dict[str, str] = {}


_PROVINCE_PREFIX_RE = re.compile(r"^(tinh|thanh pho|tp)\.?\s+")


def _fold_province(text: str) -> str:
    """Fold ten tinh, BO tien to loai don vi.

    Danh muc goc ghi "Tinh Bac Ninh"/"Thanh pho Ho Chi Minh", bang remap ghi "TP. Ho Chi Minh",
    con giay to thi ghi tran "Bac Ninh". Ba cach viet do phai la MOT tinh, neu khong moi dia chi
    di qua bang remap HCM deu bi cham la "khong con trong danh muc".
    """
    return _PROVINCE_PREFIX_RE.sub("", _fold(text)).strip()


def _ward_keys(ward_full_name: str) -> set[str]:
    """Cac cach viet ten mot xa co the gap trong du lieu doc ra.

    Ten day du ("Phuong Lang Biang - Da Lat") va phan loi truoc hau to "- <thanh pho>"
    ("Lang Biang") deu tro ve cung mot xa.
    """
    keys = {_fold_accent(ward_full_name)}
    core = _fold_accent(ward_full_name).split(" - ")[0].strip()
    if core:
        keys.add(core)
    return {key for key in keys if key}


def _build_reverse_catalog_index() -> None:
    try:
        from app.locations.catalog import PROVINCES, WARDS_BY_SLUG
    except Exception as e:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning(
            "area_remap: khong nap duoc danh muc hanh chinh de tra nguoc -- %s", e
        )
        return
    for province in PROVINCES:
        province_name = province["name"]
        for label in (province["text"], province["name"]):
            _CURRENT_PROVINCES[_fold_province(label)] = province_name
        for ward_full_name in WARDS_BY_SLUG.get(province["slug"], {}).get("communes") or []:
            for key in _ward_keys(ward_full_name):
                _CURRENT_PAIRS.add((_fold_province(province_name), key))
                existing = _PROVINCE_BY_WARD.get(key)
                if existing is None:
                    _PROVINCE_BY_WARD[key] = (province_name, ward_full_name)
                elif existing[0] != province_name:
                    _WARD_NAME_AMBIGUOUS.add(key)


_build_reverse_catalog_index()  # chay 1 lan luc import


def _build_new_province_index() -> None:
    """Dung bang tra (tinh MOI, xa CU) -> xa MOI tu chinh cac entry remap da loc ambiguous."""
    for tinh_moi, xa_cu, xa_moi in _REMAP_SOURCE_ENTRIES:
        key = (_fold_province(tinh_moi), _fold_accent(xa_cu))
        if not key[0] or not key[1]:
            continue
        existing = _REMAP_BY_NEW_PROVINCE.get(key)
        if existing is None:
            _REMAP_BY_NEW_PROVINCE[key] = xa_moi
        elif existing != xa_moi:
            # Hai tinh cu khac nhau cung co xa ten nay, cung don ve mot tinh moi nhung ra hai xa
            # moi khac nhau -> khong du can cu, bo qua ca hai.
            _REMAP_BY_NEW_PROVINCE_AMBIGUOUS.add(key)


_build_new_province_index()  # chay 1 lan luc import, sau _load_remap_files()


def _remap_by_new_province(tinh: str, xa: str) -> Optional[str]:
    """Ten xa MOI khi giay to ghi TINH MOI nhung xa van la ten CU. None neu khong chac chan.

    Chi tra ket qua khi cap (tinh, xa) hien tai THUC SU khong chon duoc tren cong: dieu kien nay
    la thu chan quan trong nhat cua ca nhanh -- dia chi dang dung tot khong bao gio bi dong.
    """
    if not xa or not tinh:
        return None
    if is_current_area(tinh, xa):
        return None
    key = (_fold_province(tinh), _fold_accent(xa))
    if key in _REMAP_BY_NEW_PROVINCE_AMBIGUOUS:
        return None
    return _REMAP_BY_NEW_PROVINCE.get(key)


def is_current_area(tinh: str, xa: str) -> bool:
    """Cap tinh/xa nay co chon duoc tren cong khong (theo danh muc hanh chinh hien hanh).

    Tinh rong -> khong co gi de kiem; xa rong -> chi kiem ten tinh. Danh muc chua nap duoc
    (import loi) thi coi nhu hop le: tha bo qua con hon xoa du lieu dung.
    """
    if not _CURRENT_PROVINCES:
        return True
    province_key = _fold_province(tinh)
    if not province_key:
        return True
    if province_key not in _CURRENT_PROVINCES:
        return False
    if not str(xa or "").strip():
        return True
    return (_fold_province(_CURRENT_PROVINCES[province_key]), _fold_accent(xa)) in _CURRENT_PAIRS


def province_for_ward(xa: str) -> Optional[tuple[str, str]]:
    """Tinh DUY NHAT dang co phuong/xa ten nay -> (ten tinh, ten xa day du).

    Tra None khi ten xa khong co trong danh muc, hoac trung ten o nhieu tinh -- luc do khong
    du can cu de sua, giu nguyen cho nguoi dung tu chon con hon doi sang tinh khac.
    """
    key = _fold_accent(xa)
    if not key or key in _WARD_NAME_AMBIGUOUS:
        return None
    return _PROVINCE_BY_WARD.get(key)


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
    huyen: str = "",
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

    # Buoc 1b: giay to CO ghi cap huyen -> tra bang 3 khoa truoc. Day la duong DUY NHAT chon dung
    # duoc mot ten xa/phuong trung o nhieu huyen trong cung tinh cu (vd "Phường 1" cua TP Da Lat cu
    # va cua TP Bao Loc cu): bang 2 khoa buoc phai bo qua ca hai vi khong du can cu, con cap
    # (tinh, xa, huyen) thi duy nhat. Tra truot -> roi xuong dung luong cu, khong doi hanh vi.
    if huyen and xa_expanded:
        mapping_huyen = _REMAP_BY_DISTRICT.get(
            (tinh_folded, _fold(xa_expanded), _fold_district(huyen))
        )
        if mapping_huyen:
            return (mapping_huyen["tinh"], mapping_huyen["xa"], dia_chi)

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

    # Buoc 2b2: giay to mang TINH MOI nhung dong dia chi con ten XA CU. Rat pho bien voi giay to
    # cap/in lai sau sap nhap 2025 (vd CCCD ghi "Thon 5 Nghia Trung / Nghia Hung, Ninh Binh": tinh
    # da la ten moi "Ninh Binh", con "Nghia Trung" la xa CU cua tinh cu Nam Dinh). _REMAP key theo
    # (tinh CU, xa cu) nen cap nay tra truot het cac buoc tren, roi xuong pass-through va tra ve mot
    # ten xa khong con trong danh muc -> dropdown Phuong/Xa tren cong bo trong.
    # _remap_by_new_province() chi tra ket qua khi cap hien tai THUC SU khong chon duoc tren cong,
    # nen khong the dong nham mot dia chi dang dung tot.
    xa_moi_theo_tinh_moi = _remap_by_new_province(tinh, xa_expanded)
    if xa_moi_theo_tinh_moi:
        return (tinh, xa_moi_theo_tinh_moi, dia_chi)

    # Buoc 2c: xa khong khop entry nao, nhung TINH CU DA BIET CHAC doi ten qua sap nhap (co trong
    # bang remap) -> phai dien TINH MOI (tinh cu chac chan khong con trong danh muc hien hanh, giu
    # nguyen se khong chon duoc tren cong). Tinh nao CHUA TUNG doi ten thi khong co trong _TINH_ONLY
    # -> roi xuong cac nhanh cu, khong dung den xa hop le chua can remap.
    tinh_only_moi = _TINH_ONLY.get(tinh_folded)
    if tinh_only_moi and _fold(tinh_only_moi) != tinh_folded:
        # Truoc khi BO TRONG xa, thu mot nhip cuoi: ten xa co the DA LA TEN HIEN HANH cua tinh MOI.
        # Hai duong dan toi day:
        #   (a) Giay to ghi tinh CU nhung xa da la ten MOI (vd "Bac Giang" + "Xa Hiep Hoa").
        #   (b) OCR/LLM tra TEN HUYEN CU lam xa -- rat pho bien vi sau sap nhap 2025 nhieu xa moi
        #       lay chinh ten huyen cu (huyen Hiep Hoa -> "Xa Hiep Hoa"). Bang remap chi co key theo
        #       ten XA cu nen tra truot.
        # Dung dung trieu chung "co luc remap duoc co luc khong": ket qua doi theo viec agent tra
        # ten xa cu hay ten huyen. So ten CO DAU (_fold_accent) de khong dong nham "Binh Thanh"
        # sang "Binh Thanh"; ten fold trung nhau trong cung tinh thi bo qua, khong doan bua.
        if xa_expanded:
            ward_key = (_fold(tinh_only_moi), _fold_accent(xa_expanded))
            if ward_key not in _CURRENT_WARD_AMBIGUOUS:
                current_ward_spaced = _CURRENT_WARD.get(ward_key)
                if current_ward_spaced:
                    return (tinh_only_moi, current_ward_spaced, dia_chi)
        # Van khong ra: BO TRONG xa de can bo tu chon (khong du can cu giu ten xa cu, vi ca tinh do
        # da to chuc lai).
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


# Đơn vị DƯỚI cấp xã — không bao giờ là tên xã/phường. Cố ý KHÔNG có "bản"/"làng": tên xã vùng cao
# hay bắt đầu bằng "Bản ..." nên đoán theo tiền tố đó là xoá nhầm xã thật.
_VILLAGE_PREFIX_RE = re.compile(
    r"^(thon|xom|ap|buon|khom|soc|to dan pho|tdp|to|khu pho|kp|khu dan cu|kdc)\b[\s.]"
)


def remap_area(
    area: Optional[dict],
    allow_diachi_fallback: bool = False,
    huyen_hint: Optional[str] = None,
) -> Optional[dict]:
    """Nhan object dia chi {quocGia, tinh, xa, diaChi}, tra ve da normalize.

    Buoc 1: neu "tinh" la thanh pho/thi xa thuoc tinh (vd "Da Lat") -> doi sang ten tinh (vd "Lam Dong").
    Buoc 1b: neu biet CAP HUYEN cu (huyen_hint, hoac khoa "huyen"/"quanHuyen" trong area) -> tra bang
             3 khoa de chon dung don vi moi khi ten xa trung o nhieu huyen (vd "Phường 1" Da Lat vs
             Bao Loc). Khoa goi y nay bi BO khoi ket qua tra ve.
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
    # "huyen"/"quanHuyen" la khoa GOI Y, khong phai o tren bieu mau (dia chi hien hanh chi con 2
    # cap). Nhan vao de go nhap nhang ten xa trung, roi BO khoi ket qua -- de lot ra ngoai la them
    # mot khoa la vao gia tri field ma khong ai doc.
    huyen_raw: str = huyen_hint or area.get("huyen") or area.get("quanHuyen") or ""

    # LLM hay đặt đơn vị DƯỚI cấp xã ("Thôn M'Lọn", "Tổ dân phố 3") vào ô xã rồi đẩy tên xã thật
    # sang "huyen" (địa chỉ "Thôn M'Lọn, xã Đơn Dương, tỉnh Lâm Đồng" ra xa="Thôn M'Lọn",
    # huyen="Đơn Dương"). Ô xã khi đó không khớp option nào → cổng bỏ trống cả xã lẫn địa chỉ chi
    # tiết. Trả thôn/tổ về diaChi; nếu gợi ý cấp huyện LÀ một xã/phường hiện hành của tỉnh thì dùng
    # nó làm xã (sau sáp nhập nhiều xã mang tên huyện cũ). Không khớp danh mục thì để trống xã.
    if xa_raw and _VILLAGE_PREFIX_RE.match(_fold(xa_raw)):
        if _fold(xa_raw) not in _fold(dia_raw):
            dia_raw = f"{dia_raw}, {xa_raw}" if dia_raw else xa_raw
        xa_raw = ""
        if huyen_raw and tinh_raw and is_current_area(tinh_raw, huyen_raw):
            # Lấy đủ nhãn trong danh mục ("Xã Đơn Dương") để khớp option trên cổng.
            found = province_for_ward(huyen_raw)
            same_province = bool(found) and _fold_province(found[0]) == _fold_province(tinh_raw)
            xa_raw = found[1] if same_province else huyen_raw
            huyen_raw = ""

    if not tinh_raw and not xa_raw:
        return {k: v for k, v in area.items() if k not in ("huyen", "quanHuyen")} if huyen_raw else area

    # Sử dụng cached function để tính toán
    tinh_moi, xa_moi, dia_moi = _remap_area_cached(
        tinh_raw,
        xa_raw,
        dia_raw,
        allow_diachi_fallback,
        huyen_raw,
    )

    out = {**area, "tinh": tinh_moi, "xa": xa_moi, "diaChi": dia_moi}
    out.pop("huyen", None)
    out.pop("quanHuyen", None)
    return out


_AREA_DETAIL_KEYS = ("diaChi", "dia_chi", "diachi", "chiTiet")
_AREA_WARD_KEYS = ("xa", "xã", "phuong", "phường")


def _looks_like_area(value: dict) -> bool:
    """Object nay co phai mot dia chi hanh chinh khong.

    Dat nguong o "co tinh + (xa hoac dia chi)": du chat de khong dung nham mot object bat ky co
    khoa "tinh", du long de bat het cac bien the dat ten ma cac pipeline dang dung.
    """
    if not any(value.get(k) for k in ("tinh", "tỉnh")):
        return False
    return any(value.get(k) for k in _AREA_WARD_KEYS + _AREA_DETAIL_KEYS)


def remap_area_deep(value, allow_diachi_fallback: bool = False):
    """Chuan hoa MOI object dia chi long trong mot gia tri field (dict/list long nhau).

    Dung o BUOC CHUNG ngay sau khi LLM tra ket qua, truoc khi mapper cua tung thu tuc dung toi --
    mot cho duy nhat thay vi 40 mapper moi cho mot dong. Nho vay:
      * goi y cap huyen ("huyen"/"quanHuyen") duoc TIEU THU dung luc no con trong du lieu; mapper
        dung sau do co dung lai dict 4 khoa cung khong lam mat no nua;
      * ten xa/phuong den tay mapper DA LA ten trong danh muc hien hanh, nen remap_area() ma mapper
        goi lai chi con la no-op.

    Gia tri khong phai dia chi -> tra ve nguyen ven, khong dung toi.
    """
    if isinstance(value, list):
        return [remap_area_deep(item, allow_diachi_fallback) for item in value]
    if not isinstance(value, dict):
        return value
    out = {k: remap_area_deep(v, allow_diachi_fallback) for k, v in value.items()}
    if _looks_like_area(out):
        remapped = remap_area(out, allow_diachi_fallback)
        if isinstance(remapped, dict):
            return remapped
    return out


_PROVINCE_LABEL_RE = re.compile(r"^(thanh pho|tinh|tp|t\.)\.?\s*", re.IGNORECASE)


def _mentioned_in(text_folded: str, name: str) -> bool:
    """Ten don vi nay co THUC SU xuat hien trong text OCR khong (bo nhan loai, bo dau)."""
    key = _PROVINCE_LABEL_RE.sub("", _fold(name)).strip()
    if not key:
        return True
    return key in text_folded


def drop_fabricated_province(value, ocr_text: str):
    """Bo ten TINH/HUYEN ma LLM tu bia ra: giay to khong he nhac toi, va cung khong khop voi xa.

    LLM doi khi "dien not" cap tren cho mot dia chi chi ghi den cap xa. Vi du that: to khai chi co
    "Tổ 3, Phường Nghĩa Lộ" (khong mot chu nao ve tinh) nhung LLM tra ve tinh "Thành phố Hà Nội" va
    huyen "Quận Hà Đông" -- ca hai deu khong co trong giay. Dien mot tinh bia ra thi nguy hiem hon
    han bo trong: no trong nhu du lieu that va cong van cho chon.

    HAI dieu kien phai cung dung moi bo, de khong dap nham suy luan DUNG:
      1. Ten tinh khong xuat hien o bat ky dau trong text OCR;
      2. cap (tinh, xa) KHONG co trong danh muc hanh chinh hien hanh.
    Suy luan dung tu ten xa duy nhat (vd doc duoc "Phường Xuân Hương - Đà Lạt" roi tu dien tinh
    "Lâm Đồng") van thoa dieu kien 1 nhung KHONG thoa dieu kien 2 -> giu nguyen.

    KHONG doi tinh theo ten xa: "Phường Nguyễn Du" (Ha Noi cu) trung khoa voi "Xã Nguyễn Du" cua
    Hung Yen, sua kieu do la keo ca dia chi sang tinh khac.
    """
    if not ocr_text:
        return value
    text_folded = _fold(ocr_text)
    if isinstance(value, list):
        return [drop_fabricated_province(item, ocr_text) for item in value]
    if not isinstance(value, dict):
        return value
    out = {k: drop_fabricated_province(v, ocr_text) for k, v in value.items()}
    if not _looks_like_area(out):
        return out
    for key in ("huyen", "quanHuyen"):
        if out.get(key) and not _mentioned_in(text_folded, out[key]):
            out.pop(key)
    for key in ("tinh", "tỉnh"):
        tinh = out.get(key)
        if not tinh or _mentioned_in(text_folded, tinh):
            continue
        xa = next((out.get(k) for k in _AREA_WARD_KEYS if out.get(k)), "")
        if not is_current_area(tinh, xa):
            out[key] = ""
    return out


def _blank_unselectable_ward(value) -> bool:
    """Xoa ten xa/phuong KHONG chon duoc tren cong. True neu co xoa (de danh dau vien vang).

    Sua TAI CHO, di sau vao list/dict long nhau nhu remap_area_deep().
    """
    changed = False
    if isinstance(value, list):
        for item in value:
            changed |= _blank_unselectable_ward(item)
        return changed
    if not isinstance(value, dict):
        return False
    for item in value.values():
        changed |= _blank_unselectable_ward(item)
    if not _looks_like_area(value):
        return changed
    tinh = value.get("tinh") or value.get("tỉnh") or ""
    for ward_key in _AREA_WARD_KEYS:
        xa = value.get(ward_key)
        if not xa or is_current_area(tinh, xa):
            continue
        value[ward_key] = ""
        changed = True
    return changed


def flag_unselectable_areas(fields):
    """Chot chan CHUNG: khong giao cho extension mot ten xa/phuong khong co trong danh muc.

    Remap khong phai luc nao cung ra ket qua -- ten xa trung o nhieu huyen (vd "Phường 1" cua ca Da
    Lat lan Bao Loc), giay to qua cu, OCR doc sai. Nhung luc do backend van tra ten cu nguyen si, va
    extension KHONG biet do la ten chet: no do lỏng trong dropdown, vo phai option nao chua cum do
    ("Phường 1 Bảo Lộc") roi to XANH nhu vua dien dung. Sai kieu nay khong ai soat ra.

    Nen: xoa ten xa do va danh dau default -> extension bo trong o phuong/xa va TO VIEN VANG, can bo
    tu chon. Tinh van duoc giu, cac o khac khong anh huong. Chua nap duoc danh muc thi
    is_current_area() tra True het -> khong dong gi ca.
    """
    if not isinstance(fields, list):
        return fields
    for field in fields:
        if not isinstance(field, dict):
            continue
        if _blank_unselectable_ward(field.get("value")):
            field["default"] = True
    return fields


def reload() -> None:
    """Reload tat ca file JSON (dung khi hot-reload trong development)."""
    _REMAP.clear()
    _REMAP_NOSPACE.clear()
    _TINH_ONLY.clear()
    _REMAP_BY_DISTRICT.clear()
    _REMAP_SOURCE_ENTRIES.clear()
    _load_remap_files()
    _CURRENT_WARD_NOSPACE.clear()
    _CURRENT_WARD.clear()
    _CURRENT_WARD_AMBIGUOUS.clear()
    _build_current_ward_index()
    _PROVINCE_BY_WARD.clear()
    _WARD_NAME_AMBIGUOUS.clear()
    _CURRENT_PAIRS.clear()
    _CURRENT_PROVINCES.clear()
    _build_reverse_catalog_index()
    _REMAP_BY_NEW_PROVINCE.clear()
    _REMAP_BY_NEW_PROVINCE_AMBIGUOUS.clear()
    _build_new_province_index()
    # Clear cache khi reload data
    _remap_area_cached.cache_clear()
