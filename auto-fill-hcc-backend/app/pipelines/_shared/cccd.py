"""Thông tin mã hoá trong số căn cước 12 chữ số: chữ số thứ 4 là giới tính + thế kỷ sinh, hai chữ số kế
tiếp là năm sinh. Dùng để soát số OCR đọc ra có đúng của người đang xét không."""
import re
import unicodedata

_ID_CENTURY_BY_CODE = {"0": 1900, "1": 1900, "2": 2000, "3": 2000, "4": 2100, "5": 2100, "8": 1800, "9": 1800}


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d").lower()).strip()


def id_birth_year(id_number, gender=None) -> int | None:
    """Năm sinh mã hoá trong số CCCD; None nếu không đọc được hoặc giới tính mã hoá lệch thẻ.

    Giới tính in trên thẻ lệch với mã trong số thì chính con số đang bị OCR đọc sai → không tin.
    """
    digits = _digits(id_number)
    if len(digits) != 12 or digits[3] not in _ID_CENTURY_BY_CODE:
        return None
    folded_gender = _fold(gender)
    id_is_female = int(digits[3]) % 2 == 1
    if folded_gender in {"nam", "male"} and id_is_female:
        return None
    if folded_gender in {"nu", "female"} and not id_is_female:
        return None
    return _ID_CENTURY_BY_CODE[digits[3]] + int(digits[4:6])


def id_gender(id_number) -> str:
    """Giới tính mã hoá trong số CCCD 12 chữ số (chữ số thứ 4 chẵn = Nam, lẻ = Nữ)."""
    digits = _digits(id_number)
    if len(digits) != 12 or digits[3] not in _ID_CENTURY_BY_CODE:
        return ""
    return "Nữ" if int(digits[3]) % 2 else "Nam"
