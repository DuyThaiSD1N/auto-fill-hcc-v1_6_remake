"""Map compact source facts → Form.io data[...] fields cho thủ tục "Cấp, cấp lại Giấy phép khai thác thủy sản".

Chỉ nhân thân Phần I/II (như #97 nhưng KHÔNG có Phần III/tàu):
- TỰ NỘP: Phần I = chủ tàu. Ô data[isOwnerDossierCheck] cổng MAE mặc định CHƯA tick → CHỦ ĐỘNG TICK
  (True) để cổng tự nhân bản Phần I → Phần II (KHÔNG điền owner_*).
- NỘP THAY: Phần I = NGƯỜI NỘP; để CHƯA tick (False) + điền owner_* = chủ tàu tường minh.

Quyết định tự-nộp/nộp-thay bằng formContext (tên + CCCD tài khoản) SO với chủ tàu.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_giay_phep_khai_thac_thuy_san.process.schema import UI_COMP_BY_NAME


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
    # t\.?\s*p\.? bắt mọi biến thể "TP", "TP.", "T.P", "T.P." (OCR/LLM hay trả "T.P Đà Nẵng").
    return re.sub(
        r"^(tỉnh|thành\s*phố|t\.?\s*p\.?|xã|phường|thị\s*trấn|t\.?\s*t\.?|huyện|quận|thị\s*xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    # BỎ tiền tố (Tỉnh/Thành phố/TP/T.P) LLM/OCR trả kèm TRƯỚC, rồi phân loại theo TÊN THÔ để gắn đúng
    # tiền tố (tránh "Tỉnh T.P Đà Nẵng"). Thành phố trực thuộc TW → "Thành phố", còn lại → "Tỉnh".
    bare = _strip_admin_prefix(text)
    if not bare:
        return None
    folded = _fold(bare)
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {bare}"


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
    """Parse và remap địa chỉ để normalize xa/phuong sau sáp nhập hành chính."""
    if isinstance(value, str):
        out = _parse_area_text(value)
    elif isinstance(value, dict):
        out = {
            "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
            "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
            "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
            "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
        }
    else:
        return None
    
    if not out or not any(out.values()):
        return None
    
    # Apply area remapping to normalize xa/phuong names for administrative mergers
    out = remap_area(out, allow_diachi_fallback=True)
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

    # --- NGƯỜI ĐỀ NGHỊ = chủ tàu = chủ hồ sơ ---
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
        warnings.append("Thiếu họ tên chủ tàu (người đề nghị) từ CCCD/Đơn Mẫu 04/05.KT.")

    # --- Quyết định TỰ NỘP / NỘP THAY: formContext SO với chủ tàu ---
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("ownerFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("ownerIdentityNumber") or ctx.get("identityNumber"))

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
        # === TỰ NỘP: Phần I = chủ tàu; TICK isOwnerDossierCheck (mặc định CHƯA tick) → Phần II tự đổ. ===
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
        # === NỘP THAY: Phần I = NGƯỜI NỘP; để CHƯA tick (False) + điền owner_* = chủ tàu. ===
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

    # --- Phần III: NỘI DUNG ĐƠN ĐỀ NGHỊ (chủ thể LUÔN là chủ tàu). Key trùng Phần I → occurrence=1.
    # chonDoiTuong occ=1 ("Cá nhân") set TRƯỚC để ô "Họ tên chủ tàu" (formio-hidden theo điều kiện) hiện ra,
    # rồi mới điền data[fullname] occ=1. ---
    add("data[chonDoiTuong]", "Cá nhân", occurrence=1)
    add("data[fullname]", name, occurrence=1)  # Họ, tên chủ tàu (Phần III).
    add("data[identityNumber]", identity, occurrence=1)
    add("data[identityDate]", id_date, occurrence=1)
    add("data[phoneNumber]", phone, occurrence=1)
    add("data[address]", _full_address(residence), occurrence=1)  # 1 ô địa chỉ đầy đủ.

    add("data[kinhgui]", _text(values.get("ToKhai_KinhGui")))
    # data[diaDanh] là SELECT tỉnh → ưu tiên tỉnh đã REMAP sáp nhập của chủ tàu (residence remap sẵn qua
    # _area, vd Quảng Nam→Đà Nẵng); ToKhai_DiaDanh thô có thể là tên tỉnh CŨ không khớp option → dự phòng.
    dia_danh = (residence.get("tinh") if residence else None) or _text(values.get("ToKhai_DiaDanh"))
    add("data[diaDanh]", _province_label(dia_danh) if dia_danh else None)
    loai_gt = _text(values.get("ToKhai_LoaiGiayTo")) or ("Thẻ Căn cước công dân" if identity and len(identity) == 12 else None)
    add("data[loaiGT]", loai_gt)
    add("data[tenCQ]", _text(values.get("ToKhai_CoQuanCap")) or issuer)
    add("data[chuCS]", name)  # NGƯỜI ĐỀ NGHỊ ký.

    # --- Trường hợp CẤP MỚI (Đơn Mẫu 04) — thông tin tàu ---
    add("data[soGDK]", _text(values.get("CapMoi_SoDangKy")))
    add("data[soGCN]", _text(values.get("CapMoi_SoGcnAtkt")))
    add("data[trangThietBi]", _text(values.get("CapMoi_TrangThietBi")))
    add("data[loaiThietBi]", _text(values.get("CapMoi_ThietBiGsht")))
    add("data[ngheChinh]", _text(values.get("CapMoi_NgheChinh")))
    add("data[nghePhu]", _text(values.get("CapMoi_NghePhu")))

    # --- Trường hợp CẤP LẠI (Đơn Mẫu 05) — GP cũ + lý do (checkbox) ---
    # Số GP cũ: ƯU TIÊN số trên CHÍNH tờ giấy phép (nguồn chuẩn); RỖNG thì mới dùng số ghi trong đơn
    # (người dân hay ghi sai). Chọn tất định ở đây thay vì để LLM tự ưu tiên nguồn.
    add("data[soGP]", _text(values.get("CapLai_SoGiayPhep_GiayPhep"))
        or _text(values.get("CapLai_SoGiayPhep_ToKhai")))
    add("data[ngayCap1]", _date(values.get("CapLai_NgayCap")))
    add("data[ngayHH]", _date(values.get("CapLai_NgayHetHan")))

    ly_do = _fold(values.get("CapLai_LyDo"))
    if ly_do:
        if "mat" in ly_do:
            add("data[biMat]", True)
        if "hu hong" in ly_do or "huhong" in ly_do:
            add("data[huHong]", True)
        if "thay doi" in ly_do:
            add("data[thayDoiTT]", True)
        if "het han" in ly_do or "hethan" in ly_do:
            add("data[gpHetHan]", True)

    return out, warnings