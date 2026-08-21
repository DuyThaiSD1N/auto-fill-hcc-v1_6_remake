"""Map compact source facts → Form.io data[...] fields cho "Cấp phép sử dụng tạm thời lòng đường, vỉa
hè" (cổng Bộ Xây dựng). Field-key FLAT data[...], nhiều phần (xem schema).

- Phần I  : người nộp (cá nhân đại diện) → fullname/birthday/gender/email/CCCD/địa chỉ + chonDoiTuong.
- Phần I-b: doanh nghiệp (khi Tổ chức) → organization/taxCode/organizationPhoneNumber/nation1/...address1.
- Phần II : tenDonVi/tenCoQuanDeNghi (= tên tổ chức, hoặc tên người nộp khi cá nhân), kinhGui, TinhThanh
            (nơi lập đơn = tỉnh của địa bàn), ngayThangNam (ngày lập đơn).
- Phần III: tenSuKien/tenDoanDuong/tenTuyenDuong/diaBan/tuNgay/denNgay.
- Phần IV : diaChiLienHe, soDienThoai (= điện thoại cá nhân người nộp).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_phep_long_duong_via_he.process.schema import UI_COMP_BY_NAME


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
            value.get("diaChi") or value.get("chiTiet"),
            value.get("xa") or value.get("phuong"),
            value.get("tinh") or value.get("tinhThanh"),
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
        r"^(tỉnh|thành\s*phố|t\.?\s*p\.?|xã|phường|thị trấn|t\.?\s*t\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    bare = _strip_admin_prefix(text)
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
    if isinstance(value, str):
        out = _parse_area_text(value)
    elif isinstance(value, dict):
        out = {
            "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
            "tinh": value.get("tinh") or value.get("tinhThanh") or "",
            "xa": value.get("xa") or value.get("phuong") or value.get("phường") or "",
            "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
        }
        out = out if any(out.values()) else None
    else:
        return None
    # Chuẩn hóa phường/xã sau sáp nhập (vd "An Hải Tây" → "Phường An Hải") để khớp SELECT trên form —
    # địa chỉ theo CCCD/GCN thường ghi tên phường CŨ, không khớp danh mục phường mới của cổng.
    # ⚠ remap_area build key lookup bằng tỉnh CÓ prefix ("thanh pho da nang") nhưng bảng remap dùng tên
    # bare ("da nang") → TP trực thuộc TW không khớp. Strip prefix tỉnh TRƯỚC khi remap; _province_label
    # gắn lại "Thành phố" sau.
    if not out:
        return None
    if out.get("tinh"):
        out["tinh"] = _strip_admin_prefix(out["tinh"])
    return remap_area(out, allow_diachi_fallback=True)


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


_ORG_MARKERS = ("cong ty", "doanh nghiep", "hop tac xa", "htx", "cty", "co phan", "tnhh", "co quan",
                "xi nghiep", "tap doan", "chi nhanh", "ngan hang")


def _is_to_chuc(loai: Any, name: Any) -> bool:
    f_loai = _fold(loai)
    if "to chuc" in f_loai:
        return True
    if "ca nhan" in f_loai:
        return False
    return any(m in _fold(name) for m in _ORG_MARKERS)


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

    # --- Xác định đối tượng ---
    org_name = _text(values.get("DoanhNghiep_Ten"))
    is_to_chuc = _is_to_chuc(values.get("ChonDoiTuong"), org_name) or bool(org_name)

    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_area = _area(values.get("NguoiNop_DiaChi"))
    org_area = _area(values.get("DoanhNghiep_DiaChi"))
    nop_phone = _phone(values.get("NguoiNop_DienThoai"))

    if not nop_name:
        warnings.append("Thiếu tên người nộp hồ sơ (người ký đơn / đại diện).")

    # --- Phần I: người nộp ---
    add("data[chonDoiTuong]", "Tổ chức" if is_to_chuc else "Cá nhân")
    add("data[fullname]", nop_name)
    add("data[birthday]", _date(values.get("NguoiNop_NgaySinh")))
    add("data[gender]", _text(values.get("NguoiNop_GioiTinh")))
    add("data[email]", _text(values.get("NguoiNop_Email")))
    add("data[identityNumber]", _identity(values.get("NguoiNop_SoDinhDanh")))
    add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
    add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap")))
    add("data[phoneNumber]", nop_phone)
    add("data[nation]", "Việt Nam")
    add_area("data[province]", "data[district]", "data[address]", nop_area)

    # --- Phần I-b: doanh nghiệp (khi Tổ chức) ---
    if is_to_chuc:
        add("data[organization]", org_name)
        add("data[taxCode]", _identity(values.get("DoanhNghiep_MaSoThue")))
        add("data[organizationPhoneNumber]", _phone(values.get("DoanhNghiep_DienThoai")))
        add("data[nation1]", "Việt Nam")
        add_area("data[province1]", "data[district1]", "data[address1]", org_area)

    # --- Phần II: đơn đề nghị (header) ---
    # Đơn vị/cơ quan đề nghị = tên tổ chức (khi Tổ chức) hoặc tên người nộp (khi cá nhân).
    don_vi = org_name if is_to_chuc else nop_name
    add("data[tenDonVi]", don_vi)
    add("data[tenCoQuanDeNghi]", don_vi)
    add("data[kinhGui]", _text(values.get("Don_KinhGui")))
    add("data[ngayThangNam]", _date(values.get("Don_NgayLap")))
    # Nơi lập đơn (TinhThanh) = tỉnh/TP của địa bàn đề nghị (ưu tiên) hoặc thường trú người nộp.
    de_nghi_area = _parse_area_text(_text(values.get("DeNghi_DiaBan")))
    tinh_lap = None
    if de_nghi_area and de_nghi_area.get("tinh"):
        tinh_lap = _province_label(de_nghi_area.get("tinh"))
    if not tinh_lap and nop_area and nop_area.get("tinh"):
        tinh_lap = _province_label(nop_area.get("tinh"))
    add("data[TinhThanh]", tinh_lap)

    # --- Phần III: thông tin đề nghị ---
    add("data[tenSuKien]", _text(values.get("DeNghi_MucDich")))
    add("data[tenDoanDuong]", _text(values.get("DeNghi_DoanDuong")))
    add("data[tenTuyenDuong]", _text(values.get("DeNghi_TuyenDuong")))
    add("data[diaBan]", _text(values.get("DeNghi_DiaBan")))
    add("data[tuNgay]", _date(values.get("DeNghi_TuNgay")))
    add("data[denNgay]", _date(values.get("DeNghi_DenNgay")))

    # --- Phần IV: liên hệ ---
    add("data[diaChiLienHe]", _text(values.get("LienHe_DiaChi")))
    add("data[soDienThoai]", nop_phone)

    return out, warnings
