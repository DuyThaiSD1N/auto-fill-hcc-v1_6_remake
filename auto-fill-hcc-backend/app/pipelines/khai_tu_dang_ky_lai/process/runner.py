"""Compact agent pipeline for "Đăng ký lại khai tử"."""

import re

from app.pipelines._shared.compact_agent import runner
from app.pipelines.khai_tu_dang_ky_lai.process import mapper
from app.pipelines.khai_tu_dang_ky_lai.process.prompt import EXTRA_RULES
from app.pipelines.khai_tu_dang_ky_lai.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


_CCCD_ISSUER = "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
_PUBLIC_SECURITY_ISSUER = "Bộ Công an"


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _fields_dict(raw_fields) -> dict:
    if isinstance(raw_fields, dict):
        return dict(raw_fields)
    if isinstance(raw_fields, list):
        out = {}
        for item in raw_fields:
            if isinstance(item, dict) and item.get("name"):
                out[item["name"]] = item.get("value")
        return out
    return {}


def _ocr_text(documents: list[dict]) -> str:
    return "\n\n".join(str(d.get("text") or "") for d in documents or [])


def _id_in_text(id_number: str, text: str) -> bool:
    digits = _digits(text)
    ident = _digits(id_number)
    return bool(ident) and ident in digits


def _issuer_from_block(block: str) -> str:
    folded = block.upper()
    if "BỘ CÔNG AN" in folded or "MINISTRY OF PUBLIC SECURITY" in folded:
        return _PUBLIC_SECURITY_ISSUER
    if "CỤC TRƯỞNG CỤC CẢNH SÁT" in folded or "POLICE DEPARTMENT" in folded:
        return _CCCD_ISSUER
    return ""


def _cccd_front_facts(text: str, id_number: str) -> dict:
    """Read identity facts from a CCCD front block matched by card number."""
    ident = re.escape(_digits(id_number))
    if not ident:
        return {}
    pattern = re.compile(
        rf"(?:Số\s*/\s*No\.?|Số định danh cá nhân[^:\n]*):\s*{ident}"
        r"(?P<body>.*?)(?=(?:Số\s*/\s*No\.?|Số định danh cá nhân[^:\n]*):|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return {}
    body = match.group("body")
    facts: dict[str, str] = {}

    name = re.search(
        r"(?:Họ và tên\s*/\s*Full name|Họ, chữ đệm và tên khai sinh\s*/\s*Full name)\s*:?\s*\n?\s*([^\n]+)",
        body,
        re.IGNORECASE,
    )
    if name:
        value = name.group(1).strip()
        if value and not re.search(r"Ngày sinh|Date of birth", value, re.IGNORECASE):
            facts["name"] = value

    dob = re.search(r"(?:Ngày sinh|Ngày, tháng, năm sinh)\s*/\s*Date of birth\s*:?\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})", body, re.IGNORECASE)
    if dob:
        facts["birthDate"] = dob.group(1)

    gender = re.search(r"Giới tính\s*/\s*Sex\s*:?\s*(Nam|Nữ)", body, re.IGNORECASE)
    if gender:
        facts["gender"] = gender.group(1).capitalize()

    nationality = re.search(r"Quốc tịch\s*/\s*Nationality\s*:?\s*([^\n]+)", body, re.IGNORECASE)
    if nationality:
        facts["nationality"] = nationality.group(1).strip()

    return facts


def _cccd_issue_facts(text: str, id_number: str) -> dict:
    """Pair CCCD back-side issue date/place with the card number.

    OCR often groups several front sides first, then several back sides. The reliable anchor
    is the MRZ/ID line after each back-side block, because it repeats the card number.
    """
    ident = _digits(id_number)
    if not ident:
        return {}
    matches = list(re.finditer(
        r"Ngày,\s*tháng,\s*năm\s*/\s*Date,\s*month,\s*year\s*:?\s*"
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        text,
        re.IGNORECASE,
    ))
    for index, match in enumerate(matches):
        block_end = matches[index + 1].start() if index + 1 < len(matches) else match.start() + 1400
        block = text[match.start(): block_end]
        if _id_in_text(ident, block):
            return {"issueDate": match.group(1).replace("-", "/"), "issuePlace": _issuer_from_block(block)}
    return {}


def _apply_identity_facts(fields: dict, prefix: str, facts: dict) -> None:
    if not facts:
        return
    if facts.get("name"):
        fields[f"{prefix}_FullName"] = facts["name"]
    if facts.get("birthDate") and prefix == "Deceased":
        fields["Deceased_BirthDate"] = facts["birthDate"]
    if facts.get("gender") and prefix == "Deceased":
        fields["Deceased_Gender"] = facts["gender"]
    if facts.get("nationality") and prefix == "Deceased":
        fields["Deceased_Nationality"] = facts["nationality"]
    if facts.get("issueDate"):
        fields[f"{prefix}_IdIssueDate"] = facts["issueDate"]
    if facts.get("issuePlace"):
        fields[f"{prefix}_IdIssuePlace"] = facts["issuePlace"]


def _compact_field_fallback(raw_fields, documents: list[dict]):
    fields = _fields_dict(raw_fields)
    text = _ocr_text(documents)
    if not fields or not text:
        return raw_fields

    role_map = {
        "Requester": fields.get("Requester_IdNumber"),
        "Deceased": fields.get("Deceased_IdNumber"),
    }
    for prefix, id_number in role_map.items():
        if not id_number:
            continue
        facts = {}
        facts.update(_cccd_front_facts(text, id_number))
        facts.update(_cccd_issue_facts(text, id_number))
        _apply_identity_facts(fields, prefix, facts)
    return fields


def _requester_hint(options: dict) -> str:
    ctx = (options or {}).get("formContext") or {}
    name = str(ctx.get("applicantFullname") or "").strip()
    idnum = str(ctx.get("applicantIdentityNumber") or "").strip()
    if not name and not idnum:
        return ""
    return (
        "\n\n<requester_context>\n"
        f'Người đăng nhập trên cổng: họ tên="{name}", số định danh="{idnum}".\n'
        "Dùng thông tin này như mỏ neo phụ để phân biệt CCCD người yêu cầu với CCCD người đã chết.\n"
        "Nếu tờ khai giấy ghi người yêu cầu khác người đăng nhập thì vẫn trích Requester_* theo người yêu cầu trên tờ khai.\n"
        "</requester_context>"
    )


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES + _requester_hint(options),
        compact_field_fallback=_compact_field_fallback,
    )
    res["fields"] = mapper.enrich(res["fields"], options)
    return res
