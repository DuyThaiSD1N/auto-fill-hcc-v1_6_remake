"""Hồ sơ vụ việc của lớp soát thứ hai: kiểu dữ liệu và phần chứng cứ do MÃ tìm trong OCR (không qua LLM)."""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from typing import Callable

_MIN_QUOTE_CHARS = 6
_MAX_HITS = 3
# Tiền tố cấp hành chính không làm hai địa danh khác nhau ("Xã Vũ Ninh" / "Vũ Ninh").
_ADMIN_PREFIX_RE = re.compile(r"^(tinh|thanh pho|tp|quan|huyen|thi xa|thi tran|phuong|xa|dac khu)\s+")
_AREA_KEYS = ("tinh", "huyen", "xa", "diaChi")


@dataclass(frozen=True)
class Field:
    """Một field schema. kind quyết định cách so và cách kiểm giá trị có thật trong OCR:
    literal = chép nguyên chữ (so có dấu); code = số / mã (so chữ số + chữ cái); date = dd/mm/yyyy;
    area = object địa chỉ; free = giá trị được chuẩn hoá (cơ quan, loại giấy) — chỉ kiểm dòng chứng cứ."""
    name: str
    label: str
    kind: str = "literal"
    canon: Callable[[object], str] | None = None  # khóa so sánh riêng của field
    same: Callable[[object, object], bool] | None = None  # hai khóa khác nhau nhưng vẫn coi là một giá trị


@dataclass(frozen=True)
class Unit:
    """Đơn vị phân xử: một ô, hoặc một cụm ô phải đi cùng nhau từ một giấy (vd cụm giấy tờ tùy thân)."""
    key: str
    label: str
    fields: tuple[Field, ...]


@dataclass(frozen=True)
class Inspector:
    key: str
    title: str
    units: tuple[Unit, ...]
    rules: str  # nghiệp vụ của nhóm: thanh tra làm theo, toà án phán theo
    # (unit, values, case) → lý do bác ứng viên của thanh tra, "" = đạt
    check: Callable[[Unit, dict, "Case"], str] | None = None
    # (unit, values, case) → tín hiệu tất định về một ứng viên: [(khớp hay lệch, mô tả)]
    signals: Callable[[Unit, dict, "Case"], list[tuple[bool, str]]] | None = None
    # Câu hỏi đóng "dòng chứng cứ thuộc về ai / giấy nào": owners là các lựa chọn, accepted là lựa chọn hợp lệ.
    # Thanh tra tự khai dòng thuộc đối tượng khác thì ứng viên bị bác trước toà.
    owners: tuple[str, ...] = ()
    accepted: tuple[str, ...] = ()
    # Cách tìm ứng viên RIÊNG của thanh tra: async (inspector, case, title) → list[Finding]. Không khai thì dùng
    # cách mặc định của khung (một lượt LLM đọc lại cả hồ sơ). Mỗi nhóm thông tin có cách kiểm khác nhau.
    find: Callable | None = None


@dataclass
class Case:
    """Hồ sơ vụ việc: OCR từng tài liệu, kết quả phân vai, field lượt trích đã qua validate."""
    documents: list[dict]
    context: str
    values: dict
    options: dict = field(default_factory=dict)


@dataclass
class Finding:
    inspector: Inspector
    unit: Unit
    values: dict
    quote: str
    doc: int
    note: str = ""
    owner: str = ""
    backed: bool = False  # thanh tra đã tự có căn cứ bằng mã (vd nhiều nguồn độc lập cùng ghi) để thay lượt trích
    evidence: tuple = ()  # dòng tín hiệu mã kèm theo cho toà


@dataclass
class Dispute:
    id: int
    finding: Finding
    current: dict  # giá trị lượt trích của các field trong đơn vị
    kind: str  # "bo_sung" (lượt trích bỏ trống) | "tranh_chap"
    conflict: bool = False  # có field hai bên cùng có giá trị mà khác nhau
    differing: tuple = ()  # các field lệch nhau


@dataclass
class Result:
    values: dict
    rulings: list[dict]
    timing: dict


def fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("Đ", "D").replace("đ", "d").lower()


def alnum(value) -> str:
    return re.sub(r"[^0-9a-z]+", "", fold(value))


def _spell(value) -> str:
    """Giữ dấu tiếng Việt, bỏ khác biệt hoa/thường và dấu câu: hai cách viết khác dấu là hai giá trị khác nhau."""
    text = unicodedata.normalize("NFC", str(value or "")).casefold()
    return " ".join(re.findall(r"[^\W_]+", text))


