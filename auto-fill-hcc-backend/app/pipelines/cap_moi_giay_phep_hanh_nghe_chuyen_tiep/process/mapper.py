"""Map compact source facts → Form.io data[...] fields cho thủ tục "Cấp mới giấy phép hành nghề trong
giai đoạn chuyển tiếp...".

HAI vai (thường trùng):
  NGƯỜI HÀNH NGHỀ (NguoiHanhNghe_*) = CHỦ HỒ SƠ = người chính (giấy phép cấp cho người này).
  NGƯỜI NỘP (NguoiNop_* / formContext) = tài khoản đứng nộp trên cổng.

Quyết định TỰ NỘP / NỘP THAY bằng formContext (tên + CCCD tài khoản cổng tự đổ vào Phần I) SO với người
hành nghề:
  - TỰ NỘP (người nộp = người hành nghề):
      Phần 1 (data[fullname...]) = người hành nghề. GIỮ tích data[isOwnerDossierCheck] mặc định (KHÔNG
      emit) → cổng TỰ nhân bản Phần 1 sang Phần 2. KHÔNG điền owner_*.
  - NỘP THAY (người nộp ≠ người hành nghề):
      Phần 1 = NGƯỜI NỘP: cổng đã đổ sẵn từ VNeID → KHÔNG điền gì vào Phần 1.
      BỎ TÍCH data[isOwnerDossierCheck]=False để mở Phần 2 → điền owner_* = người hành nghề (tường minh).

Mỗi data[key] xuất hiện 1× trong DOM → KHÔNG dùng occurrence.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_moi_giay_phep_hanh_nghe_chuyen_tiep.process.schema import UI_COMP_BY_NAME


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

    # Ô Phần I cổng đã đổ sẵn từ tài khoản VNeID (bị khoá, nền xám) → KHÔNG điền đè. Phần I luôn là
    # tài khoản đăng nhập nên giá trị cổng là chuẩn, giá trị OCR (vd "HÀNG" thay "HẰNG") chỉ làm sai.
    ctx = (options or {}).get("formContext") or {}
    portal_prefilled = {
        key
        for key, ctx_key in (
            ("data[fullname]", "applicantFullname"),
            ("data[identityNumber]", "applicantIdentityNumber"),
        )
        if _text(ctx.get(ctx_key))
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

    # --- NGƯỜI HÀNH NGHỀ = chủ hồ sơ (người chính) ---
    name = _text(values.get("NguoiHanhNghe_HoTen"))
    identity = _identity(values.get("NguoiHanhNghe_SoDinhDanh"))
    birthday = _date(values.get("NguoiHanhNghe_NgaySinh"))
    gender = _text(values.get("NguoiHanhNghe_GioiTinh"))
    id_date = _date(values.get("NguoiHanhNghe_NgayCap"))
    issuer = _issuer(values.get("NguoiHanhNghe_NoiCap"))
    residence = _area(values.get("NguoiHanhNghe_ThuongTru"))
    phone = _phone(values.get("NguoiHanhNghe_DienThoai"))
    email = _text(values.get("NguoiHanhNghe_Email"))

    if not name:
        warnings.append("Thiếu họ tên người hành nghề từ CCCD/Mẫu 08/Mẫu 09.")

    # --- Quyết định TỰ NỘP / NỘP THAY: formContext (tên+CCCD tài khoản) SO với người hành nghề. Ưu tiên
    # so theo SỐ ĐỊNH DANH; không có thì so theo TÊN đã fold. ---
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
        # === TỰ NỘP: Phần I = người hành nghề, GIỮ tích (cổng tự nhân bản Phần II). KHÔNG emit owner_*,
        # KHÔNG đụng data[isOwnerDossierCheck]. ===
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

    # === NỘP THAY: Phần I (người nộp) cổng đã đổ sẵn từ tài khoản VNeID → KHÔNG điền. BỎ TÍCH để mở
    # Phần II → điền owner_* = người hành nghề. ===
    add("data[isOwnerDossierCheck]", False)

    # Phần II = NGƯỜI HÀNH NGHỀ (chủ hồ sơ).
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
