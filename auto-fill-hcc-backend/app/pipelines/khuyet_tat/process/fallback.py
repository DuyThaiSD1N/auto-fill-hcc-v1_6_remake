"""Đọc TẤT ĐỊNH cột "Có"/"Không" của bảng dạng khuyết tật từ OCR còn giữ ranh giới ô.

LLM đọc sai bảng này vì hai lý do lặp đi lặp lại:
 - OCR làm phẳng bảng ở các trang sau (mất dấu "|") nên dấu X đứng cuối dòng không còn cho biết
   nó thuộc cột "Có" hay cột "Không";
 - nhiều dòng có nhãn bắt đầu bằng "Có kết luận của cơ sở y tế..." nên chữ "Có" trong NỘI DUNG
   bị nhầm thành ô đánh dấu.

Khi OCR vẫn giữ dấu "|" thì cột là bằng chứng chắc chắn, không cần suy đoán: parser này đọc thẳng
và GHI ĐÈ kết quả của LLM cho ĐÚNG những dòng đọc được (dòng OCR làm phẳng vẫn để LLM quyết).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# Dấu tích có thể là X/x, ✓/✔/√, ☑/☒, hoặc bọc trong ngoặc "(x)", "[X]".
_TICK_RE = re.compile(r"^[\(\[\{]?\s*[xX✓✔√☑☒]\s*[\)\]\}]?$")
_ROW_NUMBER_RE = re.compile(r"^([1-6])(?:\s*[.,]\s*([1-7]))?[.,]?$")


def _fold(value: Any) -> str:
    text = str(value or "").replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(re.sub(r"[^0-9a-zA-Z]+", " ", text).split()).lower()


def _cells(line: str) -> list[str] | None:
    """Tách 1 dòng bảng dạng "| a | b | c |" thành các ô; không phải dòng bảng thì trả None."""
    stripped = line.strip()
    if stripped.count("|") < 2:
        return None
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _row_key(cell: str) -> str:
    """Ô STT -> khóa dòng chuẩn ("1", "1.1"); không phải số thứ tự thì trả ""."""
    found = _ROW_NUMBER_RE.match(cell.strip())
    if not found:
        return ""
    return f"{found.group(1)}.{found.group(2)}" if found.group(2) else found.group(1)


def _header_columns(cells: list[str]) -> tuple[int, int] | None:
    """Chỉ số cột (Có, Không) nếu dòng này là dòng tiêu đề bảng."""
    folded = [_fold(cell) for cell in cells]
    if "co" in folded and "khong" in folded:
        return folded.index("co"), folded.index("khong")
    return None


def _tick_columns(cells: list[str]) -> tuple[int, int] | None:
    """Suy cột đánh dấu khi bảng không có dòng tiêu đề: hai ô CUỐI chỉ chứa dấu tích/để trống."""
    tail = [index for index in range(len(cells) - 1, 0, -1)
            if not cells[index] or _TICK_RE.match(cells[index])]
    ordered = sorted(tail)
    # Phải là hai ô liền nhau ở cuối dòng, đúng thứ tự "Có" rồi "Không" như mẫu số 01.
    if len(ordered) >= 2 and ordered[-1] == len(cells) - 1 and ordered[-2] == len(cells) - 2:
        return ordered[-2], ordered[-1]
    return None


def parse_disability_table(text: str) -> dict[str, str]:
    """{"1.1": "khong", "4": "co", "1.6": "", ...} cho các dòng mà OCR còn giữ cột.

    Value "" nghĩa là ĐỌC ĐƯỢC cả hai ô và cả hai đều trống (đơn bỏ trống dòng đó) — khác hẳn với
    dòng không có trong dict (OCR làm phẳng, không kết luận được). Dòng "" dùng để phủ quyết phán
    đoán "co" của LLM ở các dòng có nhãn "Có kết luận của cơ sở y tế...".
    """
    out: dict[str, str] = {}
    columns: tuple[int, int] | None = None
    for line in str(text or "").splitlines():
        cells = _cells(line)
        if not cells:
            continue
        header = _header_columns(cells)
        if header:
            columns = header
            continue
        key = _row_key(cells[0])
        if not key:
            continue
        # Ưu tiên cột theo tiêu đề của chính bảng đang đọc; bảng mất tiêu đề thì suy từ đuôi dòng.
        pair = columns if columns and max(columns) < len(cells) else _tick_columns(cells)
        if not pair:
            continue
        co_cell, khong_cell = cells[pair[0]], cells[pair[1]]
        co = bool(_TICK_RE.match(co_cell))
        khong = bool(_TICK_RE.match(khong_cell))
        if co and khong:  # đánh cả hai cột -> mâu thuẫn, không kết luận
            continue
        if co or khong:
            out[key] = "co" if co else "khong"
        elif not co_cell and not khong_cell:
            out[key] = ""  # đọc được cột, cả hai ô rỗng -> đơn bỏ trống dòng này
    return out


def _as_dict(raw_fields: Any) -> dict[str, Any]:
    if isinstance(raw_fields, dict):
        return dict(raw_fields)
    if isinstance(raw_fields, list):
        return {item.get("name"): item.get("value") for item in raw_fields
                if isinstance(item, dict) and item.get("name")}
    return {}


def apply_ocr_fallback(raw_fields: Any, documents: list[dict]) -> dict[str, Any]:
    """Ghi đè KhuyetTat_BangDanhDau bằng các dòng đọc được cột trực tiếp từ OCR."""
    fields = _as_dict(raw_fields)
    parsed: dict[str, str] = {}
    for doc in documents or []:
        parsed.update(parse_disability_table((doc or {}).get("text") or ""))
    if not parsed:
        return fields

    table = fields.get("KhuyetTat_BangDanhDau")
    merged = dict(table) if isinstance(table, dict) else {}
    merged.update(parsed)  # cột đọc trực tiếp thắng suy đoán của LLM
    fields["KhuyetTat_BangDanhDau"] = merged
    return fields
