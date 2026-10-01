"""Map facts nguồn sang Form.io cổng tỉnh (xác nhận điều kiện diện tích nhà ở đăng ký thường trú, 1.013314)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import province_for_ward, province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date

from .schema import TEN_THU_TUC, UI_COMP_BY_NAME


def _by_name(fields: list[dict]) -> dict[str, Any]:
    return {item["name"]: item.get("value") for item in fields if item.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" ,;:.")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _identity(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", _text(value) or "")
    # Ô "Mã số định danh cá nhân" nhận số định danh 12 số; số CMND 9 số cũ (hay in trên Giấy chứng nhận)
    # không phải số định danh -> bỏ, thà để cán bộ nhập còn hơn điền sai.
    return digits if len(digits) == 12 else None


def _phone(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", (_text(value) or "").upper().replace("O", "0"))
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = re.fullmatch(r"\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})\s*", text)
    return normalize_date(match.group(0).replace("-", "/")) if match else None


def _area(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        # Bảng remap khớp tên tỉnh TRẦN: Giấy chứng nhận cũ ghi "tỉnh Kon Tum" phải bỏ tiền tố mới quy đổi được.
        "tinh": re.sub(r"^(tỉnh|thành phố|tp\.?)\s+", "", _text(value.get("tinh")) or "", flags=re.IGNORECASE),
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("chiTiet") or "",
    }
    if not any((area["tinh"], area["xa"], area["diaChi"])):
        return None
    area = remap_area(area) or area
    # Tờ khai Mẫu 02 hay chỉ có "Kính gửi: UBND <phường>" mà không ghi tỉnh -> suy tỉnh từ danh mục xã hiện hành.
    if not area.get("tinh") and area.get("xa"):
        found = province_for_ward(area["xa"])
        if found:
            area = {**area, "tinh": found[0], "xa": found[1]}
    return area


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    bare = re.sub(r"^(tỉnh|thành phố|tp\.?)\s+", "", text, flags=re.IGNORECASE).strip()
    return province_label(bare)


def _plot_note(values: dict[str, Any]) -> str | None:
    thua = _text(values.get("ThuaDat_So"))
    to = _text(values.get("ThuaDat_ToBanDo"))
    parts = []
    if thua:
        thua = re.sub(r"^(thửa( đất)?( số)?)\s*", "", thua, flags=re.IGNORECASE)
        parts.append(f"Thửa đất số {thua}")
    if to:
        to = re.sub(r"^(tờ( bản đồ)?( số)?)\s*", "", to, flags=re.IGNORECASE)
        parts.append(f"Tờ bản đồ số {to}")
    return ", ".join(parts) or None


def _residence_address(area: dict | None, plot_note: str | None) -> str | None:
    """Ô textarea data[diaChiThuaDat]: địa chỉ ĐẦY ĐỦ của chỗ ở (chi tiết, xã, tỉnh) + thửa/tờ bản đồ."""
    parts: list[str] = []
    if area:
        for key in ("diaChi", "xa"):
            text = _text(area.get(key))
            if text:
                parts.append(text)
        tinh = _province_label(area.get("tinh"))
        if tinh:
            parts.append(tinh)
    text = ", ".join(parts)
    if plot_note:
        text = f"{text} ({plot_note})" if text else plot_note
    return text or None


def _request_content(values: dict[str, Any]) -> str:
    """Tên thủ tục (portal điền sẵn) + nội dung mục III của Tờ khai nếu người dân có ghi."""
    details: list[str] = []
    status = _text(values.get("ToKhai_TinhTrangChoO"))
    if status:
        details.append(f"Tình trạng chỗ ở để đăng ký thường trú, tạm trú: {status}")
    people = _text(values.get("ToKhai_SoNguoiThueMuon"))
    if people:
        details.append(f"Tổng số người thuê, mượn, ở nhờ: {people}")
    area = _text(values.get("ToKhai_DienTichThueMuon"))
    if area:
        details.append(f"Tổng số diện tích chỗ ở hợp pháp thuê, mượn, ở nhờ: {area}")
    return f"{TEN_THU_TUC}. {'; '.join(details)}" if details else TEN_THU_TUC


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
    # Tên người nộp khác chủ hồ sơ => có ủy quyền (form không có checkbox "người nộp là chủ hồ sơ").
    authorized = bool(owner_name and applicant_name and _fold(owner_name) != _fold(applicant_name))

    # Panel "Thông tin chung" (ngày sinh, giới tính, số định danh, địa chỉ...) là của CHỦ HỒ SƠ; người nộp
    # chỉ có data[fullname] + data[phoneNumber1]. Không đổi nguồn sang NguoiNop_* khi có ủy quyền.
    owner_area = _area(values.get("ChuHoSo_NoiCuTru"))
    owner_id = _identity(values.get("ChuHoSo_SoDinhDanh")) or (
        None if authorized else _identity(values.get("NguoiNop_SoDinhDanh"))
    )

    add("data[ownerFullname]", owner_name)
    add("data[fullname]", applicant_name)
    add("data[birthday]", _date(values.get("ChuHoSo_NgaySinh")))
    add("data[gender]", _text(values.get("ChuHoSo_GioiTinh")))
    add("data[identityNumber]", owner_id)
    add("data[identityDate]", _date(values.get("ChuHoSo_NgayCap")))
    issuer = _text(values.get("ChuHoSo_NoiCap"))
    add("data[identityAgency]", normalize_issuer(issuer) if issuer else None)
    add("data[phoneNumber]", _phone(values.get("ChuHoSo_DienThoai")))
    add("data[email]", _text(values.get("ChuHoSo_Email")))
    # "Số điện thoại ủy quyền" chỉ có nghĩa khi người nộp KHÁC chủ hồ sơ.
    if authorized:
        add("data[phoneNumber1]", _phone(values.get("NguoiNop_DienThoai")))
    add("data[chonDoiTuong]", "Cá nhân", default=True)
    add("data[nation]", owner_area.get("quocGia") if owner_area else "Việt Nam", default=True)
    if owner_area:
        add("data[province]", _province_label(owner_area.get("tinh")))
        # Nhãn form là "Phường/xã" nhưng field-key là district (mô hình hành chính 2 cấp).
        add("data[district]", _text(owner_area.get("xa")))
        add("data[address]", _text(owner_area.get("diaChi")))
    add("data[noidungyeucaugiaiquyet]", _request_content(values))

    # Panel "Địa chỉ thửa đất/ địa chỉ xây dựng" = CHỖ Ở HỢP PHÁP đề nghị xác nhận. Chỉ phát từ nguồn riêng
    # ChoO_DiaChi (+ thửa/tờ trên Giấy chứng nhận), không mượn nơi cư trú của chủ hồ sơ.
    home_area = _area(values.get("ChoO_DiaChi"))
    plot_note = _plot_note(values)
    add("data[diaChiThuaDat]", _residence_address(home_area, plot_note))
    if home_area:
        add("data[province2]", _province_label(home_area.get("tinh")))
        add("data[village2]", _text(home_area.get("xa")))
        add("data[nation2]", home_area.get("quocGia") or "Việt Nam", default=True)

    return out, []
