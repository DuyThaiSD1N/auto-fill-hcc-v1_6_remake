"""Đổi người chết (chủ hồ sơ) và người nộp sang field Form.io của thủ tục hỗ trợ mai táng."""

import re
import unicodedata
from dataclasses import dataclass, replace

from app.pipelines._shared import area_remap
from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer
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


# Cấu hình theo tài khoản: một số phường khai NGƯỜI ĐỀ NGHỊ trên tờ khai làm chủ hồ sơ thay vì người chết.
# Mapper không biết tài khoản nên router (Auto Fill) và pipeline_runner (Handfree) gọi
# with_account_process_options để server tự đặt cờ; cờ luôn bị ghi đè theo tài khoản, client không tự bật được.
PROCEDURE_KEYS = ("ho-tro-mai-tang-1116910",)
REQUESTER_AS_OWNER_OPTION = "requesterAsOwner"
_WARD_PREFIXES = ("xa ", "phuong ", "thi tran ")
# (tỉnh, phường) đã bỏ dấu + bỏ tiền tố, khớp ĐÚNG tên phường (phường Nha Trang không kéo theo Nam Nha Trang).
_REQUESTER_OWNER_WARDS = (
    ("khanh hoa", "nha trang"),  # 2026-11-04
    ("bac ninh", "tien du"),  # 2026-11-13
    # Khảo sát ảnh chốt 01/09–18/11: cán bộ các đơn vị này để người lo mai táng làm chủ hồ sơ (cùng cách làm ở mai
    # táng hưu trí xã hội).
    ("khanh hoa", "tay nha trang"),
    ("khanh hoa", "bac nha trang"),
    ("quang tri", "dong ha"),
    ("bac ninh", "kinh bac"),
    ("bac ninh", "hiep hoa"),
    ("bac ninh", "gia binh"),
    ("tuyen quang", "minh xuan"),
)


def is_requester_owner(options: dict | None) -> bool:
    return (options or {}).get(REQUESTER_AS_OWNER_OPTION) is True


