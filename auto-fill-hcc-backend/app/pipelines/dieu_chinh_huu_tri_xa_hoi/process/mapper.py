"""Map the two canonical subjects to Form.io fields."""

import re
import unicodedata
from dataclasses import dataclass

from app.pipelines.dieu_chinh_huu_tri_xa_hoi.process.schema import UI_COMP_BY_NAME


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
    phone: str | None = None
    residence: dict | None = None


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


def _date_with_ocr_evidence(value: str | None, ocr_text: str | None) -> str | None:
    """Chỉ nhận ngày nếu OCR có đúng ngày đó, cho phép nguồn viết d/m/yyyy.

    Guard áp dụng cho cả hai chủ thể sau khi agent đã hợp nhất nguồn. Nó chặn
    trường hợp LLM tự đảo một chuỗi viết tay mơ hồ thành ngày hợp lệ.
    """
    if not value:
        return None
    if not ocr_text:
        return str(value)

    target_match = re.fullmatch(
        r"\s*(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})\s*",
        str(value),
    )
    if not target_match:
        return None
    target = (
        f"{int(target_match.group(1)):02d}/"
        f"{int(target_match.group(2)):02d}/"
        f"{target_match.group(3)}"
    )

    for day, month, year in re.findall(
        r"\b(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})\b",
        str(ocr_text),
    ):
        if not (1 <= int(day) <= 31 and 1 <= int(month) <= 12):
            continue
        if f"{int(day):02d}/{int(month):02d}/{year}" == target:
            return target
    return None


def _strip_admin_prefix(value) -> str:
    """Field xã của eForm chỉ nhận tên đơn vị, không nhận tiền tố loại."""
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


def _document_chunks(ocr_text: str) -> list[str]:
    return [
        chunk
        for chunk in re.split(r"\n\s*---\s*\n", str(ocr_text or ""))
        if chunk.strip()
    ]


def _contains_person(text: str, name: str | None, identity: str | None) -> bool:
    normalized_identity = _norm_identity(identity)
    if normalized_identity:
        return _identity_occurs(normalized_identity, text)
    normalized_name = _norm_text(name)
    return bool(normalized_name and normalized_name in _norm_text(text))


def _section(text: str, start_pattern: str, end_pattern: str | None) -> str:
    start = re.search(start_pattern, text, flags=re.IGNORECASE)
    if not start:
        return ""
    tail = text[start.start():]
    if not end_pattern:
        return tail
    end = re.search(end_pattern, tail[start.end() - start.start():], flags=re.IGNORECASE)
    if not end:
        return tail
    return tail[:start.end() - start.start() + end.start()]


def _person_evidence_scope(
    ocr_text: str,
    prefix: str,
    name: str | None,
    identity: str | None,
) -> str:
    """Khoanh đúng CCCD hoặc mục I/II của chủ thể để chặn trộn field."""
    scopes: list[str] = []
    for chunk in _document_chunks(ocr_text):
        normalized_chunk = _norm_text(chunk)
        is_form_01 = (
            "mau so 01" in normalized_chunk
            or "van ban de nghi" in normalized_chunk
        )
        is_identity_card = (
            "can cuoc cong dan" in normalized_chunk
            or "citizen identity card" in normalized_chunk
            or "identity card" in normalized_chunk
        )

        if is_identity_card and _contains_person(chunk, name, identity):
            scopes.append(chunk)

        if is_form_01 and prefix == "ChuHoSo":
            section = _section(
                chunk,
                r"(?m)^\s*I[.\s]+Thông tin người",
                r"(?m)^\s*II[.\s]+Thông tin người",
            )
            if section and _contains_person(section, name, identity):
                scopes.append(section)
        elif is_form_01 and prefix == "NguoiNop":
            section = _section(
                chunk,
                r"(?m)^\s*II[.\s]+Thông tin người",
                None,
            )
            if section and _contains_person(section, name, identity):
                scopes.append(section)
        elif not is_form_01 and not is_identity_card:
            # Tài liệu rời chỉ chứa một chủ thể vẫn là nguồn hợp lệ.
            if _contains_person(chunk, name, identity):
                scopes.append(chunk)
    return "\n".join(scopes)


def _gender_with_evidence(
    value: str | None,
    evidence_scope: str,
    has_ocr: bool,
) -> str | None:
    if not value or not has_ocr:
        return value
    normalized_value = _norm_text(value)
    normalized_scope = _norm_text(evidence_scope)
    for label in ("gioi tinh", "sex"):
        start = normalized_scope.find(label)
        while start >= 0:
            if normalized_value in normalized_scope[start:start + 60].split():
                return str(value)
            start = normalized_scope.find(label, start + len(label))
    return None


def _text_with_evidence(
    value: str | None,
    evidence_scope: str,
    has_ocr: bool,
) -> str | None:
    if not value or not has_ocr:
        return value
    normalized_value = _norm_text(value)
    return str(value) if normalized_value in _norm_text(evidence_scope) else None


def _phone_with_evidence(
    value: str | None,
    evidence_scope: str,
    has_ocr: bool,
) -> str | None:
    if not value or not has_ocr:
        return value
    normalized = _norm_identity(value)
    return str(value) if normalized and _identity_occurs(normalized, evidence_scope) else None


