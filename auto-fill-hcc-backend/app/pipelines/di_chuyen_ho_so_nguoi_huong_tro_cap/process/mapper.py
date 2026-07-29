"""Map compact source facts → Form.io data[...] fields cho thủ tục "Di chuyển hồ sơ khi người hưởng
trợ cấp ưu đãi thay đổi nơi thường trú".

HAI vai (mirror giai_quyet):
  Phần I  (occ 0)  = NGƯỜI NỘP (NguoiNop_*, fallback người hưởng khi tự nộp).
  Phần II (owner*) = NGƯỜI HƯỞNG TRỢ CẤP = chủ hồ sơ (NguoiHuong_*).
  Phần III(occ 1)  = NGƯỜI HƯỞNG (đơn Mẫu 27) + key riêng (DcHsNcc/identityAgency/ThuocDienNcc/
                     province1/district1/address1).
BỎ TÍCH data[isOwnerDossierCheck] để mở Phần II (như giai_quyet — robust cả tự nộp lẫn nộp thay).

⚠️ BẪY occurrence (NGƯỢC sua_doi_ttncc): province/district/address occ1 = QUÊ QUÁN người hưởng;
   province1/district1/address1 = NƠI THƯỜNG TRÚ người hưởng.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.process.schema import UI_COMP_BY_NAME


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

    # === NGƯỜI HƯỞNG TRỢ CẤP = chủ hồ sơ (đối tượng chính) ===
    h_name = _text(values.get("NguoiHuong_HoTen"))
    h_identity = _identity(values.get("NguoiHuong_SoDinhDanh"))
    h_birthday = _date(values.get("NguoiHuong_NgaySinh"))
    h_gender = _text(values.get("NguoiHuong_GioiTinh"))
    h_id_date = _date(values.get("NguoiHuong_NgayCap"))
    h_issuer = _issuer(values.get("NguoiHuong_NoiCap"))
    h_residence = _area(values.get("NguoiHuong_ThuongTru"))
    h_quequan = _area(values.get("NguoiHuong_QueQuan"))
    h_phone = _phone(values.get("NguoiHuong_DienThoai"))
    h_email = _text(values.get("NguoiHuong_Email"))

    if not h_name or not h_identity:
        warnings.append("Thiếu họ tên hoặc số định danh người hưởng trợ cấp từ CCCD/Đơn Mẫu 27.")

    # === NGƯỜI NỘP (Phần I occ0). Quyết định TỰ NỘP / NỘP THAY bằng formContext (tên+CCCD tài khoản đăng
    # nhập cổng tự đổ vào Phần I) SO với chủ hồ sơ — KHÔNG dựa vào việc có trích được NguoiNop_* hay không. ===
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("ownerFullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("ownerIdentityNumber"))
    # Người nộp có thể có CCCD riêng trong hồ sơ (ưu tiên) hoặc chỉ biết qua formContext.
    nop_ext_name = _text(values.get("NguoiNop_HoTen"))
    nop_ext_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    sub_name = nop_ext_name or ctx_name
    sub_id = nop_ext_id or ctx_identity

    # Nộp thay khi CÓ danh tính người nộp và KHÁC chủ hồ sơ (so số định danh trước, rồi tên). Không có
    # danh tính người nộp (test trực tiếp / cổng chưa đổ) → coi như tự nộp.
    is_nop_thay = False
    if sub_id and h_identity:
        is_nop_thay = sub_id != h_identity
    elif sub_name and h_name:
        is_nop_thay = _fold(sub_name) != _fold(h_name)

    if is_nop_thay:
        # Phần I = THÔNG TIN NGƯỜI NỘP. Chỉ điền cái CÓ (tên/CCCD từ tài khoản + NguoiNop_* nếu hồ sơ có
        # CCCD người nộp). TUYỆT ĐỐI KHÔNG lấy nhân thân chủ hồ sơ đổ vào đây — thiếu thì ĐỂ TRỐNG.
        nop_name = nop_ext_name or ctx_name
        nop_identity = nop_ext_id or ctx_identity
        nop_birthday = _date(values.get("NguoiNop_NgaySinh"))
        nop_gender = _text(values.get("NguoiNop_GioiTinh"))
        nop_id_date = _date(values.get("NguoiNop_NgayCap"))
        nop_issuer = _issuer(values.get("NguoiNop_NoiCap"))
        nop_residence = _area(values.get("NguoiNop_ThuongTru"))
        nop_phone = _phone(values.get("NguoiNop_DienThoai"))
    else:
        # Tự nộp (người nộp = chủ hồ sơ, hoặc không xác định được người nộp) → Phần I = chủ hồ sơ.
        nop_name = h_name
        nop_identity = h_identity
        nop_birthday = h_birthday
        nop_gender = h_gender
        nop_id_date = h_id_date
        nop_issuer = h_issuer
        nop_residence = h_residence
        nop_phone = h_phone

    add("data[chonDoiTuong]", "Cá nhân")
    add("data[fullname]", nop_name, occurrence=0)
    add("data[birthday]", nop_birthday, occurrence=0)
    add("data[gender]", nop_gender, occurrence=0)
    add("data[identityNumber]", nop_identity, occurrence=0)
    add("data[identityDate]", nop_id_date, occurrence=0)
    add("data[idIssuePlace]", nop_issuer)  # Nơi cấp Phần I (key riêng, 1×).
    add_area("data[province]", "data[district]", "data[address]", nop_residence, occurrence=0)  # Thường trú người nộp.
    add("data[phoneNumber]", nop_phone, occurrence=0)

    # === Mở khoá Phần II: BỎ TÍCH "Người nộp là chủ hồ sơ" ===
    add("data[isOwnerDossierCheck]", False)
    add("data[chonDoiTuong1]", "Cá nhân")

    # === Phần II: chủ hồ sơ = NGƯỜI HƯỞNG TRỢ CẤP ===
    add("data[ownerFullname]", h_name)
    add("data[ownerBirthday]", h_birthday)
    add("data[ownerGender]", h_gender)
    add("data[ownerIdentityNumber]", h_identity)
    add("data[ownerIdentityDate]", h_id_date)
    add("data[ownerIdIssuePlace]", h_issuer)
    add_area("data[ownerProvince]", "data[ownerDistrict]", "data[ownerAddress]", h_residence)  # Thường trú.
    add("data[ownerPhoneNumber]", h_phone)
    add("data[ownerNation]", "Việt Nam" if h_name or h_identity else None)

    # === Phần III: Đơn Mẫu 27 = NGƯỜI HƯỞNG (occurrence 1 cho key dùng chung) ===
    add("data[DcHsNcc]", _text(values.get("Don_TenHoSoNCC")))
    add("data[fullname]", h_name, occurrence=1)
    add("data[birthday]", h_birthday, occurrence=1)
    add("data[gender]", h_gender, occurrence=1)
    add("data[identityNumber]", h_identity, occurrence=1)
    add("data[identityDate]", h_id_date, occurrence=1)
    add("data[identityAgency]", h_issuer)  # Nơi cấp (Phần III, key riêng).
    add_area("data[province]", "data[district]", "data[address]", h_quequan, occurrence=1)  # ⚠️ QUÊ QUÁN.
    add_area("data[province1]", "data[district1]", "data[address1]", h_residence)  # NƠI THƯỜNG TRÚ.
    add("data[phoneNumber]", h_phone, occurrence=1)
    add("data[ThuocDienNcc]", _text(values.get("Don_ThuocDienNCC")))

    return out, warnings
