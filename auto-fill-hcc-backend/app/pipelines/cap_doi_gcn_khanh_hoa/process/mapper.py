"""Map facts nguồn sang Form.io cổng iGate Khánh Hòa (cấp đổi Giấy chứng nhận, 1.012783).

Cùng template ba khối với đăng ký đất đai lần đầu Khánh Hòa nên dùng lại các hàm chuẩn hóa của mapper đó:
- Phần I  người nộp  -> data[fullname]/phoneNumber/birthday/email/identityNumber/identityDate/identityAgency_text/
                         province/village/address + data[noidungyeucaugiaiquyet] (Đơn mục 2 "Nội dung biến động").
- Phần II chủ hồ sơ  -> data[chonDoiTuong]/owner*/province1/village1/ownerAddress.
- Phần III thửa đất  -> data[diaChiThuaDat] (nguyên văn GCN)/SoThuaDat/SoToBanDo/province2/village2/nation2.
Người nộp khác tên chủ hồ sơ = có ủy quyền: mỗi khối chỉ dùng facts của đúng vai, không mượn chéo.

Ô giấy tờ không có dữ liệu thì TRẢ VỀ TRỐNG (clear, ô bắt buộc tô đỏ + nhắc trong cảnh báo), không bỏ qua: Phần I cổng
đổ sẵn theo tài khoản đăng nhập, sai người khi cán bộ nộp thay. Chỉ giữ Phần I của cổng khi formContext cho thấy tài khoản
chính là người nộp (cùng số định danh) — finish_blank_fields. Ô chọn Tỉnh/Phường-xã không xoá (xem clear_blank_fields).
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.area_remap import canonical_ward
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.mapper import (
    BLANK_PART_ONE,
    _area,
    _by_name,
    _date,
    _fold,
    _identity,
    _is_to_chuc,
    _parcel_number,
    _phone,
    _province,
    _text,
    _ward,
    account_is_applicant,
    clear_blank_fields,
)

from .schema import UI_COMP_BY_NAME

PORTAL_PROVINCE = "Khánh Hòa"
DEFAULT_REQUEST = "Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất"

# Ô bắt buộc (dấu required trên form) -> nhãn nhắc cán bộ khi giấy tờ không có.
_REQUIRED_LABELS = {
    "data[fullname]": "Họ tên người nộp",
    "data[phoneNumber]": "Số điện thoại người nộp",
    "data[birthday]": "Ngày sinh người nộp",
    "data[identityNumber]": "CMND/CCCD người nộp",
    "data[ownerFullname]": "Họ tên chủ hồ sơ",
    "data[ownerPhoneNumber]": "Số điện thoại chủ hồ sơ",
    "data[ownerBirthday]": "Ngày sinh chủ hồ sơ",
    "data[ownerIdentityNumber]": "CMND/CCCD chủ hồ sơ",
    "data[village2]": "Phường/xã của thửa đất",
}


def finish_blank_fields(out: list[dict], seen: set[str], warnings: list[str], options: dict | None,
                        applicant_identity: Any) -> None:
    """Nhắc ô bắt buộc giấy tờ không có, rồi trả mọi ô chữ/ngày còn thiếu của ba khối về TRỐNG (clear_blank_fields của
    mapper gốc Khánh Hòa; ô bắt buộc tô đỏ). Tài khoản chính là người nộp thì Phần I giữ giá trị cổng, không nhắc."""
    keep_part_one = account_is_applicant(options, applicant_identity)
    missing = [label for name, label in _REQUIRED_LABELS.items()
               if name not in seen and not (keep_part_one and name in BLANK_PART_ONE)]
    if missing:
        warnings.append("Ô bắt buộc chưa có trong giấy tờ: " + "; ".join(missing) + " — đã để trống, cán bộ nhập tay.")
    clear_blank_fields(out, seen, options, applicant_identity)


def _phone_vn(value: Any) -> tuple[str | None, str | None]:
    """(số hợp lệ, số bị loại). Di động Việt Nam đúng 10 chữ số; 11 chữ số chỉ hợp lệ với máy bàn đầu 02 — số di động
    dư chữ số là OCR đọc sai chữ viết tay (vd "090.7096679" thành "09070966912"), điền vào là sai số người dân."""
    digits = _phone(value)
    if digits and len(digits) == 11 and not digits.startswith("02"):
        return None, digits
    return digits, None


def phone_warning(rejected: set[str]) -> list[str]:
    return [f"Số điện thoại đọc được '{number}' không hợp lệ (di động phải đủ 10 chữ số) — có thể đọc sai chữ viết tay, "
            "cán bộ nhập lại." for number in sorted(rejected)]


def _date_loose(value: Any) -> str | None:
    """Ngày viết tay có khoảng trắng quanh dấu ngăn ("1 - 2 - 1985") -> dd/mm/yyyy; chỉ có năm -> None."""
    text = _text(value)
    return _date(re.sub(r"\s*([/.-])\s*", r"\1", text)) if text else None


def _person_area(value: Any, fallback_provinces: tuple[str | None, ...]) -> dict | None:
    """Địa chỉ người; Đơn chỉ ghi "tổ/thôn, phường X" mà thiếu tỉnh thì thử tỉnh của thửa đất rồi tỉnh của cổng —
    chỉ nhận khi phường/xã thật sự thuộc tỉnh đó (canonical_ward), không thì giữ nguyên để không gán tỉnh sai."""
    area = _area(value)
    if not area or _text(area.get("tinh")) or not _text(area.get("xa")) or not isinstance(value, dict):
        return area
    for tinh in fallback_provinces:
        if not tinh:
            continue
        candidate = _area({**value, "tinh": tinh})
        if candidate and canonical_ward(candidate.get("tinh"), candidate.get("xa")):
            return candidate
    return area


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
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

    def add_person_area(province_name: str, ward_name: str, address_name: str, area: dict | None, who: str) -> None:
        # Chỉ có tỉnh mà thiếu cả phường/xã lẫn chi tiết thì nhiều khả năng là tỉnh đoán -> bỏ cả cụm.
        if not area or not (_text(area.get("xa")) or _text(area.get("diaChi"))):
            return
        add(province_name, _province(area))
        ward = _ward(area)
        add(ward_name, ward)
        add(address_name, _text(area.get("diaChi")))
        tinh = _text(area.get("tinh"))
        if ward and tinh and not canonical_ward(tinh, ward):
            warnings.append(f"Phường/xã '{ward}' ({who}) không có trong danh mục {_province(area)} — cán bộ chọn lại.")

    parcel_area = _area(values.get("ThuaDat_DiaChi"))
    fallback_provinces = ((parcel_area or {}).get("tinh"), PORTAL_PROVINCE)

    owner_name = _text(values.get("ChuHoSo_HoTen"))
    applicant_name = _text(values.get("NguoiNop_HoTen")) or owner_name
    authorized = bool(owner_name and applicant_name and _fold(owner_name) != _fold(applicant_name))
    if not authorized and owner_name:
        applicant_name = owner_name  # cùng một người: hai khối ghi tên giống hệt nhau (LLM hay trả hai kiểu hoa/thường)

    def owner_val(key: str) -> Any:
        value = values.get(f"ChuHoSo_{key}")
        if value in (None, "", {}, []) and not authorized:
            value = values.get(f"NguoiNop_{key}")
        return value

    def applicant_val(key: str) -> Any:
        if not authorized:
            return owner_val(key)  # cùng một người: hai khối lấy đúng một nguồn, ghi giống hệt nhau
        return values.get(f"NguoiNop_{key}")

    rejected_phones: set[str] = set()

    def phone(value: Any) -> str | None:
        number, rejected = _phone_vn(value)
        if rejected:
            rejected_phones.add(rejected)
        return number

    # --- Phần I: người nộp ---
    add("data[fullname]", applicant_name)
    add("data[phoneNumber]", phone(applicant_val("DienThoai")))
    add("data[birthday]", _date_loose(applicant_val("NgaySinh")))
    add("data[email]", _text(applicant_val("Email")))
    add("data[identityNumber]", _identity(applicant_val("SoDinhDanh")))
    add("data[identityDate]", _date_loose(applicant_val("NgayCap")))
    applicant_issuer = _text(applicant_val("NoiCap"))
    add("data[identityAgency_text]", normalize_issuer(applicant_issuer) if applicant_issuer else None)
    applicant_area = _person_area(applicant_val("DiaChi"), fallback_provinces)
    add_person_area("data[province]", "data[village]", "data[address]", applicant_area, "người nộp")
    request = _text(values.get("Don_NoiDungBienDong"))
    if request:
        add("data[noidungyeucaugiaiquyet]", request)
    else:
        serial = _text(values.get("GCN_SoPhatHanh"))
        add("data[noidungyeucaugiaiquyet]", f"{DEFAULT_REQUEST} số phát hành {serial}" if serial else DEFAULT_REQUEST,
            default=True)

    # --- Phần II: chủ hồ sơ ---
    if _is_to_chuc(values.get("ChuHoSo_LoaiChuThe"), owner_name):
        add("data[chonDoiTuong]", "Tổ chức")
    else:
        add("data[chonDoiTuong]", "Cá nhân", default=True)
    add("data[ownerFullname]", owner_name)
    add("data[ownerPhoneNumber]", phone(owner_val("DienThoai")))
    add("data[ownerBirthday]", _date_loose(owner_val("NgaySinh")))
    add("data[ownerEmail]", _text(owner_val("Email")))
    add("data[ownerIdentityNumber]", _identity(owner_val("SoDinhDanh")))
    add("data[ownerIdentityDate]", _date_loose(owner_val("NgayCap")))
    owner_issuer = _text(owner_val("NoiCap"))
    add("data[ownerIdentityAgency]", normalize_issuer(owner_issuer) if owner_issuer else None)
    add_person_area("data[province1]", "data[village1]", "data[ownerAddress]",
                    _person_area(owner_val("DiaChi"), fallback_provinces), "chủ hồ sơ")
    co_users = _text(values.get("ChuHoSo_NguoiCungSuDung"))
    if owner_name and co_users and _fold(co_users) != _fold(owner_name):
        warnings.append(
            f"Giấy tờ ghi người cùng sử dụng đất: {co_users}. Form chỉ có một chủ hồ sơ — đã điền {owner_name}; cán "
            "bộ kiểm tra lại."
        )

    # --- Phần III: thửa đất — chỉ từ nguồn thửa đất, KHÔNG lấy nơi cư trú thay thế ---
    add("data[SoThuaDat]", _parcel_number(values.get("ThuaDat_SoThua")))
    add("data[SoToBanDo]", _parcel_number(values.get("ThuaDat_SoTo")))
    parcel_ward = _ward(parcel_area) if parcel_area else None
    full_address = _text(values.get("ThuaDat_DiaChiDayDu"))
    if not full_address and parcel_area:
        full_address = ", ".join(part for part in (_text(parcel_area.get("diaChi")), parcel_ward) if part) or None
    add("data[diaChiThuaDat]", full_address)
    if parcel_area:
        add("data[province2]", _province(parcel_area))
        add("data[nation2]", parcel_area.get("quocGia") or "Việt Nam", default=True)
        add("data[village2]", parcel_ward)

    warnings.extend(phone_warning(rejected_phones))
    if not owner_name:
        warnings.append("Thiếu tên chủ hồ sơ (người sử dụng đất hiện tại).")
    finish_blank_fields(out, seen, warnings, options, applicant_val("SoDinhDanh"))
    return out, warnings