def _person(values: dict, prefix: str, ocr_text: str | None) -> Person | None:
    name = values.get(f"{prefix}_HoTen")
    identity = values.get(f"{prefix}_SoDinhDanh")
    if not name and not identity:
        return None
    has_ocr = bool(ocr_text)
    evidence_scope = _person_evidence_scope(
        str(ocr_text or ""),
        prefix,
        name,
        identity,
    )
    return Person(
        prefix=prefix,
        name=name,
        identity=identity,
        birthday=_date_with_ocr_evidence(
            values.get(f"{prefix}_NgaySinh"),
            evidence_scope,
        ) if has_ocr else values.get(f"{prefix}_NgaySinh"),
        gender=_gender_with_evidence(
            values.get(f"{prefix}_GioiTinh"),
            evidence_scope,
            has_ocr,
        ),
        nationality=_text_with_evidence(
            values.get(f"{prefix}_QuocTich"),
            evidence_scope,
            has_ocr,
        ) or "Việt Nam",
        issue_date=_date_with_ocr_evidence(
            values.get(f"{prefix}_NgayCap"),
            evidence_scope,
        ) if has_ocr else values.get(f"{prefix}_NgayCap"),
        # Không mặc định cơ quan cấp từ ngày cấp. Có bằng chứng mới được điền.
        issuer=_text_with_evidence(
            values.get(f"{prefix}_NoiCap"),
            evidence_scope,
            has_ocr,
        ),
        phone=_phone_with_evidence(
            values.get(f"{prefix}_DienThoai"),
            evidence_scope,
            has_ocr,
        ),
        residence=_area(values.get(f"{prefix}_NoiCuTru")),
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
    context_name = _norm_text(context.get("applicant_name"))
    context_identity = _norm_identity(context.get("applicant_identity"))
    person_name = _norm_text(person.name)
    person_identity = _norm_identity(person.identity)

    # Có đủ hai mỏ neo thì bắt buộc khớp cả hai, không cho một field bù field sai.
    if context_name and context_identity:
        return (
            person_name == context_name
            and person_identity == context_identity
        )
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


def _identity_occurs(identity: str, text: str) -> bool:
    candidates = re.findall(r"(?:\d[ \t.\-]*){9,12}", str(text or ""))
    return any(
        _norm_identity(candidate) == identity
        for candidate in candidates
    )


def _person_has_ocr_evidence(person: Person, ocr_text: str) -> bool:
    """Không cho agent biến chính mỏ neo UI thành dữ liệu tài liệu."""
    if not ocr_text:
        return True
    person_name = _norm_text(person.name)
    person_identity = _norm_identity(person.identity)
    if person_name and person_name not in _norm_text(ocr_text):
        return False
    if person_identity and not _identity_occurs(person_identity, ocr_text):
        return False
    return bool(person_name or person_identity)


def enrich(
    fields: list[dict],
    options: dict | None = None,
) -> tuple[list[dict], list[str]]:
    """Xác thực hai vai trò rồi đổi sang hợp đồng UI.

    Agent đã hợp nhất nguồn thành ChuHoSo/NguoiNop. Mapper không phân loại lại
    tài liệu; nó chỉ kiểm tra người nộp có khớp tên + CCCD từ UI hay không.
    """
    values = _by_name(fields)
    ocr_text = (options or {}).get("_ocr_text") or ""
    owner = _person(values, "ChuHoSo", ocr_text)
    requester = _person(values, "NguoiNop", ocr_text)
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
        return out, [
            "Không bóc tách được chủ hồ sơ hoặc người nộp từ tài liệu hợp lệ."
        ]

    # Trường hợp tự nộp: agent chỉ cần trả ChuHoSo. Mapper dùng chính chủ hồ sơ
    # để điền phần người nộp và không tạo khối owner trùng lặp.
    if (
        owner
        and _matches_applicant(owner, context)
        and _person_has_ocr_evidence(owner, ocr_text)
    ):
        add("data[isOwnerDossierCheck]", True)
        _add_requester(add, owner)
        return out, warnings

    # Trường hợp nộp thay: NguoiNop chỉ được dùng sau khi khớp lại mỏ neo UI.
    if (
        owner
        and requester
        and _matches_applicant(requester, context)
        and _person_has_ocr_evidence(requester, ocr_text)
    ):
        if _same_person(owner, requester):
            add("data[isOwnerDossierCheck]", True)
            _add_requester(add, owner)
        else:
            add("data[isOwnerDossierCheck]", False)
            _add_requester(add, requester)
            _add_owner(add, owner)
        return out, warnings

    # Chủ hồ sơ là dữ liệu độc lập, chắc chắn từ mục I: vẫn phải điền dù không
    # tìm thấy người nộp. Checkbox false giúp eForm mở khối chủ hồ sơ.
    if owner:
        add("data[isOwnerDossierCheck]", False)
        _add_owner(add, owner)
        anchor = (
            context.get("applicant_identity")
            or context.get("applicant_name")
            or "(trống)"
        )
        if _has_applicant_anchor(context):
            warnings.append(
                "Không xác định được người nộp khớp thông tin trên form "
                f"({anchor}); không điền phần người nộp."
            )
        else:
            warnings.append(
                "Chưa có họ tên hoặc CCCD trên form để xác định người nộp; "
                "không điền phần người nộp."
            )
        return out, warnings

    # Hiếm gặp: chỉ xác định được người nộp nhưng không có nguồn đủ chắc cho chủ
    # hồ sơ. Không biến người nộp thành chủ hồ sơ.
    if (
        requester
        and _matches_applicant(requester, context)
        and _person_has_ocr_evidence(requester, ocr_text)
    ):
        add("data[isOwnerDossierCheck]", False)
        _add_requester(add, requester)
        warnings.append(
            "Đã xác định người nộp nhưng chưa đọc được chủ hồ sơ từ Mẫu số 01."
        )
        return out, warnings

    anchor = (
        context.get("applicant_identity")
        or context.get("applicant_name")
        or "(trống)"
    )
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
