"""Tên thành phần hồ sơ cho giấy tờ hộ tịch — dùng chung cho nhánh tách và không tách.

Giấy bản chính và trích lục là hai giấy KHÁC NHAU (Giấy khai sinh ≠ Trích lục khai sinh). Tên chọn theo
TIÊU ĐỀ LLM đọc trên giấy, trong danh sách được phép của từng loại; ngoài danh sách thì về nhãn mặc định.
"Giấy chứng nhận kết hôn" giữ nhãn cũ "Giấy đăng ký kết hôn" của eForm (contract có test khoá).
"""

import re

from app.pipelines._shared import fold as _fold

BIRTH_LABEL = "Giấy khai sinh"
MARRIAGE_LABEL = "Giấy đăng ký kết hôn"
DEATH_LABEL = "Trích lục khai tử"

DEFAULT_LABELS = {
    "civil_status_birth": BIRTH_LABEL,
    "civil_status_marriage": MARRIAGE_LABEL,
    "civil_status_death": DEATH_LABEL,
}

_TITLES_BY_TYPE: dict[str, dict[str, str]] = {
    "civil_status_birth": {
        "giay khai sinh": BIRTH_LABEL,
        "trich luc khai sinh": "Trích lục khai sinh",
    },
    "civil_status_marriage": {
        "giay chung nhan ket hon": MARRIAGE_LABEL,
        "giay dang ky ket hon": MARRIAGE_LABEL,
        "trich luc ket hon": "Trích lục kết hôn",
        "trich luc ghi chu ket hon": "Trích lục ghi chú kết hôn",
    },
    "civil_status_death": {
        "trich luc khai tu": DEATH_LABEL,
        "giay chung tu": "Giấy chứng tử",
    },
}


def is_civil_status(doc_type: str) -> bool:
    return doc_type in _TITLES_BY_TYPE


def civil_status_name(doc_type: str, *titles: str) -> str:
    """Tên theo tiêu đề đầu tiên KHỚP ĐÚNG danh sách của loại; không khớp → nhãn mặc định.

    Bỏ phần trong ngoặc ("Giấy khai sinh (bản sao)") và dấu câu hai đầu rồi so KHỚP ĐÚNG, không khớp
    chuỗi con — khớp chuỗi con thì "Trích lục khai sinh" vẫn trúng "khai sinh" của Giấy khai sinh.
    """
    names = _TITLES_BY_TYPE.get(doc_type, {})
    for title in titles:
        key = _fold(re.sub(r"\([^)]*\)", " ", str(title or ""))).strip(" .,:;-")
        if key in names:
            return names[key]
    return DEFAULT_LABELS.get(doc_type, "")
