"""Map facts nguồn sang form quy trình iLis của đăng ký đất đai lần đầu — cổng iGate Tuyên Quang."""

from __future__ import annotations

from typing import Any

from app.pipelines._shared.area_remap import province_label
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.process.mapper import (
    _by_name,
    _text,
    clear_missing,
    cleared_warning,
)
from app.pipelines.giao_thue_chuyen_muc_dich_dat_giao_rung_gia_han_tuyen_quang.process.mapper import (
    applicant,
    person,
)

from ..process.mapper import MISSING_OWNER, parcel_area
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

    def add_person(who: dict, names: dict[str, str]) -> None:
        area = who["area"]
        add(names["fullname"], who["name"])
        add(names["birthday"], who["birthday"])
        add(names["gender"], who["gender"])
        add(names["phone"], who["phone"])
        add(names["email"], who["email"])
        add(names["identity"], who["number"])
        add(names["identityDate"], who["issued"])
        add(names["identityAgency"], who["issuer"])
        add(names["nation"], (area or {}).get("quocGia") or "Việt Nam", default=True)
        if area:
            add(names["province"], province_label(area.get("tinh")))
            add(names["village"], _text(area.get("xa")))
            add(names["address"], _text(area.get("diaChi")))

    # Không có văn bản ủy quyền: applicant() chính là chủ hồ sơ → hai khối cùng một người.
    add_person(applicant(values), {
        "fullname": "data[fullname]", "birthday": "data[birthday]", "gender": "data[gender]",
        "phone": "data[phoneNumber]", "email": "data[email]", "identity": "data[identityNumber]",
        "identityDate": "data[identityDate]", "identityAgency": "data[identityAgency]", "nation": "data[nation]",
        "province": "data[province]", "village": "data[village]", "address": "data[address]",
    })

    parcel = parcel_area(values)
    if parcel:
        add("data[province2]", province_label(parcel.get("tinh")))
        add("data[village2]", _text(parcel.get("xa")))

    add_person(person(values, "ChuHoSo"), {
        "fullname": "data[ownerFullname]", "birthday": "data[ownerBirthday]", "gender": "data[gender1]",
        "phone": "data[ownerPhoneNumber]", "email": "data[ownerEmail]", "identity": "data[ownerIdentityNumber]",
        "identityDate": "data[ownerIdentityDate]", "identityAgency": "data[ownerIdentityAgency]",
        "nation": "data[nation1]", "province": "data[province1]", "village": "data[village1]",
        "address": "data[ownerAddress]",
    })

    warnings = [] if _text(values.get("ChuHoSo_HoTen")) else [MISSING_OWNER]
    warnings.extend(cleared_warning(clear_missing(out, seen, _CLEARABLE, UI_COMP_BY_NAME), _LABELS))
    return out, warnings
