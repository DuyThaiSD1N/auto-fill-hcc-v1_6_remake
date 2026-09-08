"""Map compact ATTP reissue facts to Form.io fields."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_lai_an_toan_thuc_pham.process.schema import UI_COMP_BY_NAME


@dataclass
class Person:
    name: str | None = None
    identity: str | None = None
    birthday: str | None = None
    issue_date: str | None = None
    issuer: str | None = None
    residence: Any = None
    phone: str | None = None
    email: str | None = None


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        return _full_address(value)
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _field(value: Any, *keys: str) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in keys:
        raw = value.get(key)
        if raw not in (None, "", {}, []):
            return _text(raw)
    return None


def _full_address(value: Any) -> str | None:
    if isinstance(value, str):
        return _text(value)
    if not isinstance(value, dict):
        return None
    direct = _field(value, "fullText", "full", "text", "diaChiDayDu")
    if direct:
        return direct
    parts = [
        _field(value, "diaChi", "chiTiet", "thonXom", "soNha"),
        _field(value, "xa", "phuongXa", "phuong"),
        _field(value, "huyen", "quanHuyen"),
        _field(value, "tinh", "tinhThanh"),
    ]
    return ", ".join(p for p in parts if p) or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _norm_identity(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _same_person(a_id: Any, a_name: Any, b_id: Any, b_name: Any) -> bool:
    ai, bi = _norm_identity(a_id), _norm_identity(b_id)
    if ai and bi:
        if ai == bi:
            return True
        if len(ai) >= 9 and len(bi) >= 9:
            return False
    an, bn = _fold(a_name), _fold(b_name)
    return bool(an and bn and an == bn)


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(xã|phường|thị trấn|tt\.?|tỉnh|thành phố|tp\.?)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _area(value: Any) -> dict | None:
    if isinstance(value, str):
        parts = [p.strip(" .") for p in re.split(r"[,;\n-]+", value) if p.strip(" .")]
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
        return remap_area(out, allow_diachi_fallback=True) if any(out.values()) else None
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    if not any(out.values()):
        return None
    return remap_area(out, allow_diachi_fallback=True)


def _area_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    changed = True
    prefixes = ("Thành phố", "Tỉnh", "Thị trấn", "Thị xã", "Phường", "Xã", "Huyện", "Quận", "TP.")
    while changed:
        changed = False
        norm_text = _fold(text)
        for prefix in prefixes:
            norm_prefix = _fold(prefix)
            if norm_text == norm_prefix:
                return None
            if norm_text.startswith(norm_prefix + " "):
                text = text[len(prefix):].strip()
                changed = True
                break
    return text


def _phone(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    text = text.upper().replace("O", "0").replace("S", "5")
    digits = re.sub(r"\D+", "", text)
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    if 10 <= len(digits) <= 11 and digits.startswith("0"):
        return digits
    return None


def _issuer(place: Any, issue_date: Any) -> str | None:
    normalized = normalize_issuer(place)
    if normalized:
        return normalized
    date = normalize_date(str(issue_date)) if issue_date else ""
    return default_issuer(date) if date else None


def _person(values: dict, prefix: str) -> Person | None:
    name = values.get(f"{prefix}_HoTen")
    identity = values.get(f"{prefix}_SoDinhDanh")
    if not name and not identity:
        return None
    issue_date = normalize_date(values.get(f"{prefix}_NgayCap"))
    return Person(
        name=name,
        identity=identity,
        birthday=normalize_date(values.get(f"{prefix}_NgaySinh")),
        issue_date=issue_date,
        issuer=_issuer(values.get(f"{prefix}_NoiCap"), issue_date),
        residence=values.get(f"{prefix}_NoiCuTru"),
        phone=_phone(values.get(f"{prefix}_DienThoai")),
        email=_text(values.get(f"{prefix}_Email")),
    )


def _auth_person(values: dict, prefix: str) -> Person | None:
    name = values.get(f"{prefix}_HoTen")
    identity = values.get(f"{prefix}_SoDinhDanh")
    if not name and not identity:
        return None
    issue_date = normalize_date(values.get(f"{prefix}_NgayCap"))
    return Person(
        name=name,
        identity=identity,
        issue_date=issue_date,
        issuer=_issuer(values.get(f"{prefix}_NoiCap"), issue_date),
    )


def _form_context(options: dict | None) -> dict:
    ctx = (options or {}).get("formContext") or {}
    return {
        "applicant_name": ctx.get("applicantFullname") or ctx.get("fullname") or "",
        "applicant_identity": ctx.get("applicantIdentityNumber") or ctx.get("identityNumber") or "",
    }


def _pick_requester(values: dict, options: dict | None) -> Person | None:
    context = _form_context(options)
    candidates = [
        _person(values, "Applicant"),
        _auth_person(values, "UyQuyen_BenDuocUyQuyen"),
        _auth_person(values, "UyQuyen_BenUyQuyen"),
        Person(name=values.get("DonCapLai_NguoiKy")) if values.get("DonCapLai_NguoiKy") else None,
        Person(name=values.get("ThuyetMinh_DaiDienCoSo")) if values.get("ThuyetMinh_DaiDienCoSo") else None,
        Person(name=values.get("DangKy_NguoiDaiDien")) if values.get("DangKy_NguoiDaiDien") else None,
    ]
    people = [p for p in candidates if p]
    matches = [
        p for p in people
        if _same_person(p.identity, p.name, context.get("applicant_identity"), context.get("applicant_name"))
    ]
    if len(matches) == 1:
        return matches[0]
    if not context.get("applicant_identity") and not context.get("applicant_name"):
        return people[0] if people else None
    return None


def _pick(*values):
    for value in values:
        if value not in (None, "", {}, []):
            return value
    return None


def _clean_gcn_number(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _looks_organization(value: Any) -> bool:
    folded = _fold(value)
    markers = (
        "cong ty",
        "chi nhanh",
        "dia diem kinh doanh",
        "ho kinh doanh",
        "doanh nghiep",
        "co so",
        "winmart",
    )
    return any(marker in folded for marker in markers)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
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

    requester = _pick_requester(values, options)
    if requester:
        add("data[fullname]", requester.name)
        add("data[identityNumber]", requester.identity)
        add("data[identityDate]", requester.issue_date)
        add("data[birthday]", requester.birthday)
        add("data[phoneNumber]", requester.phone)
        add("data[email]", requester.email)
        area = _area(requester.residence)
        if area:
            add("data[province]", _area_label(area.get("tinh")))
            add("data[district]", _area_label(area.get("xa")))
            add("data[address]", area.get("diaChi"))

    owner_name = _pick(values.get("DonCapLai_TenCoSo"), values.get("CoSo_TenCoSo"), values.get("DangKy_TenDonVi"), values.get("GCNCu_TenCoSo"))
    owner_tax = _pick(values.get("CoSo_MaSoThue"), values.get("DangKy_MaSo"))
    owner_phone = _phone(_pick(values.get("CoSo_DienThoai"), values.get("ThuyetMinh_DienThoai"), values.get("GCNCu_DienThoai"), values.get("DangKy_DienThoai")))
    owner_address = _text(_pick(values.get("DonCapLai_DiaChiCoSo"), values.get("CoSo_DiaChi"), values.get("DangKy_DiaChi"), values.get("ThuyetMinh_DiaChiCoSo"), values.get("GCNCu_DiaChiCoSo")))
    owner_identity = None
    if not owner_tax and owner_name and not _looks_organization(owner_name):
        owner_identity = _pick(values.get("GCNCu_SoDinhDanhChuCoSo"), values.get("UyQuyen_BenUyQuyen_SoDinhDanh"))

    add("data[isOwnerDossier]", False)
    add("data[ownerFullname]", owner_name)
    add("data[ownerIdentityNumber]", owner_identity)
    add("data[ownertaxCode]", owner_tax)
    add("data[ownerPhoneNumber]", owner_phone)
    add("data[ownerAddress]", owner_address)

    reissue_content = _pick(
        values.get("DonCapLai_NoiDungYeuCau"),
        "Đề nghị cấp lại Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm" if values.get("DonCapLai_TenCoSo") else None,
    )
    add("data[noidungyeucaugiaiquyet]", reissue_content)
    add("data[tinhThanhPhoNopDon]", _area_label(values.get("DonCapLai_DiaDanh")))
    # "Ngày nộp đơn" = ngày NỘP LÊN CỔNG (submission), KHÔNG phải ngày ghi trên tờ đơn giấy (thường quá
    # khứ → date-picker chặn, để trống báo bắt buộc). Luôn điền NGÀY HÔM NAY (ngày server, giờ VN).
    add("data[ngayNopDon]", date.today().strftime("%d/%m/%Y"))
    add("data[kinhGui]", _text(values.get("DonCapLai_KinhGui")))
    add("data[TenCoSoSanXuatKinhDoanh]", owner_name)
    add("data[GCNCuSo]", _clean_gcn_number(_pick(values.get("DonCapLai_GCNCuSo"), values.get("GCNCu_SoCap"))))
    add("data[NgayCapGCNCu]", normalize_date(_pick(values.get("DonCapLai_NgayCapGCNCu"), values.get("GCNCu_NgayCap"))))
    add("data[LyDoCapLaiGCN]", _text(values.get("DonCapLai_LyDoCapLai")))
    add("data[KyTen]", _pick(values.get("DonCapLai_NguoiKy"), values.get("ThuyetMinh_DaiDienCoSo"), values.get("DangKy_NguoiDaiDien")))

    if not values.get("DonCapLai_TenCoSo") and not values.get("DonCapLai_GCNCuSo"):
        warnings.append("Không đọc được Đơn đề nghị cấp lại hoặc thiếu các trường chính của đơn.")
    return out, warnings
