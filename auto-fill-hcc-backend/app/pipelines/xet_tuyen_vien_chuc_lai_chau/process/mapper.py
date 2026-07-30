"""Map compact source facts → CongDan_* UI fields cho xét tuyển viên chức Lai Châu.

Chỉ điền block người dự tuyển (người nộp). Địa chỉ theo nơi thường trú: maTinhThanh/maPhuongXa (dropdown
Semantic UI) + diaChi + chuỗi đầy đủ vào noiOHienTai/diaChiThuongTru.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.xet_tuyen_vien_chuc_lai_chau.process.schema import UI_COMP_BY_NAME
from app.pipelines._shared.area_remap import remap_area


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
    return text.replace("Đ", "D").replace("đ", "d").lower().strip()


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


def _area(value: Any) -> dict | None:
    if isinstance(value, str):
        text = _text(value)
        return {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": text} if text else None
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    return remap_area(out if any(out.values()) else None)


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
    digits = re.sub(r"\D+", "", text.upper().replace("O", "0"))
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
    return normalize_date(m.group(0).replace("-", "/"))


def _issuer(value: Any, ngay_cap: Any) -> str | None:
    text = _text(value)
    if text:
        return normalize_issuer(text)
    d = _date(ngay_cap)
    return default_issuer(d) if d else None


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

    name = _text(values.get("Nguoi_HoTen"))
    identity = _identity(values.get("Nguoi_SoDinhDanh"))
    birthday = _date(values.get("Nguoi_NgaySinh"))
    gender = _text(values.get("Nguoi_GioiTinh"))
    dan_toc = _text(values.get("Nguoi_DanToc"))
    id_date = _date(values.get("Nguoi_NgayCap"))
    issuer = _issuer(values.get("Nguoi_NoiCap"), values.get("Nguoi_NgayCap"))
    residence = _area(values.get("Nguoi_ThuongTru"))
    di_dong = _phone(values.get("Nguoi_DiDong"))
    email = _text(values.get("Nguoi_Email"))

    add("CongDan_tenCongDan", name)
    add("CongDan_ngaySinhCongDan", birthday)
    add("CongDan_gioiTinhCongDan", gender)
    add("CongDan_danTocCongDan", dan_toc)
    add("CongDan_soCmnd", identity)
    add("CongDan_soCCCD", identity)
    add("CongDan_ngayCapCmnd", id_date)
    add("CongDan_noiCapCmnd", issuer)
    add("CongDan_diDong", di_dong)
    add("CongDan_email", email)
    add("CongDan_maDMQuocGia", "Việt Nam")

    if residence:
        add("CongDan_maTinhThanh", _province_label(residence.get("tinh")))
        add("CongDan_maPhuongXa", _commune_label(residence.get("xa")))
        add("CongDan_diaChi", _text(residence.get("diaChi")))
        full = _full_address(residence)
        add("CongDan_noiOHienTai", full)
        add("CongDan_diaChiThuongTru", full)

    if not name or not identity:
        warnings.append("Thiếu họ tên hoặc số định danh người dự tuyển từ CCCD/Phiếu Mẫu 01.")
    return out, warnings
