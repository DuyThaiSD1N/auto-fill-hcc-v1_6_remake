"""Map compact source facts → Form.io data[...] fields cho [Lâm Đồng] đính chính GCN.

Điền 4 khối: Người nộp (Phần I) · Thửa đất (Phần II) · Chủ hồ sơ (Phần III) · Chi tiết GCN
(Phần IV). Không cần `occurrence` — mọi tên field trên form là DUY NHẤT (province/province1/
province2, district/district1/village2 khác nhau).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.dinh_chinh_sai_sot_lam_dong.process.schema import UI_COMP_BY_NAME
from app.pipelines._shared.area_remap import remap_area

# Ô người mà extension CHỊU TRÁCH NHIỆM điền từ CCCD/đơn. Không có dữ liệu → phát "dom-expect" để FE
# TÔ ĐỎ (không điền), dù form không đánh dấu ô đó bắt buộc.
_EXPECT_APPLICANT = (
    "data[fullname]", "data[birthday]", "data[gender]", "data[identityNumber]",
    "data[identityDate]", "data[identityAgency]", "data[phoneNumber]",
)
_EXPECT_OWNER = (
    "data[ownerFullname]", "data[ownerBirthday]", "data[gender1]", "data[ownerIdentityNumber]",
    "data[ownerIdentityDate]", "data[ownerIdentityAgency]", "data[ownerPhoneNumber]",
)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        return _full_address(value)
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
        r"^(xã|phường|thị trấn|tt\.?|tỉnh|thành phố|tp\.?|huyện|quận|thị xã)\s+",
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
    prefix = "Thành phố" if folded in city_markers else "Tỉnh"
    return f"{prefix} {_strip_admin_prefix(text)}"


def _commune_label(value: Any) -> str | None:
    # Giữ nguyên nhãn phường/xã (đã là tên MỚI theo Đơn); FE khớp option theo text đã fold + chuẩn hóa gạch.
    return _text(value)


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
        return " ".join(value.replace("\n", " ").split()).strip(" :;,-") or None
    if not isinstance(value, dict):
        return None
    direct = _field(value, "fullText", "full", "text", "diaChiDayDu")
    if direct:
        return direct
    parts = [
        _field(value, "diaChi", "chiTiet", "soNha", "thonXom"),
        _field(value, "xa", "phuongXa", "phuong"),
        _field(value, "huyen", "quanHuyen"),
        _field(value, "tinh", "tinhThanh"),
    ]
    return ", ".join(p for p in parts if p) or None


def _parse_area_text(value: str) -> dict | None:
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
    return remap_area(out if any(out.values()) else None)


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
    if not m:
        return None
    return normalize_date(m.group(0))


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or None


def _normalize_serial(prefix: str, number: str) -> str | None:
    prefix = re.sub(r"[^A-Z]", "", (prefix or "").upper())
    number = re.sub(r"\D", "", number or "")
    if not prefix or not number:
        return None
    if prefix.startswith("SO") and len(prefix) > 2:
        prefix = prefix[2:]
    elif prefix.startswith("S") and len(prefix) > 1:
        prefix = prefix[1:]
    if not 1 <= len(prefix) <= 3 or not 5 <= len(number) <= 8:
        return None
    return f"{prefix} {number}"


def _serial(value: Any) -> str | None:
    """Số phát hành GCN: '2 chữ cái + số'. Bỏ đuôi 'số vào sổ' nếu OCR dính vào."""
    text = _text(value)
    if not text:
        return None
    text = re.split(r"\(|số\s+vào\s+sổ|so\s+vao\s+so", text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = " ".join(text.split()).strip(" :;,-")
    match = re.search(r"\b([A-Z]{1,5})\s*[-.]?\s*(\d{5,8})\b", text.upper())
    if match:
        serial = _normalize_serial(match.group(1), match.group(2))
        if serial:
            return serial
    return text or None


def _agency(value: Any) -> str | None:
    """Đơn vị cấp GCN: bỏ 'TM.'/'CHỦ TỊCH', đổi ỦY BAN NHÂN DÂN → UBND."""
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"^TM\.?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bCHỦ\s*TỊCH\b.*$", "", text, flags=re.IGNORECASE).strip(" :;,-")
    text = re.sub(r"ỦY\s*BAN\s*NHÂN\s*DÂN", "UBND", text, flags=re.IGNORECASE)
    return text or None


def _cccd_issuer(value: Any, ngay_cap: Any) -> str | None:
    text = _text(value)
    if text:
        return normalize_issuer(text)
    d = _date(ngay_cap)
    return default_issuer(d) if d else None


def _date_ymd(value: Any) -> str | None:
    """Định dạng yyyy/mm/dd — RIÊNG các ô ngày Phần IV (Ngày cấp/hiệu lực/hết hạn của GCN) dùng
    flatpickr format yyyy/mm/dd, KHÁC các ô người (dd/MM/yyyy). FE type thẳng chuỗi vào flatpickr
    nên phải gửi đúng thứ tự, không thì bị parse lệch (vd '23/05/2005' → '2306/08/05')."""
    d = _date(value)
    if not d:
        return None
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", d)
    if not m:
        return None
    dd, mm, yyyy = m.groups()
    return f"{yyyy}/{mm}/{dd}"


def _expiration(value: Any) -> str | None:
    """Thời hạn 'Lâu dài' → không có ngày hết hạn (trống). Ngược lại parse ngày về yyyy/mm/dd."""
    text = _text(value)
    if not text or "lau dai" in _fold(text):
        return None
    return _date_ymd(text)


def _ghi_chu(values: dict) -> str | None:
    noi_dung = _text(values.get("Don_NoiDungDinhChinh"))
    thua = _text(values.get("ThuaDat_So"))
    to = _text(values.get("ThuaDat_ToBanDo"))
    suffix = ""
    if thua and to:
        suffix = f" (thửa {thua}, tờ bản đồ số {to})"
    elif thua:
        suffix = f" (thửa {thua})"
    if noi_dung:
        return noi_dung + suffix if suffix and suffix.strip(" ()") not in _fold(noi_dung) else noi_dung
    return suffix.strip() or None


def _form_context(options: dict | None) -> dict:
    ctx = (options or {}).get("formContext") or {}
    return {
        "applicant_name": ctx.get("applicantFullname") or ctx.get("fullname") or "",
        "applicant_identity": ctx.get("applicantIdentityNumber") or ctx.get("identityNumber") or "",
    }


def _has_context_anchor(context: dict) -> bool:
    return bool(_identity(context.get("applicant_identity")) or _fold(context.get("applicant_name")))


def _same_person(doc_id: Any, doc_name: Any, ctx_id: Any, ctx_name: Any) -> bool:
    did, cid = _identity(doc_id), _identity(ctx_id)
    if did and cid:
        return did == cid
    dname, cname = _fold(doc_name), _fold(ctx_name)
    return bool(dname and cname and dname == cname)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()
    context = _form_context(options)

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    def expect(names: tuple[str, ...]) -> None:
        # Ô extension chịu trách nhiệm nhưng thiếu dữ liệu → FE tô đỏ (không điền).
        for name in names:
            if name not in seen:
                out.append({"name": name, "comp": "dom-expect", "value": ""})
                seen.add(name)

    # HAI NGƯỜI khi có ủy quyền:
    #  - Chủ hồ sơ (Phần III) = chủ Giấy chứng nhận (Nguoi_*) — người có sai sót.
    #  - Người nộp (Phần I) = người đại diện/được ủy quyền (DaiDien_*) nếu có; không thì trùng chủ hồ sơ.
    has_uy_quyen = bool(values.get("DaiDien_HoTen") or values.get("DaiDien_SoDinhDanh"))

    owner_name = _text(values.get("Nguoi_HoTen"))
    owner_identity = _identity(values.get("Nguoi_SoDinhDanh"))
    owner_birthday = _date(values.get("Nguoi_NgaySinh"))
    owner_gender = _text(values.get("Nguoi_GioiTinh"))
    owner_phone = _phone(values.get("Nguoi_DienThoai"))
    owner_email = _text(values.get("Nguoi_Email"))
    owner_id_date = _date(values.get("Nguoi_NgayCapCccd"))
    owner_id_agency = _cccd_issuer(values.get("Nguoi_NoiCapCccd"), values.get("Nguoi_NgayCapCccd"))
    owner_residence = _area(values.get("Nguoi_ThuongTru"))

    if has_uy_quyen:
        sub_name = _text(values.get("DaiDien_HoTen"))
        sub_identity = _identity(values.get("DaiDien_SoDinhDanh"))
        sub_birthday = _date(values.get("DaiDien_NgaySinh"))
        sub_gender = _text(values.get("DaiDien_GioiTinh"))
        sub_phone = _phone(_pick(values.get("DaiDien_DienThoai"), values.get("Nguoi_DienThoai")))
        sub_email = _text(_pick(values.get("DaiDien_Email"), values.get("Nguoi_Email")))
        sub_id_date = _date(values.get("DaiDien_NgayCapCccd"))
        sub_id_agency = _cccd_issuer(values.get("DaiDien_NoiCapCccd"), values.get("DaiDien_NgayCapCccd"))
        sub_residence = _area(_pick(values.get("DaiDien_ThuongTru"), values.get("Nguoi_ThuongTru")))
    else:
        sub_name, sub_identity, sub_birthday, sub_gender = owner_name, owner_identity, owner_birthday, owner_gender
        sub_phone, sub_email, sub_id_date, sub_id_agency = owner_phone, owner_email, owner_id_date, owner_id_agency
        sub_residence = owner_residence

    # Phần I chỉ ghi đè khi khớp tài khoản đang đăng nhập (tránh đè nhầm thông tin người khác).
    # Không có anchor (tài khoản trống) → cứ điền theo giấy tờ ("sửa lại theo người nộp thực tế").
    can_fill_applicant = (
        not _has_context_anchor(context)
        or _same_person(sub_identity, sub_name, context.get("applicant_identity"), context.get("applicant_name"))
    )

    # ---- Phần I: Thông tin người nộp ----
    if can_fill_applicant:
        add("data[fullname]", sub_name)
        add("data[birthday]", sub_birthday)
        add("data[gender]", sub_gender)
        add("data[phoneNumber]", sub_phone)
        add("data[email]", sub_email)
        add("data[identityNumber]", sub_identity)
        add("data[identityDate]", sub_id_date)
        add("data[identityAgency]", sub_id_agency)
        add("data[nation]", "Việt Nam" if sub_name or sub_identity else None)
        if sub_residence:
            add("data[province]", _province_label(sub_residence.get("tinh")))
            add("data[district]", _commune_label(sub_residence.get("xa")))
            add("data[address]", _text(sub_residence.get("diaChi")))
        expect(_EXPECT_APPLICANT)

    add("data[ghiChu]", _ghi_chu(values))

    # ---- Phần II: Thông tin thửa đất ----
    land = _area(values.get("ThuaDat_DiaChi"))
    if land:
        add("data[province2]", _province_label(land.get("tinh")))
        add("data[village2]", _commune_label(land.get("xa")))

    # ---- Phần III: Thông tin chủ hồ sơ (chủ GCN) ----
    # Tự nộp (người nộp = chủ hồ sơ) VÀ đã điền được Phần I → BẤM nút "Người nộp là chủ hồ sơ"
    # (data[BUTTON3]) để form tự copy toàn bộ Phần I xuống Phần III, thay vì fill tay. Đúng UX form,
    # tránh lệch cascade. Có ủy quyền (2 người khác nhau) hoặc không đè được Phần I → fill trực tiếp.
    if not has_uy_quyen and can_fill_applicant:
        add("data[BUTTON3]", True)
    else:
        add("data[ownerFullname]", owner_name)
        add("data[ownerBirthday]", owner_birthday)
        add("data[gender1]", owner_gender)
        add("data[ownerPhoneNumber]", owner_phone)
        add("data[ownerEmail]", owner_email)
        add("data[ownerIdentityNumber]", owner_identity)
        add("data[ownerIdentityDate]", owner_id_date)
        add("data[ownerIdentityAgency]", owner_id_agency)
        add("data[nation1]", "Việt Nam" if owner_name or owner_identity else None)
        if owner_residence:
            add("data[province1]", _province_label(owner_residence.get("tinh")))
            add("data[district1]", _commune_label(owner_residence.get("xa")))
            add("data[ownerAddress]", _text(owner_residence.get("diaChi")))
        expect(_EXPECT_OWNER)

    # ---- Phần IV: Chi tiết Giấy chứng nhận cần đính chính ----
    # Ngày cấp/hiệu lực/hết hạn dùng flatpickr yyyy/mm/dd (KHÁC các ô người dd/MM/yyyy) → _date_ymd.
    gcn_date = _date_ymd(values.get("Gcn_NgayCap"))
    add("data[licenseCode]", _serial(values.get("Gcn_SoPhatHanh")))
    add("data[licenseDate]", gcn_date)
    add("data[licensingPlace]", _agency(values.get("Gcn_DonViCap")))
    add("data[licensingAgency]", _text(values.get("Gcn_NoiCap")))
    # Ngày hiệu lực: GCN không có ô riêng → dùng ngày cấp GCN. Ngày hết hạn: 'Lâu dài' → trống.
    add("data[effectiveDate]", gcn_date)
    add("data[expirationDate]", _expiration(values.get("Gcn_ThoiHan")))

    if not owner_name or not owner_identity:
        warnings.append("Thiếu họ tên/số định danh chủ hồ sơ từ CCCD hoặc Đơn.")
    if not values.get("Gcn_SoPhatHanh") and not values.get("Gcn_NgayCap"):
        warnings.append("Chưa đọc được số phát hành/ngày cấp Giấy chứng nhận cần đính chính.")
    return out, warnings
