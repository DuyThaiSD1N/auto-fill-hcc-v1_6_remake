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


# Vùng máy đọc (MRZ) mặt sau thẻ căn cước: ba dòng in máy, OCR đọc ổn định hơn chữ trên mặt thẻ.
# Dòng 1 "IDVNM" + 9 số cuối + số kiểm + đủ 12 số; dòng 2 ngày sinh YYMMDD + số kiểm + giới tính; dòng 3 họ tên
# không dấu, họ và tên ngăn bằng "<<". OCR hay đọc số 0 đầu thành chữ O.
_MRZ_ID_RE = re.compile(r"IDVNM[O0-9]{10}(\d{12})")
_MRZ_BIRTH_RE = re.compile(r"^(\d{2})(\d{2})(\d{2})\d([MF])\d{6}")
_MRZ_NAME_RE = re.compile(r"^[A-Z]+<<[A-Z<]+$")
_MRZ_LOOKAHEAD_LINES = 4


def mrz_records(text) -> list[dict]:
    """Các thẻ căn cước có vùng MRZ trong văn bản OCR → [{id, birth: (yy, mm, dd), gender, name}] (name không dấu,
    chữ thường). Trường nào không đọc được thì vắng."""
    lines = [re.sub(r"\s+", "", line) for line in str(text or "").splitlines()]
    records = []
    for index, line in enumerate(lines):
        match = _MRZ_ID_RE.search(line)
        if not match:
            continue
        record: dict = {"id": match[1]}
        for following in lines[index + 1:index + 1 + _MRZ_LOOKAHEAD_LINES]:
            birth = _MRZ_BIRTH_RE.match(following)
            if birth and "birth" not in record:
                record["birth"] = (int(birth[1]), int(birth[2]), int(birth[3]))
                record["gender"] = "Nam" if birth[4] == "M" else "Nữ"
            elif _MRZ_NAME_RE.match(following) and "name" not in record:
                record["name"] = " ".join(following.replace("<", " ").split()).lower()
        records.append(record)
    return records
