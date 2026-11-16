"""Hai chủ thể của hồ sơ đăng ký lại kết hôn (chồng = bên nam, vợ = bên nữ) và khối vợ / chồng của tờ khai.

Mỗi bên là một người, nhân thân đọc từ thẻ của chính họ và từ khối của họ trên tờ khai. Mọi thanh tra chạy cho TỪNG
bên và chỉ nhận nguồn mà MÃ gắn được với đúng bên đó.
"""

import re
from dataclasses import dataclass

from app.pipelines._shared.thanh_tra.ho_so import fold

from ..process import mapper


@dataclass(frozen=True)
class Side:
    key: str       # "nam" / "nu"
    card: str      # tiền tố field đọc từ thẻ và giấy khác: BenNam / BenNu
    declared: str  # tiền tố field đọc từ khối tờ khai: ToKhaiNam / ToKhaiNu
    label: str     # nhãn dùng trong biên bản
    gender: str


SIDES = (Side("nam", "BenNam", "ToKhaiNam", "bên chồng", "Nam"), Side("nu", "BenNu", "ToKhaiNu", "bên vợ", "Nữ"))
_IDENTITY_KEYS = ("HoTen", "SoDinhDanh", "NgaySinh", "NgayCap", "NoiCap")
AREA = "NoiCuTru_TrongNuoc"


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _other(side: Side) -> Side:
    return next(item for item in SIDES if item is not side)


def card_is_other(values: dict, side: Side) -> bool:
    """Thẻ đọc ra lệch cả tên lẫn số so với khối tờ khai: mapper bỏ thẻ, điền theo tờ khai."""
    return mapper._card_is_other_person(
        values.get(f"{side.card}_HoTen"), values.get(f"{side.card}_SoDinhDanh"),
        values.get(f"{side.declared}_HoTen"), values.get(f"{side.declared}_SoDinhDanh"),
        values.get(f"{_other(side).card}_SoDinhDanh"))


def _has_area(value) -> bool:
    return isinstance(value, dict) and bool(value.get("tinh") or value.get("xa") or value.get("diaChi"))


def effective(values: dict) -> dict:
    """Giá trị mapper SẼ dùng để điền, đặt về field mà thanh tra soát và ghi đè: nhân thân ở field thẻ (thẻ trước, tờ
    khai bù ô thẻ thiếu), nơi cư trú ở field tờ khai (tờ khai trước, thẻ bù). Bên có thẻ của người khác thì giữ nguyên
    — mapper điền bên đó theo tờ khai và các thanh tra nhân thân bỏ qua."""
    out = dict(values)
    for side in SIDES:
        if card_is_other(values, side):
            continue
        for key in _IDENTITY_KEYS:
            if not out.get(f"{side.card}_{key}") and out.get(f"{side.declared}_{key}"):
                out[f"{side.card}_{key}"] = out[f"{side.declared}_{key}"]
        if not _has_area(out.get(f"{side.declared}_{AREA}")) and _has_area(out.get(f"{side.card}_{AREA}")):
            out[f"{side.declared}_{AREA}"] = out[f"{side.card}_{AREA}"]
    return out


def identity(values: dict, side: Side) -> dict:
    """Nhân thân đang dùng của một bên (trên giá trị đã qua ``effective``)."""
    return {"name": " ".join(str(values.get(f"{side.card}_HoTen") or "").split()),
            "number": _digits(values.get(f"{side.card}_SoDinhDanh")),
            "birth": values.get(f"{side.card}_NgaySinh"),
            "ethnic": values.get(f"{side.declared}_DanToc") or values.get(f"{side.card}_DanToc")}


# Tờ khai đăng ký lại kết hôn chia KHỐI theo dòng: "Họ, chữ đệm, tên của vợ: ..." rồi các dòng ngày sinh, dân tộc, nơi
# cư trú, giấy tờ tùy thân của người đó; tiếp theo là khối của chồng.
_HEAD_RE = re.compile(r"^ho,? chu dem,?( va)? ten (cua )?(vo|chong)\b")
_ROWS = (("ngay_sinh", re.compile(r"^ngay,? thang,? nam sinh")),
         ("dan_toc", re.compile(r"^dan toc")),
         ("cu_tru", re.compile(r"^noi cu tru")),
         ("giay_to", re.compile(r"^giay to tuy than")))
