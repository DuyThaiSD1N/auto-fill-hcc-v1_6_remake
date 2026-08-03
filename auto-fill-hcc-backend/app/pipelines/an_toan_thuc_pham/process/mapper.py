"""Map compact ATTP facts to Form.io fields."""

import re
import unicodedata
from dataclasses import dataclass

from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines.an_toan_thuc_pham.process.schema import UI_COMP_BY_NAME


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
    fax: str | None = None
    note: str | None = None


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
    return re.sub(
        r"^(xã|phường|thị trấn|tt\.?|tỉnh|thành phố|tp\.?)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _parse_area_text(value: str) -> dict | None:
    parts = [p.strip(" .") for p in re.split(r"[,;\n-]+", value or "") if p.strip(" .")]
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


def _don_owner(values: dict) -> Person | None:
    name = values.get("DonDeNghi_ChuCoSoHoTen")
    if not name:
        return None
    return Person(
        prefix="DonDeNghi",
        name=name,
        nationality="Việt Nam",
        residence=_area(values.get("DonDeNghi_DiaChiChuCoSo")),
        phone=_phone(values.get("DonDeNghi_DienThoai")),
    )


def _health_person(values: dict) -> Person | None:
    name = values.get("GiayKham_HoTen")
    identity = values.get("GiayKham_SoDinhDanh")
    if not name and not identity:
        return None
    issue_date = values.get("GiayKham_NgayCap")
    note = _note("Giấy khám sức khỏe", values.get("GiayKham_KetLuan"))
    return Person(
        prefix="GiayKham",
        name=name,
        identity=identity,
        birthday=values.get("GiayKham_NgaySinh"),
        gender=values.get("GiayKham_GioiTinh"),
        nationality="Việt Nam",
        issue_date=issue_date,
        issuer=values.get("GiayKham_NoiCap") or (default_issuer(issue_date) if issue_date else None),
        residence=_area(values.get("GiayKham_NoiOHienTai")),
        note=note,
    )


def _assessment_person(values: dict) -> Person | None:
    name = values.get("GiamDinh_HoTen")
    identity = values.get("GiamDinh_SoDinhDanh")
    if not name and not identity:
        return None
    issue_date = values.get("GiamDinh_NgayCap")
    note = "; ".join(
        p for p in (values.get("GiamDinh_MucDo"), values.get("GiamDinh_KetLuan")) if p
    ) or None
    return Person(
        prefix="GiamDinh",
        name=name,
        identity=identity,
        birthday=values.get("GiamDinh_NgaySinh"),
        gender=values.get("GiamDinh_GioiTinh"),
        nationality="Việt Nam",
        issue_date=issue_date,
        issuer=values.get("GiamDinh_NoiCap") or (default_issuer(issue_date) if issue_date else None),
        residence=_area(values.get("GiamDinh_NoiCuTru")),
        note=note,
    )


def _phone(value) -> str | None:
    if not value:
        return None
    text = str(value).upper().replace("O", "0").replace("S", "5")
    digits = re.sub(r"\D+", "", text)
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    if len(digits) == 10 and digits.startswith("0"):
        return digits
    return None


def _note(label: str, value) -> str | None:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return None
    return f"{label}: {text}"


def _pick(base, *candidates):
    if base not in (None, "", {}, []):
        return base
    for candidate in candidates:
        if candidate not in (None, "", {}, []):
            return candidate
    return None


def _merge_owner(base: Person, people: list[Person], health: Person | None, assessment: Person | None) -> Person:
    candidates = people[:]
    if health:
        candidates.append(health)
    if assessment:
        candidates.append(assessment)
    matches = [p for p in candidates if _same_person(p.identity, p.name, base.identity, base.name)]
    cccd = next((p for p in matches if p.prefix.startswith("Person")), None)
    health_match = next((p for p in matches if p.prefix == "GiayKham"), None)
    assessment_match = next((p for p in matches if p.prefix == "GiamDinh"), None)
    issue_date = _pick(
        cccd.issue_date if cccd else None,
        health_match.issue_date if health_match else None,
        assessment_match.issue_date if assessment_match else None,
        base.issue_date,
    )
    return Person(
        prefix="Owner",
        name=_pick(base.name, cccd.name if cccd else None, health_match.name if health_match else None, assessment_match.name if assessment_match else None),
        identity=_pick(cccd.identity if cccd else None, health_match.identity if health_match else None, assessment_match.identity if assessment_match else None, base.identity),
        birthday=_pick(cccd.birthday if cccd else None, health_match.birthday if health_match else None, assessment_match.birthday if assessment_match else None, base.birthday),
        gender=_pick(cccd.gender if cccd else None, health_match.gender if health_match else None, assessment_match.gender if assessment_match else None, base.gender),
        nationality=_pick(cccd.nationality if cccd else None, health_match.nationality if health_match else None, assessment_match.nationality if assessment_match else None, base.nationality, "Việt Nam"),
        issue_date=issue_date,
        issuer=_pick(
            cccd.issuer if cccd else None,
            health_match.issuer if health_match else None,
            assessment_match.issuer if assessment_match else None,
            base.issuer,
            default_issuer(issue_date) if issue_date else None,
        ),
        residence=_pick(
            cccd.residence if cccd else None,
            health_match.residence if health_match else None,
            assessment_match.residence if assessment_match else None,
            base.residence,
        ),
        phone=base.phone,
        note=_pick(assessment_match.note if assessment_match else None, health_match.note if health_match else None, base.note),
    )


def _pick_requester(people: list[Person], context: dict, owner: Person) -> tuple[Person | None, str | None]:
    matches = [p for p in people if _matches_context(p, context)]
    if len(matches) == 1:
        return matches[0], None
    if len(people) == 1:
        return people[0], None
    ctx = context.get("applicant_identity") or context.get("applicant_name") or "(trống)"
    return None, (
        "Không xác định được CCCD người nộp từ thông tin trên form "
        f"({ctx}); cần upload CCCD người nộp khớp thông tin UI."
    )


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    people = _people(values)
    context = _form_context(options)
    health = _health_person(values)
    assessment = _assessment_person(values)
    owner_from_don = _don_owner(values)
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

    owner_seed = owner_from_don or health or assessment
    if not owner_seed:
        return out, ["Không đọc được Đơn đề nghị/Giấy khám sức khỏe để xác định chủ hồ sơ."]

    owner = _merge_owner(owner_seed, people, health, assessment)
    if context.get("applicant_identity") or context.get("applicant_name"):
        owner_matches_ui = _same_person(
            owner.identity,
            owner.name,
            context.get("applicant_identity"),
            context.get("applicant_name"),
        )
    else:
        owner_matches_ui = len(people) == 1 and _same_person(
            people[0].identity,
            people[0].name,
            owner.identity,
            owner.name,
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
    add("data[fax]", person.fax)


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
    add("data[ownerFax]", person.fax)
    add("data[ownerNation]", person.nationality or "Việt Nam")
    add("data[ghiChu]", person.note)
