"""Map compact source facts → Form.io data[...] fields cho thủ tục "Thực hiện, điều chỉnh, thôi hưởng
trợ cấp xã hội hàng tháng, hỗ trợ kinh phí chăm sóc, nuôi dưỡng hàng tháng".

HAI vai (có thể NỘP THAY):
  Phần 1 (data[fullname...])   — NGƯỜI NỘP = người khai thay trên tờ khai. Không có block người khai thay
                                 → dùng đối tượng; không sử dụng tài khoản/formContext do FE truyền.
  Phần 2 (data[owner*])        — CHỦ HỒ SƠ = ĐỐI TƯỢNG hưởng trợ cấp. LUÔN bỏ tích isOwnerDossierCheck +
                                 điền tường minh (không dựa vào auto-copy của cổng).
Mỗi data[key] xuất hiện 1× trong DOM → KHÔNG dùng occurrence.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.tro_cap_xa_hoi_hang_thang.process.schema import UI_COMP_BY_NAME


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


def _locality_key(value: Any) -> str:
    """Khóa so xã/phường, chịu được tiền tố Phường/P./Xã và khác biệt dấu câu."""
    text = re.sub(r"[^a-z0-9]+", " ", _fold(value)).strip()
    return re.sub(r"^(?:phuong|p|xa|thi tran|tt)\s+", "", text).strip()


def _complete_missing_provinces(*areas: dict | None) -> None:
    """Bổ sung tỉnh khi cùng xã/phường chỉ ánh xạ tới đúng một tỉnh trong hồ sơ.

    Không dùng danh sách địa danh hay ví dụ hồ sơ cụ thể: chỉ tổng hợp chứng cứ địa chỉ đã trích trong
    chính hồ sơ. Tỉnh đã có không bao giờ bị ghi đè; tên xã trùng nhiều tỉnh thì giữ trống.
    """
    province_by_locality: dict[str, dict[str, str]] = {}
    for area in areas:
        if not area:
            continue
        locality = _locality_key(area.get("xa"))
        province = _text(area.get("tinh"))
        if not locality or not province:
            continue
        province_key = _fold(_strip_admin_prefix(province))
        if province_key:
            province_by_locality.setdefault(locality, {}).setdefault(province_key, province)

    for area in areas:
        if not area or _text(area.get("tinh")):
            continue
        candidates = province_by_locality.get(_locality_key(area.get("xa")), {})
        if len(candidates) == 1:
            area["tinh"] = next(iter(candidates.values()))


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


def _validated_submitter_identity(value: Any) -> str | None:
    """Người khai thay chỉ được điền CMND 9 số hoặc CCCD/CMND 12 số; không sửa đoán OCR sai."""
    digits = _identity(value)
    return digits if digits and len(digits) in {9, 12} else None


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
    # Giữ tham số để tương thích caller/test cũ, nhưng thủ tục này cố ý không dùng nhân thân từ FE.
    _ = options
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

    # --- ĐỐI TƯỢNG hưởng trợ cấp = chủ hồ sơ (đối tượng chính) ---
    name = _text(values.get("DoiTuong_HoTen"))
    identity = _identity(values.get("DoiTuong_SoDinhDanh"))
    birthday = _date(values.get("DoiTuong_NgaySinh"))
    gender = _text(values.get("DoiTuong_GioiTinh"))
    id_date = _date(values.get("DoiTuong_NgayCap"))
    issuer = _issuer(values.get("DoiTuong_NoiCap"))
    residence = _area(values.get("DoiTuong_ThuongTru"))
    phone = _phone(values.get("DoiTuong_DienThoai"))
    ghichu = _text(values.get("DoiTuong_GhiChu"))

    if not name:
        warnings.append("Thiếu họ tên đối tượng hưởng trợ cấp từ CCCD/Tờ khai/Giấy khai sinh.")

    # --- NGƯỜI NỘP (Phần I) = người tại block "Thông tin người khai thay" trên tờ khai. ---
    nop_ext_name = _text(values.get("NguoiNop_HoTen"))
    nop_ext_id = _validated_submitter_identity(values.get("NguoiNop_SoDinhDanh"))
    has_declarant = bool(nop_ext_name or nop_ext_id)

    if has_declarant:
        # Có người khai thay: chỉ điền dữ liệu đọc được của đúng người này; thiếu thì để trống.
        nop_name = nop_ext_name
        nop_identity = nop_ext_id
        nop_birthday = _date(values.get("NguoiNop_NgaySinh"))
        nop_gender = _text(values.get("NguoiNop_GioiTinh"))
        nop_id_date = _date(values.get("NguoiNop_NgayCap"))
        nop_issuer = _issuer(values.get("NguoiNop_NoiCap"))
        nop_residence = _area(values.get("NguoiNop_ThuongTru"))
        nop_phone = _phone(values.get("NguoiNop_DienThoai"))
        nop_email = _text(values.get("NguoiNop_Email"))
    else:
        # Không có block người khai thay → đối tượng tự khai, Phần I dùng cùng nhân thân đối tượng.
        nop_name = name
        nop_identity = identity
        nop_birthday = birthday
        nop_gender = gender
        nop_id_date = id_date
        nop_issuer = issuer
        nop_residence = residence
        nop_phone = phone
        nop_email = _text(values.get("DoiTuong_Email"))

    _complete_missing_provinces(residence, nop_residence)

    add("data[chonDoiTuong]", "Cá nhân")
    add("data[fullname]", nop_name)
    add("data[birthday]", nop_birthday)
    add("data[gender]", nop_gender)
    add("data[identityNumber]", nop_identity)
    add("data[identityDate]", nop_id_date)
    add("data[idIssuePlace]", nop_issuer)
    add_area("data[province]", "data[district]", "data[address]", nop_residence)  # Thường trú người nộp.
    add("data[phoneNumber]", nop_phone)
    add("data[email]", nop_email)

    # --- Mở khoá Phần II: BỎ TÍCH "Người nộp là chủ hồ sơ" ---
    add("data[isOwnerDossierCheck]", False)

    # --- Phần II: chủ hồ sơ = ĐỐI TƯỢNG hưởng trợ cấp ---
    add("data[ownerFullname]", name)
    add("data[ownerBirthday]", birthday)
    add("data[ownerGender]", gender)
    add("data[ownerIdentityNumber]", identity)
    add("data[ownerIdentityDate]", id_date)
    add("data[ownerIdIssuePlace]", issuer)
    add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", residence)  # Thường trú.
    add("data[ownerPhoneNumber]", phone)
    add("data[ownerEmail]", _text(values.get("DoiTuong_Email")))
    add("data[ownerNation]", "Việt Nam" if name or identity else None)
    add("data[ghiChu]", ghichu)

    return out, warnings
