"""Map facts nguồn sang form 2 (quy trình iLis) của thủ tục đính chính GCN có sai sót — cổng iGate Tuyên Quang."""

from __future__ import annotations

import re
from typing import Any

from app.locations.catalog import find_province
from app.pipelines._shared.area_remap import province_label

from ..process.mapper import (
    _area,
    _by_name,
    _date,
    _fold,
    _gender,
    _id_issued,
    _identity,
    _phone,
    _text,
    clear_missing,
    cleared_warning,
)
from .schema import UI_COMP_BY_NAME

# Ô cá nhân (người nộp, chủ hồ sơ) và ô thửa đất: không có nguồn thì xoá trắng — cổng đổ sẵn theo TÀI KHOẢN ngày sinh,
# nơi cấp ("Cục Cảnh sát quản lý hành chính về trật tự xã hội") và tỉnh thửa đất ("Tỉnh Tuyên Quang").
_CLEARABLE = (
    "data[fullname]", "data[birthday]", "data[gender]", "data[phoneNumber]", "data[email]", "data[identityNumber]",
    "data[identityDate]", "data[identityAgency]", "data[province]", "data[village]", "data[address]",
    "data[province2]", "data[village2]",
    "data[ownerFullname]", "data[ownerBirthday]", "data[gender1]", "data[ownerPhoneNumber]", "data[ownerEmail]",
    "data[ownerIdentityNumber]", "data[ownerIdentityDate]", "data[ownerIdentityAgency]", "data[province1]",
    "data[village1]", "data[ownerAddress]",
)
_LABELS = {
    "data[birthday]": "Ngày sinh người nộp",
    "data[identityAgency]": "Nơi cấp CMND/CCCD người nộp",
    "data[province2]": "Tỉnh/TP thửa đất",
}


def _place(value: Any) -> str | None:
    """Địa danh cấp GCN: đúng tên một tỉnh (có/không tiền tố) → nhãn đầy đủ "Thành phố X"/"Tỉnh X"; khác giữ nguyên."""
    text = _text(value)
    province = find_province(text) if text else None
    bare = re.sub(r"^(tỉnh|thành phố|tp\.?)\s+", "", text or "", flags=re.IGNORECASE)
    return province["text"] if province and _fold(bare) == _fold(province["name"]) else text


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    del options
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()
    warnings: list[str] = []

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
    applicant_name = _text(values.get("NguoiNop_HoTen"))
    # Đơn chỉ một người (hoặc LLM chỉ trả một vai): hai khối là cùng một người, thiếu bên này lấy bên kia. Hai người
    # khác nhau thì tuyệt đối không mượn thuộc tính của nhau.
    same_person = not owner_name or not applicant_name or _fold(owner_name) == _fold(applicant_name)

    def person(role: str, key: str):
        value = values.get(f"{role}_{key}")
        if value in (None, "", {}, []) and same_person:
            value = values.get(f"{'ChuHoSo' if role == 'NguoiNop' else 'NguoiNop'}_{key}")
        return value

    def add_person(role: str, names: dict[str, str]) -> None:
        area = _area(person(role, "NoiCuTru"))
        number = _identity(person(role, "SoDinhDanh"))
        issued, issuer = _id_issued(number, person(role, "NgayCap"), person(role, "NoiCap"))
        add(names["fullname"], _text(person(role, "HoTen")))
        add(names["birthday"], _date(person(role, "NgaySinh")))
        add(names["gender"], _gender(person(role, "GioiTinh")))
        add(names["phone"], _phone(person(role, "DienThoai")))
        add(names["email"], _text(person(role, "Email")))
        add(names["identity"], number)
        add(names["identityDate"], issued)
        add(names["identityAgency"], issuer)
        add(names["nation"], (area or {}).get("quocGia") or "Việt Nam", default=True)
        if area:
            add(names["province"], province_label(area.get("tinh")))
            add(names["village"], _text(area.get("xa")))
            add(names["address"], _text(area.get("diaChi")))

    add_person("NguoiNop", {
        "fullname": "data[fullname]", "birthday": "data[birthday]", "gender": "data[gender]",
        "phone": "data[phoneNumber]", "email": "data[email]", "identity": "data[identityNumber]",
        "identityDate": "data[identityDate]", "identityAgency": "data[identityAgency]", "nation": "data[nation]",
        "province": "data[province]", "village": "data[village]", "address": "data[address]",
    })
    add("data[ghiChu]", _text(values.get("Don_NoiDungBienDong")))

    parcel = _area(values.get("ThuaDat_DiaChi"))
    if parcel:
        add("data[province2]", province_label(parcel.get("tinh")))
        add("data[village2]", _text(parcel.get("xa")))

    add_person("ChuHoSo", {
        "fullname": "data[ownerFullname]", "birthday": "data[ownerBirthday]", "gender": "data[gender1]",
        "phone": "data[ownerPhoneNumber]", "email": "data[ownerEmail]", "identity": "data[ownerIdentityNumber]",
        "identityDate": "data[ownerIdentityDate]", "identityAgency": "data[ownerIdentityAgency]",
        "nation": "data[nation1]", "province": "data[province1]", "village": "data[village1]",
        "address": "data[ownerAddress]",
    })

    add("data[licenseCode]", _text(values.get("GCN_So")))  # số seri có thể có chữ (vd "CS 01234")
    add("data[licenseDate]", _date(values.get("GCN_NgayCap")))
    add("data[licensingPlace]", _text(values.get("GCN_DonViCap")))
    add("data[licensingAgency]", _place(values.get("GCN_NoiCap")))

    warnings.extend(cleared_warning(clear_missing(out, seen, _CLEARABLE, UI_COMP_BY_NAME), _LABELS))
    return out, warnings
