"""Map người nộp, chủ hồ sơ và người có công sang Form.io của cổng Bộ Nội vụ."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.giai_quyet_che_do_khang_chien.process.schema import UI_COMP_BY_NAME


def _by_name(fields: list[dict]) -> dict:
    return {field["name"]: field["value"] for field in fields if field.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        direct = value.get("fullText") or value.get("full") or value.get("text")
        if direct:
            return _text(direct)
        parts = [
            value.get("diaChi") or value.get("dia_chi") or value.get("chiTiet"),
            value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường"),
            value.get("huyen") or value.get("quanHuyen"),
            value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh"),
        ]
        return ", ".join(str(part).strip() for part in parts if str(part or "").strip()) or None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _pick(*values):
    for value in values:
        if value not in (None, "", {}, []):
            return value
    return None


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(tỉnh|thành phố|tp\.?|xã|phường|thị trấn|tt\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    if folded.startswith(("tinh ", "thanh pho ", "tp ")):
        return text
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "tp ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {_strip_admin_prefix(text)}"


def _commune_label(value: Any) -> str | None:
    return _text(value)


def _parse_area_text(value: Any) -> dict | None:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip(" .")
    if not text:
        return None
    parts = [part.strip(" .") for part in re.split(r"\s*(?:,|;|\s+-\s+)\s*", text) if part.strip(" .")]
    if not parts:
        return None
    out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
    district_prefix = re.compile(r"^(huyện|quận|thành phố|tp\.?|thị xã)\s+", re.IGNORECASE)
    if len(parts) >= 4 and district_prefix.match(parts[-2]):
        out["tinh"] = parts[-1]
        out["xa"] = parts[-3]
        out["diaChi"] = ", ".join(parts[:-3]).strip()
    elif len(parts) >= 3:
        out["tinh"] = parts[-1]
        out["xa"] = parts[-2]
        out["diaChi"] = ", ".join(parts[:-2]).strip()
    elif len(parts) == 2:
        out["tinh"] = parts[-1]
        out["diaChi"] = parts[0]
    else:
        out["diaChi"] = parts[0]
    return out if any(out.values()) else None


def _area(value: Any) -> dict | None:
    if isinstance(value, str):
        out = _parse_area_text(value)
    elif isinstance(value, dict):
        out = {
            "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
            "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
            "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
            "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
        }
        if not any(out.values()):
            out = None
    else:
        out = None
    if out and (out.get("tinh") or out.get("xa")):
        return remap_area(out) or out
    return out


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or None


def _phone(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text.upper().replace("O", "0").replace("S", "5"))
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text)
    if match:
        return normalize_date(match.group(0).replace("-", "/"))
    return normalize_date(text)


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _item_text(item: Any, *keys: str) -> str | None:
    if not isinstance(item, dict):
        return None
    return _text(_pick(*(item.get(key) for key in keys)))


def _form_context(options: dict | None) -> dict:
    context = (options or {}).get("formContext") or {}
    return {
        "applicant_name": context.get("applicantFullname") or context.get("fullname") or "",
        "applicant_identity": context.get("applicantIdentityNumber") or context.get("identityNumber") or "",
    }


def _has_context_anchor(context: dict) -> bool:
    return bool(_identity(context.get("applicant_identity")) or _fold(context.get("applicant_name")))


def _matches_context(person: dict, context: dict) -> bool:
    """Khi UI có cả tên và CCCD thì ứng viên bắt buộc khớp cả hai."""
    context_name = _fold(context.get("applicant_name"))
    context_identity = _identity(context.get("applicant_identity"))
    person_name = _fold(person.get("name"))
    person_identity = _identity(person.get("identity"))
    if context_name and context_identity:
        return person_name == context_name and person_identity == context_identity
    if context_identity:
        return bool(person_identity and person_identity == context_identity)
    return bool(context_name and person_name == context_name)


def _role(values: dict, prefix: str) -> dict | None:
    name = _text(values.get(f"{prefix}_HoTen"))
    identity = _identity(values.get(f"{prefix}_SoDinhDanh"))
    if not name and not identity:
        return None
    return {
        "name": name,
        "birthday": values.get(f"{prefix}_NgaySinh"),
        "gender": values.get(f"{prefix}_GioiTinh"),
        "identity": identity,
        "issue_date": values.get(f"{prefix}_NgayCap"),
        "issue_place": values.get(f"{prefix}_NoiCap"),
        "residence": values.get(f"{prefix}_NoiCuTru"),
        "phone": values.get(f"{prefix}_DienThoai"),
        "nationality": values.get(f"{prefix}_QuocTich") or "Việt Nam",
        "origin": values.get(f"{prefix}_QueQuan"),
        "relationship": values.get(f"{prefix}_MoiQuanHe"),
    }


def _add_area(add, province_name, district_name, address_name, value, *, occurrence=None) -> None:
    area = _area(value)
    if not area:
        return
    add(province_name, _province_label(area.get("tinh")), occurrence=occurrence)
    add(district_name, _commune_label(area.get("xa")), occurrence=occurrence)
    add(address_name, _text(area.get("diaChi")), occurrence=occurrence)


def _add_person_block(add, person: dict, *, owner: bool, occurrence=None) -> None:
    if owner:
        add("data[ownerFullname]", person.get("name"))
        add("data[ownerBirthday]", _date(person.get("birthday")))
        add("data[ownerGender]", _text(person.get("gender")))
        add("data[ownerIdentityNumber]", _identity(person.get("identity")))
        add("data[ownerIdentityDate]", _date(person.get("issue_date")))
        add("data[ownerIdIssuePlace]", _issuer(person.get("issue_place")) or _text(person.get("issue_place")))
        _add_area(add, "data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", person.get("residence"))
        add("data[ownerPhoneNumber]", _phone(person.get("phone")))
        add("data[ownerNation]", person.get("nationality") or "Việt Nam")
        return

    add("data[fullname]", person.get("name"), occurrence=occurrence)
    add("data[birthday]", _date(person.get("birthday")), occurrence=occurrence)
    add("data[gender]", _text(person.get("gender")), occurrence=occurrence)
    add("data[identityNumber]", _identity(person.get("identity")), occurrence=occurrence)
    add("data[identityDate]", _date(person.get("issue_date")), occurrence=occurrence)
    add("data[idIssuePlace]", _issuer(person.get("issue_place")) or _text(person.get("issue_place")), occurrence=occurrence)
    _add_area(add, "data[province]", "data[district]", "data[address]", person.get("residence"), occurrence=occurrence)
    add("data[phoneNumber]", _phone(person.get("phone")), occurrence=occurrence)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    owner = _role(values, "ChuHoSo")
    requester = _role(values, "NguoiNop")
    subject = _role(values, "NguoiCoCong")
    detail_subject = subject or owner
    context = _form_context(options)

    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None]] = set()

    def add(name: str, value, *, occurrence=None) -> None:
        key = (name, occurrence)
        if key in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if occurrence is not None:
            field["occurrence"] = occurrence
        out.append(field)
        seen.add(key)

    owner_matches = bool(owner and _matches_context(owner, context))
    requester_matches = bool(requester and _matches_context(requester, context))

    # Checkbox phải đứng trước để portal render/clear đúng khối chủ hồ sơ.
    if owner or requester:
        add("data[isOwnerDossierCheck]", owner_matches)

    if owner_matches and owner:
        add("data[chonDoiTuong]", "Cá nhân")
        _add_person_block(add, owner, owner=False, occurrence=0)
    elif requester_matches and requester:
        add("data[chonDoiTuong]", "Cá nhân")
        _add_person_block(add, requester, owner=False, occurrence=0)
        add("data[email]", _text(values.get("NguoiNop_Email")))
    elif _has_context_anchor(context) and owner:
        anchor = context.get("applicant_identity") or context.get("applicant_name")
        warnings.append(f"Không xác định được người nộp khớp thông tin trên form ({anchor}); không điền phần người nộp.")

    # Chủ hồ sơ luôn giữ nguyên dù không xác minh được người nộp.
    if owner:
        add("data[chonDoiTuong1]", "Cá nhân")
        _add_person_block(add, owner, owner=True)
    else:
        warnings.append("Chưa đọc được chủ hồ sơ từ người nhận mai táng phí/đại diện thân nhân trong Bản khai.")

    # Mẫu 12: Mục 1 là người có công đã chết. Mẫu 11 không tách NguoiCoCong_*
    # nên dùng chính chủ hồ sơ để giữ tương thích biểu mẫu đang sống.
    add("data[CheDo]", _text(values.get("HDKC_CheDo")))
    if detail_subject:
        add("data[fullname]", detail_subject.get("name"), occurrence=1)
        add("data[birthday]", _date(detail_subject.get("birthday")), occurrence=1)
        add("data[gender]", _text(detail_subject.get("gender")), occurrence=1)
        add("data[identityNumber]", _identity(detail_subject.get("identity")), occurrence=1)
        add("data[identityDate]", _date(detail_subject.get("issue_date")), occurrence=1)
        add("data[identityAgency]", _issuer(detail_subject.get("issue_place")) or _text(detail_subject.get("issue_place")))
        _add_area(add, "data[province]", "data[district]", "data[address]", detail_subject.get("origin"), occurrence=1)
    bi_danh = _text(values.get("HDKC_BiDanh"))
    if bi_danh and _fold(bi_danh) in {"nam", "nu"}:
        bi_danh = None
    add("data[biDanh]", bi_danh)
    add("data[quaTrinh]", _text(values.get("HDKC_QuaTrinh")))
    add("data[thanhTich]", _text(values.get("HDKC_ThanhTich")))
    add("data[duocTang]", _text(values.get("HDKC_DuocTang")))

    # Khi NguoiCoCong_* tách khỏi chủ hồ sơ, chủ hồ sơ chính là cá nhân
    # nhận mai táng phí/đại diện thân nhân, nên lặp đúng người đó vào Mục 2.
    if subject and owner:
        add("data[fullname1]", owner.get("name"))
        add("data[birthday1]", _date(owner.get("birthday")))
        add("data[gender1]", _text(owner.get("gender")))
        add("data[identityNumber1]", _identity(owner.get("identity")))
        add("data[identityDate1]", _date(owner.get("issue_date")))
        add("data[identityAgency1]", _issuer(owner.get("issue_place")) or _text(owner.get("issue_place")))
        _add_area(add, "data[province1]", "data[district1]", "data[address1]", owner.get("origin"))
        _add_area(add, "data[province2]", "data[district2]", "data[address2]", owner.get("residence"))
        add("data[phoneNumber]", _phone(owner.get("phone")), occurrence=1)
        add("data[moiQH]", _text(owner.get("relationship")))
    add("data[ngayMat]", _date(values.get("NguoiCoCong_NgayMat")))

    ho_so = _list(values.get("HoSoDinhKem"))
    if ho_so:
        add("data[hoSoDinhKem][0][textField1]", _item_text(ho_so[0], "tenGiayTo", "ten", "name"))
        add("data[hoSoDinhKem][0][textField2]", _item_text(ho_so[0], "loaiBan", "loai", "type") or "Bản chính")

    return out, warnings
