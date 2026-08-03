"""Chuan hoa ten dan toc ve dung nhan option dropdown.

Xu ly cac bien the OCR pho bien va ten viet tat/sai chinh ta.
Dat biet phan biet:
  - "Mong" (viet khong dau) -> "Mong"
  - "H.Mong", "H'Mong", "Hmong"... -> "Mong (Hmong)"

Cach dung:
    from app.pipelines._shared.ethnic_normalize import normalize_ethnic
    normalize_ethnic("H.Mong")   # -> "Mong (Hmong)"
    normalize_ethnic("Giay")     # -> "Giay"
    normalize_ethnic("Kinh")     # -> "Kinh"
"""

from __future__ import annotations

import re
import unicodedata


def _fold(text: str) -> str:
    """Bo dau, lowercase, bo dau cham/phay/khoang trang thua."""
    t = unicodedata.normalize("NFD", str(text or ""))
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    t = t.replace("\u0110", "D").replace("\u0111", "d")
    # Bo cac ky tu dac biet thuong gap trong OCR viet tat dan toc
    t = re.sub(r"['.`''\-]", "", t)
    return re.sub(r"\s+", " ", t).strip().lower()


# Bang mapping: fold(bien_the_ocr) -> ten_chuan_trong_dropdown
# Key: da fold (bo dau, bo dau cham, lowercase)
# Value: ten chinh xac theo dropdown x-select
_ETHNIC_MAP: dict[str, str] = {
    # ===== KINH =====
    "kinh": "Kinh",

    # ===== MONG / HMONG (phan biet 2 option) =====
    # "Mong" ghi khong dau -> option "Mong"
    "mong": "Mông",
    # H.Mong, H'Mong, HMong, H Mong... -> option "Mong (Hmong)"
    "hmong": "Mông (Hmông)",
    "hmong": "Mông (Hmông)",
    "h mong": "Mông (Hmông)",

    # ===== TAY =====
    "tay": "Tày",
    "tay den": "Tày",

    # ===== THAI =====
    "thai": "Thái",
    "thai den": "Thái",
    "thai trang": "Thái",

    # ===== MUONG =====
    "muong": "Mường",

    # ===== KHMER =====
    "khmer": "Khmer",
    "kho me": "Khmer",
    "khome": "Khmer",

    # ===== NUNG =====
    "nung": "Nùng",

    # ===== HOA =====
    "hoa": "Hoa",
    "nguoi hoa": "Hoa",

    # ===== DAO =====
    "dao": "Dao",
    "yao": "Dao",

    # ===== GIA RAI =====
    "gia rai": "Gia Rai",
    "giarai": "Gia Rai",
    "jarai": "Gia Rai",

    # ===== E DE =====
    "e de": "Ê Đê",
    "ede": "Ê Đê",

    # ===== BA NA =====
    "ba na": "Ba Na",
    "bana": "Ba Na",
    "bahnar": "Ba Na",

    # ===== SAN CHAY =====
    "san chay": "Sán Chay",
    "cao lan": "Sán Chay",

    # ===== CHAM =====
    "cham": "Chăm",
    "chiem thanh": "Chăm",

    # ===== CO HO =====
    "co ho": "Cơ Ho",
    "kho": "Cơ Ho",
    "k ho": "Cơ Ho",
    "c ho": "Cơ Ho",
    "k h ro": "Cơ Ho",
    "khro": "Cơ Ho",
    "k hro": "Cơ Ho",
    # Co Ho (Cill) - nhom Cill la mot nhanh cua Co Ho
    "cill": "Cơ Ho (Cill)",
    "co ho cill": "Cơ Ho (Cill)",
    "kho cill": "Cơ Ho (Cill)",
    "coho": "Cơ Ho",

    # ===== XO DANG =====
    "xo dang": "Xơ Đăng",
    "sedang": "Xơ Đăng",

    # ===== SAN DIU =====
    "san diu": "Sán Dìu",

    # ===== HROI (BA NA nhom nho) =====
    "hre": "Hrê",
    "hre": "Hrê",

    # ===== MNONG =====
    "mnong": "Mnông",
    "m nong": "Mnông",

    # ===== THO =====
    "tho": "Thổ",

    # ===== XTIENG =====
    "xtieng": "Xtiêng",
    "x tieng": "Xtiêng",

    # ===== BANA nhom (Bahnar) =====
    "bahnar": "Ba Na",

    # ===== CO TU =====
    "co tu": "Cơ Tu",
    "katu": "Cơ Tu",

    # ===== GIE TRIENG =====
    "gie trieng": "Giẻ Triêng",
    "gie-trieng": "Giẻ Triêng",

    # ===== MA =====
    "ma": "Mạ",

    # ===== KHOR =====
    "kho mu": "Khơ Mú",
    "khmu": "Khơ Mú",

    # ===== LO LO =====
    "lo lo": "Lô Lô",

    # ===== CHUT =====
    "chut": "Chứt",

    # ===== MANG =====
    "mang": "Mảng",

    # ===== PA THEN =====
    "pa then": "Pà Thẻn",
    "pathen": "Pà Thẻn",

    # ===== CO =====
    "co": "Co",

    # ===== TA OI =====
    "ta oi": "Tà Ôi",
    "ta-oi": "Tà Ôi",

    # ===== BRAO =====
    "brao": "Brâu",

    # ===== RO MAM =====
    "ro mam": "Rơ Măm",
    "romam": "Rơ Măm",

    # ===== GIAY =====
    "giay": "Giáy",
    "giáy": "Giáy",
    "zay": "Giáy",

    # ===== HA NHI =====
    "ha nhi": "Hà Nhì",
    "hanhi": "Hà Nhì",

    # ===== PHU LA =====
    "phu la": "Phù Lá",
    "phula": "Phù Lá",

    # ===== LA CHI =====
    "la chi": "La Chí",
    "lachi": "La Chí",

    # ===== LA HA =====
    "la ha": "La Ha",

    # ===== CO LAO =====
    "co lao": "Cơ Lao",
    "colao": "Cơ Lao",

    # ===== KHANG =====
    "khang": "Kháng",

    # ===== XINH MUN =====
    "xinh mun": "Xinh Mun",
    "xinhmun": "Xinh Mun",

    # ===== LU =====
    "lu": "Lự",

    # ===== LAO =====
    "lao": "Lào",

    # ===== LA HU =====
    "la hu": "La Hủ",
    "lahu": "La Hủ",

    # ===== SI LA =====
    "si la": "Si La",
    "sila": "Si La",

    # ===== PU PEO =====
    "pu peo": "Pu Péo",
    "pupeo": "Pu Péo",

    # ===== CONG =====
    "cong": "Cống",

    # ===== O DU =====
    "o du": "Ơ Đu",
    "odu": "Ơ Đu",

    # ===== NGAI =====
    "ngai": "Ngái",

    # ===== BO Y =====
    "bo y": "Bố Y",
    "boy": "Bố Y",

    # ===== BRU VAN KIEU =====
    "bru van kieu": "Bru - Vân Kiều",
    "bru-van kieu": "Bru - Vân Kiều",
    "van kieu": "Bru - Vân Kiều",

    # ===== RA GLAI =====
    "ra glai": "Raglai",
    "raglai": "Raglai",

    # ===== CHUA =====
    "chut": "Chứt",
}


def normalize_ethnic(value: str | None) -> str:
    """Chuan hoa ten dan toc ve dung nhan option dropdown.

    Tra ve ten chuan neu tim thay trong bang, nguyen ban neu khong tim thay.
    Khong bao gio tra chuoi rong neu dau vao co gia tri.
    """
    if not value:
        return value or ""
    raw = str(value).strip()
    if not raw:
        return raw
    key = _fold(raw)
    return _ETHNIC_MAP.get(key, raw)
