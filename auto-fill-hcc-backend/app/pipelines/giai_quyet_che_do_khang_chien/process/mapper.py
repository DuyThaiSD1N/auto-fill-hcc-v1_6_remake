"""Map compact source facts → Form.io data[...] fields cho thủ tục giải quyết chế độ HĐKC.

MỘT người (đối tượng HĐKC = chủ hồ sơ) điền vào: Phần II (owner*) + Phần IV Mục 1 (occurrence 1).
BỎ TÍCH data[isOwnerDossierCheck] để mở khoá Phần II. Phần I (người nộp) disabled → không điền;
Phần V Mục 2 (đại diện thân nhân) chỉ khi đối tượng chết → để trống.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.giai_quyet_che_do_khang_chien.process.schema import UI_COMP_BY_NAME


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


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _item_text(item: Any, *keys: str) -> str | None:
    if not isinstance(item, dict):
        return None
    return _text(_pick(*(item.get(k) for k in keys)))


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None]] = set()

    def add(name: str, value, *, occurrence=None) -> None:
        seen_key = (name, occurrence)
        if seen_key in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if occurrence is not None:
            field["occurrence"] = occurrence
        out.append(field)
        seen.add(seen_key)

    def add_area(province_name, district_name, address_name, area, *, occurrence=None) -> None:
        if not area:
            return
        add(province_name, _province_label(area.get("tinh")), occurrence=occurrence)
        add(district_name, _commune_label(area.get("xa")), occurrence=occurrence)
        add(address_name, _text(area.get("diaChi")), occurrence=occurrence)

    name = _text(values.get("Nguoi_HoTen"))
    identity = _identity(values.get("Nguoi_SoDinhDanh"))
    birthday = _date(values.get("Nguoi_NgaySinh"))
    gender = _text(values.get("Nguoi_GioiTinh"))
    id_date = _date(values.get("Nguoi_NgayCap"))
    issuer = _issuer(values.get("Nguoi_NoiCap"))
    residence = _area(values.get("Nguoi_ThuongTru"))
    quequan = _area(values.get("Nguoi_QueQuan"))
    phone = _phone(values.get("Nguoi_DienThoai"))

    if not name or not identity:
        warnings.append("Thiếu họ tên hoặc số định danh đối tượng HĐKC từ CCCD/Bản khai Mẫu 11.")

    # --- Phần I: NGƯỜI NỘP (occurrence 0). Cổng tự đổ họ tên/ngày sinh/CCCD (disabled); ta điền các ô
    # BẮT BUỘC cổng KHÔNG tự đổ: tỉnh/phường/địa chỉ + ngày/nơi cấp + giới tính + email + SĐT.
    # Quyết định TỰ NỘP / NỘP THAY bằng formContext (tên+CCCD tài khoản) SO với đối tượng HĐKC —
    # KHÔNG dựa vào việc có trích được NguoiNop_* hay không.
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("ownerFullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("ownerIdentityNumber"))
    sub_id = _identity(values.get("NguoiNop_SoDinhDanh")) or ctx_identity
    sub_name = _text(values.get("NguoiNop_HoTen")) or ctx_name

    is_nop_thay = False
    if sub_id and identity:
        is_nop_thay = sub_id != identity
    elif sub_name and name:
        is_nop_thay = _fold(sub_name) != _fold(name)

    if is_nop_thay:
        # Nộp thay: Phần I = NGƯỜI NỘP. Chỉ điền cái CÓ (NguoiNop_* nếu hồ sơ có CCCD người nộp); THIẾU
        # thì ĐỂ TRỐNG. TUYỆT ĐỐI KHÔNG lấy nhân thân đối tượng HĐKC đổ vào Phần I.
        nop_gender = _text(values.get("NguoiNop_GioiTinh"))
        nop_residence = _area(values.get("NguoiNop_ThuongTru"))
        nop_id_date = _date(values.get("NguoiNop_NgayCap"))
        nop_issuer = _issuer(values.get("NguoiNop_NoiCap"))
        nop_phone = _phone(values.get("NguoiNop_DienThoai"))
    else:
        # Tự nộp (người nộp = đối tượng, hoặc không xác định được người nộp) → Phần I = đối tượng.
        nop_gender = _text(values.get("NguoiNop_GioiTinh")) or gender
        nop_residence = _area(values.get("NguoiNop_ThuongTru")) or residence
        nop_id_date = _date(values.get("NguoiNop_NgayCap")) or id_date
        nop_issuer = _issuer(values.get("NguoiNop_NoiCap")) or issuer
        nop_phone = _phone(values.get("NguoiNop_DienThoai")) or phone

    add("data[gender]", nop_gender, occurrence=0)
    if nop_residence:
        add_area("data[province]", "data[district]", "data[address]", nop_residence, occurrence=0)
    add("data[identityDate]", nop_id_date, occurrence=0)
    add("data[idIssuePlace]", nop_issuer)
    add("data[email]", _text(values.get("NguoiNop_Email")))
    add("data[phoneNumber]", nop_phone, occurrence=0)

    # --- Mở khoá Phần II: BỎ TÍCH "Người nộp là chủ hồ sơ" (chủ hồ sơ = đối tượng, khác người nộp) ---
    add("data[isOwnerDossierCheck]", False)
    add("data[chonDoiTuong1]", "Cá nhân")

    # --- Phần II: Chủ hồ sơ (= đối tượng HĐKC) ---
    add("data[ownerFullname]", name)
    add("data[ownerBirthday]", birthday)
    add("data[ownerGender]", gender)
    add("data[ownerIdentityNumber]", identity)
    add("data[ownerIdentityDate]", id_date)
    add("data[ownerIdIssuePlace]", issuer)
    add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", residence)
    add("data[ownerPhoneNumber]", phone)
    add("data[ownerNation]", "Việt Nam" if name or identity else None)

    # --- Phần III: hồ sơ kèm theo (hàng 0) ---
    ho_so = _list(values.get("HoSoDinhKem"))
    if ho_so:
        add("data[hoSoDinhKem][0][textField1]", _item_text(ho_so[0], "tenGiayTo", "ten", "name"))
        add("data[hoSoDinhKem][0][textField2]", _item_text(ho_so[0], "loaiBan", "loai", "type") or "Bản chính")

    # --- Phần IV Mục 1: Người HĐKC (occurrence 1 cho các key dùng chung) ---
    add("data[CheDo]", _text(values.get("HDKC_CheDo")))
    add("data[fullname]", name, occurrence=1)
    # Bí danh: bỏ nếu LLM rò nhầm giá trị giới tính ("Nam"/"Nữ") vào ô này (bản khai thường để trống).
    _bi_danh = _text(values.get("HDKC_BiDanh"))
    if _bi_danh and _fold(_bi_danh) in ("nam", "nu"):
        _bi_danh = None
    add("data[biDanh]", _bi_danh)
    add("data[gender]", gender, occurrence=1)
    add("data[birthday]", birthday, occurrence=1)
    add("data[identityNumber]", identity, occurrence=1)
    add("data[identityDate]", id_date, occurrence=1)
    add("data[identityAgency]", issuer)  # select nơi cấp (Mục 1).
    add_area("data[province]", "data[district]", "data[address]", quequan, occurrence=1)  # QUÊ QUÁN.
    add("data[quaTrinh]", _text(values.get("HDKC_QuaTrinh")))
    add("data[thanhTich]", _text(values.get("HDKC_ThanhTich")))
    add("data[duocTang]", _text(values.get("HDKC_DuocTang")))

    return out, warnings
