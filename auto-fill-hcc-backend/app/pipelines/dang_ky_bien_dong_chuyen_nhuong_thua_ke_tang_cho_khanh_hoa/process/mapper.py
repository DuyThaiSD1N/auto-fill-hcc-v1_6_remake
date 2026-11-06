"""Map facts nguồn sang Form.io cổng iGate Khánh Hòa (đăng ký biến động chuyển nhượng, thừa kế, tặng cho, 1.013831).

Cùng template ba khối với cấp đổi GCN Khánh Hòa nên dùng lại các hàm chuẩn hóa của mapper đó:
- Phần I  người nộp  -> data[fullname]/phoneNumber/birthday/email/identityNumber/identityDate/identityAgency_text/
                         province/village/address + data[noidungyeucaugiaiquyet] (nguyên văn Đơn mục II).
- Phần II chủ hồ sơ  -> data[chonDoiTuong]/owner*/province1/village1/ownerAddress — chủ hồ sơ là BÊN NHẬN chuyển quyền.
- Phần III thửa đất  -> data[diaChiThuaDat] (địa danh hiện hành)/SoThuaDat/SoToBanDo/province2/village2/nation2.
Số thửa/số tờ sau đo đạc chỉnh lý ghi kèm số cũ theo cách tờ khai thuế ghi: "1016 (257 cũ)".
Thẻ căn cước cấp từ 01/07/2024 do Bộ Công an cấp: ngày cấp từ mốc đó thì nơi cấp là "Bộ Công an" — văn bản công chứng/
quyết định hay chép tên cơ quan cấp thẻ CCCD cũ kèm ngày cấp thẻ mới.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.area_remap import canonical_ward
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines.cap_doi_gcn_khanh_hoa.process.mapper import (
    PORTAL_PROVINCE,
    _date_loose,
    _person_area,
    _phone_vn,
    finish_blank_fields,
    phone_warning,
)
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.mapper import (
    _area,
    _by_name,
    _fold,
    _identity,
    _is_to_chuc,
    _parcel_number,
    _province,
    _text,
    _ward,
)

from .schema import UI_COMP_BY_NAME

DEFAULT_REQUEST = "Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất"
CAN_CUOC_ISSUER = "Bộ Công an"
_CAN_CUOC_FROM = (2024, 7, 1)


def _issued(date_value: Any, issuer_value: Any) -> tuple[str | None, str | None]:
    """(ngày cấp, nơi cấp) của giấy tờ tùy thân; thẻ căn cước (từ 01/07/2024) luôn do Bộ Công an cấp."""
    date = _date_loose(date_value)
    if date:
        day, month, year = (int(part) for part in date.split("/"))
        if (year, month, day) >= _CAN_CUOC_FROM:
            return date, CAN_CUOC_ISSUER
    issuer = _text(issuer_value)
    return date, normalize_issuer(issuer) if issuer else None


_REQUEST_THUA = re.compile(r"(thửa\s+đất\s+số\s*:?\s*)(\d+)", re.IGNORECASE)
# OCR chữ viết tay hay đọc "tờ" thành "đồ" và dính mã mảnh vào số: "đồ bản đồ Số 150123456-A-A)".
_REQUEST_TO = re.compile(r"((?:tờ|đồ)\s+bản\s+đồ\s+số\s*:?\s*)(\d[0-9A-Za-z.\-]*(?:\s*\([^)]*\))?\)?)", re.IGNORECASE)


def _fix_request_numbers(request: str, values: dict) -> tuple[str, str | None]:
    """Câu nội dung biến động chép nguyên văn từ Đơn viết tay: số thửa/số tờ OCR đọc lệch (không trùng số hiện hành lẫn
    số cũ in trên giấy tờ) -> thay bằng số cũ (Đơn nhắc thửa theo Giấy chứng nhận), số tờ kèm mã mảnh nếu có. Trả
    (câu, cảnh báo)."""
    notes: list[str] = []
    for label, pattern, current_key, old_key, keep_code in (
        # Số thửa chỉ thay chữ số ("(trích một phần)" phía sau giữ nguyên); số tờ thay cả cụm dính mã mảnh.
        ("số thửa", _REQUEST_THUA, "ThuaDat_SoThua", "ThuaDat_SoThuaCu", False),
        ("số tờ", _REQUEST_TO, "ThuaDat_SoTo", "ThuaDat_SoToCu", True),
    ):
        current, old = _parcel_number(values.get(current_key)), _parcel_number(values.get(old_key))
        target = old or current
        match = pattern.search(request)
        if not target or not match or re.match(r"\d+", match.group(2)).group(0) in {current, old}:
            continue
        old_text = _text(values.get(old_key)) if old and keep_code else None
        replacement = old_text if old_text and _parcel_number(old_text) == target else target
        prefix = match.group(1)
        if prefix[:2].lower() == "đồ":
            prefix = "tờ" + prefix[2:]
        request = request[:match.start()] + prefix + replacement + request[match.end():]
        notes.append(f"{label} đọc là '{match.group(2).strip()}' -> '{replacement}'")
    if not notes:
        return request, None
    return request, ("Nội dung biến động: chữ viết tay đọc lệch, đã sửa theo giấy tờ in — " + "; ".join(notes)
                     + ". Cán bộ đối chiếu Đơn.")


def _parcel_with_old(current: Any, old: Any) -> str | None:
    """Số thửa/số tờ hiện hành, kèm số cũ khi khác: "1016 (257 cũ)"."""
    now, before = _parcel_number(current), _parcel_number(old)
    if now and before and now != before:
        return f"{now} ({before} cũ)"
    return now or before


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
        applicant_name = owner_name  # cùng một người: hai khối ghi tên giống hệt nhau

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
    applicant_date, applicant_issuer = _issued(applicant_val("NgayCap"), applicant_val("NoiCap"))
    add("data[identityDate]", applicant_date)
    add("data[identityAgency_text]", applicant_issuer)
    add_person_area("data[province]", "data[village]", "data[address]",
                    _person_area(applicant_val("DiaChi"), fallback_provinces), "người nộp")
    request = _text(values.get("Don_NoiDungBienDong"))
    if request:
        request, request_warning = _fix_request_numbers(request, values)
        if request_warning:
            warnings.append(request_warning)
        add("data[noidungyeucaugiaiquyet]", request)
    else:
        add("data[noidungyeucaugiaiquyet]", DEFAULT_REQUEST, default=True)

    # --- Phần II: chủ hồ sơ (bên nhận chuyển quyền) ---
    if _is_to_chuc(values.get("ChuHoSo_LoaiChuThe"), owner_name):
        add("data[chonDoiTuong]", "Tổ chức")
    else:
        add("data[chonDoiTuong]", "Cá nhân", default=True)
    add("data[ownerFullname]", owner_name)
    add("data[ownerPhoneNumber]", phone(owner_val("DienThoai")))
    add("data[ownerBirthday]", _date_loose(owner_val("NgaySinh")))
    add("data[ownerEmail]", _text(owner_val("Email")))
    add("data[ownerIdentityNumber]", _identity(owner_val("SoDinhDanh")))
    owner_date, owner_issuer = _issued(owner_val("NgayCap"), owner_val("NoiCap"))
    add("data[ownerIdentityDate]", owner_date)
    add("data[ownerIdentityAgency]", owner_issuer)
    add_person_area("data[province1]", "data[village1]", "data[ownerAddress]",
                    _person_area(owner_val("DiaChi"), fallback_provinces), "chủ hồ sơ")
    co_users = _text(values.get("ChuHoSo_NguoiCungSuDung"))
    if owner_name and co_users and _fold(co_users) != _fold(owner_name):
        warnings.append(
            f"Giấy tờ ghi người cùng nhận chuyển quyền: {co_users}. Form chỉ có một chủ hồ sơ — đã điền {owner_name}; "
            "cán bộ kiểm tra lại."
        )

    # --- Phần III: thửa đất — chỉ từ nguồn thửa đất, KHÔNG lấy nơi cư trú thay thế ---
    add("data[SoThuaDat]", _parcel_with_old(values.get("ThuaDat_SoThua"), values.get("ThuaDat_SoThuaCu")))
    add("data[SoToBanDo]", _parcel_with_old(values.get("ThuaDat_SoTo"), values.get("ThuaDat_SoToCu")))
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
        warnings.append("Thiếu tên chủ hồ sơ (bên nhận chuyển nhượng/tặng cho/thừa kế).")
    finish_blank_fields(out, seen, warnings, options, applicant_val("SoDinhDanh"))
    return out, warnings
