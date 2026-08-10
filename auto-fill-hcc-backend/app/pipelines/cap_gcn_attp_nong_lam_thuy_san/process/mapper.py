"""Map facts cấp GCN ATTP nông, lâm, thủy sản sang Form.io của cổng MAE."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_gcn_attp_nong_lam_thuy_san.process.schema import UI_COMP_BY_NAME


@dataclass
class Person:
    name: str | None = None
    identity: str | None = None
    birthday: str | None = None
    gender: str | None = None
    nationality: str | None = None
    issue_date: str | None = None
    issuer: str | None = None
    residence: dict | None = None


def _by_name(fields: list[dict]) -> dict:
    return {field["name"]: field["value"] for field in fields if field.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        direct = value.get("fullText") or value.get("full") or value.get("text") or value.get("diaChiDayDu")
        return _text(direct) if direct else _full_address(value)
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"[^0-9a-zA-Z]+", " ", text).strip().lower()


def _identity(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", str(value or ""))
    return digits or None


def _date(value: Any) -> str | None:
    text = _text(value)
    return normalize_date(text) if text else None


def _issuer(value: Any, issue_date: Any = None) -> str | None:
    text = _text(value)
    normalized = normalize_issuer(text) if text else None
    if normalized:
        return normalized
    date = _date(issue_date)
    return default_issuer(date) if date else None


def _phone(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    text = text.upper().replace("O", "0").replace("S", "5")
    digits = re.sub(r"\D+", "", text)
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(tỉnh|thành phố|tp\.?|xã|phường|thị trấn|tt\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _area(value: Any) -> dict | None:
    if isinstance(value, str):
        parts = [part.strip(" .") for part in re.split(r"\s*(?:,|;|\s+-\s+)\s*", value) if part.strip(" .")]
        if not parts:
            return None
        out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
        district_prefix = re.compile(r"^(huyện|quận|thành phố|tp\.?|thị xã)\s+", re.IGNORECASE)
        if len(parts) >= 4 and district_prefix.match(parts[-2]):
            out["tinh"], out["xa"], out["diaChi"] = parts[-1], parts[-3], ", ".join(parts[:-3])
        elif len(parts) >= 3:
            out["tinh"], out["xa"], out["diaChi"] = parts[-1], parts[-2], ", ".join(parts[:-2])
        elif len(parts) == 2:
            out["tinh"], out["diaChi"] = parts[-1], parts[0]
        else:
            out["diaChi"] = parts[0]
    elif isinstance(value, dict):
        out = {
            "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
            "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
            "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
            "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
        }
    else:
        return None
    
    # Apply area remapping to normalize xa/phuong names for administrative mergers
    out = remap_area(out, allow_diachi_fallback=True)
    return out if any(out.values()) else None


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    if folded.startswith("tinh ") or folded.startswith("thanh pho "):
        return text
    if folded.startswith("tp "):
        return re.sub(r"^TP\.?\s+", "Thành phố ", text, flags=re.IGNORECASE)
    cities = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
    return f"{'Thành phố' if folded in cities else 'Tỉnh'} {_strip_admin_prefix(text)}"


def _commune_label(value: Any) -> str | None:
    text = _text(value)
    return text


def _full_address(value: Any) -> str | None:
    area = _area(value)
    if not area:
        return None
    parts = [_text(area.get("diaChi")), _commune_label(area.get("xa")), _province_label(area.get("tinh"))]
    return ", ".join(part for part in parts if part) or None


def _person(values: dict, prefix: str) -> Person | None:
    name = _text(values.get(f"{prefix}_HoTen"))
    identity = _identity(values.get(f"{prefix}_SoDinhDanh"))
    if not name and not identity:
        return None
    issue_date = _date(values.get(f"{prefix}_NgayCap"))
    return Person(
        name=name,
        identity=identity,
        birthday=_date(values.get(f"{prefix}_NgaySinh")),
        gender=_text(values.get(f"{prefix}_GioiTinh")),
        nationality=_text(values.get(f"{prefix}_QuocTich")) or "Việt Nam",
        issue_date=issue_date,
        issuer=_issuer(values.get(f"{prefix}_NoiCap"), issue_date),
        residence=_area(values.get(f"{prefix}_NoiCuTru")),
    )


def _people(values: dict) -> list[Person]:
    return [person for prefix in ("Person1", "Person2") if (person := _person(values, prefix))]


def _same_name(a: Any, b: Any) -> bool:
    return bool(_fold(a) and _fold(a) == _fold(b))


def _same_person_strict(a: Person | None, name: Any, identity: Any) -> bool:
    return bool(
        a
        and a.name
        and a.identity
        and _same_name(a.name, name)
        and a.identity == _identity(identity)
    )


def _requester_from_context(people: list[Person], options: dict | None) -> tuple[Person | None, str | None]:
    context = (options or {}).get("formContext") or {}
    context_name = _text(context.get("applicantFullname") or context.get("fullname"))
    context_identity = _identity(context.get("applicantIdentityNumber") or context.get("identityNumber"))
    if not context_name or not context_identity:
        return None, "Không nhận đủ họ tên và CCCD người nộp từ biểu mẫu; giữ nguyên Phần I."
    matches = [person for person in people if _same_person_strict(person, context_name, context_identity)]
    if len(matches) != 1:
        return None, "Không có đúng một CCCD upload khớp cả họ tên và số định danh người nộp; giữ nguyên Phần I."
    requester = matches[0]
    requester.name = context_name
    requester.identity = context_identity
    return requester, None


def _pick(*values: Any) -> Any:
    return next((value for value in values if value not in (None, "", {}, [])), None)


def _owner(values: dict, people: list[Person]) -> Person | None:
    representative = _text(_pick(
        values.get("Don_DaiDienCoSo"),
        values.get("DangKy_NguoiDaiDien"),
        values.get("ThuyetMinh_DaiDienCoSo"),
    ))
    if not representative:
        return None
    matching = [person for person in people if _same_name(person.name, representative)]
    if len(matching) == 1:
        matched = matching[0]
        person = Person(
            name=representative,
            identity=matched.identity,
            birthday=matched.birthday,
            gender=matched.gender,
            nationality=matched.nationality,
            issue_date=matched.issue_date,
            issuer=matched.issuer,
            residence=matched.residence,
        )
    else:
        person = Person(name=representative, nationality="Việt Nam")
    person.residence = person.residence or _area(_pick(
        values.get("Don_DiaChiCoSo"),
        values.get("DangKy_DiaChiCoSo"),
        values.get("ThuyetMinh_DiaChiCoSo"),
    ))
    return person


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    people = _people(values)
    requester, requester_warning = _requester_from_context(people, options)
    owner = _owner(values, people)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None]] = set()

    def add(name: str, value: Any, *, occurrence: int | None = None, default: bool = False) -> None:
        seen_key = (name, occurrence)
        if seen_key in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if occurrence is not None:
            item["occurrence"] = occurrence
        if default:
            item["default"] = True
        out.append(item)
        seen.add(seen_key)

    if requester_warning:
        warnings.append(requester_warning)
    if not owner:
        warnings.append("Không đọc được họ tên đại diện cơ sở từ Đơn đề nghị/Giấy đăng ký kinh doanh.")

    # Snapshot được cung cấp là nhánh Cá nhân. Không tự mở nhánh Tổ chức khi chưa có HTML các field điều kiện.
    add("data[chonDoiTuong]", "Cá nhân", default=True)

    if requester:
        add("data[fullname]", requester.name)
        add("data[birthday]", requester.birthday)
        add("data[gender]", requester.gender)
        add("data[identityNumber]", requester.identity)
        add("data[identityDate]", requester.issue_date)
        add("data[idIssuePlace]", requester.issuer)
        if requester.residence:
            add("data[province]", _province_label(requester.residence.get("tinh")))
            add("data[district]", _commune_label(requester.residence.get("xa")))
            add("data[address]", _text(requester.residence.get("diaChi")), occurrence=0)

    requester_is_owner = bool(owner and requester and _same_person_strict(owner, requester.name, requester.identity))
    add("data[isOwnerDossierCheck]", requester_is_owner)
    if owner and not requester_is_owner:
        add("data[ownerFullname]", owner.name)
        add("data[ownerBirthday]", owner.birthday)
        add("data[ownerGender]", owner.gender)
        add("data[ownerIdentityNumber]", owner.identity)
        add("data[ownerIdentityDate]", owner.issue_date)
        add("data[ownerIdIssuePlace]", owner.issuer)
        if owner.residence:
            add("data[ownerProvince]", _province_label(owner.residence.get("tinh")))
            add("data[ownerDistrict]", _commune_label(owner.residence.get("xa")))
            add("data[ownerAddress]", _text(owner.residence.get("diaChi")))
        add("data[ownerPhoneNumber]", _phone(values.get("Don_DienThoai")))
        add("data[ownerEmail]", _text(values.get("Don_Email")))
        add("data[ownerNation]", owner.nationality or "Việt Nam")

    facility_name = _text(_pick(values.get("Don_TenCoSo"), values.get("DangKy_TenCoSo"), values.get("ThuyetMinh_TenCoSo")))
    facility_area = _area(_pick(values.get("Don_DiaChiCoSo"), values.get("DangKy_DiaChiCoSo"), values.get("ThuyetMinh_DiaChiCoSo")))
    representative = _text(_pick(values.get("Don_DaiDienCoSo"), values.get("DangKy_NguoiDaiDien"), values.get("ThuyetMinh_DaiDienCoSo")))

    add("data[diaDanh]", _province_label(values.get("Don_DiaDanh")))
    add("data[ngayBC]", _date(values.get("Don_NgayDon")))
    add("data[kinhGui1]", _text(values.get("Don_KinhGui")))
    add("data[organization]", facility_name, occurrence=0)
    add("data[address]", _full_address(facility_area), occurrence=1)
    add("data[phoneNumber]", _phone(values.get("Don_DienThoai")), occurrence=1)
    add("data[email2]", _text(values.get("Don_Email")))
    add("data[maso]", _text(_pick(values.get("Don_MaSoDKKD"), values.get("DangKy_MaSo"))))
    add("data[soGDK]", _text(_pick(values.get("Don_SoDangKy"), values.get("DangKy_SoDangKy"))))
    add("data[ngayCap]", _date(_pick(values.get("Don_NgayCapDKKD"), values.get("DangKy_NgayCap"))))
    add("data[noiCap]", _text(_pick(values.get("Don_NoiCapDKKD"), values.get("DangKy_NoiCap"))))
    add("data[mathangsx]", _text(_pick(values.get("Don_MatHang"), values.get("ThuyetMinh_MatHang"))))
    add("data[lydocaplai]", _text(values.get("Don_LyDoCap")))
    add("data[daidiencoso]", representative)

    return out, warnings
