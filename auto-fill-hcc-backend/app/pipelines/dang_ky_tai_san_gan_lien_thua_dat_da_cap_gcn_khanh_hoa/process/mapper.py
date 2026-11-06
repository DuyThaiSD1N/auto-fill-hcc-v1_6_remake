"""Map facts nguồn sang Form.io cổng iGate Khánh Hòa (đăng ký tài sản gắn liền với thửa đất đã cấp GCN, 1.013995).

Cùng template ba khối với cấp đổi GCN / đăng ký biến động Khánh Hòa nên dùng lại các hàm chuẩn hóa của các mapper đó:
- Phần I  người nộp  -> data[fullname]/phoneNumber/birthday/email/identityNumber/identityDate/identityAgency_text/
                         province/village/address + data[noidungyeucaugiaiquyet] (nguyên văn Đơn mục "Nội dung biến động").
- Phần II chủ hồ sơ  -> data[chonDoiTuong]/owner*/province1/village1/ownerAddress — người thứ nhất đứng Đơn; người cùng
                         đứng tên chỉ nhắc trong cảnh báo (form có một chủ hồ sơ).
- Phần III thửa đất  -> data[diaChiThuaDat] (địa danh mới: tờ khai LPTB rồi GCN)/SoThuaDat/SoToBanDo/province2/village2/
                         nation2.
Không có Đơn ghi nội dung thì điền câu mặc định theo trường hợp giải quyết công dân đã chọn trên cổng (trợ lý truyền
options.truongHop = "thay_doi" cho quy trình 1.013995-2.x "đăng ký thay đổi về tài sản").
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.area_remap import canonical_ward
from app.pipelines.cap_doi_gcn_khanh_hoa.process.mapper import (
    PORTAL_PROVINCE,
    _date_loose,
    _person_area,
    _phone_vn,
    finish_blank_fields,
    phone_warning,
)
from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_khanh_hoa.process.mapper import _issued
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

DEFAULT_REQUEST = "Đăng ký bổ sung tài sản gắn liền với đất"
DEFAULT_REQUEST_THAY_DOI = "Đăng ký thay đổi về tài sản gắn liền với đất so với nội dung đã đăng ký"


_ITEM_START = re.compile(r"^(?:[-–+•*]|\d+(?:\.\d+)*[.)])\s*")


def _multiline(value: Any) -> str | None:
    """Ô textarea "Nội dung yêu cầu giải quyết": giữ xuống dòng trước mỗi dòng gạch đầu dòng/đánh số của Đơn (liệt kê giấy
    tờ), còn dòng bị ngắt giữa câu do khổ giấy ("… ngày\\n18/6/2026") thì nối lại bằng dấu cách."""
    if not isinstance(value, str):
        return _text(value)
    out: list[str] = []
    for line in (" ".join(raw.split()) for raw in value.splitlines()):
        if not line:
            continue
        if out and not _ITEM_START.match(line):
            out[-1] = f"{out[-1]} {line}"
        else:
            out.append(line)
    return "\n".join(out) or None


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
    request = _multiline(values.get("Don_NoiDungBienDong"))
    if request:
        add("data[noidungyeucaugiaiquyet]", request)
    else:
        thay_doi = (options or {}).get("truongHop") == "thay_doi"
        add("data[noidungyeucaugiaiquyet]", DEFAULT_REQUEST_THAY_DOI if thay_doi else DEFAULT_REQUEST, default=True)

    # --- Phần II: chủ hồ sơ (người thứ nhất đứng Đơn) ---
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
            f"Hồ sơ có người cùng đứng tên: {co_users}. Form chỉ có một chủ hồ sơ — đã điền {owner_name}; cán bộ kiểm "
            "tra lại."
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
        warnings.append("Thiếu tên chủ hồ sơ (người đứng Đơn đăng ký biến động).")
    finish_blank_fields(out, seen, warnings, options, applicant_val("SoDinhDanh"))
    return out, warnings
