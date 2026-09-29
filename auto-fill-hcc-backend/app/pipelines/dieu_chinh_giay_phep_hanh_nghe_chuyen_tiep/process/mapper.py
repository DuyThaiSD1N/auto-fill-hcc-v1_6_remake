"""Map compact source facts → Form.io data[...] fields cho thủ tục "Điều chỉnh giấy phép hành nghề trong
giai đoạn chuyển tiếp...".

Quyết định TỰ NỘP / NỘP THAY bằng formContext (tên + CCCD tài khoản cổng tự đổ vào Phần I) SO với người
hành nghề:
  - TỰ NỘP: Phần 1 = người hành nghề (trừ ô cổng khoá sẵn). TÍCH data[isOwnerDossierCheck]=True — cổng
    này để ô TRỐNG mặc định; engine tick SAU CÙNG nên cổng nhân bản Phần 1 đã điền sang Phần 2.
  - NỘP THAY: cổng chỉ đổ sẵn họ tên + số định danh vào Phần 1 → điền phần còn lại từ NguoiNop_* (CCCD
    người nộp). data[isOwnerDossierCheck]=False rồi điền owner_* = người hành nghề.
data[ghiChu] (cả hai trường hợp) = trường hợp đề nghị + phạm vi hành nghề trên Đơn Mẫu 08.

Mỗi data[key] xuất hiện 1× trong DOM → KHÔNG dùng occurrence.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.dieu_chinh_giay_phep_hanh_nghe_chuyen_tiep.process.schema import UI_COMP_BY_NAME

_CITY_MARKERS = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
_ADMIN_PREFIX = re.compile(
    r"^(tỉnh|thành phố|t\.\s*p\.?|tp\.?|xã|phường|thị trấn|tt\.?|đặc khu)\s+",
    re.IGNORECASE,
)


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


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = _ADMIN_PREFIX.match(text)
    bare = text[match.end():].strip() if match else text
    if not bare:
        return None
    prefix = _fold(match.group(1)) if match else ""
    is_city = prefix.startswith(("thanh pho", "t.", "tp")) or _fold(bare) in _CITY_MARKERS
    return f"{'Thành phố' if is_city else 'Tỉnh'} {bare}"


def _commune_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = _ADMIN_PREFIX.match(text)
    if not match:
        return text
    # "phường An Biên" (viết tay) → "Phường An Biên" cho khớp danh mục cổng.
    head = match.group(1)
    return f"{head[:1].upper()}{head[1:].lower()} {text[match.end():].strip()}"


def _parse_area_text(value: Any) -> dict | None:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip(" .")
    if not text:
        return None
    parts = [p.strip(" .") for p in re.split(r"\s*(?:,|;|\s+-\s+)\s*", text) if p.strip(" .")]
    if not parts:
        return None
    out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
    if len(parts) >= 3:
        out["tinh"], out["xa"], out["diaChi"] = parts[-1], parts[-2], ", ".join(parts[:-2])
    elif len(parts) == 2:
        out["tinh"], out["xa"] = parts[-1], parts[0]
    else:
        out["diaChi"] = parts[0]
    return out


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
    return out if any(v for k, v in out.items() if k != "quocGia") else None


def _address_detail(area: dict) -> str | None:
    """Ô "Địa chỉ chi tiết" là (*) nhưng Đơn Mẫu 08 hay chỉ ghi phường + tỉnh → ghi lại phường, tỉnh."""
    detail = _text(area.get("diaChi"))
    if detail:
        return detail
    parts = [_commune_label(area.get("xa")), _province_label(area.get("tinh"))]
    return ", ".join(p for p in parts if p) or None


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


def _email(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"\s+", "", text).lower()
    return text if re.fullmatch(r"[^@]+@[^@]+\.[a-z]{2,}", text) else None


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


def _ghi_chu(values: dict) -> str | None:
    truong_hop = _text(values.get("HoSo_TruongHopDeNghi"))
    pham_vi = _text(values.get("HoSo_PhamViHanhNghe"))
    parts = [truong_hop, f"Phạm vi hành nghề đề nghị cấp: {pham_vi}" if pham_vi else None]
    return "; ".join(p for p in parts if p) or None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    # Ô Phần I cổng đã đổ sẵn từ tài khoản VNeID (bị khoá) → KHÔNG điền đè bằng giá trị OCR.
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
        add(address_name, _address_detail(area))

    # --- NGƯỜI HÀNH NGHỀ = chủ hồ sơ ---
    name = _text(values.get("NguoiHanhNghe_HoTen"))
    identity = _identity(values.get("NguoiHanhNghe_SoDinhDanh"))
    birthday = _date(values.get("NguoiHanhNghe_NgaySinh"))
    gender = _text(values.get("NguoiHanhNghe_GioiTinh"))
    id_date = _date(values.get("NguoiHanhNghe_NgayCap"))
    issuer = _issuer(values.get("NguoiHanhNghe_NoiCap"))
    residence = _area(values.get("NguoiHanhNghe_ThuongTru"))
    phone = _phone(values.get("NguoiHanhNghe_DienThoai"))
    email = _email(values.get("NguoiHanhNghe_Email"))

    if not name:
        warnings.append("Thiếu họ tên người hành nghề từ CCCD/Đơn Mẫu 08.")
    if identity and len(identity) != 12:
        warnings.append(
            f"Số định danh người hành nghề '{identity}' không đủ 12 chữ số — có thể là CMND cũ trên chứng chỉ "
            "hành nghề, cán bộ kiểm tra lại."
        )

    # --- TỰ NỘP / NỘP THAY: ưu tiên so SỐ ĐỊNH DANH, không có thì so TÊN đã fold. ---
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("ownerFullname") or ctx.get("fullname"))
    ctx_identity = _identity(
        ctx.get("applicantIdentityNumber") or ctx.get("ownerIdentityNumber") or ctx.get("identityNumber")
    )
    sub_name = _text(values.get("NguoiNop_HoTen")) or ctx_name
    sub_id = _identity(values.get("NguoiNop_SoDinhDanh")) or ctx_identity

    is_nop_thay = False
    if sub_id and identity:
        is_nop_thay = sub_id != identity
    elif sub_name and name:
        is_nop_thay = _fold(sub_name) != _fold(name)

    add("data[chonDoiTuong]", "Cá nhân")

    if not is_nop_thay:
        add("data[fullname]", name)
        add("data[birthday]", birthday)
        add("data[gender]", gender)
        add("data[identityNumber]", identity)
        add("data[identityDate]", id_date)
        add("data[idIssuePlace]", issuer)
        add_area("data[province]", "data[district]", "data[address]", residence)
        add("data[phoneNumber]", phone)
        add("data[email]", email)
        add("data[isOwnerDossierCheck]", True)
    else:
        # Cổng chỉ đổ sẵn họ tên + số định danh tài khoản (bị khoá, add() bỏ qua) — ngày sinh, giới tính,
        # ngày/nơi cấp, địa chỉ của NGƯỜI NỘP vẫn trống → điền từ CCCD người nộp nếu hồ sơ có.
        add("data[fullname]", _text(values.get("NguoiNop_HoTen")))
        add("data[birthday]", _date(values.get("NguoiNop_NgaySinh")))
        add("data[gender]", _text(values.get("NguoiNop_GioiTinh")))
        add("data[identityNumber]", _identity(values.get("NguoiNop_SoDinhDanh")))
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
        add("data[idIssuePlace]", _issuer(values.get("NguoiNop_NoiCap")))
        add_area("data[province]", "data[district]", "data[address]", _area(values.get("NguoiNop_ThuongTru")))
        add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")))
        add("data[email]", _email(values.get("NguoiNop_Email")))

        add("data[isOwnerDossierCheck]", False)
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

    add("data[ghiChu]", _ghi_chu(values))
    return out, warnings
