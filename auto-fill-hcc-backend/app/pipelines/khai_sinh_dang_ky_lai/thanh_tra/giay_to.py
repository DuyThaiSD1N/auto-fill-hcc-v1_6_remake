"""Thanh tra GIẤY TỜ TÙY THÂN hồ sơ đăng ký lại khai sinh: số định danh và ngày cấp của mẹ, cha, người yêu cầu.

Mã thuần, không gọi model:
1. Số định danh: vùng MRZ ở mặt sau thẻ mang họ tên (không dấu) đúng người ở vai đó, giới tính mã hoá trong số khớp vai
   (mẹ nữ, cha nam), năm sinh trong số khớp ngày sinh in ở MRZ → số theo MRZ khi lượt trích bỏ trống hoặc khác. Ba dòng
   MRZ in máy đọc ổn định hơn chữ số trên mặt thẻ / tờ khai viết tay.
2. Ngày cấp: mặt sau thẻ mang ĐÚNG số định danh của vai (khối kết thúc bằng dải MRZ của chính thẻ) → ngày cấp in trên
   đó. Lượt trích bỏ trống → bổ sung; lượt trích khác → đổi khi ngày trên thẻ được nhiều giấy ghi hơn (đếm số giấy).
"""

import re

from app.pipelines._shared.cccd import id_birth_year, id_gender, mrz_records
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold, parse_date

from ..process import reason
from . import chu_the
from .chu_the import ROLE_BY_KEY, Role
from .dinh_danh import ACCOUNT_DOC_NAME

_ROLES = (ROLE_BY_KEY["me"], ROLE_BY_KEY["cha"], ROLE_BY_KEY["nyc"])
_GENDER = {"me": "Nữ", "cha": "Nam"}


def _units(role: Role) -> dict[str, Unit]:
    return {
        "so": Unit(f"{role.key}.so_dinh_danh", f"Số định danh của {role.label}",
                   (Field(f"{role.prefix}_IdNumber", "số định danh 12 chữ số", "code"),)),
        "ngay": Unit(f"{role.key}.ngay_cap", f"Ngày cấp giấy tờ tùy thân của {role.label}",
                     (Field(f"{role.prefix}_IdIssueDate", "ngày cấp dd/mm/yyyy", "date"),)),
    }


UNITS_BY_ROLE = {role.key: _units(role) for role in _ROLES}
UNITS = tuple(unit for units in UNITS_BY_ROLE.values() for unit in units.values())
_ROLE_BY_UNIT = {unit.key: role for role in _ROLES for unit in UNITS_BY_ROLE[role.key].values()}

RULES = """
<so_dinh_danh>
Dòng "Tín hiệu mã" ghi B lấy ở vùng MRZ mặt sau thẻ mang họ tên (không dấu) của chính người ở vai đang xét, giới tính và
năm sinh mã hoá trong số khớp ngày sinh in ở MRZ → chọn B: ba dòng MRZ in máy đọc ổn định hơn chữ số trên mặt thẻ hay tờ
khai viết tay.
</so_dinh_danh>

<ngay_cap>
Ngày cấp đọc ở mặt sau thẻ, trong khối kết thúc bằng dải MRZ mang đúng số định danh của người ở vai đang xét → khối đó
chắc chắn là thẻ của người này. A bỏ trống → chọn B. A khác B: chọn B khi mã ghi B được nhiều giấy ghi hơn A. Ngày hết hạn
("Có giá trị đến") không phải ngày cấp.
</ngay_cap>
"""


def _documents(case: Case) -> list[dict]:
    return [document for document in case.documents if document.get("name") != ACCOUNT_DOC_NAME]


def _line(documents: list[dict], pattern: str, *, squeeze: bool = False) -> tuple[str, int]:
    for index, document in enumerate(documents, start=1):
        for line in str(document.get("text") or "").splitlines():
            if re.search(pattern, re.sub(r"\s+", "", line) if squeeze else line):
                return line.strip(), index
    return "", 0


def _date_pattern(value: str) -> str:
    parsed = parse_date(value)
    if not parsed:
        return r"(?!)"
    return rf"(?<!\d)0?{parsed.day}\s*[/.-]\s*0?{parsed.month}\s*[/.-]\s*{parsed.year}(?!\d)"