_BLOCK_END_RE = re.compile(r"^(da dang ky ket hon|theo giay chung nhan|chung toi cam doan|de nghi cap ban sao|"
                           r"ho,? chu dem,?( va)? ten nguoi yeu cau|lam tai)")
_FOOTNOTE_RE = re.compile(r"^\s*\(\d\)\s*")
_MAX_BLOCK_LINES = 12


def _lead(line: str) -> str:
    return re.sub(r"^\W+", "", fold(line))


def _value(line: str) -> str:
    return _FOOTNOTE_RE.sub("", line.split(":", 1)[1]).strip() if ":" in line else ""


def declaration_tables(documents: list[dict]) -> list[dict]:
    """Khối vợ / chồng của các tờ khai đăng ký lại kết hôn: [{doc, order: ("nu", "nam"), rows: {hàng: {"cells":
    [ô của vợ, ô của chồng], "line": dòng OCR của hàng}}}] — cùng khuôn với bảng hai cột của tờ khai đăng ký kết hôn để
    các thanh tra đọc như nhau. Dòng nơi cư trú xuống dòng không nhãn thì nối lại; khối thiếu hàng nào thì ô đó rỗng."""
    tables = []
    for index, document in enumerate(documents, start=1):
        text = str(document.get("text") or "")
        if "to khai dang ky lai ket hon" not in fold(text):
            continue
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        found: dict[str, dict[str, tuple[str, str]]] = {}
        for at, line in enumerate(lines):
            head = _HEAD_RE.match(_lead(line))
            if not head:
                continue
            key = "nu" if head.group(3) == "vo" else "nam"
            if key in found:
                continue
            block = {"ho_ten": (_value(line), line)}
            for row_at in range(at + 1, min(len(lines), at + 1 + _MAX_BLOCK_LINES)):
                following = lines[row_at]
                lead = _lead(following)
                if _HEAD_RE.match(lead) or _BLOCK_END_RE.match(lead):
                    break
                row = next((name for name, pattern in _ROWS if pattern.match(lead)), "")
                if not row or row in block:
                    continue
                value = _value(following)
                if row == "dan_toc":
                    value = re.split(r"\s+quoc tich|\s+Quốc tịch", value, maxsplit=1, flags=re.IGNORECASE)[0].strip()
                if row == "cu_tru" and row_at + 1 < len(lines):
                    nxt = lines[row_at + 1]
                    if ":" not in nxt and not _HEAD_RE.match(_lead(nxt)) and not _BLOCK_END_RE.match(_lead(nxt)) and len(nxt) < 70:
                        value = f"{value.rstrip(' ,')}, {nxt}"
                block[row] = (value.strip(" ,"), following)
            found[key] = block
        if found:
            rows = {}
            for row in ("ho_ten", "ngay_sinh", "dan_toc", "cu_tru", "giay_to"):
                cells = [found.get(key, {}).get(row, ("", ""))[0] for key in ("nu", "nam")]
                line = next((found[key][row][1] for key in ("nu", "nam") if row in found.get(key, {})), "")
                if any(cells):
                    rows[row] = {"line": line, "cells": cells, "lines": [found.get(key, {}).get(row, ("", ""))[1]
                                                                          for key in ("nu", "nam")]}
            tables.append({"doc": index, "order": ("nu", "nam"), "rows": rows})
    return tables


def cell(table: dict, row: str, side: Side) -> tuple[str, str]:
    """(ô của bên đó ở một hàng, dòng OCR của ô đó) — ("", "") khi khối không có hàng đó."""
    found = table["rows"].get(row)
    if not found or side.key not in table["order"]:
        return "", ""
    at = table["order"].index(side.key)
    return found["cells"][at], found["lines"][at] or found["line"]
