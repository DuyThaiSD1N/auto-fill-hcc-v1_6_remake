"""Bốn chủ thể của hồ sơ đăng ký lại khai sinh: người được đăng ký lại (con), mẹ, cha, người yêu cầu.

Vai đã do bước phân vai chốt (reason.py) và lượt trích ghi theo tiền tố field (Subject_ / Mother_ / Father_ /
Requester_). Thanh tra không phân vai lại: chỉ soát cách viết của chính người đã nằm ở vai đó.
"""

import re
from dataclasses import dataclass

from app.pipelines._shared.thanh_tra.ho_so import fold


@dataclass(frozen=True)
class Role:
    key: str        # "con" / "me" / "cha" / "nyc"
    prefix: str     # tiền tố field lượt trích
    label: str      # nhãn dùng trong biên bản
    birth: str      # field ngày / năm sinh của vai ("" = không có)
    ethnic: str     # field dân tộc của vai ("" = không có)
    residence: str  # field nơi cư trú của vai ("" = không có)
    page_roles: tuple[str, ...]  # chữ (bỏ dấu) của "vai trên trang" chỉ ĐÚNG vai này trên giấy hộ tịch / tờ khai


ROLES = (
    Role("con", "Subject", "người được đăng ký lại khai sinh", "Subject_BirthDate", "Subject_Ethnicity", "",
         ("duoc khai sinh", "duoc dang ky lai")),
    Role("me", "Mother", "mẹ", "Mother_BirthDateOrYear", "Mother_Ethnicity", "Mother_ResidenceDomestic",
         ("me",)),
    Role("cha", "Father", "cha", "Father_BirthDateOrYear", "Father_Ethnicity", "Father_ResidenceDomestic",
         ("cha", "bo")),
    Role("nyc", "Requester", "người yêu cầu", "", "", "Requester_ResidenceDomestic",
         ("nguoi yeu cau",)),
)
ROLE_BY_KEY = {role.key: role for role in ROLES}


def digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def birth_year(value) -> int | None:
    found = re.findall(r"(?<!\d)(1[89]\d{2}|20\d{2})(?!\d)", str(value or ""))
    return int(found[-1]) if found else None


def identity(values: dict, role: Role) -> dict:
    return {
        "name": " ".join(str(values.get(f"{role.prefix}_FullName") or "").split()),
        "number": digits(values.get(f"{role.prefix}_IdNumber")),
        "birth": str(values.get(role.birth) or "").strip() if role.birth else "",
        "ethnic": str(values.get(role.ethnic) or "").strip() if role.ethnic else "",
    }


def plays(page_role: str, role: Role) -> bool:
    """Vai trên trang (model chép) chỉ đúng vai đang xét: so theo TỪ, "mẹ" không khớp "mẹ kế" / "người mẹ nuôi"."""
    words = fold(page_role).replace(",", " ").split()
    text = " ".join(words)
    if any(extra in words for extra in ("nuoi", "ke", "vo", "chong")):
        return False
    return any(re.search(rf"(?<![a-z]){re.escape(marker)}(?![a-z])", text) for marker in role.page_roles)


_ISSUED_MARKERS = ("trich luc", "giay khai sinh", "giay chung tu", "giay bao tu")
_SELF_MADE_MARKERS = ("to khai", "cam doan", "cam ket", "don ", "uy quyen", "xac nhan")
_HEADER_LINES = 12


def issued(page_lines: list[str]) -> bool:
    """Trang là giấy do cơ quan hộ tịch cấp (trích lục, giấy khai sinh, giấy khai tử). Bản cam đoan, đơn, tờ khai khác
    cũng do người dân tự viết / tự gõ — OCR không phân biệt được chữ in hay chữ viết tay của các giấy đó."""
    head = " ".join(fold(line) for line in page_lines[:_HEADER_LINES])
    return any(marker in head for marker in _ISSUED_MARKERS) and not any(marker in head for marker in _SELF_MADE_MARKERS)
