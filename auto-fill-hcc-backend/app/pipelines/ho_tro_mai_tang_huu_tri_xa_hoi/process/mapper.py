"""Đổi hai chủ thể nghiệp vụ sang field Form.io của mai táng hưu trí xã hội."""

import re
import unicodedata
from dataclasses import dataclass, replace

from app.pipelines._shared import area_remap
from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.process.schema import UI_COMP_BY_NAME


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


# Cấu hình theo tài khoản: phường Cam Đường (Lào Cai), xã Bình Chương (Quảng Ngãi) và các đơn vị trong _DECEASED_OWNER_WARDS khai NGƯỜI CHẾT làm chủ hồ sơ trên cổng; người
# đứng ra mai táng chỉ còn là ứng viên người nộp. Nơi khác giữ nguyên logic. Mapper không biết tài
# khoản nên router (Auto Fill) và pipeline_runner (Handfree) gọi with_account_process_options để server
# tự đặt cờ; cờ luôn bị ghi đè theo tài khoản, client không tự bật được cho xã khác.
PROCEDURE_KEY = "ho-tro-mai-tang-huu-tri-xa-hoi"
DECEASED_AS_OWNER_OPTION = "deceasedAsOwner"
_WARD_PREFIXES = ("xa ", "phuong ", "thi tran ")


def is_deceased_owner(options: dict | None) -> bool:
    """Người chết là chủ hồ sơ: cờ theo tài khoản HOẶC công tắc "Lấy người nộp theo tờ khai" đang bật
    (submitterMode=owner_as_submitter, mọi tài khoản) — bật thì chủ hồ sơ = người mất, người nộp = người đề
    nghị trên tờ khai; tắt thì giữ logic mỏ neo UI cũ."""
    options = options or {}
    return (
        options.get(DECEASED_AS_OWNER_OPTION) is True
        or str(options.get("submitterMode") or "") == "owner_as_submitter"
    )


def is_lao_cai_cam_duong(user: dict | None) -> bool:
    """True khi tài khoản thuộc phường Cam Đường, tỉnh Lào Cai (khớp tỉnh và ĐÚNG tên phường)."""
    if not user:
        return False
    tinh = _norm_text(user.get("tinh"))
    xa = _norm_text(user.get("xa"))
    for prefix in _WARD_PREFIXES:
        if xa.startswith(prefix):
            xa = xa[len(prefix):].strip()
            break
    return "lao cai" in tinh and xa == "cam duong"


def is_quang_ngai_binh_chuong(user: dict | None) -> bool:
    """True khi tài khoản thuộc xã Bình Chương, tỉnh Quảng Ngãi (khớp tỉnh và ĐÚNG tên xã)."""
    if not user:
        return False
    tinh = _norm_text(user.get("tinh"))
    xa = _norm_text(user.get("xa"))
    for prefix in _WARD_PREFIXES:
        if xa.startswith(prefix):
            xa = xa[len(prefix):].strip()
            break
    return "quang ngai" in tinh and xa == "binh chuong"


# Cấu hình theo tài khoản: xã Nghĩa Hưng (Ninh Bình) không điền email người nộp. Cổng tự nạp email
# tài khoản cán bộ vào ô "Email liên hệ" nên phải XOÁ ô; nơi khác giữ nguyên ô email như cũ.
CLEAR_EMAIL_OPTION = "clearEmail"


def is_ninh_binh_nghia_hung(user: dict | None) -> bool:
    """True khi tài khoản thuộc xã Nghĩa Hưng, tỉnh Ninh Bình (khớp tỉnh và ĐÚNG tên xã)."""
    if not user:
        return False
    tinh = _norm_text(user.get("tinh"))
    xa = _norm_text(user.get("xa"))
    for prefix in _WARD_PREFIXES:
        if xa.startswith(prefix):
            xa = xa[len(prefix):].strip()
            break
    return "ninh binh" in tinh and xa == "nghia hung"


# Các đơn vị khác cũng khai NGƯỜI CHẾT làm chủ hồ sơ trên cổng: (tỉnh, tên phường/xã) bỏ dấu, bỏ cấp. Tên xã tài khoản có
# thể kèm hậu tố khu vực cũ ("<tên> - Đà Lạt") nên khớp phần đầu theo ranh giới từ.
_DECEASED_OWNER_WARDS = (
    ("quang ngai", "dak bla"),
    ("ninh binh", "nam hoa lu"),
    ("bac ninh", "canh thuy"),
    ("da nang", "lien chieu"),
    ("bac ninh", "vu ninh"),
)


