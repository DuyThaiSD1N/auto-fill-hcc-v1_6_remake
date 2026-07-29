"""Map compact source facts → UI fields (section, mat-label) cho engine fill-liz.js.

Chủ điểm cá nhân → 1 người điền vào 3 section: Người nộp (II), Người được giải quyết (III),
Người đại diện pháp luật của hộ KD (IV). Hộ KD (IV) lấy từ Giấy phép kinh doanh.
Mỗi field emit {name=<mat-label>, comp, value, section=<group-header>}.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_gcn_diem_tro_choi_dien_tu.process.schema import (
    COMP_BY_UI,
    S_DN,
    S_GQ,
    S_NOP,
)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        return None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(xã|phường|thị trấn|tt\.?|tỉnh|thành phố|tp\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("Đ", "D").replace("đ", "d").lower().strip()


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
    # Giữ nguyên nhãn phường/xã (đã là tên MỚI theo Đơn/GPKD).
    return _text(value)


def _area(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    out = {
        "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    return out if any(out.values()) else None


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
    return normalize_date(m.group(0))


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or None


def _issuer(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    # Đơn 51a có thể ghi gọn "Bắc Ninh" → giữ nguyên; nếu là cụm "CỤC ... CẢNH SÁT" thì chuẩn hóa.
    if "canh sat" in _fold(text) or "cong an" in _fold(text):
        return normalize_issuer(text)
    return text


def _full_address(area: dict | None) -> str | None:
    if not area:
        return None
    parts = [_text(area.get("diaChi")), _commune_label(area.get("xa")), _province_label(area.get("tinh"))]
    return ", ".join(p for p in parts if p) or None


def _admin_select(area: dict | None) -> str | None:
    """Ô 'Địa chỉ hành chính' (mat-select) = 'Phường …, Tỉnh …' (option gộp phường+tỉnh)."""
    if not area:
        return None
    xa = _commune_label(area.get("xa"))
    tinh = _province_label(area.get("tinh"))
    if xa and tinh:
        return f"{xa}, {tinh}"
    return xa or tinh


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []

    def put(section: str, label: str, value) -> None:
        if value in (None, "", {}, []):
            return
        comp = COMP_BY_UI.get((section, label))
        if not comp:
            return
        out.append({"name": label, "comp": comp, "value": value, "section": section})

    # ---- Người (chủ điểm cá nhân) ----
    name = _text(values.get("Nguoi_HoTen"))
    identity = _identity(values.get("Nguoi_SoDinhDanh"))
    birthday = _date(values.get("Nguoi_NgaySinh"))
    id_date = _date(values.get("Nguoi_NgayCapCccd"))
    issuer = _issuer(values.get("Nguoi_NoiCapCccd"))
    phone = _phone(values.get("Nguoi_DienThoai"))
    residence = _area(values.get("Nguoi_ThuongTru"))
    res_detail = _text(residence.get("diaChi")) if residence else None
    admin = _admin_select(residence)
    full_res = _full_address(residence)

    # Phần II — Người nộp (Tên + CMND disabled/tự điền từ tài khoản → bỏ).
    put(S_NOP, "Ngày sinh", birthday)
    put(S_NOP, "Số điện thoại", phone)
    put(S_NOP, "Ngày cấp", id_date)
    put(S_NOP, "Nơi cấp", issuer)
    put(S_NOP, "Địa chỉ", res_detail)
    put(S_NOP, "Địa chỉ hành chính", admin)

    # Phần III — Người được giải quyết (trùng người nộp).
    put(S_GQ, "Tên người / Tên đơn vị được giải quyết", name)
    put(S_GQ, "Ngày sinh", birthday)
    put(S_GQ, "CMND/Hộ chiếu", identity)
    put(S_GQ, "Số điện thoại", phone)
    put(S_GQ, "Ngày cấp", id_date)
    put(S_GQ, "Nơi cấp", issuer)
    put(S_GQ, "Địa chỉ", res_detail)
    put(S_GQ, "Địa chỉ hành chính", admin)

    # ---- Hộ kinh doanh (Phần IV) ----
    truso = _area(values.get("HoKD_TruSo"))
    put(S_DN, "Mã số thuế", _identity(values.get("HoKD_MaSo")))
    put(S_DN, "Cơ quan cấp", _text(values.get("HoKD_CoQuanCap")))
    put(S_DN, "Đăng ký lần đầu", _date(values.get("HoKD_NgayDangKyLanDau")))
    put(S_DN, "Tên tiếng việt", _text(values.get("HoKD_TenTiengViet")))
    put(S_DN, "Điện thoại", _phone(values.get("HoKD_DienThoai")) or phone)
    if truso:
        put(S_DN, "Địa chỉ trụ sở - Tỉnh/TP", _province_label(truso.get("tinh")))
        put(S_DN, "Địa chỉ trụ sở - Xã", _commune_label(truso.get("xa")))
        put(S_DN, "Địa chỉ chi tiết trụ sở", _text(truso.get("diaChi")))
    # Người đại diện pháp luật = chủ điểm.
    put(S_DN, "Số CCCD người đại diện pháp luật", identity)
    put(S_DN, "Tên người đại diện pháp luật", name)
    put(S_DN, "Địa chỉ người đại diện pháp luật", full_res)

    if not name or not identity:
        warnings.append("Thiếu họ tên/số định danh chủ điểm từ CCCD hoặc Đơn 51a.")
    return out, warnings
