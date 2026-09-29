"""Map compact source facts → Form.io data[...] fields cho thủ tục "Cấp lại giấy phép hành nghề đối với
trường hợp được cấp trước ngày 01/01/2024...".

HAI vai (thường trùng):
  NGƯỜI HÀNH NGHỀ (NguoiHanhNghe_*) = CHỦ HỒ SƠ = người đề nghị cấp lại.
  NGƯỜI NỘP (NguoiNop_* / formContext) = tài khoản đứng nộp trên cổng.

Hai chế độ người nộp:
  · THEO TÀI KHOẢN (FE gửi họ tên/CCCD tài khoản trong formContext): người hành nghề khớp tài khoản (CCCD,
    hoặc họ tên bỏ dấu) → TỰ NỘP; không khớp → NỘP THAY.
  · NGƯỜI NỘP = CHỦ HỒ SƠ (submitterMode="owner_as_submitter", hoặc FE không gửi mốc — extension đời
    cũ): luôn TỰ NỘP.
TỰ NỘP: Phần I = người hành nghề, tích data[isOwnerDossierCheck] → cổng tự nhân bản sang Phần II.
NỘP THAY: Phần I = người nộp (họ tên + CCCD cổng đã đổ từ tài khoản; nhân thân khác lấy từ CCCD người nộp
nếu hồ sơ có), BỎ TÍCH rồi điền Phần II owner_* = người hành nghề.
Ô Phần I cổng đổ sẵn từ tài khoản (họ tên, CCCD) không bao giờ bị ghi đè.

Mỗi data[key] xuất hiện 1× trong DOM → KHÔNG dùng occurrence.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_lai_giay_phep_hanh_nghe_truoc_2024.process.schema import UI_COMP_BY_NAME


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


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
        return ", ".join(str(p).strip() for p in parts if str(p or "").strip()) or None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


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
    parts = [p.strip(" .") for p in re.split(r"\s*(?:,|;|\s+-\s+)\s*", text) if p.strip(" .")]
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
        return _parse_area_text(value)
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    return out if any(out.values()) else None


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
    if 10 <= len(digits) <= 11 and digits.startswith("0"):
        return digits
    return None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text)
    if m:
        return normalize_date(m.group(0).replace("-", "/"))
    return normalize_date(text)


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


def _account_anchor(options: dict | None) -> dict | None:
    """Mốc tài khoản cho chế độ THEO TÀI KHOẢN; None → chế độ người nộp = chủ hồ sơ.

    FE đời cũ không gửi formContext → mốc rỗng → coi là tự nộp thay vì đoán người nộp.
    """
    options = options or {}
    if str(options.get("submitterMode") or "") == "owner_as_submitter":
        return None
    context = options.get("formContext") or {}
    name = _text(context.get("applicantFullname"))
    identity = _identity(context.get("applicantIdentityNumber"))
    if not name and not identity:
        return None
    return {"name": name, "identity": identity}


def _matches_account(person: dict, anchor: dict) -> bool:
    # Có CCCD cả hai phía thì CCCD quyết: hai người trùng họ tên bỏ dấu chỉ tách được bằng CCCD.
    if anchor["identity"] and person.get("identity"):
        return person["identity"] == anchor["identity"]
    return bool(anchor["name"] and person.get("name") and _fold(person["name"]) == _fold(anchor["name"]))


def _person(values: dict, prefix: str) -> dict:
    return {
        "name": _text(values.get(f"{prefix}HoTen")),
        "identity": _identity(values.get(f"{prefix}SoDinhDanh")),
        "birthday": _date(values.get(f"{prefix}NgaySinh")),
        "gender": _text(values.get(f"{prefix}GioiTinh")),
        "id_date": _date(values.get(f"{prefix}NgayCap")),
        "issuer": _issuer(values.get(f"{prefix}NoiCap")),
        "residence": remap_area(_area(values.get(f"{prefix}ThuongTru"))),
        "phone": _phone(values.get(f"{prefix}DienThoai")),
        "email": _text(values.get(f"{prefix}Email")),
    }


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()
    anchor = _account_anchor(options)

    # Theo tài khoản: ô Phần I cổng đã đổ sẵn từ tài khoản VNeID (bị khoá) là đúng người nộp → KHÔNG điền
    # đè; giá trị OCR chỉ làm sai dấu. Theo tờ khai (anchor None) người nộp là người trong hồ sơ, KHÁC tài
    # khoản → phải ghi đè họ tên + CCCD, không thì khối thành nửa tài khoản nửa người trong hồ sơ.
    ctx = (options or {}).get("formContext") or {}
    portal_prefilled = {
        key
        for key, ctx_key in (
            ("data[fullname]", "applicantFullname"),
            ("data[identityNumber]", "applicantIdentityNumber"),
        )
        if anchor is not None and _text(ctx.get(ctx_key))
    }

    def add(name: str, value) -> None:
        if name in seen or name in portal_prefilled or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    def add_area(province_name, district_name, address_name, area) -> None:
        if not area:
            return
        add(province_name, _province_label(area.get("tinh")))
        add(district_name, _commune_label(area.get("xa")))
        add(address_name, _text(area.get("diaChi")))

    def add_part_one(person: dict) -> None:
        add("data[fullname]", person.get("name"))
        add("data[birthday]", person.get("birthday"))
        add("data[gender]", person.get("gender"))
        add("data[identityNumber]", person.get("identity"))
        add("data[identityDate]", person.get("id_date"))
        add("data[idIssuePlace]", person.get("issuer"))
        add_area("data[province]", "data[district]", "data[address]", person.get("residence"))
        add("data[phoneNumber]", person.get("phone"))
        add("data[email]", person.get("email"))

    owner = _person(values, "NguoiHanhNghe_")
    if not owner["name"]:
        warnings.append("Thiếu họ tên người hành nghề từ CCCD / Đơn Mẫu 08 / chứng chỉ hành nghề.")

    add("data[chonDoiTuong]", "Cá nhân")

    if anchor is None or _matches_account(owner, anchor):
        # === TỰ NỘP: Phần I = người hành nghề, tích ô → cổng tự nhân bản sang Phần II. ===
        add("data[isOwnerDossierCheck]", True)
        add_part_one(owner)
        return out, warnings

    # === NỘP THAY: Phần I = người nộp. Chỉ dùng nhân thân CCCD người nộp khi khớp tài khoản; không
    # khớp thì Phần I chỉ có họ tên + CCCD cổng đã đổ, không mượn nhân thân người khác. ===
    submitter = _person(values, "NguoiNop_")
    if submitter["name"] or submitter["identity"]:
        if _matches_account(submitter, anchor):
            add_part_one(submitter)
        else:
            warnings.append(
                "CCCD người nộp trong hồ sơ không khớp tài khoản đăng nhập "
                f"({anchor['identity'] or anchor['name']}) — không điền nhân thân người nộp từ giấy tờ."
            )
    else:
        warnings.append(
            "Người nộp khác người hành nghề nhưng hồ sơ không có CCCD người nộp — Phần I chỉ có họ tên và "
            "CCCD do cổng điền sẵn, cán bộ bổ sung các ô còn trống."
        )
    # Bỏ tích để cổng mở Phần II cho người hành nghề.
    add("data[isOwnerDossierCheck]", False)

    # Phần II = NGƯỜI HÀNH NGHỀ (chủ hồ sơ).
    add("data[ownerFullname]", owner["name"])
    add("data[ownerBirthday]", owner["birthday"])
    add("data[ownerGender]", owner["gender"])
    add("data[ownerIdentityNumber]", owner["identity"])
    add("data[ownerIdentityDate]", owner["id_date"])
    add("data[ownerIdIssuePlace]", owner["issuer"])
    add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", owner["residence"])
    add("data[ownerPhoneNumber]", owner["phone"])
    add("data[ownerEmail]", owner["email"])
    add("data[ownerNation]", "Việt Nam" if owner["name"] or owner["identity"] else None)

    return out, warnings
