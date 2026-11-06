"""Map facts nguồn sang Form.io cổng iGate Khánh Hòa (xác nhận tiếp tục sử dụng đất nông nghiệp, 1.013947).

Cùng template ba khối với các thủ tục đất đai Khánh Hòa nên dùng lại helper của mapper gốc / cấp đổi GCN / biến động.
Phân vai theo file mapping: Phần I người nộp = người THỨ NHẤT đứng Đơn (có văn bản ủy quyền thì bên được ủy quyền), Phần
II chủ hồ sơ = người THỨ HAI (Đơn một người thì chính người đó). Điện thoại + địa chỉ liên hệ ở Đơn mục 2 dùng chung cho
người đứng Đơn (địa danh mới, đứng trước nơi thường trú cũ in trên GCN). Số thửa/tờ theo GCN; số mới của Phiếu đo đạc chỉ
cảnh báo. Ô giấy tờ không có dữ liệu thì trả về TRỐNG (finish_blank_fields).
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
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

DEFAULT_REQUEST = "Xác nhận lại thời hạn sử dụng đất nông nghiệp"
_REQUEST_PREFIX = "Xác nhận lại thời hạn sử dụng đất"
# Số định danh 12 chữ số chỉ có từ 2012 (CMND 12 số, rồi CCCD): ngày cấp trước mốc này là của CMND 9 số cũ in trên GCN.
_ID12_FROM_YEAR = 2012
# Tên đường viết tay đọc lệch vẫn giống tên in từ mức này ("le hong thang" / "le hong phong" ≈ 0.85).
_SAME_STREET_RATIO = 0.75


def _request(value: Any) -> str | None:
    """Đơn mục 4 thường chỉ ghi phần đuôi ("…đến ngày 15 tháng 10 năm 2063…", dấu chấm lửng in sẵn của mẫu) → bỏ dấu
    chấm lửng, ghép tên việc phía trước như file mapping."""
    text = (_text(value) or "").lstrip(" .…:-–")
    if not text:
        return None
    if _fold(text).startswith("den ngay"):
        return f"{_REQUEST_PREFIX} {text[0].lower()}{text[1:]}"
    return text


def _same_address(handwritten: dict, printed: dict) -> bool:
    """Địa chỉ liên hệ viết tay trên Đơn và địa chỉ in (thửa đất) là MỘT địa chỉ: cùng số nhà (một bên có thể dư/thiếu
    ký tự cuối do OCR: "5785" / "578E" / "578") và tên đường gần giống ("Lê Hồng Thang" / "Lê Hồng Phong")."""
    left, right = _fold(handwritten.get("diaChi")), _fold(printed.get("diaChi"))
    left_no, right_no = re.match(r"(?:so\s*)?(\d+)", left), re.match(r"(?:so\s*)?(\d+)", right)
    if not left_no or not right_no:
        return False
    a, b = left_no.group(1), right_no.group(1)
    if not (a.startswith(b) or b.startswith(a)) or min(len(a), len(b)) < 2:
        return False
    rest_left = re.sub(r"^\S+\s*", "", left[left_no.start():])
    rest_right = re.sub(r"^\S+\s*", "", right[right_no.start():])
    return bool(rest_left and rest_right) and SequenceMatcher(None, rest_left, rest_right).ratio() >= _SAME_STREET_RATIO


def _person(values: dict, prefix: str, warnings: list[str]) -> dict:
    name = _text(values.get(f"{prefix}_HoTen"))
    identity = _identity(values.get(f"{prefix}_SoDinhDanh"))
    date, issuer = _issued(values.get(f"{prefix}_NgayCap"), values.get(f"{prefix}_NoiCap"))
    if identity and len(identity) == 12 and date and int(date[-4:]) < _ID12_FROM_YEAR:
        warnings.append(f"Ngày cấp {date} ({name or prefix}) là của CMND cũ, không khớp số CCCD {identity} — đã để trống "
                        "ngày cấp, nơi cấp; cán bộ nhập theo thẻ CCCD.")
        date = issuer = None
    return {
        "name": name,
        "birthday": _date_loose(values.get(f"{prefix}_NgaySinh")),
        "identity": identity,
        "date": date,
        "issuer": issuer,
        "residence": values.get(f"{prefix}_DiaChi"),
    }


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

    parcel_area = _area(values.get("ThuaDat_DiaChi"))
    fallback_provinces = ((parcel_area or {}).get("tinh"), PORTAL_PROVINCE)
    rejected_phones: set[str] = set()

    def phone(value: Any) -> str | None:
        number, rejected = _phone_vn(value)
        if rejected:
            rejected_phones.add(rejected)
        return number

    def add_person(names: tuple[str, ...], person: dict, phone_value: Any, email: Any, area: dict | None, who: str) -> None:
        full, tel, birthday, mail, number, date, issuer, province, ward, address = names
        add(full, person["name"])
        add(tel, phone(phone_value))
        add(birthday, person["birthday"])
        add(mail, _text(email))
        add(number, person["identity"])
        add(date, person["date"])
        add(issuer, person["issuer"])
        # Chỉ có tỉnh mà thiếu cả phường/xã lẫn chi tiết thì nhiều khả năng là tỉnh đoán -> bỏ cả cụm.
        if not area or not (_text(area.get("xa")) or _text(area.get("diaChi"))):
            return
        add(province, _province(area))
        ward_value = _ward(area)
        add(ward, ward_value)
        add(address, _text(area.get("diaChi")))
        tinh = _text(area.get("tinh"))
        if ward_value and tinh and not canonical_ward(tinh, ward_value):
            warnings.append(f"Phường/xã '{ward_value}' ({who}) không có trong danh mục {_province(area)} — cán bộ chọn lại.")

    first = _person(values, "NSD1", warnings)
    second = _person(values, "NSD2", warnings)
    if not second["name"] or _fold(second["name"]) == _fold(first["name"]):
        second = None
    agent = _person(values, "UyQuyen", warnings)
    land_users = {_fold(first["name"])} | ({_fold(second["name"])} if second else set())
    authorized = bool(agent["name"] and _fold(agent["name"]) not in land_users)
    owner = second or first
    contact = _person_area(values.get("Don_DiaChiLienHe"), fallback_provinces)
    if contact and parcel_area and _same_address(contact, parcel_area) and (
            _fold(contact.get("diaChi")) != _fold(parcel_area.get("diaChi")) or _ward(contact) != _ward(parcel_area)):
        # Đơn viết tay ghi địa chỉ liên hệ trùng thửa đất nhưng OCR đọc lệch số nhà/tên đường/phường → lấy bản IN của địa
        # chỉ thửa đất (Phiếu đo đạc/GCN, địa danh mới).
        warnings.append(f"Địa chỉ liên hệ viết tay trên Đơn đọc là '{_text(contact.get('diaChi'))}, {_ward(contact)}' — "
                        f"trùng địa chỉ thửa đất nên đã lấy theo bản in '{_text(parcel_area.get('diaChi'))}, "
                        f"{_ward(parcel_area)}'; cán bộ đối chiếu Đơn.")
        contact = dict(parcel_area)

    def land_user_area(person: dict) -> dict | None:
        # Địa chỉ liên hệ ở Đơn mục 2 (địa danh mới) đứng trước nơi thường trú in trên GCN (địa danh cũ).
        return contact or _person_area(person["residence"], fallback_provinces)

    # --- Phần I: người nộp ---
    part_one = ("data[fullname]", "data[phoneNumber]", "data[birthday]", "data[email]", "data[identityNumber]",
                "data[identityDate]", "data[identityAgency_text]", "data[province]", "data[village]", "data[address]")
    if authorized:
        add_person(part_one, agent, values.get("UyQuyen_DienThoai"), None,
                   _person_area(agent["residence"], fallback_provinces), "người nộp")
    else:
        add_person(part_one, first, values.get("Don_DienThoai"), values.get("Don_Email"), land_user_area(first),
                   "người nộp")
    request = _request(values.get("Don_NoiDungDeNghi"))
    add("data[noidungyeucaugiaiquyet]", request or DEFAULT_REQUEST, default=not request)

    # --- Phần II: chủ hồ sơ (người thứ hai đứng Đơn; một người thì chính người đó) ---
    if _is_to_chuc(values.get("NSD_LoaiChuThe"), owner["name"]):
        add("data[chonDoiTuong]", "Tổ chức")
    else:
        add("data[chonDoiTuong]", "Cá nhân", default=True)
    add_person(("data[ownerFullname]", "data[ownerPhoneNumber]", "data[ownerBirthday]", "data[ownerEmail]",
                "data[ownerIdentityNumber]", "data[ownerIdentityDate]", "data[ownerIdentityAgency]", "data[province1]",
                "data[village1]", "data[ownerAddress]"),
               owner, values.get("Don_DienThoai"), values.get("Don_Email"), land_user_area(owner), "chủ hồ sơ")
    if authorized and second and first["name"]:
        warnings.append(f"Hồ sơ có hai người sử dụng đất ({first['name']}; {second['name']}), người nộp là bên được ủy "
                        f"quyền {agent['name']} — chủ hồ sơ đã điền {second['name']}; cán bộ kiểm tra lại.")

    # --- Phần III: thửa đất — số theo Giấy chứng nhận, địa chỉ theo Phiếu đo đạc (địa danh mới) ---
    so_thua, so_to = _parcel_number(values.get("ThuaDat_SoThua")), _parcel_number(values.get("ThuaDat_SoTo"))
    add("data[SoThuaDat]", so_thua)
    add("data[SoToBanDo]", so_to)
    thua_moi, to_moi = _parcel_number(values.get("ThuaDat_SoThuaMoi")), _parcel_number(values.get("ThuaDat_SoToMoi"))
    if (thua_moi and thua_moi != so_thua) or (to_moi and to_moi != so_to):
        moi = ", ".join(part for part in (f"thửa {thua_moi}" if thua_moi else "", f"tờ {to_moi}" if to_moi else "") if part)
        warnings.append(f"Phiếu đo đạc ghi thêm số thửa/tờ khác Giấy chứng nhận ({moi}) — đã điền theo Giấy chứng nhận "
                        f"(thửa {so_thua or '?'}, tờ {so_to or '?'}); cán bộ xác nhận số dùng để nộp.")
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
    if not owner["name"]:
        warnings.append("Thiếu tên người sử dụng đất đứng Đơn xin xác nhận lại thời hạn sử dụng đất.")
    finish_blank_fields(out, seen, warnings, options, (agent if authorized else first)["identity"])
    return out, warnings
