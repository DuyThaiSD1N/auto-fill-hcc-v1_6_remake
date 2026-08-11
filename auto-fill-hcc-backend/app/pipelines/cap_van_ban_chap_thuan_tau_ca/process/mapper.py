"""Map compact source facts → Form.io data[...] fields cho thủ tục "Cấp văn bản chấp thuận đóng mới,
cải hoán, thuê, mua tàu cá Việt Nam".

- Nhân thân: như #92 (tự nộp giữ tích / nộp thay bỏ tích, quyết định bằng formContext).
- Phần III (nội dung tờ khai): các key TRÙNG Phần I điền bằng occurrence=1 (data[chonDoiTuong/
  identityNumber/identityDate/address]); kèm data[kinhgui/diaDanh/loaiGT/tenCQ]. Chủ thể Phần III LUÔN là
  NGƯỜI ĐỀ NGHỊ (không phải người nộp).
- Phần IV/V (thông số tàu): DongMoi_* → data[vatLieuVo/ngheKhaiThac/vungHoatDong]; CaiHoan_* →
  data[kichThuocChinh/chieuChim/congSuat/vatLieuVo1/ngheKhaiThac1/vungHoatDong1/noiDungCaiHoan].
- Phần VI: data[chuCS] = họ tên người đề nghị.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_van_ban_chap_thuan_tau_ca.process.schema import UI_COMP_BY_NAME


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


def _full_address(area: dict | None) -> str | None:
    """Ghép địa chỉ đầy đủ cho ô Phần III (1 ô free-text): 'chi tiết, xã, tỉnh'."""
    if not area:
        return None
    parts = [
        _text(area.get("diaChi")),
        _commune_label(area.get("xa")),
        _province_label(area.get("tinh")),
    ]
    joined = ", ".join(p for p in parts if p)
    return joined or None


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


def _number(value: Any) -> str | None:
    """Chỉ giữ số (và dấu chấm thập phân) — cho chiều chìm / công suất."""
    text = _text(value)
    if not text:
        return None
    m = re.search(r"\d+(?:[.,]\d+)?", text)
    return m.group(0).replace(",", ".") if m else None


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
        warnings.append("Thiếu họ tên người đề nghị từ CCCD/Tờ khai Mẫu 12.")

    # --- Quyết định TỰ NỘP / NỘP THAY: formContext SO với người đề nghị ---
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
        # === TỰ NỘP: Phần I = người đề nghị. Ô "Người nộp là chủ hồ sơ" của cổng MAE mặc định CHƯA tick
        # (KHÁC #92/#101 mặc định đã tick) → phải CHỦ ĐỘNG TICH (True) để cổng tự nhân bản Phần I → Phần II. ===
        add("data[fullname]", name)
        add("data[birthday]", birthday)
        add("data[gender]", gender)
        add("data[identityNumber]", identity)
        add("data[identityDate]", id_date)
        add("data[idIssuePlace]", issuer)
        add_area("data[province]", "data[district]", "data[address]", residence)
        add("data[phoneNumber]", phone)
        add("data[email]", email)
        add("data[isOwnerDossierCheck]", True)  # TICH: người nộp = chủ hồ sơ → Phần II tự đổ.
    else:
        # === NỘP THAY: Phần I = NGƯỜI NỘP; BỎ TÍCH; Phần II owner_* = người đề nghị. ===
        add("data[fullname]", nop_ext_name or ctx_name)
        add("data[birthday]", _date(values.get("NguoiNop_NgaySinh")))
        add("data[gender]", _text(values.get("NguoiNop_GioiTinh")))
        add("data[identityNumber]", nop_ext_id or ctx_identity)
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
        add("data[idIssuePlace]", _issuer(values.get("NguoiNop_NoiCap")))
        add_area("data[province]", "data[district]", "data[address]", _area(values.get("NguoiNop_ThuongTru")))
        add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")))
        add("data[email]", _text(values.get("NguoiNop_Email")))

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

    # --- Phần III: NỘI DUNG TỜ KHAI (chủ thể LUÔN là người đề nghị). Key trùng Phần I → occurrence=1.
    # chonDoiTuong occ=1 ("Cá nhân") set TRƯỚC để ô "Họ và tên cá nhân" (formio-hidden theo điều kiện) hiện
    # ra, rồi mới điền data[fullname] occ=1 = họ tên người đề nghị. ---
    add("data[chonDoiTuong]", "Cá nhân", occurrence=1)
    add("data[fullname]", name, occurrence=1)  # Họ và tên cá nhân người đề nghị (Phần III).
    add("data[identityNumber]", identity, occurrence=1)
    add("data[identityDate]", id_date, occurrence=1)
    add("data[address]", _full_address(residence), occurrence=1)  # 1 ô địa chỉ đầy đủ.

    add("data[kinhgui]", _text(values.get("ToKhai_KinhGui")))
    dia_danh = _text(values.get("ToKhai_DiaDanh")) or (_province_label(residence.get("tinh")) if residence else None)
    add("data[diaDanh]", _province_label(dia_danh) if dia_danh else None)
    loai_gt = _text(values.get("ToKhai_LoaiGiayTo")) or ("Thẻ Căn cước công dân" if identity and len(identity) == 12 else None)
    add("data[loaiGT]", loai_gt)
    add("data[tenCQ]", _text(values.get("ToKhai_CoQuanCap")) or issuer)

    # --- Phần IV: ĐÓNG MỚI ---
    add("data[vatLieuVo]", _text(values.get("DongMoi_VatLieuVo")))
    add("data[ngheKhaiThac]", _text(values.get("DongMoi_NgheKhaiThac")))
    add("data[vungHoatDong]", _text(values.get("DongMoi_VungHoatDong")))

    # --- Phần V: CẢI HOÁN/THUÊ/MUA ---
    add("data[kichThuocChinh]", _text(values.get("CaiHoan_KichThuoc")))
    add("data[chieuChim]", _number(values.get("CaiHoan_ChieuChim")))
    add("data[congSuat]", _number(values.get("CaiHoan_CongSuat")))
    add("data[vatLieuVo1]", _text(values.get("CaiHoan_VatLieuVo")))
    add("data[ngheKhaiThac1]", _text(values.get("CaiHoan_NgheKhaiThac")))
    add("data[vungHoatDong1]", _text(values.get("CaiHoan_VungHoatDong")))
    add("data[noiDungCaiHoan]", _text(values.get("CaiHoan_NoiDung")))

    # --- Phần VI: CAM KẾT (họ tên người đề nghị ký) ---
    add("data[chuCS]", name)

    return out, warnings
