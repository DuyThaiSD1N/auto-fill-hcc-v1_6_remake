"""Map compact mai táng dân công hỏa tuyến facts to Form.io fields."""

import re
import unicodedata
from dataclasses import dataclass

from app.pipelines.mai_tang_dan_cong.process.schema import UI_COMP_BY_NAME
from app.pipelines._shared.compact_agent.issuer import default_issuer


@dataclass
class Person:
    prefix: str
    name: str | None = None
    identity: str | None = None
    birthday: str | None = None
    gender: str | None = None
    nationality: str | None = None
    issue_date: str | None = None
    issuer: str | None = None
    residence: dict | None = None
    phone: str | None = None
    email: str | None = None


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _norm_text(value: str | None) -> str:
    if not value:
        return ""
    text = str(value).replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^0-9a-zA-Z]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def _norm_identity(value: str | None) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _strip_admin_prefix(value):
    text = str(value or "").strip()
    return re.sub(r"^(xã|phường|thị trấn|tt\\.?|tỉnh|thành phố|tp\\.?)\\s+", "", text, flags=re.IGNORECASE).strip()


def _parse_area_text(value: str) -> dict | None:
    parts = [p.strip(" .") for p in re.split(r"[,;\n]+", value or "") if p.strip(" .")]
    if not parts:
        return None
    out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
    district_prefix = re.compile(r"^(huyện|quận|thành phố|tp\.?|thị xã)\s+", re.IGNORECASE)
    if len(parts) >= 4 and district_prefix.match(parts[-2]):
        out["tinh"] = _strip_admin_prefix(parts[-1])
        out["xa"] = _strip_admin_prefix(parts[-3])
        out["diaChi"] = ", ".join(parts[:-3]).strip()
    elif len(parts) >= 3:
        out["tinh"] = _strip_admin_prefix(parts[-1])
        out["xa"] = _strip_admin_prefix(parts[-2])
        out["diaChi"] = ", ".join(parts[:-2]).strip()
    elif len(parts) == 2:
        out["tinh"] = _strip_admin_prefix(parts[-1])
        out["diaChi"] = parts[0]
    else:
        out["diaChi"] = parts[0]
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    return out