def _date_count(value: str, documents: list[dict]) -> int:
    pattern = _date_pattern(value)
    return sum(1 for document in documents if re.search(pattern, str(document.get("text") or "")))


def _mrz_card(role: Role, person: dict, documents: list[dict]) -> dict | None:
    name = " ".join(fold(person["name"]).split())
    gender = _GENDER.get(role.key)
    cards = [card for document in documents for card in mrz_records(document.get("text"))]
    cards = [card for card in cards if name and card.get("name") == name and card.get("birth")
             and (not gender or id_gender(card["id"]) == gender)
             and (id_birth_year(card["id"]) or 0) % 100 == card["birth"][0]]
    return cards[0] if len({card["id"] for card in cards}) == 1 else None


def _number_finding(role: Role, person: dict, case: Case, card: dict) -> Finding | None:
    if card["id"] == person["number"]:
        return None
    quote, doc = _line(case.documents, rf"I[DO]VNM\S*{card['id']}", squeeze=True)
    if not quote:
        return None
    return Finding(INSPECTOR, UNITS_BY_ROLE[role.key]["so"], {f"{role.prefix}_IdNumber": card["id"]}, quote, doc,
                   f"dòng MRZ ở mặt sau thẻ của {role.label}", role.label, backed=True,
                   evidence=(f"vùng MRZ của thẻ mang họ tên {role.label} (không dấu), giới tính và năm sinh trong số định "
                             "danh khớp ngày sinh in ở MRZ",))


def _date_finding(role: Role, person: dict, case: Case, number: str) -> Finding | None:
    documents = _documents(case)
    back = reason._mrz_card_backs(documents).get(number) if len(number) == 12 else None
    printed = parse_date((back or {}).get("issue_date"))
    if not printed:
        return None
    proposed = printed.strftime("%d/%m/%Y")
    current = case.values.get(f"{role.prefix}_IdIssueDate")
    current_date = parse_date(current)
    if current_date == printed:
        return None
    if current_date and _date_count(proposed, documents) <= _date_count(current, documents):
        return None
    quote, doc = _line(case.documents, _date_pattern(proposed))
    if not quote:
        return None
    return Finding(INSPECTOR, UNITS_BY_ROLE[role.key]["ngay"], {f"{role.prefix}_IdIssueDate": proposed}, quote, doc,
                   f"dòng in ở mặt sau thẻ của {role.label}", role.label, backed=True,
                   evidence=(f"mã đọc ở mặt sau thẻ, trong khối kết thúc bằng dải MRZ mang đúng số định danh của "
                             f"{role.label}; ngày này có trên {_date_count(proposed, documents)} giấy, ngày của A trên "
                             f"{_date_count(current, documents) if current_date else 0} giấy",))


def findings_from(case: Case) -> list[Finding]:
    documents = _documents(case)
    findings = []
    for role in _ROLES:
        person = chu_the.identity(case.values, role)
        if not person["name"]:
            continue
        card = _mrz_card(role, person, documents)
        number_finding = _number_finding(role, person, case, card) if card else None
        if number_finding:
            findings.append(number_finding)
        number = card["id"] if card else person["number"]
        date_finding = _date_finding(role, person, case, number)
        if date_finding:
            findings.append(date_finding)
    return findings


def check(unit: Unit, values: dict, case: Case) -> str:
    role = _ROLE_BY_UNIT[unit.key]
    number = chu_the.digits(values.get(f"{role.prefix}_IdNumber"))
    gender = id_gender(number) if unit.key.endswith(".so_dinh_danh") else ""
    if gender and _GENDER.get(role.key) and gender != _GENDER[role.key]:
        return f"số mã hoá giới tính {gender}, không phải {role.label}"
    return ""


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    return findings_from(case)


_OWNERS = tuple(role.label for role in _ROLES)
INSPECTOR = Inspector("giay_to", "GIẤY TỜ TÙY THÂN (số định danh, ngày cấp) đăng ký lại khai sinh", UNITS, RULES,
                      owners=_OWNERS, accepted=_OWNERS, find=find, check=check)
