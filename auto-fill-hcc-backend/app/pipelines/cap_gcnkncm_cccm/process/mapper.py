"""Map compact facts → Form.io data[...] cho "Cấp, cấp lại, chuyển đổi GCNKNCM, CCCM" (dvc.moc).

Khối A (Thông tin chung — người nộp) phẳng; Khối B (Cá nhân/Tổ chức đề nghị) đổi theo data[chonDoiTuong].
Ô đăng ký DN/hộ KD chỉ phát khi LLM trích được (hồ sơ có giấy đăng ký) — `add()` bỏ giá trị rỗng.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_gcnkncm_cccm.process.schema import UI_COMP_BY_NAME


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        parts = [
            value.get("diaChi") or value.get("dia_chi") or value.get("chiTiet"),
            value.get("xa") or value.get("phuong") or value.get("phường"),
            value.get("huyen") or value.get("quanHuyen"),
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
        r"^(tỉnh|thành phố|tp\.?|xã|phường|thị trấn|tt\.?|huyện|quận|thị xã)\s+",
        "", text, flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    if folded.startswith(("tinh ", "thanh pho ", "tp ")):
        return text
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
    bare = _strip_admin_prefix(text)
    return f"{'Thành phố' if _fold(bare) in city_markers else 'Tỉnh'} {bare}"


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
        out["tinh"], out["xa"], out["diaChi"] = parts[-1], parts[-3], ", ".join(parts[:-3]).strip()
    elif len(parts) >= 3:
        out["tinh"], out["xa"], out["diaChi"] = parts[-1], parts[-2], ", ".join(parts[:-2]).strip()
    elif len(parts) == 2:
        out["tinh"], out["diaChi"] = parts[-1], parts[0]
    else:
        out["diaChi"] = parts[0]
    return out if any(out.values()) else None


def _area(value: Any) -> dict | None:
    """CCCD/đơn address → {tinh,xa,diaChi} đã chuẩn hóa tỉnh/xã sau sáp nhập (Quảng Nam→Đà Nẵng…)."""
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
    if not out:
        return None
    if out.get("tinh"):
        out["tinh"] = _strip_admin_prefix(out["tinh"])
    return remap_area(out, allow_diachi_fallback=True)


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return re.sub(r"\D+", "", text) or None


def _phone(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


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


def _flatten(area: dict | None) -> str | None:
    if not area:
        return None
    parts = [area.get("diaChi"), area.get("xa"), area.get("tinh")]
    return ", ".join(str(p).strip() for p in parts if str(p or "").strip()) or None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    _ = options
    v = _by_name(fields)
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

    name = _text(v.get("NguoiNop_HoTen"))
    residence = _area(v.get("NguoiNop_ThuongTru"))
    is_to_chuc = "to chuc" in _fold(v.get("DoiTuong"))

    if not name:
        warnings.append("Thiếu họ tên người nộp từ CCCD/GCNKNCM/Đơn/Giấy khám sức khỏe.")

    # --- Khối A: Thông tin chung (người nộp) ---
    add("data[chonDoiTuong]", "Tổ chức" if is_to_chuc else "Cá nhân")
    add("data[fullname]", name)
    add("data[birthday]", _date(v.get("NguoiNop_NgaySinh")))
    add("data[gender]", _text(v.get("NguoiNop_GioiTinh")))
    add("data[identityNumber]", _identity(v.get("NguoiNop_SoDinhDanh")))
    add("data[identityDate]", _date(v.get("NguoiNop_NgayCapCccd")))
    add("data[identityAgency]", _issuer(v.get("NguoiNop_NoiCapCccd")))
    # SĐT người nộp → ô "Số điện thoại" (phoneNumber), KHÔNG phải ô "SĐT người được ủy quyền".
    add("data[phoneNumber]", _phone(v.get("NguoiNop_DienThoai")))
    add("data[nation]", _text(v.get("NguoiNop_QuocTich")) or ("Việt Nam" if name else None))
    if residence:
        add("data[province]", _province_label(residence.get("tinh")))
        add("data[district]", _text(residence.get("xa")))

    # --- Khối B: đối tượng đề nghị (đổi theo Cá nhân/Tổ chức) ---
    ten = _text(v.get("DoiTuong_Ten")) or name
    dia_chi = _text(v.get("DoiTuong_DiaChi")) or _flatten(residence)
    nguoi_dd = _text(v.get("DoiTuong_NguoiDaiDien"))
    so_dk = _text(v.get("DoiTuong_SoDangKy"))
    ngay_dk = _date(v.get("DoiTuong_NgayCapDangKy"))
    noi_dk = _text(v.get("DoiTuong_NoiCapDangKy"))

    if is_to_chuc:
        add("data[ownerFullname]", ten)
        add("data[diaChitoChuc]", dia_chi)
        add("data[nguoidaidiendoanhnghiep]", nguoi_dd)
        add("data[dangkydoanhnghiep]", so_dk)
        add("data[captaidoanhnghiep]", noi_dk)
        add("data[ngaythangnamdoanhnghiep]", ngay_dk)
        add("data[phoneNumberTC]", _phone(v.get("DoiTuong_DienThoai")))
    else:
        add("data[fullName]", ten)
        add("data[diachicanhan]", dia_chi)
        add("data[nguoidaidiencanhan]", nguoi_dd)
        add("data[dangkyhogiadinh]", so_dk)
        add("data[captaicaNhan]", noi_dk)
        add("data[ngayThangNamCN]", ngay_dk)

    return out, warnings
