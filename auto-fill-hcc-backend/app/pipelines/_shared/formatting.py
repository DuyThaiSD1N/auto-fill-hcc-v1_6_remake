"""Helper dùng chung cho mapping OCR → fields."""
import re
import unicodedata

Field = dict  # { "name": str, "comp": str, "value": str | dict }


def parse_address(addr: str | None) -> dict:
    """Tách "Khu 2, Hoàng Cương, Thanh Ba, Phú Thọ" → { tinh, diaChi }.

    - tinh  = cụm CUỐI (sau dấu phẩy cuối).
    - diaChi = CHỈ đơn vị nhỏ nhất (số nhà/khu/xóm/thôn/bản) = cụm ĐẦU; KHÔNG kèm xã/huyện/tỉnh
      (vì xã/phường đã có dropdown riêng trong x-select-area).
    """
    if not addr:
        return {}
    parts = [s.strip() for s in str(addr).split(",") if s.strip()]
    if not parts:
        return {}
    if len(parts) == 1:
        return {"diaChi": parts[0]}
    return {"tinh": parts[-1], "diaChi": parts[0]}


def _norm(s: str | None) -> str:
    return unicodedata.normalize("NFC", (s or "").strip().lower())


def same_name(a: str | None, b: str | None) -> bool:
    na, nb = re.sub(r"\s+", " ", _norm(a)), re.sub(r"\s+", " ", _norm(b))
    return bool(na) and bool(nb) and na == nb


def normalize_date(d: str | None) -> str:
    """"22/4/2021" → "22/04/2021" (zero-pad ngày & tháng)."""
    if not d:
        return ""
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", str(d))
    if not m:
        return str(d)
    return f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{m.group(3)}"


def parse_death_time(time: str | None) -> dict:
    """"HH:mm" hoặc "06 giờ 38 phút" → { hour, minute } (2 chữ số)."""
    if not time:
        return {}
    s = str(time).strip()
    m1 = re.match(r"^(\d{1,2})\s*:\s*(\d{1,2})", s)
    if m1:
        return {"hour": m1.group(1).zfill(2), "minute": m1.group(2).zfill(2)}
    m2 = re.search(r"(\d{1,2})\s*giờ\s*(\d{1,2})", s, re.IGNORECASE)
    if m2:
        return {"hour": m2.group(1).zfill(2), "minute": m2.group(2).zfill(2)}
    return {}


def area_value(tinh: str | None, dia_chi: str | None, quoc_gia: str = "Việt Nam") -> dict:
    return {"quocGia": quoc_gia, "tinh": tinh or "", "diaChi": dia_chi or ""}