def is_deceased_owner_ward(user: dict | None) -> bool:
    if not user:
        return False
    tinh = _norm_text(user.get("tinh"))
    xa = _norm_text(user.get("xa"))
    for prefix in _WARD_PREFIXES:
        if xa.startswith(prefix):
            xa = xa[len(prefix):].strip()
            break
    return any(province in tinh and (xa == ward or xa.startswith(ward + " ")) for province, ward in _DECEASED_OWNER_WARDS)


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Trả bản sao options với các cờ theo tài khoản do server quyết (người chết là chủ hồ sơ, xoá email)."""
    result = dict(options or {})
    result.pop(DECEASED_AS_OWNER_OPTION, None)
    result.pop(CLEAR_EMAIL_OPTION, None)
    if procedure == PROCEDURE_KEY and (is_lao_cai_cam_duong(user) or is_quang_ngai_binh_chuong(user)
                                       or is_deceased_owner_ward(user)):
        result[DECEASED_AS_OWNER_OPTION] = True
    if procedure == PROCEDURE_KEY and is_ninh_binh_nghia_hung(user):
        result[CLEAR_EMAIL_OPTION] = True
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
    """Số di động 10 chữ số; tờ khai hay viết tách bằng dấu chấm / khoảng trắng ("038.649.7941") mà ô SĐT của cổng chỉ nhận
    chữ số. Không đủ 10 số (thiếu / số bàn) thì bỏ trống."""
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
        # OCR chữ viết tay hay lệch 1–2 ký tự ở MỘT trong hai (tên đọc "TUẤY", số rơi một chữ số): một bên khớp hẳn, bên
        # kia lệch không quá 2 ký tự vẫn là cùng người; lệch cả hai thì không nhận.
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
    """Xác thực người nộp rồi phát hai khối UI theo đúng vai trò."""
    out, warnings = _enrich_roles(fields, options)
    if (options or {}).get(CLEAR_EMAIL_OPTION) is True:
        # Phát SAU khối người nộp: cổng tự nạp email tài khoản cán bộ khi điền/tick người nộp nên
        # phải xoá cuối cùng. `clear`: extension không tô xanh ô trống.
        out = [f for f in out if f["name"] != "data[email]"]
        out.append({"name": "data[email]", "comp": UI_COMP_BY_NAME["data[email]"], "value": "", "clear": True})
    return out, warnings


def _enrich_roles(
    fields: list[dict],
    options: dict | None = None,
) -> tuple[list[dict], list[str]]:
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

    if is_deceased_owner(options):
        return out, _fill_deceased_owner(add, values, owner, requester, context, options)

    if not owner and not requester:
        return out, ["Không bóc tách được chủ hồ sơ hoặc người nộp từ tài liệu hợp lệ."]

    # Người đứng ra mai táng trùng mỏ neo UI: tự nộp, tích checkbox và dùng
    # chính chủ hồ sơ cho khối người nộp. Ngày sinh UI cũ không tham gia khớp.
    if owner and _matches_applicant(owner, context):
        add("data[isOwnerDossierCheck]", True)
        _add_requester(add, _as_account(owner, context))
        # Portal tự sao chép hầu hết field khi tick nhưng bỏ sót ngày sinh chủ
        # hồ sơ, nên phải phát riêng đúng field này sau khối người nộp.
        add("data[ownerBirthday]", owner.birthday)
        # Cổng cũng không chép giới tính khi tích (cán bộ phải tự sửa từ giới tính người chết).
        add("data[ownerGender]", owner.gender)
        return out, warnings

    # Nộp thay: chỉ dùng NguoiNop sau khi khớp lại toàn bộ mỏ neo UI hiện có.
    if owner and requester and _matches_applicant(requester, context):
        if _same_person(owner, requester):
            add("data[isOwnerDossierCheck]", True)
            _add_requester(add, _as_account(owner, context))
            add("data[ownerBirthday]", owner.birthday)
            # Cổng cũng không chép giới tính khi tích (cán bộ phải tự sửa từ giới tính người chết).
            add("data[ownerGender]", owner.gender)
        else:
            add("data[isOwnerDossierCheck]", False)
            _add_requester(add, _as_account(requester, context))
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
        _add_requester(add, _as_account(requester, context))
        warnings.append("Đã xác định người nộp nhưng chưa đọc được chủ hồ sơ từ Mẫu số 04.")
        return out, warnings

    anchor = context.get("applicant_identity") or context.get("applicant_name") or "(trống)"
    return out, [
        "Người nộp trích xuất không khớp thông tin trên form "
        f"({anchor}); không điền để tránh nhầm người."
    ]


def _fill_deceased_owner(
    add,
    values: dict,
    organizer: Person | None,
    requester: Person | None,
    context: dict,
    options: dict | None,
) -> list[str]:
    """Cờ deceasedAsOwner / công tắc owner_as_submitter: khối chủ hồ sơ = người chết, không bao giờ tick tự nộp.

    Người đứng ra mai táng (ChuHoSo_*) hoặc NguoiNop_* chỉ vào khối người nộp khi khớp mỏ neo UI;
    toggle owner_as_submitter thì lấy thẳng người đứng ra mai táng làm người nộp.
    """
    deceased = _person(values, "NguoiMat")
    warnings: list[str] = []
    add("data[isOwnerDossierCheck]", False)

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
