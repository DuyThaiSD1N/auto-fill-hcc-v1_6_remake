"""Map compact source facts → Form.io data[...] fields cho thủ tục "Cấp Chứng chỉ hành nghề dược...".

HAI vai (thường trùng):
  NGƯỜI ĐỀ NGHỊ (NguoiDeNghi_*) = CHỦ HỒ SƠ = dược sĩ (chứng chỉ cấp cho người này).
  NGƯỜI NỘP (NguoiNop_* / formContext) = tài khoản đứng nộp trên cổng.

Quyết định TỰ NỘP / NỘP THAY bằng formContext (tên + CCCD tài khoản cổng tự đổ vào Phần I) SO với người
đề nghị:
  - TỰ NỘP: Phần 1 = người đề nghị. GIỮ tích data[isOwnerDossierCheck] mặc định (KHÔNG emit) → cổng TỰ
    nhân bản Phần 1 sang Phần 2. KHÔNG điền owner_*.
  - NỘP THAY: Phần 1 = NGƯỜI NỘP (chỉ điền cái CÓ). BỎ TÍCH data[isOwnerDossierCheck]=False → điền owner_*
    = người đề nghị (tường minh).

Mỗi data[key] xuất hiện 1× trong DOM → KHÔNG dùng occurrence.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_chung_chi_hanh_nghe_duoc.process.schema import UI_COMP_BY_NAME


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

    def add_area(province_name, district_name, address_name, area) -> None:
        if not area:
            return
        add(province_name, _province_label(area.get("tinh")))
        add(district_name, _commune_label(area.get("xa")))
        add(address_name, _text(area.get("diaChi")))

    # --- NGƯỜI ĐỀ NGHỊ = chủ hồ sơ (người chính) ---
    name = _text(values.get("NguoiDeNghi_HoTen"))
    identity = _identity(values.get("NguoiDeNghi_SoDinhDanh"))
    birthday = _date(values.get("NguoiDeNghi_NgaySinh"))
    gender = _text(values.get("NguoiDeNghi_GioiTinh"))
    id_date = _date(values.get("NguoiDeNghi_NgayCap"))
    issuer = _issuer(values.get("NguoiDeNghi_NoiCap"))
    residence = _area(values.get("NguoiDeNghi_ThuongTru"))
    phone = _phone(values.get("NguoiDeNghi_DienThoai"))
    email = _text(values.get("NguoiDeNghi_Email"))

    if not name:
        warnings.append("Thiếu họ tên người đề nghị cấp CCHN dược từ CCCD/Đơn Mẫu 02/Phiếu LLTP.")

    # --- Quyết định TỰ NỘP / NỘP THAY: formContext (tên+CCCD tài khoản) SO với người đề nghị. Ưu tiên so
    # theo SỐ ĐỊNH DANH; không có thì so theo TÊN đã fold. ---
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("ownerFullname") or ctx.get("fullname"))
    ctx_identity = _identity(
        ctx.get("applicantIdentityNumber") or ctx.get("ownerIdentityNumber") or ctx.get("identityNumber")
    )
    nop_ext_name = _text(values.get("NguoiNop_HoTen"))
    nop_ext_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    sub_name = nop_ext_name or ctx_name
    sub_id = nop_ext_id or ctx_identity

    is_nop_thay = False
    if sub_id and identity:
        is_nop_thay = sub_id != identity
    elif sub_name and name:
        is_nop_thay = _fold(sub_name) != _fold(name)

    add("data[chonDoiTuong]", "Cá nhân")

    if not is_nop_thay:
        # === TỰ NỘP: Phần I = người đề nghị, GIỮ tích (cổng tự nhân bản Phần II). ===
        add("data[fullname]", name)
        add("data[birthday]", birthday)
        add("data[gender]", gender)
        add("data[identityNumber]", identity)
        add("data[identityDate]", id_date)
        add("data[idIssuePlace]", issuer)
        add_area("data[province]", "data[district]", "data[address]", residence)
        add("data[phoneNumber]", phone)
        add("data[email]", email)
        return out, warnings

    # === NỘP THAY: Phần I = NGƯỜI NỘP (chỉ điền cái CÓ; thiếu để trống). BỎ TÍCH để mở Phần II → điền
    # owner_* = người đề nghị. ===
    sub_full = nop_ext_name or ctx_name
    sub_identity = nop_ext_id or ctx_identity
    sub_birthday = _date(values.get("NguoiNop_NgaySinh"))
    sub_gender = _text(values.get("NguoiNop_GioiTinh"))
    sub_id_date = _date(values.get("NguoiNop_NgayCap"))
    sub_issuer = _issuer(values.get("NguoiNop_NoiCap"))
    sub_residence = _area(values.get("NguoiNop_ThuongTru"))
    sub_phone = _phone(values.get("NguoiNop_DienThoai"))
    sub_email = _text(values.get("NguoiNop_Email"))

    add("data[fullname]", sub_full)
    add("data[birthday]", sub_birthday)
    add("data[gender]", sub_gender)
    add("data[identityNumber]", sub_identity)
    add("data[identityDate]", sub_id_date)
    add("data[idIssuePlace]", sub_issuer)
    add_area("data[province]", "data[district]", "data[address]", sub_residence)
    add("data[phoneNumber]", sub_phone)
    add("data[email]", sub_email)

    # Mở khoá Phần II.
    add("data[isOwnerDossierCheck]", False)

    # Phần II = NGƯỜI ĐỀ NGHỊ (chủ hồ sơ).
    add("data[ownerFullname]", name)
    add("data[ownerBirthday]", birthday)
    add("data[ownerGender]", gender)
    add("data[ownerIdentityNumber]", identity)
    add("data[ownerIdentityDate]", id_date)
    add("data[ownerIdIssuePlace]", issuer)
    add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", residence)
    add("data[ownerPhoneNumber]", phone)
    add("data[ownerEmail]", email)
    add("data[ownerNation]", "Việt Nam" if name or identity else None)

    return out, warnings
