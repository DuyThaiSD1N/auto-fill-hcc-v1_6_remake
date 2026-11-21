"""Nhân thân theo THẺ CĂN CƯỚC in máy trong hồ sơ (bản sao CCCD), áp lên lượt trích trước mapper.

Đơn đề nghị viết tay: OCR hay đọc lệch chữ trong họ tên ("Bắc" thành "Bầu"). Bản sao CCCD in máy của CHÍNH người đó (cùng
số định danh) đáng tin hơn. MÃ đọc từng trang: mặt trước (số, họ tên) và vùng MRZ (số, ngày sinh, họ tên không dấu) — rồi:
- họ tên: lượt trích lệch CHỮ CÁI (bỏ dấu vẫn khác) với tên mặt trước, và vùng MRZ cùng thẻ xác nhận tên mặt trước → tên
  mặt trước. Chỉ lệch dấu thì giữ: MRZ không có dấu nên không kiểm được, mà mặt trước OCR cũng hay lệch dấu (đo 2 / 2);
- ngày sinh: theo MRZ (năm hai chữ số + thế kỷ theo số định danh) khi lượt trích lệch.
KHÔNG lấy ngày cấp / cơ quan cấp / số định danh theo thẻ: chữ in mặt sau OCR cũng lệch, cán bộ giữ theo Đơn (đo trên 175
hồ sơ: đổi nhầm nhiều hơn đổi đúng). Không có thẻ cùng số thì giữ nguyên lượt trích.
"""

import re
import unicodedata

from app.pipelines._shared.cccd import id_birth_year, mrz_records

_PAGE_SPLIT_RE = re.compile(r"(?m)^[─\-=\s]*Trang\s+\d+\s*/\s*\d+[─\-=\s]*$|^=====.*=====$")
_FRONT_ID_RE = re.compile(r"(?i)s[ốo]\s*/\s*no\.?\s*:?\s*(\d{12})(?!\d)")
_NAME_RE = re.compile(r"(?i)h[ọo]\s*v[àa]\s*t[êe]n\s*/\s*full\s*name\s*:?\s*(.*)")
_BIRTH_RE = re.compile(r"(?i)ng[àa]y\s*sinh\s*/\s*date\s*of\s*birth\s*:?\s*(\d{1,2})/(\d{1,2})/(\d{4})")
_PEOPLE = ("NguoiDungRa", "NguoiChet", "NguoiUyQuyen")
# Dòng tên của MRZ ("HO<<TEN<DEM"); bản sao chứng thực hay dính chữ dấu chứng thực vào cuối dòng ("...<BAC<CNHO<SAO<ĐÚNG")
# nên chỉ lấy phần đầu toàn chữ in và "<", rồi so tên mặt trước với PHẦN ĐẦU các chữ của dòng này.
_MRZ_NAME_RE = re.compile(r"^([A-Z]+<<[A-Z<]+)")
_MRZ_LINE_RE = re.compile(r"IDVNM[O0-9]{10}(\d{12})")


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn").replace("Đ", "D").replace("đ", "d")
    return " ".join(re.findall(r"[a-z]+", text.lower()))


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def cards(ocr_text: str) -> dict[str, dict]:
    """{số định danh: {name, birth, mrz_name, mrz_birth}} của các thẻ đọc được, mỗi trang một lượt."""
    out: dict[str, dict] = {}
    for page in _PAGE_SPLIT_RE.split(str(ocr_text or "")):
        lines = [line.strip() for line in page.splitlines()]
        mrz = mrz_records(page)
        fronts = []
        for at, line in enumerate(lines):
            found = _FRONT_ID_RE.search(line)
            if not found:
                continue
            card = {"id": found.group(1)}
            for following in lines[at + 1:at + 6]:
                name = _NAME_RE.search(following)
                if name and "name" not in card:
                    text = name.group(1).strip() or next((x for x in lines[lines.index(following) + 1:] if x), "")
                    card["name"] = " ".join(text.split())
                birth = _BIRTH_RE.search(following)
                if birth and "birth" not in card:
                    card["birth"] = birth.groups()
            fronts.append(card)
        for card in fronts:
            out.setdefault(card["id"], {}).update({k: v for k, v in card.items() if k != "id"})
        names = _mrz_names(page)
        for record in mrz:
            entry = out.setdefault(record["id"], {})
            if names.get(record["id"]):
                entry["mrz_name"] = names[record["id"]]
            if record.get("birth"):
                entry["mrz_birth"] = record["birth"]
    return out


def _mrz_names(page: str) -> dict[str, list[str]]:
    """{số: các chữ tên (không dấu, chữ thường)} từ dòng tên MRZ đứng trong 3 dòng sau dòng IDVNM của thẻ."""
    lines = [re.sub(r"\s+", "", line) for line in page.splitlines()]
    out = {}
    for at, line in enumerate(lines):
        found = _MRZ_LINE_RE.search(line)
        if not found:
            continue
        for following in lines[at + 1:at + 4]:
            name = _MRZ_NAME_RE.match(following)
            if name:
                out[found.group(1)] = [word.lower() for word in re.split(r"<+", name.group(1)) if word]
                break
    return out


def _confirmed(front: str, mrz_words) -> bool:
    words = _fold(front).split()
    return bool(words) and bool(mrz_words) and list(mrz_words[:len(words)]) == words


def _date(day, month, year) -> str:
    return f"{int(day):02d}/{int(month):02d}/{int(year)}"


def apply(fields: list[dict], ocr_text: str) -> list[dict]:
    """Sửa nhân thân của người đứng ra / người chết / người ủy quyền theo thẻ cùng số (xem đầu file)."""
    found = cards(ocr_text)
    if not found:
        return fields
    values = {f.get("name"): f.get("value") for f in fields if isinstance(f, dict)}
    changes: dict[str, str] = {}
    for person in _PEOPLE:
        number = _digits(values.get(f"{person}_SoDinhDanh"))
        name = values.get(f"{person}_HoTen")
        card = found.get(number)
        if not card:
            continue
        front = card.get("name")
        if front and name and _confirmed(front, card.get("mrz_name")) and _fold(front) != _fold(name):
            changes[f"{person}_HoTen"] = front
        mrz_birth = card.get("mrz_birth")
        year = id_birth_year(number)
        if mrz_birth and year and year % 100 == mrz_birth[0]:
            birth = _date(mrz_birth[2], mrz_birth[1], year)
            if values.get(f"{person}_NgaySinh") and values.get(f"{person}_NgaySinh") != birth:
                changes[f"{person}_NgaySinh"] = birth
    if not changes:
        return fields
    out = [dict(f, value=changes.pop(f.get("name"))) if isinstance(f, dict) and f.get("name") in changes else f
           for f in fields]
    # Ô lượt trích bỏ trống mà thẻ có (ngày cấp, nơi cấp...) — chỉ cho người đã có trong lượt trích.
    out += [{"name": name, "value": value} for name, value in changes.items()]
    return out
