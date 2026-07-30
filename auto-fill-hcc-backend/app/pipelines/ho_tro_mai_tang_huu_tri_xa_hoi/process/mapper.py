"""Map compact CCCD facts to Form.io fields for funeral support."""

import re
import unicodedata
from dataclasses import dataclass

from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.process.schema import UI_COMP_BY_NAME

from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines._shared.area_remap import remap_area


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
    """xa CHỈ giữ TÊN đơn vị, bỏ tiền tố loại (Xã/Phường/Thị trấn/TT)."""
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
    return remap_area(out)


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
    return Person(
        prefix=prefix,
        name=name,
        identity=identity,
        birthday=values.get(f"{prefix}_NgaySinh"),
        gender=values.get(f"{prefix}_GioiTinh"),
        nationality=values.get(f"{prefix}_QuocTich") or "Việt Nam",
        issue_date=values.get(f"{prefix}_NgayCap"),
        issuer=values.get(f"{prefix}_NoiCap") or default_issuer(values.get(f"{prefix}_NgayCap")),
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


def _matches_applicant(person: Person, context: dict) -> bool:
    ctx_identity = _norm_identity(context.get("applicant_identity"))
    if ctx_identity and _norm_identity(person.identity) == ctx_identity:
        return True
    ctx_name = _norm_text(context.get("applicant_name"))
    return bool(ctx_name and _norm_text(person.name) == ctx_name)


def _same_person(a_id, a_name, b_id, b_name) -> bool:
    """Hai người trùng nhau? Số định danh khớp → cùng người. Nếu số LỆCH hoặc THIẾU thì vẫn
    xét tên (bỏ dấu) — vì số CMND/CCCD trên TỜ KHAI VIẾT TAY hay bị OCR sai vài chữ số, không được
    để số sai phủ quyết một tên trùng khớp hoàn toàn."""
    ai, bi = _norm_identity(a_id), _norm_identity(b_id)
    if ai and bi and ai == bi:
        return True
    an, bn = _norm_text(a_name), _norm_text(b_name)
    return bool(an and bn and an == bn)


def _tokhai_owner(values: dict) -> dict | None:
    """Chủ hồ sơ lấy từ TỜ KHAI mục II.2 (nhóm ToKhai_ChuHo*). Không có → None."""
    name = values.get("ToKhai_ChuHoTen")
    identity = values.get("ToKhai_ChuHoSoGiayTo")
    if not name and not identity:
        return None
    return {
        "name": name,
        "identity": identity,
        "birthday": values.get("ToKhai_ChuHoNamSinh"),
        "issue_date": values.get("ToKhai_ChuHoNgayCap"),
        "issuer": values.get("ToKhai_ChuHoNoiCap"),
        "residence": _area(values.get("ToKhai_ChuHoNoiCuTru")),
    }


def _owner_from_tokhai(tk: dict, people: list[Person]) -> Person:
    """Dựng chủ hồ sơ: định danh ƯU TIÊN CCCD của chính người đó (nếu upload có),
    KHÔNG có thì lấy từ tờ khai. Địa chỉ ƯU TIÊN tờ khai (2 cấp xã+tỉnh); nếu tờ khai không
    tách được xã/tỉnh thì fallback CCCD của người đó.
    """
    match = next(
        (p for p in people if _same_person(p.identity, p.name, tk.get("identity"), tk.get("name"))),
        None,
    )

    def pick(cccd_val, tk_val):
        return cccd_val or tk_val

    tk_res = tk.get("residence")
    if tk_res and (tk_res.get("tinh") or tk_res.get("xa")):
        residence = tk_res                       # tờ khai rõ (địa chỉ 2 cấp sáp nhập)
    else:
        residence = (match.residence if match else None) or tk_res

    issue_date = pick(match.issue_date if match else None, tk.get("issue_date"))
    return Person(
        prefix="Owner",
        name=pick(match.name if match else None, tk.get("name")),
        identity=pick(match.identity if match else None, tk.get("identity")),
        birthday=pick(match.birthday if match else None, tk.get("birthday")),
        gender=(match.gender if match else None),  # tờ khai không ghi giới tính → để trống
        nationality=(match.nationality if match else None) or "Việt Nam",
        issue_date=issue_date,
        issuer=pick(match.issuer if match else None, tk.get("issuer")) or default_issuer(issue_date),
        residence=residence,
    )


def _pick_requester(people: list[Person], context: dict) -> tuple[Person | None, str | None]:
    """Người nộp = CCCD khớp tên/số UI truyền lên. Chỉ 1 CCCD thì coi CCCD đó là người nộp."""
    matches = [p for p in people if _matches_applicant(p, context)]
    if len(matches) == 1:
        return matches[0], None
    if len(people) == 1:
        return people[0], None
    ctx = context.get("applicant_identity") or context.get("applicant_name") or "(trống)"
    return None, (
        "Không xác định được CCCD người nộp từ thông tin trên form "
        f"({ctx}); cần form prefill khớp một CCCD đã upload."
    )


def _split_roles(people: list[Person], context: dict) -> tuple[Person | None, Person | None, list[str]]:
    if len(people) == 1:
        return people[0], people[0], []

    matches = [p for p in people if _matches_applicant(p, context)]
    if len(matches) == 1:
        applicant = matches[0]
        owner = next((p for p in people if p is not applicant), None)
        return applicant, owner, []

    ctx = context.get("applicant_identity") or context.get("applicant_name") or "(trống)"
    return None, None, [
        "Không xác định được CCCD người nộp từ thông tin đang có trên form "
        f"({ctx}); cần form prefill khớp một trong các CCCD đã upload."
    ]


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    """Derive ordered DOM fields and warnings from compact source facts."""
    values = _by_name(fields)
    people = _people(values)
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

    context = _form_context(options)
    tk = _tokhai_owner(values)

    # ── Có TỜ KHAI (Mẫu 04): người nộp = CCCD khớp UI; chủ hồ sơ = mục II.2 tờ khai ──
    if tk is not None:
        if not people:
            return out, ["Có tờ khai nhưng không đọc được CCCD của người nộp hồ sơ."]
        requester, warn = _pick_requester(people, context)
        if warn:
            warnings.append(warn)
        if not requester:
            return out, warnings

        owner = _owner_from_tokhai(tk, people)
        same_person = _same_person(requester.identity, requester.name, owner.identity, owner.name)
        add("data[isOwnerDossierCheck]", same_person)
        _add_requester(add, requester)
        if not same_person:
            _add_owner(add, owner)
        return out, warnings

    # ── Không có tờ khai (chỉ CCCD): giữ logic cũ ──
    if not people:
        return out, ["Không đọc được CCCD/CMND hợp lệ cho thủ tục hỗ trợ mai táng."]

    applicant, owner, role_warnings = _split_roles(people, context)
    warnings.extend(role_warnings)
    if not applicant or not owner:
        return out, warnings

    same_person = applicant is owner
    add("data[isOwnerDossierCheck]", same_person)

    if same_person:
        _add_requester(add, applicant)
    else:
        _add_requester(add, applicant)
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
    add("data[ownerNation]", person.nationality or "Việt Nam")
