"""Đổi hai chủ thể nghiệp vụ sang field Form.io của thủ tục hỗ trợ mai táng."""

import re
import unicodedata
from dataclasses import dataclass

from app.pipelines._shared.area_remap import remap_area
from app.pipelines.ho_tro_mai_tang.process.schema import UI_COMP_BY_NAME


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


def _by_name(fields: list[dict]) -> dict:
    return {
        field["name"]: field["value"]
        for field in fields
        if field.get("value") not in (None, "", {}, [])
    }


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


def _strip_admin_prefix(value) -> str:
    text = str(value or "").strip()
    return re.sub(
        r"^(xã|phường|thị trấn|tt\.?)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _area(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or "",
        "xa": _strip_admin_prefix(
            value.get("xa")
            or value.get("xã")
            or value.get("phuong")
            or value.get("phường")
        ),
        "diaChi": (
            value.get("diaChi")
            or value.get("dia_chi")
            or value.get("diachi")
            or ""
        ),
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    return remap_area(out) or out


def _area_label(value: str | None) -> str | None:
    if not value:
        return None
    text = " ".join(str(value).split()).strip()
    prefixes = (
        "Thành phố",
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
        normalized = _norm_text(text)
        for prefix in prefixes:
            normalized_prefix = _norm_text(prefix)
            if normalized == normalized_prefix:
                return None
            if normalized.startswith(normalized_prefix + " "):
                text = text[len(prefix):].strip()
                changed = True
                break
    return text


def _person(values: dict, prefix: str) -> Person | None:
    name = values.get(f"{prefix}_HoTen")
    identity = values.get(f"{prefix}_SoDinhDanh")
    if not name and not identity:
        return None
    return Person(
        prefix=prefix,
        name=name,
        identity=identity,
        birthday=values.get(f"{prefix}_NgaySinh"),
        gender=values.get(f"{prefix}_GioiTinh"),
        nationality=values.get(f"{prefix}_QuocTich") or "Việt Nam",
        issue_date=values.get(f"{prefix}_NgayCap"),
        issuer=values.get(f"{prefix}_NoiCap"),
        residence=_area(values.get(f"{prefix}_NoiCuTru")),
        phone=values.get(f"{prefix}_DienThoai"),
    )


def _form_context(options: dict | None) -> dict:
    context = (options or {}).get("formContext") or {}
    return {
        "applicant_name": (
            context.get("applicantFullname")
            or context.get("fullname")
            or ""
        ),
        "applicant_identity": (
            context.get("applicantIdentityNumber")
            or context.get("identityNumber")
            or ""
        ),
    }


def _has_applicant_anchor(context: dict) -> bool:
    return bool(
        _norm_text(context.get("applicant_name"))
        or _norm_identity(context.get("applicant_identity"))
    )


def _matches_applicant(person: Person, context: dict) -> bool:
    """Có cả tên và CCCD từ UI thì bắt buộc cùng khớp."""
    context_name = _norm_text(context.get("applicant_name"))
    context_identity = _norm_identity(context.get("applicant_identity"))
    person_name = _norm_text(person.name)
    person_identity = _norm_identity(person.identity)

    if context_name and context_identity:
        return person_name == context_name and person_identity == context_identity
    if context_identity:
        return bool(person_identity and person_identity == context_identity)
    return bool(context_name and person_name == context_name)


def _same_person(first: Person, second: Person) -> bool:
    first_identity = _norm_identity(first.identity)
    second_identity = _norm_identity(second.identity)
    if first_identity and second_identity:
        return first_identity == second_identity
    first_name = _norm_text(first.name)
    second_name = _norm_text(second.name)
    return bool(first_name and first_name == second_name)


def enrich(
    fields: list[dict],
    options: dict | None = None,
) -> tuple[list[dict], list[str]]:
    """Xác thực người nộp rồi phát hai khối UI theo đúng vai trò."""
    values = _by_name(fields)
    owner = _person(values, "ChuHoSo")
    requester = _person(values, "NguoiNop")
    context = _form_context(options)

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

    if not owner and not requester:
        return out, ["Không bóc tách được chủ hồ sơ hoặc người nộp từ tài liệu hợp lệ."]

    # === MODE "owner_as_submitter" (toggle extension): KHÔNG dùng mỏ neo UI. LUÔN lấy CHỦ HỒ SƠ làm người
    # nộp (tự nộp, tick checkbox) — thủ tục này thực tế không có giấy ủy quyền. Nghĩa Hưng: người nộp lấy
    # theo thông tin người đề nghị trong Tờ khai (Mẫu số 04), không so khớp tài khoản đăng nhập. ===
    if str((options or {}).get("submitterMode") or "") == "owner_as_submitter":
        person = owner or requester
        if person is owner:
            add("data[isOwnerDossierCheck]", True)
            _add_requester(add, person)      # người nộp = chủ hồ sơ
            add("data[ownerBirthday]", person.birthday)  # portal bỏ sót khi tick
        else:
            add("data[isOwnerDossierCheck]", False)
            _add_requester(add, person)
        return out, warnings

    # Người đứng ra mai táng trùng mỏ neo UI: tự nộp, tích checkbox và dùng
    # chính chủ hồ sơ cho khối người nộp. Ngày sinh UI cũ không tham gia khớp.
    if owner and _matches_applicant(owner, context):
        add("data[isOwnerDossierCheck]", True)
        _add_requester(add, owner)
        # Portal tự sao chép hầu hết field khi tick nhưng bỏ sót ngày sinh chủ
        # hồ sơ, nên phải phát riêng đúng field này sau khối người nộp.
        add("data[ownerBirthday]", owner.birthday)
        return out, warnings

    # Nộp thay: chỉ dùng NguoiNop sau khi khớp lại toàn bộ mỏ neo UI hiện có.
    if owner and requester and _matches_applicant(requester, context):
        if _same_person(owner, requester):
            add("data[isOwnerDossierCheck]", True)
            _add_requester(add, owner)
            add("data[ownerBirthday]", owner.birthday)
        else:
            add("data[isOwnerDossierCheck]", False)
            _add_requester(add, requester)
            _add_owner(add, owner)
        return out, warnings

    # Không có/không xác định được người nộp vẫn trả chủ hồ sơ bình thường.
    if owner:
        add("data[isOwnerDossierCheck]", False)
        _add_owner(add, owner)
        if _has_applicant_anchor(context):
            anchor = context.get("applicant_identity") or context.get("applicant_name")
            warnings.append(
                "Không xác định được người nộp khớp thông tin trên form "
                f"({anchor}); không điền phần người nộp."
            )
        return out, warnings

    if requester and _matches_applicant(requester, context):
        add("data[isOwnerDossierCheck]", False)
        _add_requester(add, requester)
        warnings.append("Đã xác định người nộp nhưng chưa đọc được chủ hồ sơ từ Mẫu số 04.")
        return out, warnings

    anchor = context.get("applicant_identity") or context.get("applicant_name") or "(trống)"
    return out, [
        "Người nộp trích xuất không khớp thông tin trên form "
        f"({anchor}); không điền để tránh nhầm người."
    ]


def _add_requester(add, person: Person) -> None:
    add("data[fullname]", person.name)
    add("data[birthday]", person.birthday)
    add("data[gender]", person.gender)
    add("data[identityNumber]", person.identity)
    add("data[identityDate]", person.issue_date)
    add("data[idIssuePlace]", person.issuer)
    add("data[phoneNumber]", person.phone)
    if person.residence:
        add("data[province]", _area_label(person.residence.get("tinh")))
        add("data[district]", _area_label(person.residence.get("xa")))
        add("data[address]", person.residence.get("diaChi"))


def _add_owner(add, person: Person) -> None:
    add("data[ownerFullname]", person.name)
    add("data[ownerBirthday]", person.birthday)
    add("data[ownerGender]", person.gender)
    add("data[ownerIdentityNumber]", person.identity)
    add("data[ownerIdentityDate]", person.issue_date)
    add("data[ownerIdIssuePlace]", person.issuer)
    add("data[ownerPhoneNumber]", person.phone)
    if person.residence:
        add("data[ownerProvince]", _area_label(person.residence.get("tinh")))
        add("data[ownerDistrict]", _area_label(person.residence.get("xa")))
        add("data[ownerAddress]", person.residence.get("diaChi"))
    add("data[ownerNation]", person.nationality or "Việt Nam")
