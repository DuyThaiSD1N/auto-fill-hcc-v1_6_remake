"""Compact agent process pipeline for "Đăng ký giám hộ"."""

import re

from app.pipelines._shared.formatting import normalize_date
from app.pipelines._shared.compact_agent import runner
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines.dang_ky_giam_ho.process import mapper
from app.pipelines.dang_ky_giam_ho.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_giam_ho.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


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


def _clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" ;,.")


def _title_admin(value) -> str:
    text = _clean(value)
    if not text:
        return ""
    text = re.sub(r"^tp\.?\s+", "Thành phố ", text, flags=re.IGNORECASE)
    for prefix in ("tỉnh", "thành phố", "phường", "xã", "thị trấn"):
        m = re.match(rf"^{prefix}\s+(.+)$", text, flags=re.IGNORECASE)
        if m:
            return f"{prefix.capitalize()} {_clean(m.group(1))}"
    return text


def _parse_area_text(value: str) -> dict | None:
    text = _clean(value)
    if not text:
        return None
    province = ""
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if parts and re.match(r"^(tỉnh|thành phố|tp\.?)\s+", parts[-1], flags=re.IGNORECASE):
        province = _title_admin(parts[-1])
    else:
        m_prov = re.search(r"\b(tỉnh|thành phố|tp\.?)\s+([A-ZÀ-Ỹa-zà-ỹ\s]+)$", text, flags=re.IGNORECASE)
        if m_prov:
            province = _title_admin(m_prov.group(0))

    m_commune = re.search(
        r"\b(phường|xã|thị trấn)\s+(.+?)(?=,|\s+(?:tp\.?|thành phố|huyện|thị xã|tỉnh)\b|$)",
        text,
        flags=re.IGNORECASE,
    )
    commune = _title_admin(m_commune.group(0)) if m_commune else ""
    detail = ""
    if m_commune:
        detail = _clean(text[:m_commune.start()])
    elif parts:
        detail = parts[0]

    out = {"quocGia": "Việt Nam", "tinh": province, "xa": commune, "diaChi": detail}
    return out if any(out.values()) else None


def _extract_ward_block(text: str) -> str:
    m = re.search(
        r"Người\s+được\s+giám\s+hộ\s*:?(?P<block>.*?)(?=Lý\s+do\s+đăng\s+ký\s+giám\s+hộ|Tôi\s+cam\s+đoan|Người\s+yêu\s+cầu|Đề\s+nghị\s+cấp\s+bản\s+sao|$)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return m.group("block") if m else ""


def _extract_ward_residence(text: str) -> dict | None:
    block = _extract_ward_block(text)
    if not block:
        return None
    m = re.search(
        r"Nơi\s+cư\s+trú\s*:\s*(?P<addr>.*?)(?=Giấy\s+khai\s+sinh|Giấy\s+tờ\s+tùy\s+thân|Lý\s+do|$)",
        block,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return _parse_area_text(m.group("addr")) if m else None


def _contains_identity_doc(value: str) -> bool:
    return bool(
        re.search(
            r"\b(thẻ\s*(?:cccd|cc|căn\s+cước(?:\s+công\s+dân)?)|"
            r"căn\s+cước(?:\s+công\s+dân)?|cccd|cmnd|chứng\s+minh\s+nhân\s+dân)\b",
            value or "",
            flags=re.IGNORECASE,
        )
    )


def _extract_ward_identity_doc(text: str) -> dict:
    out: dict[str, str] = {}
    block = _extract_ward_block(text)
    if not block:
        return out

    line = re.search(
        r"(?:Giấy\s+khai\s+sinh\s*/\s*)?Giấy\s+tờ\s+tùy\s+thân\s*:\s*"
        r"(?P<body>.*?)(?=Lý\s+do\s+đăng\s+ký\s+giám\s+hộ|Nơi\s+cư\s+trú|Tôi\s+cam\s+đoan|Đề\s+nghị\s+cấp\s+bản\s+sao|$)",
        block,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not line:
        return out

    body = _clean(line.group("body"))
    if not _contains_identity_doc(body):
        return out

    number = re.search(
        r"(?:số|cccd\s+số|cc\s+số|cmnd\s+số)\s*[:\-]?\s*(\d{9,12})",
        body,
        flags=re.IGNORECASE,
    )
    if not number:
        number = re.search(r"\b(\d{9,12})\b", body)
    if number:
        out["Ward_IdNumber"] = number.group(1)

    issue_date = re.search(
        r"(?:cấp\s+ngày|ngày\s+cấp)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        body,
        flags=re.IGNORECASE,
    )
    if issue_date:
        out["Ward_IdIssueDate"] = normalize_date(issue_date.group(1))

    issuer = normalize_issuer(body)
    if issuer and issuer != body:
        out["Ward_IdIssuePlace"] = issuer
    return out


def _extract_birth_certificate(text: str) -> dict:
    out: dict[str, str] = {}
    block = _extract_ward_block(text) or text

    number = re.search(r"giấy\s+khai\s+sinh\s+số\s*[:\-]?\s*([A-Z0-9./-]+)", block, re.IGNORECASE)
    if not number:
        number = re.search(r"\bSố\s*:\s*([A-Z0-9./-]+)\b", text, re.IGNORECASE)
    if number:
        out["Ward_BirthCertificateNumber"] = number.group(1).strip()

    place = re.search(
        r"(?:do|Nơi\s+đăng\s+ký\s+khai\s+sinh\s*:?)\s*(.+?)(?=(?:\s+cấp\s+ngày|\s*;\s*Ngày|Ngày,\s*tháng,\s*năm\s+đăng\s+ký|$))",
        block,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not place:
        place = re.search(
            r"Nơi\s+đăng\s+ký\s+khai\s+sinh\s*:?\s*(.+?)(?=Ngày,\s*tháng,\s*năm\s+đăng\s+ký|CHỦ\s+TỊCH|$)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
    if place:
        out["Ward_BirthCertificateIssuePlace"] = _clean(place.group(1))

    date = re.search(
        r"giấy\s+khai\s+sinh\s+số\s*[:\-]?\s*[A-Z0-9./-]+.*?cấp\s+ngày\s*"
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        block,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not date:
        date = re.search(
            r"Ngày,\s*tháng,\s*năm\s+đăng\s+ký\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
            text,
            flags=re.IGNORECASE,
        )
    if date:
        out["Ward_BirthCertificateIssueDate"] = normalize_date(date.group(1))
    return out


def _compact_field_fallback(raw_fields, documents: list[dict]):
    fields = _fields_dict(raw_fields)
    text = _ocr_text(documents)
    if not fields or not text:
        return raw_fields

    if not fields.get("Ward_ResidenceDomestic"):
        residence = _extract_ward_residence(text)
        if residence:
            fields["Ward_ResidenceDomestic"] = residence

    ward_identity = _extract_ward_identity_doc(text)
    for key, value in ward_identity.items():
        if value and not fields.get(key):
            fields[key] = value

    birth_cert = _extract_birth_certificate(text)
    for key, value in birth_cert.items():
        if value and not fields.get(key):
            fields[key] = value
    return fields


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        compact_field_fallback=_compact_field_fallback,
        options=options,
    )
    res["fields"] = mapper.enrich(res["fields"], options)
    return res
