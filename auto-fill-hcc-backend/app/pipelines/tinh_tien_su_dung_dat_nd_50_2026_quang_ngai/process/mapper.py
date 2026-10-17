"""Map facts nguồn sang Form.io của cổng DVC Quảng Ngãi (tính lại tiền sử dụng đất, NĐ 50/2026)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date

from .schema import UI_COMP_BY_NAME


def _by_name(fields: list[dict]) -> dict[str, Any]:
    return {item["name"]: item.get("value") for item in fields if item.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" ,;:")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _digits(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", _text(value) or "")
    return digits or None


def _phone(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", (_text(value) or "").upper().replace("O", "0"))
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = re.fullmatch(r"\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\s*", text)
    return normalize_date(f"{match.group(1)}/{match.group(2)}/{match.group(3)}") if match else None


# Đơn viết tay hay ghi tắt "P. Đăk Bla, T. Quảng Ngãi" — khai triển trước khi remap/khớp danh mục cổng.
_WARD_ABBR = ((re.compile(r"^ph?\.\s*", re.IGNORECASE), "Phường "), (re.compile(r"^x\.\s*", re.IGNORECASE), "Xã "))
_PROVINCE_ABBR = (
    (re.compile(r"^tp\.\s*", re.IGNORECASE), "Thành phố "),
    (re.compile(r"^t\.\s*", re.IGNORECASE), "Tỉnh "),
)


def _expand(value: Any, rules) -> str:
    text = _text(value) or ""
    for pattern, full in rules:
        if pattern.match(text):
            return pattern.sub(full, text, count=1)
    return text


def _area(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": _expand(value.get("tinh"), _PROVINCE_ABBR),
        "xa": _expand(value.get("xa") or value.get("phuong"), _WARD_ABBR),
        "diaChi": value.get("diaChi") or value.get("chiTiet") or "",
    }
    return remap_area(area) if any((area["tinh"], area["xa"], area["diaChi"])) else None


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    bare = re.sub(r"^(tỉnh|thành phố|tp\.?)\s+", "", text, flags=re.IGNORECASE).strip()
    return province_label(bare)


def _lower_unit(value: str | None) -> str | None:
    """'Phường Đăk Bla' -> 'phường Đăk Bla' khi đặt giữa câu (như Giấy chứng nhận ghi)."""
    if not value:
        return value
    return re.sub(r"^(Phường|Xã|Tỉnh|Thành phố|Đặc khu)\b", lambda m: m.group(1).lower(), value)


def _parcel_text(values: dict[str, Any], parcel_area: dict | None) -> str | None:
    """'Thửa đất số 223, tờ bản đồ số 77, phường X, tỉnh Y' — đúng cách cán bộ ghi ô Địa chỉ thửa đất."""
    parts: list[str] = []
    thua = _digits(values.get("ThuaDat_SoThua"))
    to = _digits(values.get("ThuaDat_SoTo"))
    if thua:
        parts.append(f"Thửa đất số {thua}")
    if to:
        parts.append(f"tờ bản đồ số {to}")
    if parcel_area:
        parts.append(_text(parcel_area.get("diaChi")) or "")
        parts.append(_lower_unit(_text(parcel_area.get("xa"))) or "")
        parts.append(_lower_unit(_province_label(parcel_area.get("tinh"))) or "")
    parts = [part for part in parts if part]
    return ", ".join(parts) if parts else None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    del options
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value: Any, *, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if default:
            item["default"] = True
        out.append(item)
        seen.add(name)

    owner_name = _text(values.get("ChuHoSo_HoTen"))
    applicant_name = _text(values.get("NguoiNop_HoTen")) or owner_name
    # Cổng không có ô "người nộp là chủ hồ sơ": tên khác nhau là tín hiệu duy nhất của việc ủy quyền.
    authorized = bool(owner_name and applicant_name and _fold(owner_name) != _fold(applicant_name))

    # Panel "Thông tin chung" là của CHỦ HỒ SƠ (người sử dụng đất); về người nộp cổng chỉ có
    # data[fullname] và data[phoneNumber1].
    owner_area = _area(values.get("ChuHoSo_DonDiaChi")) or _area(values.get("ChuHoSo_NoiCuTru"))
    owner_phone = _phone(values.get("ChuHoSo_DienThoai"))
    if not owner_phone and not authorized:
        owner_phone = _phone(values.get("NguoiNop_DienThoai"))

    add("data[ownerFullname]", owner_name)
    add("data[fullname]", applicant_name)
    add("data[birthday]", _date(values.get("ChuHoSo_NgaySinh")))
    add("data[gender]", _text(values.get("ChuHoSo_GioiTinh")))
    add("data[identityNumber]", _digits(values.get("ChuHoSo_SoDinhDanh")))
    add("data[identityDate]", _date(values.get("ChuHoSo_NgayCap")))
    issuer = _text(values.get("ChuHoSo_NoiCap"))
    add("data[identityAgency]", normalize_issuer(issuer) if issuer else None)
    add("data[phoneNumber]", owner_phone)
    add("data[email]", _text(values.get("ChuHoSo_Email")))
    # "Số điện thoại ủy quyền" là ô BẮT BUỘC: có ủy quyền -> số bên được ủy quyền; chủ hồ sơ tự nộp ->
    # nhập lại chính số chủ hồ sơ (theo mapping của bộ phận một cửa).
    add("data[phoneNumber1]", _phone(values.get("NguoiNop_DienThoai")) if authorized else owner_phone)
    add("data[chonDoiTuong]", "Cá nhân", default=True)
    add("data[nation]", owner_area.get("quocGia") if owner_area else "Việt Nam", default=True)
    if owner_area:
        add("data[province]", _province_label(owner_area.get("tinh")))
        # Nhãn form là "Phường/xã" nhưng field-key là district (mô hình hành chính 2 cấp).
        add("data[district]", _text(owner_area.get("xa")))
        add("data[address]", _text(owner_area.get("diaChi")))
    add("data[noidungyeucaugiaiquyet]", _text(values.get("Don_NoiDungDeNghi")))

    # KHỐI THỬA ĐẤT: chỉ từ nguồn riêng của thửa đất, KHÔNG bao giờ lấy nơi cư trú thay thế.
    parcel_area = _area(values.get("ThuaDat_DiaChi"))
    add("data[diaChiThuaDat]", _parcel_text(values, parcel_area))
    if parcel_area:
        add("data[province2]", _province_label(parcel_area.get("tinh")))
        add("data[village2]", _text(parcel_area.get("xa")))
        add("data[nation2]", parcel_area.get("quocGia") or "Việt Nam", default=True)

    return out, []
