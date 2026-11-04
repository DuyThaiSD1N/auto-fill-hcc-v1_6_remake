"""Map facts nguồn sang Form.io cổng iGate Khánh Hòa (đăng ký đất đai, cấp GCN lần đầu, 1.013978).

Ba khối tách riêng (xem schema.py):
- Phần I  người nộp   -> data[fullname]/phoneNumber/birthday/email/identityNumber/identityDate/identityAgency_text/
                          province/village/address + data[noidungyeucaugiaiquyet].
- Phần II chủ hồ sơ   -> data[chonDoiTuong]/ownerFullname/ownerPhoneNumber/ownerBirthday/ownerEmail/
                          ownerIdentityNumber/ownerIdentityDate/ownerIdentityAgency/province1/village1/ownerAddress.
- Phần III thửa đất   -> data[diaChiThuaDat]/SoThuaDat/SoToBanDo/province2/village2/nation2.
Không có văn bản ủy quyền (tên người nộp trùng chủ hồ sơ) thì hai vai là MỘT người: thuộc tính thiếu ở vai này
được lấy từ vai kia. Có ủy quyền thì mỗi khối chỉ dùng facts của đúng vai, không mượn chéo.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import canonical_province, canonical_ward, province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date

from .schema import UI_COMP_BY_NAME

_ORG_MARKERS = ("cong ty", "doanh nghiep", "hop tac xa", "htx", "cty", "co phan", "tnhh", "co quan",
                "xi nghiep", "tap doan", "chi nhanh", "ngan hang")


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


def _identity(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", _text(value) or "")
    return digits or None


def _phone(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", (_text(value) or "").upper().replace("O", "0").replace("S", "5"))
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b", text)
    # Chỉ có NĂM sinh (hợp đồng cũ ghi "Sinh năm 19xx") -> bỏ trống, ô flatpickr nhận năm trơn sẽ ra ngày sai.
    return normalize_date(f"{match.group(1)}/{match.group(2)}/{match.group(3)}") if match else None


def _parcel_number(value: Any) -> str | None:
    """Số thửa/số tờ: bỏ chữ dẫn ("nay là tờ bản đồ số 99" -> "99") và mã mảnh trong ngoặc ("12 (123456-7-a)" -> "12")."""
    text = _text(value)
    if not text:
        return None
    text = re.sub(
        r"(?i)^.*?\b(thửa\s*đất\s*số|thửa\s*số|số\s*thửa|tờ\s*bản\s*đồ\s*số|tờ\s*số|số\s*tờ)\s*:?\s*", "", text
    )
    match = re.match(r"[^\s(,;]+", text)
    if not match:
        return None
    return match.group(0).strip(" .:-") or None


def _area(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("chiTietDuoiXa") or value.get("chiTiet") or "",
    }
    if not any((area["tinh"], area["xa"], area["diaChi"])):
        return None
    return remap_area(area, allow_diachi_fallback=True)


def _province(area: dict) -> str | None:
    tinh = _text(area.get("tinh"))
    if not tinh:
        return None
    return province_label(canonical_province(tinh) or tinh)


def _ward(area: dict) -> str | None:
    xa = _text(area.get("xa"))
    if not xa:
        return None
    return canonical_ward(area.get("tinh"), xa) or xa


def _is_to_chuc(loai: Any, name: Any) -> bool:
    folded = _fold(loai)
    if "to chuc" in folded:
        return True
    if "ca nhan" in folded:
        return False
    return any(marker in _fold(name) for marker in _ORG_MARKERS)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    del options
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
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

    def add_person_area(province_name: str, ward_name: str, address_name: str, area: dict | None) -> None:
        # Chỉ có tỉnh mà thiếu cả phường/xã lẫn chi tiết thì nhiều khả năng là tỉnh đoán (từ thửa đất, nơi cấp...)
        # chứ không phải nơi thường trú thật -> bỏ cả cụm.
        if not area or not (_text(area.get("xa")) or _text(area.get("diaChi"))):
            return
        add(province_name, _province(area))
        add(ward_name, _ward(area))
        add(address_name, _text(area.get("diaChi")))

    owner_name = _text(values.get("ChuHoSo_HoTen"))
    applicant_name = _text(values.get("NguoiNop_HoTen")) or owner_name
    authorized = bool(owner_name and applicant_name and _fold(owner_name) != _fold(applicant_name))

    def owner_val(key: str) -> Any:
        value = values.get(f"ChuHoSo_{key}")
        if value in (None, "", {}, []) and not authorized:
            value = values.get(f"NguoiNop_{key}")
        return value

    def applicant_val(key: str) -> Any:
        value = values.get(f"NguoiNop_{key}")
        if value in (None, "", {}, []) and not authorized:
            value = values.get(f"ChuHoSo_{key}")
        return value

    if not owner_name:
        warnings.append("Thiếu tên chủ hồ sơ (người sử dụng đất đứng Đơn đăng ký đất đai).")

    # --- Phần I: người nộp ---
    add("data[fullname]", applicant_name)
    add("data[phoneNumber]", _phone(applicant_val("DienThoai")))
    add("data[birthday]", _date(applicant_val("NgaySinh")))
    add("data[email]", _text(applicant_val("Email")))
    add("data[identityNumber]", _identity(applicant_val("SoDinhDanh")))
    add("data[identityDate]", _date(applicant_val("NgayCap")))
    applicant_issuer = _text(applicant_val("NoiCap"))
    add("data[identityAgency_text]", normalize_issuer(applicant_issuer) if applicant_issuer else None)
    # Tự nộp: địa chỉ CHỦ HỒ SƠ (đọc từ Đơn) đứng trước — NguoiNop_DiaChi hay bị LLM lấy từ CCCD/giấy tờ cũ.
    applicant_area = _area(applicant_val("DiaChi")) if authorized else (
        _area(values.get("ChuHoSo_DiaChi")) or _area(values.get("NguoiNop_DiaChi"))
    )
    add_person_area("data[province]", "data[village]", "data[address]", applicant_area)
    add("data[noidungyeucaugiaiquyet]", _text(values.get("Don_NoiDungDeNghi")))

    # --- Phần II: chủ hồ sơ ---
    if _is_to_chuc(values.get("ChuHoSo_LoaiChuThe"), owner_name):
        add("data[chonDoiTuong]", "Tổ chức")
    else:
        add("data[chonDoiTuong]", "Cá nhân", default=True)
    add("data[ownerFullname]", owner_name)
    add("data[ownerPhoneNumber]", _phone(owner_val("DienThoai")))
    add("data[ownerBirthday]", _date(owner_val("NgaySinh")))
    add("data[ownerEmail]", _text(owner_val("Email")))
    add("data[ownerIdentityNumber]", _identity(owner_val("SoDinhDanh")))
    add("data[ownerIdentityDate]", _date(owner_val("NgayCap")))
    owner_issuer = _text(owner_val("NoiCap"))
    add("data[ownerIdentityAgency]", normalize_issuer(owner_issuer) if owner_issuer else None)
    add_person_area("data[province1]", "data[village1]", "data[ownerAddress]", _area(owner_val("DiaChi")))

    # --- Phần III: thửa đất — chỉ từ nguồn thửa đất riêng, KHÔNG bao giờ lấy nơi cư trú thay thế ---
    add("data[SoThuaDat]", _parcel_number(values.get("ThuaDat_SoThua")))
    add("data[SoToBanDo]", _parcel_number(values.get("ThuaDat_SoTo")))
    parcel_area = _area(values.get("ThuaDat_DiaChi"))
    if parcel_area:
        parcel_ward = _ward(parcel_area)
        # Ô "Địa chỉ thửa đất/ địa chỉ xây dựng" là textarea: ghi chi tiết + phường/xã như dòng địa chỉ trên Đơn.
        detail = ", ".join(part for part in (_text(parcel_area.get("diaChi")), parcel_ward) if part)
        add("data[diaChiThuaDat]", detail or None)
        add("data[province2]", _province(parcel_area))
        add("data[nation2]", parcel_area.get("quocGia") or "Việt Nam", default=True)
        add("data[village2]", parcel_ward)

    return out, warnings