def is_requester_owner_account(user: dict | None) -> bool:
    """True khi tài khoản thuộc một phường / xã trong _REQUESTER_OWNER_WARDS."""
    if not user:
        return False
    tinh = _norm_text(user.get("tinh"))
    xa = _norm_text(user.get("xa"))
    for prefix in _WARD_PREFIXES:
        if xa.startswith(prefix):
            xa = xa[len(prefix):].strip()
            break
    return any(tinh_key in tinh and xa == xa_key for tinh_key, xa_key in _REQUESTER_OWNER_WARDS)


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Trả bản sao options với cờ requesterAsOwner do server quyết theo tài khoản."""
    result = dict(options or {})
    result.pop(REQUESTER_AS_OWNER_OPTION, None)
    if procedure in PROCEDURE_KEYS and is_requester_owner_account(user):
        result[REQUESTER_AS_OWNER_OPTION] = True
    return result


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
        # So CÓ dấu: bỏ dấu thì tên "Phương Liễu", "Quân …" trùng tiền tố "Phường", "Quận" và bị cắt mất chữ đầu.
        normalized = unicodedata.normalize("NFC", text).casefold()
        for prefix in prefixes:
            normalized_prefix = prefix.casefold()
            if normalized == normalized_prefix:
                return None
            if normalized.startswith(normalized_prefix + " "):
                text = text[len(prefix):].strip()
                changed = True
                break
    return text


def _province_label(value: str | None) -> str | None:
    """Tên tỉnh trần như danh mục. Chữ viết tay hay bị OCR đọc lệch một chữ ("Quân Ngãi") — không khớp option nào trên cổng
    → nắn về tỉnh DUY NHẤT trong danh mục chỉ lệch một ký tự (bỏ dấu); nhiều tỉnh cùng gần thì giữ nguyên."""
    label = _area_label(value)
    if not label:
        return None
    canonical = area_remap.canonical_province(label)
    if canonical:
        return canonical
    key = area_remap._fold_province(label)
    near = {name for name in area_remap._CURRENT_PROVINCES.values()
            if _edit_distance(area_remap._fold_province(name), key) <= 1}
    return near.pop() if len(near) == 1 else label


def _phone(value) -> str | None:
    """Số di động 10 chữ số; tờ khai hay viết tách bằng dấu chấm / khoảng trắng mà ô SĐT của cổng chỉ nhận chữ số. Không đủ
    10 số (thiếu / số bàn) thì bỏ trống."""
    digits = re.sub(r"\D+", "", str(value or ""))
    return digits if len(digits) == 10 else None


def _person(values: dict, prefix: str) -> Person | None:
    name = values.get(f"{prefix}_HoTen")
    identity = values.get(f"{prefix}_SoDinhDanh")
    if not name and not identity:
        return None
    issue_date = values.get(f"{prefix}_NgayCap")
    issuer = values.get(f"{prefix}_NoiCap")
    if not issuer and len(_norm_identity(identity)) == 12 and re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", str(issue_date or "").strip()):
        # Thẻ / tờ khai không ghi (hoặc OCR không đọc được) nơi cấp: cơ quan cấp căn cước xác định theo ngày cấp.
        issuer = default_issuer(issue_date)
    return Person(
        prefix=prefix,
        name=name,
        identity=identity,
        birthday=values.get(f"{prefix}_NgaySinh"),
        gender=values.get(f"{prefix}_GioiTinh"),
        nationality=values.get(f"{prefix}_QuocTich") or "Việt Nam",
        issue_date=issue_date,
        issuer=issuer,
        residence=_area(values.get(f"{prefix}_NoiCuTru")),
        phone=_phone(values.get(f"{prefix}_DienThoai")),
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


_NEAR_EDITS = 2


def _edit_distance(first: str, second: str) -> int:
    previous = list(range(len(second) + 1))
    for i, a in enumerate(first, start=1):
        current = [i]
        for j, b in enumerate(second, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def _matches_applicant(person: Person, context: dict) -> bool:
    """Có cả tên và CCCD từ UI thì bắt buộc cùng khớp."""
    context_name = _norm_text(context.get("applicant_name"))
    context_identity = _norm_identity(context.get("applicant_identity"))
    person_name = _norm_text(person.name)
    person_identity = _norm_identity(person.identity)

    if context_name and context_identity:
        # OCR chữ viết tay hay lệch 1–2 ký tự ở MỘT trong hai (tên, số rơi một chữ số): một bên khớp hẳn, bên kia lệch không
        # quá 2 ký tự vẫn là cùng người; lệch cả hai thì không nhận.
        if person_identity == context_identity:
            return _edit_distance(person_name, context_name) <= _NEAR_EDITS
        return person_name == context_name and bool(person_identity) and (
            _edit_distance(person_identity, context_identity) <= _NEAR_EDITS)
    if context_identity:
        return bool(person_identity and person_identity == context_identity)
    return bool(context_name and person_name == context_name)


def _as_account(person: Person, context: dict) -> Person:
    """Người đã khớp mốc tài khoản (có thể khớp GẦN): họ tên / số lệch so với tài khoản là OCR đọc lệch — cổng khoá hai ô
    này theo tài khoản nên lấy đúng giá trị của tài khoản."""
    name = str(context.get("applicant_name") or "").strip()
    identity = _norm_identity(context.get("applicant_identity"))
    return replace(
        person,
        name=name if name and _norm_text(name) != _norm_text(person.name) else person.name,
        identity=identity if identity and identity != _norm_identity(person.identity) else person.identity,
    )


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
    """Khối chủ hồ sơ = người chết (trừ cờ requesterAsOwner), không bao giờ tick "Người nộp là chủ hồ sơ".

    Người đứng ra mai táng (ChuHoSo_*) hoặc NguoiNop_* chỉ vào khối người nộp khi khớp mỏ neo UI;
    toggle owner_as_submitter thì lấy thẳng người đứng ra mai táng làm người nộp.
    """
    values = _by_name(fields)
    deceased = _person(values, "NguoiMat")
    organizer = _person(values, "ChuHoSo")
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

    if not deceased and not organizer and not requester:
        return out, ["Không bóc tách được người chết hoặc người nộp từ tài liệu hợp lệ."]

    if is_requester_owner(options):
        return out, _fill_requester_owner(add, organizer, requester, deceased, context, options)

    add("data[isOwnerDossierCheck]", False)

    # Toggle owner_as_submitter: KHÔNG dùng mỏ neo UI, người nộp lấy theo người đứng ra mai táng trên
    # Tờ khai (Nghĩa Hưng), không so khớp tài khoản đăng nhập.
    submitter: Person | None = None
    if str((options or {}).get("submitterMode") or "") == "owner_as_submitter":
        submitter = organizer or requester
    elif organizer and _matches_applicant(organizer, context):
        submitter = _as_account(organizer, context)
    elif requester and _matches_applicant(requester, context):
        submitter = _as_account(requester, context)
    elif _has_applicant_anchor(context):
        anchor = context.get("applicant_identity") or context.get("applicant_name")
        warnings.append(
            "Không xác định được người nộp khớp thông tin trên form "
            f"({anchor}); không điền phần người nộp."
        )
    # Người chết không thể là người nộp, kể cả khi LLM lỡ trộn vai.
    if submitter and deceased and _same_person(submitter, deceased):
        submitter = None
    if submitter:
        _add_requester(add, submitter)

    if deceased:
        _add_owner(add, deceased)
    else:
        warnings.append("Không đọc được thông tin người chết để điền chủ hồ sơ.")
    return out, warnings


def _fill_requester_owner(
    add,
    owner: Person | None,
    requester: Person | None,
    deceased: Person | None,
    context: dict,
    options: dict | None,
) -> list[str]:
    """Cờ requesterAsOwner (phường Nha Trang, phường Tiên Du): khối chủ hồ sơ = người đề nghị trên tờ khai (ChuHoSo_*).

    Người đề nghị cũng là người nộp (khớp mỏ neo UI, hoặc toggle owner_as_submitter) thì tick "Người nộp là
    chủ hồ sơ"; NguoiNop_* khác người khớp UI thì vào khối người nộp, chủ hồ sơ vẫn là người đề nghị.
    """
    warnings: list[str] = []
    # Người chết không bao giờ là chủ hồ sơ/người nộp ở cấu hình này, kể cả khi LLM lỡ trộn vai.
    if owner and deceased and _same_person(owner, deceased):
        owner = None

    submitter: Person | None = None
    # Người nộp có phải chính người đề nghị không — xét trên người đọc từ giấy tờ, TRƯỚC khi thay họ tên / số theo tài
    # khoản (khớp gần thì số đã thay khác số trên giấy).
    is_owner = False
    if str((options or {}).get("submitterMode") or "") == "owner_as_submitter":
        submitter = owner or requester
        is_owner = submitter is not None and submitter is owner
    elif owner and _matches_applicant(owner, context):
        submitter, is_owner = _as_account(owner, context), True
    elif requester and _matches_applicant(requester, context):
        submitter = _as_account(requester, context)
        is_owner = bool(owner) and _same_person(owner, requester)
    elif _has_applicant_anchor(context):
        anchor = context.get("applicant_identity") or context.get("applicant_name")
        warnings.append(
            "Không xác định được người nộp khớp thông tin trên form "
            f"({anchor}); không điền phần người nộp."
        )
    if submitter and deceased and _same_person(submitter, deceased):
        submitter = None

    if owner and submitter and is_owner:
        add("data[isOwnerDossierCheck]", True)
        _add_requester(add, submitter)
        # Portal tự sao chép hầu hết field khi tick nhưng bỏ sót ngày sinh chủ hồ sơ, nên phát riêng sau
        # khối người nộp (như mai táng hưu trí xã hội).
        add("data[ownerBirthday]", owner.birthday)
        # Cổng cũng không chép giới tính khi tích (cán bộ phải tự sửa từ giới tính người chết).
        add("data[ownerGender]", owner.gender)
        return warnings

    add("data[isOwnerDossierCheck]", False)
    if submitter:
        _add_requester(add, submitter)
    if owner:
        _add_owner(add, owner)
    else:
        warnings.append("Không đọc được người đề nghị trên tờ khai để điền chủ hồ sơ.")
    return warnings


def _add_requester(add, person: Person) -> None:
    add("data[fullname]", person.name)
    add("data[birthday]", person.birthday)
    add("data[gender]", person.gender)
    add("data[identityNumber]", person.identity)
    add("data[identityDate]", person.issue_date)
    add("data[idIssuePlace]", person.issuer)
    add("data[phoneNumber]", person.phone)
    if person.residence:
        add("data[province]", _province_label(person.residence.get("tinh")))
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
        add("data[ownerProvince]", _province_label(person.residence.get("tinh")))
        add("data[ownerDistrict]", _area_label(person.residence.get("xa")))
        add("data[ownerAddress]", person.residence.get("diaChi"))
    add("data[ownerNation]", person.nationality or "Việt Nam")
