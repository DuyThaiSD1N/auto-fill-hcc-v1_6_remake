"""Map facts nguồn sang Form.io cổng iGate Khánh Hòa (giao đất, cho thuê đất, chuyển mục đích sử dụng đất, 1.013949).

Cùng template ba khối với đăng ký đất đai lần đầu Khánh Hòa nên dùng lại các hàm chuẩn hóa của mapper đó:
- Phần I  người nộp  -> data[fullname]/phoneNumber/birthday/email/identityNumber/identityDate/identityAgency_text/
                         province/village/address + data[noidungyeucaugiaiquyet].
- Phần II chủ hồ sơ  -> data[chonDoiTuong]/owner*/province1/village1/ownerAddress.
- Phần III thửa đất  -> data[diaChiThuaDat] (chữ, theo GCN + "(nay là …)")/SoThuaDat/SoToBanDo/province2/village2/
                         nation2.
Người nộp khác tên chủ hồ sơ = có ủy quyền: mỗi khối chỉ dùng facts của đúng vai, không mượn chéo.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.mapper import (
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
)

from .schema import UI_COMP_BY_NAME

# "…, tỉnh E (nay là phường D)" -> "… (nay là phường D), tỉnh E": cụm "nay là" chú thích đơn vị cũ cấp xã/huyện, đặt
# sau tên tỉnh thì đọc như tỉnh đổi tên.
_TRAILING_NAY_LA = re.compile(r"^(.*?)(,\s*(?:tỉnh|thành phố)\s+[^,()]+?)\s*(\(\s*nay là[^()]*\))\s*\.?$", re.IGNORECASE)


def _parcel_text(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = _TRAILING_NAY_LA.match(text)
    return f"{match.group(1)} {match.group(3)}{match.group(2)}" if match else text


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
        # Chỉ có tỉnh mà thiếu cả phường/xã lẫn chi tiết thì nhiều khả năng là tỉnh đoán -> bỏ cả cụm.
        if not area or not (_text(area.get("xa")) or _text(area.get("diaChi"))):
            return
        add(province_name, _province(area))
        add(ward_name, _ward(area))
        add(address_name, _text(area.get("diaChi")))

    owner_name = _text(values.get("ChuHoSo_HoTen"))
    # Tên in trong giấy ủy quyền đứng trước NguoiNop_HoTen: người nộp hay ký tay trên Đơn, OCR chữ ký mất chữ.
    applicant_name = (
        _text(values.get("UyQuyen_HoTenNguoiDuocUyQuyen")) or _text(values.get("NguoiNop_HoTen")) or owner_name
    )
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
        warnings.append("Thiếu tên chủ hồ sơ (người đề nghị/người sử dụng đất).")

    # --- Phần I: người nộp ---
    add("data[fullname]", applicant_name)
    applicant_phone = _phone(applicant_val("DienThoai"))
    add("data[phoneNumber]", applicant_phone)
    if applicant_name and not applicant_phone:
        warnings.append("Số điện thoại người nộp là ô bắt buộc nhưng hồ sơ không ghi số của người nộp — cán bộ nhập tay.")
    add("data[birthday]", _date(applicant_val("NgaySinh")))
    add("data[email]", _text(applicant_val("Email")))
    add("data[identityNumber]", _identity(applicant_val("SoDinhDanh")))
    add("data[identityDate]", _date(applicant_val("NgayCap")))
    applicant_issuer = _text(applicant_val("NoiCap"))
    add("data[identityAgency_text]", normalize_issuer(applicant_issuer) if applicant_issuer else None)
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

    # --- Phần III: thửa đất — chỉ từ nguồn thửa đất, KHÔNG lấy nơi cư trú thay thế ---
    add("data[SoThuaDat]", _parcel_number(values.get("ThuaDat_SoThua")))
    so_to = _parcel_number(values.get("ThuaDat_SoTo"))
    add("data[SoToBanDo]", so_to)
    so_to_moi = _parcel_number(values.get("ThuaDat_SoToMoi"))
    if so_to and so_to_moi and so_to_moi != so_to:
        warnings.append(
            f"Đơn ghi tờ bản đồ mới số {so_to_moi}, Giấy chứng nhận ghi tờ số {so_to} — đã điền theo Giấy chứng nhận, "
            "cán bộ xác nhận số tờ dùng để nộp."
        )
    parcel_area = _area(values.get("ThuaDat_DiaChi"))
    parcel_ward = _ward(parcel_area) if parcel_area else None
    # Câu địa chỉ in trong giấy ủy quyền cùng nội dung GCN nhưng OCR rõ hơn bản quét GCN.
    full_address = _parcel_text(values.get("UyQuyen_DiaChiThuaDat")) or _parcel_text(values.get("ThuaDat_DiaChiDayDu"))
    if not full_address and parcel_area:
        full_address = ", ".join(part for part in (_text(parcel_area.get("diaChi")), parcel_ward) if part) or None
    add("data[diaChiThuaDat]", full_address)
    if parcel_area:
        add("data[province2]", _province(parcel_area))
        add("data[nation2]", parcel_area.get("quocGia") or "Việt Nam", default=True)
        add("data[village2]", parcel_ward)

    return out, warnings
