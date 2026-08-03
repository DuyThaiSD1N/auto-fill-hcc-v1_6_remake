"""Map compact xét tuyển viên chức facts to Form.io fields."""

import re
import unicodedata
from dataclasses import dataclass

from app.pipelines.xet_tuyen_vien_chuc.process.schema import UI_COMP_BY_NAME
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
    return re.sub(r"^(xã|phường|thị trấn|tt\.?)\s+", "", text, flags=re.IGNORECASE).strip()


def _area(value):
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


def _same_person(a_id, a_name, b_id, b_name) -> bool:
    ai, bi = _norm_identity(a_id), _norm_identity(b_id)
    if ai and bi:
        if ai == bi:
            return True
        # Full identity numbers conflict: do not let same name silently override.
        if len(ai) >= 9 and len(bi) >= 9:
            return False
    an, bn = _norm_text(a_name), _norm_text(b_name)
    return bool(an and bn and an == bn)


def _matches_context(person: Person, context: dict) -> bool:
    return _same_person(
        person.identity,
        person.name,
        context.get("applicant_identity"),
        context.get("applicant_name"),
    )


def _phieu_owner(values: dict) -> Person | None:
    name = values.get("Phieu_HoTen")
    identity = values.get("Phieu_SoDinhDanh")
    if not name and not identity:
        return None
    issue_date = values.get("Phieu_NgayCap")
    residence = _area(values.get("Phieu_HoKhau")) or _area(values.get("Phieu_DiaChiNhanThongBao"))
    return Person(
        prefix="Phieu",
        name=name,
        identity=identity,
        birthday=values.get("Phieu_NgaySinh"),
        gender=values.get("Phieu_GioiTinh"),
        nationality="Việt Nam",
        issue_date=issue_date,
        issuer=values.get("Phieu_NoiCap") or (default_issuer(issue_date) if issue_date else None),
        residence=residence,
        phone=values.get("Phieu_DienThoai"),
        email=values.get("Phieu_Email"),
    )


def _merge_owner_with_matching_cccd(owner: Person, people: list[Person]) -> Person:
    match = next(
        (p for p in people if _same_person(p.identity, p.name, owner.identity, owner.name)),
        None,
    )
    if not match:
        return owner
    issue_date = owner.issue_date or match.issue_date
    return Person(
        prefix="Owner",
        # Phiếu đăng ký dự tuyển remains source of truth for candidate identity.
        name=owner.name or match.name,
        identity=owner.identity or match.identity,
        birthday=owner.birthday or match.birthday,
        gender=owner.gender or match.gender,
        nationality=owner.nationality or match.nationality or "Việt Nam",
        issue_date=issue_date,
        issuer=owner.issuer or match.issuer or (default_issuer(issue_date) if issue_date else None),
        # Owner address priority: phiếu hộ khẩu -> phiếu địa chỉ nhận thông báo -> matching CCCD.
        residence=owner.residence or match.residence,
        phone=owner.phone,
        email=owner.email,
    )


def _pick_requester(people: list[Person], context: dict, owner: Person) -> tuple[Person | None, str | None]:
    matches = [p for p in people if _matches_context(p, context)]
    if len(matches) == 1:
        return matches[0], None

    if len(people) == 1 and not _same_person(people[0].identity, people[0].name, owner.identity, owner.name):
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
    owner_from_phieu = _phieu_owner(values)
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

    if not owner_from_phieu:
        return out, ["Không đọc được Phiếu đăng ký dự tuyển để xác định chủ hồ sơ/người dự tuyển."]

    owner = _merge_owner_with_matching_cccd(owner_from_phieu, people)
    owner_matches_ui = _same_person(
        owner.identity,
        owner.name,
        context.get("applicant_identity"),
        context.get("applicant_name"),
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
