"""Map facts → ô UI (section, mat-label) cho engine fill-liz.js — thông báo sản phẩm quảng cáo băng-rôn.

Mỗi field {name=<mat-label>, comp, value, section=<group-header>}; nhãn "Ngày cấp/Nơi cấp/Số điện thoại/
Email/Địa chỉ…" LẶP giữa khối người nộp và khối ủy quyền nên `section` là bắt buộc. Khối người nộp không
phát (cổng đổ sẵn từ tài khoản định danh).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.thong_bao_san_pham_quang_cao_bang_ron.process.schema import (
    COMP_BY_UI,
    S_TB,
    S_UQ,
    UY_QUYEN_CHECKBOX,
)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []) or isinstance(value, dict):
        return None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,")
    return text or None


def _one_line(value: Any) -> str | None:
    """Ô trên cổng là input MỘT dòng → các dòng liệt kê (số lượng từng địa bàn) nối bằng "; "."""
    if value in (None, "", {}, []) or isinstance(value, dict):
        return None
    lines = [" ".join(line.split()).strip(" ;,") for line in str(value).splitlines()]
    text = "; ".join(line for line in lines if line)
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(r"^(tỉnh|thành phố|tp\.?)\s+", "", text, flags=re.IGNORECASE).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    if _fold(text).startswith(("tinh ", "thanh pho ")):
        return text
    bare = _strip_admin_prefix(text)
    city = _fold(bare) in {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
    return f"{'Thành phố' if city else 'Tỉnh'} {bare}"


def _commune_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return text if _fold(text).startswith(("xa ", "phuong ", "thi tran ", "dac khu ")) else f"Xã {text}"


def _area(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    out = {
        "tinh": value.get("tinh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("chiTiet") or "",
    }
    if not any(out.values()):
        return None
    # Địa chỉ trước sáp nhập 2025 → đơn vị hiện hành mà danh sách "Địa chỉ hành chính" của cổng có.
    return remap_area(out) or out


def _admin_select(area: dict | None) -> str | None:
    """Ô 'Địa chỉ hành chính' (mat-select) gộp xã + tỉnh trong một option: 'Xã …, Tỉnh …'."""
    if not area:
        return None
    xa, tinh = _commune_label(area.get("xa")), _province_label(area.get("tinh"))
    return f"{xa}, {tinh}" if xa and tinh else None


def _digits(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _phone(value: Any) -> str | None:
    digits = _digits(value)
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _enterprise_code(value: Any) -> str | None:
    """Mã số doanh nghiệp 10 số (đơn vị phụ thuộc thêm "-xxx"); thiếu số thì KHÔNG điền."""
    match = re.fullmatch(r"(\d{10})(?:-?(\d{3}))?", re.sub(r"\s+", "", str(value or "")))
    if not match:
        return None
    return f"{match.group(1)}-{match.group(2)}" if match.group(2) else match.group(1)


def _date(value: Any) -> str | None:
    """Chỉ nhận ngày ĐỦ ngày/tháng/năm — tờ khai để trống "…/…/2026" thì bỏ, không ghép 01/01."""
    text = normalize_date(str(value)) if value else ""
    return text if text and re.fullmatch(r"\d{2}/\d{2}/\d{4}", text) else None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    del options
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []

    def put(section: str, label: str, value) -> None:
        if value in (None, "", {}, []):
            return
        comp = COMP_BY_UI.get((section, label))
        if comp:
            out.append({"name": label, "comp": comp, "value": value, "section": section})

    def warn_unreadable(label: str, raw: Any, parsed: Any) -> None:
        if raw not in (None, "") and not parsed:
            warnings.append(f"{label} đọc được \"{_text(raw)}\" nhưng không đủ chữ số — vui lòng nhập tay.")

    name = _text(values.get("DoanhNghiep_Ten"))
    code = _enterprise_code(values.get("DoanhNghiep_MaSo"))
    issuer = _text(values.get("DoanhNghiep_NoiCap"))
    phone = _phone(values.get("DoanhNghiep_DienThoai"))
    head_office = _area(values.get("DoanhNghiep_TruSo"))
    warn_unreadable("Mã số doanh nghiệp", values.get("DoanhNghiep_MaSo"), code)
    warn_unreadable("Điện thoại doanh nghiệp", values.get("DoanhNghiep_DienThoai"), phone)

    # ---- Khối ỦY QUYỀN = doanh nghiệp. Tích ô trước: cổng chỉ ghi nhận khối này khi đã tích. ----
    # Khối có 4 ô BẮT BUỘC; tích mà thiếu ô nào thì cổng báo đỏ và khoá nút nộp → chỉ tích khi đủ cả 4.
    detail_address = _text(head_office.get("diaChi")) if head_office else None
    required = {
        "Tên đơn vị ủy quyền": name,
        "Mã số doanh nghiệp": code,
        "Số điện thoại": phone,
        "Địa chỉ chi tiết": detail_address,
    }
    missing = [label for label, value in required.items() if not value]
    if not missing:
        out.append({"name": UY_QUYEN_CHECKBOX, "comp": "liz-checkbox", "value": True, "section": ""})
        put(S_UQ, "Tên người / Tên đơn vị ủy quyền", name)
        put(S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp", code)
        put(S_UQ, "Ngày cấp", _date(values.get("DoanhNghiep_NgayCap")))
        put(S_UQ, "Nơi cấp", issuer)
        put(S_UQ, "Số điện thoại", phone)
        put(S_UQ, "Email", _text(values.get("DoanhNghiep_Email")))
        put(S_UQ, "Địa chỉ hành chính", _admin_select(head_office))
        put(S_UQ, "Địa chỉ chi tiết", detail_address)
    else:
        warnings.append(
            "Không tích \"Thông tin người ủy quyền\" vì thiếu thông tin bắt buộc: " + ", ".join(missing)
            + " — cán bộ tự tích và nhập nếu hồ sơ có ủy quyền."
        )

    # ---- Khối THÔNG BÁO SẢN PHẨM QUẢNG CÁO (nội dung tờ khai Mẫu 01) ----
    put(S_TB, "Số GPKD", code)
    put(S_TB, "Nơi cấp GPKD", issuer)
    put(S_TB, "Nội dung trên bảng quảng cáo, băng-rôn", _one_line(values.get("ThongBao_NoiDung")))
    put(S_TB, "Địa điểm thực hiện", _one_line(values.get("ThongBao_DiaDiem")))
    tu_ngay = _date(values.get("ThongBao_TuNgay"))
    den_ngay = _date(values.get("ThongBao_DenNgay"))
    put(S_TB, "Từ ngày thực hiện", tu_ngay)
    put(S_TB, "Đến ngày thực hiện", den_ngay)
    put(S_TB, "Số lượng", _one_line(values.get("ThongBao_SoLuong")))
    put(S_TB, "Phương án tháo dỡ (nếu có)", _one_line(values.get("ThongBao_PhuongAnThaoDo")))
    if not tu_ngay or not den_ngay:
        warnings.append("Tờ khai chưa ghi đủ thời gian thực hiện (mục 4) — vui lòng nhập tay Từ ngày / Đến ngày.")

    return out, warnings
