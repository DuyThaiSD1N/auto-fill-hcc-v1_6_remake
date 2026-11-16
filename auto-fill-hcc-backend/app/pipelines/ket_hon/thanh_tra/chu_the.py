"""Hai chủ thể của hồ sơ đăng ký kết hôn (bên nam, bên nữ) và bảng hai cột của tờ khai.

Hồ sơ kết hôn không có bước phân vai: mỗi bên là một người, nhân thân đọc từ thẻ của chính họ và từ cột của họ trên tờ
khai. Mọi thanh tra chạy cho TỪNG bên và chỉ nhận nguồn mà MÃ gắn được với đúng bên đó.
"""

import re
from dataclasses import dataclass

from app.pipelines._shared.thanh_tra.ho_so import fold

from ..process import mapper


@dataclass(frozen=True)
class Side:
    key: str       # "nam" / "nu"
    card: str      # tiền tố field đọc từ thẻ và giấy khác: BenNam / BenNu
    declared: str  # tiền tố field đọc từ cột tờ khai: ToKhaiNam / ToKhaiNu
    label: str     # nhãn dùng trong biên bản
    gender: str


SIDES = (Side("nam", "BenNam", "ToKhaiNam", "bên nam", "Nam"), Side("nu", "BenNu", "ToKhaiNu", "bên nữ", "Nữ"))
_IDENTITY_KEYS = ("HoTen", "SoDinhDanh", "NgaySinh", "NgayCap", "NoiCap")
AREA = "NoiCuTru_TrongNuoc"


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def card_is_other(values: dict, side: Side) -> bool:
    """Thẻ đọc ra lệch cả tên lẫn số so với cột tờ khai: mapper bỏ thẻ, điền theo tờ khai."""
    return mapper._card_is_other_person(
        values.get(f"{side.card}_HoTen"), values.get(f"{side.card}_SoDinhDanh"),
        values.get(f"{side.declared}_HoTen"), values.get(f"{side.declared}_SoDinhDanh"))


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


# Các hàng của bảng "Thông tin | Bên nữ | Bên nam" trên tờ khai đăng ký kết hôn.
_ROWS = (("ho_ten", re.compile(r"ho,? chu dem,?( va)? ten|ho va ten")),
         ("ngay_sinh", re.compile(r"ngay,? thang,? nam sinh")),
         ("dan_toc", re.compile(r"dan toc")),
         ("quoc_tich", re.compile(r"quoc tich")),
         ("cu_tru", re.compile(r"noi cu tru")),
         ("giay_to", re.compile(r"giay to tuy than")),
         ("so_lan", re.compile(r"ket hon lan thu may")))
_TABLE_END_RE = re.compile(r"^\W*(chung toi cam doan|de nghi quy co quan|de nghi cap ban sao)")
_SEPARATOR_RE = re.compile(r"^[\s|:\-]+$")
_MAX_TABLE_LINES = 60


def _row_key(line: str) -> str:
    head = fold(line.lstrip(" |"))[:40]
    return next((key for key, pattern in _ROWS if pattern.match(head)), "")


def declaration_tables(documents: list[dict]) -> list[dict]:
    """Bảng hai cột của các tờ khai đăng ký kết hôn: [{doc, order: (bên của cột 1, bên của cột 2), rows: {hàng:
    {"cells": [ô cột 1, ô cột 2], "line": dòng OCR đầu của hàng}}}]. Thứ tự cột lấy ở dòng tiêu đề "Bên nữ | Bên nam";
    ô xuống nhiều dòng được nối lại; hàng không tách ra đúng hai ô thì bỏ (không đoán ô nào của ai)."""
    tables = []
    for index, document in enumerate(documents, start=1):
        lines = [line.rstrip() for line in str(document.get("text") or "").splitlines()]
        for at, line in enumerate(lines):
            head = fold(line)
            if "|" not in line or "ben nu" not in head or "ben nam" not in head:
                continue
            order = ("nu", "nam") if head.index("ben nu") < head.index("ben nam") else ("nam", "nu")
            # OCR có khi dựng thêm cột trống giữa cột nhãn và hai cột bên ("| Thông tin | | Bên nữ | Bên nam |"):
            # hàng đủ số ô như dòng tiêu đề thì lấy ô theo vị trí hai cột bên, chỉ khi cột thừa trống.
            heads = [fold(cell) for cell in line.strip().strip("|").split("|")]
            sides = [at_col for at_col, cell in enumerate(heads) if "ben nu" in cell or "ben nam" in cell]
            rows: dict[str, dict] = {}
            current = ""
            for following in lines[at + 1:at + 1 + _MAX_TABLE_LINES]:
                if not following.strip() or _SEPARATOR_RE.match(following):
                    continue
                if _TABLE_END_RE.match(fold(following)):
                    break
                key = _row_key(following)
                if key and key not in rows:
                    current = key
                    rows[key] = {"line": following.strip(), "text": following.strip()}
                elif current:
                    rows[current]["text"] += "\n" + following.strip()
            for key, row in list(rows.items()):
                cells = [" ".join(cell.replace("\n", ", ").split()).strip(" ,") for cell in row["text"].strip(" |").split("|")]
                if len(cells) == 3:
                    rows[key] = {"line": row["line"], "cells": cells[1:]}
                elif len(heads) > 3 and len(cells) == len(heads) and len(sides) == 2 and not any(
                        cells[col] for col in range(1, len(cells)) if col not in sides):
                    rows[key] = {"line": row["line"], "cells": [cells[col] for col in sides]}
                else:
                    del rows[key]
            if rows:
                tables.append({"doc": index, "order": order, "rows": rows})
            break  # mỗi tài liệu một tờ khai
    return tables


def cell(table: dict, row: str, side: Side) -> tuple[str, str]:
    """(ô của bên đó ở một hàng, dòng OCR của hàng) — ("", "") khi bảng không có hàng đó."""
    found = table["rows"].get(row)
    if not found or side.key not in table["order"]:
        return "", ""
    return found["cells"][table["order"].index(side.key)], found["line"]