def parse_date(value) -> date | None:
    match = re.match(r"^\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\s*$", str(value or ""))
    if not match:
        return None
    try:
        return date(int(match[3]), int(match[2]), int(match[1]))
    except ValueError:
        return None


def _place(value) -> str:
    return _ADMIN_PREFIX_RE.sub("", " ".join(re.findall(r"[0-9a-z]+", fold(value))))


def is_empty(value) -> bool:
    if isinstance(value, dict):
        return not any(str(value.get(key) or "").strip() for key in _AREA_KEYS)
    return value is None or not str(value).strip()


def compare_key(spec: Field, value):
    """Khóa so sánh hai giá trị của cùng một field."""
    if is_empty(value):
        return None
    if spec.canon:
        return spec.canon(value)
    if spec.kind == "area":
        if not isinstance(value, dict):
            return _spell(value)
        return tuple(_place(value.get(key)) if key != "diaChi" else _spell(value.get(key))
                     for key in ("tinh", "xa", "diaChi"))
    if spec.kind == "date":
        return parse_date(value) or _spell(value)
    if spec.kind == "code":
        return alnum(value)
    return _spell(value)


def _date_needles(value) -> list[str]:
    parsed = parse_date(value)
    if not parsed:
        return []
    d, m, y = parsed.day, parsed.month, parsed.year
    return [f"{d:02d}{m:02d}{y}", f"{d}{m}{y}", f"ngay{d:02d}thang{m:02d}nam{y}", f"ngay{d}thang{m}nam{y}",
            f"ngay{d:02d}thang{m}nam{y}", f"ngay{d}thang{m:02d}nam{y}"]


def _line_has(spec: Field, value, line: str) -> bool:
    if spec.kind == "date":
        squeezed = alnum(line)
        return any(needle in squeezed for needle in _date_needles(value))
    if spec.kind == "code":
        needle = alnum(value)
        return len(needle) >= 2 and needle in alnum(line)
    if spec.canon:  # field có cách viết tương đương (vd "UBND" / "Ủy ban nhân dân") → so theo khóa của field
        needle = spec.canon(value)
        return bool(needle) and needle in spec.canon(line)
    needle = _spell(value)
    return bool(needle) and needle in _spell(line)


def _area_parts(value) -> list[str]:
    if not isinstance(value, dict):
        return [str(value)]
    return [str(value.get(key)) for key in ("diaChi", "xa") if str(value.get(key) or "").strip()]


def locate(spec: Field, value, documents: list[dict]) -> list[str]:
    """Dòng OCR chứa giá trị (tối đa vài dòng, kèm số tài liệu) — bằng chứng do mã tìm, không qua LLM."""
    if is_empty(value):
        return []
    hits: list[str] = []
    for index, document in enumerate(documents, start=1):
        for line in str(document.get("text") or "").splitlines():
            if not line.strip():
                continue
            if spec.kind == "area":
                found = any(_place(part) and _place(part) in _place_line(line) for part in _area_parts(value))
            else:
                found = _line_has(spec, value, line)
            if found:
                hits.append(f'tài liệu {index}: "{line.strip()[:160]}"')
                if len(hits) >= _MAX_HITS:
                    return hits
    return hits


def _place_line(line: str) -> str:
    return " ".join(re.findall(r"[0-9a-z]+", fold(line)))


def quote_in_documents(quote: str, documents: list[dict]) -> bool:
    needle = alnum(quote)
    return len(needle) >= _MIN_QUOTE_CHARS and any(needle in alnum(d.get("text")) for d in documents)


def surrounding(quote: str, documents: list[dict], radius: int = 2) -> str:
    """Đoạn OCR quanh dòng chứng cứ (kèm tài liệu và mấy dòng đầu giấy) để toà biết dòng đó thuộc khối nào."""
    needle = alnum(quote)
    if len(needle) < _MIN_QUOTE_CHARS:
        return ""
    for index, document in enumerate(documents, start=1):
        lines = [line.strip() for line in str(document.get("text") or "").splitlines() if line.strip()]
        for at, line in enumerate(lines):
            if needle in alnum(line) or alnum(line) and alnum(line) in needle and len(alnum(line)) >= _MIN_QUOTE_CHARS:
                head = " | ".join(lines[:2])[:160]
                window = "\n".join(f"    {text[:200]}" for text in lines[max(0, at - radius):at + radius + 1])
                return f"tài liệu {index} (đầu giấy: {head})\n{window}"
    return ""
