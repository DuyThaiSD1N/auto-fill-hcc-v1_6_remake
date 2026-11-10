"""Map facts nguồn sang Form.io cổng iGate Khánh Hòa (đính chính Giấy chứng nhận đã cấp, 1.012790).

Cùng template ba khối với cấp đổi GCN Khánh Hòa nên dùng lại các hàm chuẩn hóa + finish_blank_fields của mapper đó:
- Phần I  người nộp  -> data[fullname]/phoneNumber/birthday/email/identityNumber/identityDate/identityAgency_text/
                         province/village/address + data[noidungyeucaugiaiquyet] (NGUYÊN VĂN Đơn mục 2, giữ xuống dòng).
- Phần II chủ hồ sơ  -> data[chonDoiTuong]/owner*/province1/village1/ownerAddress.
- Phần III thửa đất  -> data[diaChiThuaDat] (địa chỉ thửa đất ở Đơn mục 2, không có mới lấy GCN)/SoThuaDat/SoToBanDo/
                         province2/village2/nation2.
Người nộp khác tên chủ hồ sơ = có ủy quyền: mỗi khối chỉ dùng facts của đúng vai, không mượn chéo. Ô giấy tờ không có dữ
liệu thì TRẢ VỀ TRỐNG như cấp đổi (Phần I cổng đổ sẵn theo tài khoản đăng nhập).

Thêm so với cấp đổi: người in trên Giấy chứng nhận (GCN_NguoiSuDung) khác hẳn chủ hồ sơ ở Đơn mà Đơn mục 2 không nhắc tên
đó (không phải đính chính tên) -> cảnh báo Đơn và GCN có thể không cùng một hồ sơ.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines.cap_doi_gcn_khanh_hoa.process.mapper import (
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
from app.pipelines._shared.area_remap import canonical_ward

from .schema import UI_COMP_BY_NAME

PORTAL_PROVINCE = "Khánh Hòa"
DEFAULT_REQUEST = "Đính chính Giấy chứng nhận đã cấp"
_HONORIFIC = re.compile(r"^\s*(?:hộ\s+)?(?:(?:vợ|chồng)\s+là\s+)?(?:ông|bà|anh|chị)\s*:?\s+", re.IGNORECASE)
# "Ông A và vợ là bà B", "Hộ ông: A; bà: B" -> từng người.
_PERSON_SEP = re.compile(r"\s*(?:;|,|\bvà\b)\s*", re.IGNORECASE)


def _multiline(value: Any) -> str | None:
    """Nội dung Đơn mục 2 vào textarea: giữ xuống dòng giữa các đoạn ("- Thay đổi …"), gộp khoảng trắng trong dòng."""
    if value in (None, "", {}, []):
        return None
    lines = [" ".join(line.split()) for line in str(value).splitlines()]
    text = "\n".join(line for line in lines if line).strip(" ,;:")
    return text or None


def _people(value: Any) -> list[str]:
    names = (_fold(_HONORIFIC.sub("", part)) for part in _PERSON_SEP.split(_text(value) or ""))
    return [name for name in names if name]


def gcn_owner_warning(gcn_name: Any, owner_name: str | None, co_users: str | None, request: str | None) -> list[str]:
    """Không người nào in trên GCN là chủ hồ sơ / người cùng sử dụng, Đơn mục 2 cũng không nhắc tên họ (không phải đính
    chính tên) -> nhiều khả năng Đơn và GCN thuộc hai hồ sơ khác nhau."""
    gcn = _people(gcn_name)
    if not gcn or not owner_name:
        return []
    known = set(_people(owner_name)) | set(_people(co_users))
    folded_request = _fold(request or "")
    if any(name in known or name in folded_request for name in gcn):
        return []
    return [f"Giấy chứng nhận ghi người sử dụng đất '{_text(gcn_name)}' nhưng Đơn ghi '{owner_name}' — kiểm tra Đơn và "
            "Giấy chứng nhận có cùng một hồ sơ không trước khi nộp."]


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
    add("data[identityDate]", _date_loose(applicant_val("NgayCap")))
    applicant_issuer = _text(applicant_val("NoiCap"))
    add("data[identityAgency_text]", normalize_issuer(applicant_issuer) if applicant_issuer else None)
    add_person_area("data[province]", "data[village]", "data[address]",
                    _person_area(applicant_val("DiaChi"), fallback_provinces), "người nộp")
    request = _multiline(values.get("Don_NoiDungBienDong"))
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
            f"Giấy tờ ghi người cùng sử dụng đất: {co_users}. Form chỉ có một chủ hồ sơ — đã điền {owner_name}; người "
            "còn lại có trong Nội dung yêu cầu giải quyết, cán bộ kiểm tra lại."
        )
    warnings.extend(gcn_owner_warning(values.get("GCN_NguoiSuDung"), owner_name, co_users, request))

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
        warnings.append("Thiếu tên chủ hồ sơ (người sử dụng đất đề nghị đính chính).")
    finish_blank_fields(out, seen, warnings, options, applicant_val("SoDinhDanh"))
    return out, warnings