def _area(value):
    if isinstance(value, str):
        return _parse_area_text(value)
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or "",
        "xa": _strip_admin_prefix(value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường")),
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    return out


def _area_label(value: str | None) -> str | None:
    if not value:
        return None
    text = " ".join(str(value).split()).strip()
    prefixes = (
        "Thành phố",
        "Thành Phố",
        "Tỉnh",
        "Thị trấn",
        "Thị xã",
        "Phường",
        "Xã",
        "Huyện",
        "Quận",
        "TP.",
    )
    changed = True
    while changed:
        changed = False
        norm_text = _norm_text(text)
        for prefix in prefixes:
            norm_prefix = _norm_text(prefix)
            if norm_text == norm_prefix:
                return None
            if norm_text.startswith(norm_prefix + " "):
                text = text[len(prefix):].strip()
                changed = True
                break
    return text


def _same_person(a_id, a_name, b_id, b_name) -> bool:
    ai, bi = _norm_identity(a_id), _norm_identity(b_id)
    if ai and bi:
        if ai == bi:
            return True
        if len(ai) >= 9 and len(bi) >= 9:
            return False
    an, bn = _norm_text(a_name), _norm_text(b_name)
    return bool(an and bn and an == bn)


def _person(values: dict, prefix: str) -> Person | None:
    name = values.get(f"{prefix}_HoTen")
    identity = values.get(f"{prefix}_SoDinhDanh")
    if not name and not identity:
        return None
    issue_date = values.get(f"{prefix}_NgayCap")
    return Person(
        prefix=prefix,
        name=name,
        identity=identity,
        birthday=values.get(f"{prefix}_NgaySinh"),
        gender=values.get(f"{prefix}_GioiTinh"),
        nationality=values.get(f"{prefix}_QuocTich") or "Việt Nam",
        issue_date=issue_date,
        issuer=values.get(f"{prefix}_NoiCap") or (default_issuer(issue_date) if issue_date else None),
        residence=_area(values.get(f"{prefix}_NoiCuTru")),
    )


def _people(values: dict) -> list[Person]:
    out = []
    for prefix in ("Person1", "Person2"):
        person = _person(values, prefix)
        if person:
            out.append(person)
    return out


def _form_context(options: dict | None) -> dict:
    ctx = (options or {}).get("formContext") or {}
    return {
        "applicant_name": ctx.get("applicantFullname") or ctx.get("fullname") or "",
        "applicant_identity": ctx.get("applicantIdentityNumber") or ctx.get("identityNumber") or "",
    }


def _matches_context(person: Person, context: dict) -> bool:
    return _same_person(
        person.identity,
        person.name,
        context.get("applicant_identity"),
        context.get("applicant_name"),
    )


def _tokhai_claimant(values: dict) -> Person | None:
    name = values.get("ToKhai_ThanNhanHoTen")
    birthday = values.get("ToKhai_ThanNhanNgaySinh")
    phone = values.get("ToKhai_ThanNhanSoDienThoai")
    residence = _area(values.get("ToKhai_ThanNhanTruQuan"))
    if not name and not birthday and not phone and not residence:
        return None
    return Person(
        prefix="ToKhai",
        name=name,
        birthday=birthday,
        residence=residence,
        phone=phone,
        nationality="Việt Nam",
    )


def _merge_claimant_with_matching_cccd(claimant: Person, people: list[Person]) -> Person:
    match = next(
        (p for p in people if _same_person(p.identity, p.name, claimant.identity, claimant.name)),
        None,
    )
    issue_date = match.issue_date if match else None
    return Person(
        prefix="Claimant",
        # Per procedure rule: declaration is source of truth for name/birthday/phone/residence.
        name=claimant.name or (match.name if match else None),
        identity=(match.identity if match else None) or claimant.identity,
        birthday=claimant.birthday or (match.birthday if match else None),
        gender=(match.gender if match else None) or claimant.gender,
        nationality=(match.nationality if match else None) or claimant.nationality or "Việt Nam",
        issue_date=issue_date or claimant.issue_date,
        issuer=(match.issuer if match else None) or claimant.issuer or (default_issuer(issue_date) if issue_date else None),
        residence=claimant.residence or (match.residence if match else None),
        phone=claimant.phone,
        email=claimant.email,
    )


def _pick_requester(people: list[Person], context: dict, owner: Person) -> tuple[Person | None, str | None]:
    matches = [p for p in people if _matches_context(p, context)]
    if len(matches) == 1:
        return matches[0], None
    if len(people) == 1 and _same_person(people[0].identity, people[0].name, owner.identity, owner.name):
        return owner, None
    if len(people) == 1 and not context.get("applicant_identity") and not context.get("applicant_name"):
        return owner if _same_person(people[0].identity, people[0].name, owner.identity, owner.name) else people[0], None
    ctx = context.get("applicant_identity") or context.get("applicant_name") or "(trống)"
    return None, (
        "Không xác định được CCCD người nộp từ thông tin trên form "
        f"({ctx}); cần upload CCCD người nộp khớp thông tin UI."
    )


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    people = _people(values)
    claimant_from_decl = _tokhai_claimant(values)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    if not claimant_from_decl:
        return out, ["Không đọc được bản khai thân nhân để xác định chủ hồ sơ/người đứng khai nhận trợ cấp."]

    owner = _merge_claimant_with_matching_cccd(claimant_from_decl, people)
    if not people:
        add("data[isOwnerDossierCheck]", True)
        _add_requester(add, owner)
        return out, ["Có bản khai nhưng không đọc được CCCD; chỉ điền các trường đọc được từ bản khai."]

    context = _form_context(options)
    owner_matches_ui = (
        _same_person(owner.identity, owner.name, context.get("applicant_identity"), context.get("applicant_name"))
        if context.get("applicant_identity") or context.get("applicant_name")
        else len(people) == 1 and _same_person(people[0].identity, people[0].name, owner.identity, owner.name)
    )

    if owner_matches_ui:
        add("data[isOwnerDossierCheck]", True)
        _add_requester(add, owner)
        return out, warnings

    requester, warn = _pick_requester(people, context, owner)
    if warn:
        warnings.append(warn)
    add("data[isOwnerDossierCheck]", False)
    if requester:
        _add_requester(add, requester)
    _add_owner(add, owner)
    return out, warnings


def _add_requester(add, person: Person) -> None:
    add("data[fullname]", person.name)
    add("data[birthday]", person.birthday)
    add("data[gender]", person.gender)
    add("data[identityNumber]", person.identity)
    add("data[identityDate]", person.issue_date)
    add("data[idIssuePlace]", person.issuer)
    if person.residence:
        add("data[province]", _area_label(person.residence.get("tinh")))
        add("data[district]", _area_label(person.residence.get("xa")))
        add("data[address]", person.residence.get("diaChi"))
    add("data[phoneNumber]", person.phone)
    add("data[email]", person.email)


def _add_owner(add, person: Person) -> None:
    add("data[ownerFullname]", person.name)
    add("data[ownerBirthday]", person.birthday)
    add("data[ownerGender]", person.gender)
    add("data[ownerIdentityNumber]", person.identity)
    add("data[ownerIdentityDate]", person.issue_date)
    add("data[ownerIdIssuePlace]", person.issuer)
    if person.residence:
        add("data[ownerProvince]", _area_label(person.residence.get("tinh")))
        add("data[ownerDistrict]", _area_label(person.residence.get("xa")))
        add("data[ownerAddress]", person.residence.get("diaChi"))
    add("data[ownerPhoneNumber]", person.phone)
    add("data[ownerEmail]", person.email)
    add("data[ownerNation]", person.nationality or "Việt Nam")
