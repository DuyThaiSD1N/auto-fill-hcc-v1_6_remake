"""Map facts nguồn sang form quy trình VBDLIS của đăng ký đất đai lần đầu — cổng iGate Tuyên Quang."""

from __future__ import annotations

from typing import Any

from app.pipelines._shared.area_remap import province_label
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.mapper import _is_to_chuc, _parcel_number
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.process.mapper import (
    _by_name,
    _text,
    clear_missing,
    cleared_warning,
)
from app.pipelines.giao_thue_chuyen_muc_dich_dat_giao_rung_gia_han_tuyen_quang.process.mapper import (
    applicant,
    place_text,
)

from ..process.mapper import MISSING_OWNER, parcel_area
from .schema import UI_COMP_BY_NAME

# Ô cá nhân và tỉnh/xã thửa đất: không có nguồn thì xoá trắng — cổng đổ sẵn theo TÀI KHOẢN ngày sinh và tỉnh thửa đất
# "Tỉnh Tuyên Quang".
_CLEARABLE = (
    "data[ownerFullname]", "data[fullname]", "data[birthday]", "data[gender]", "data[email]", "data[phoneNumber]",
    "data[identityNumber]", "data[identityDate]", "data[identityAgency]", "data[province]", "data[district]",
    "data[address]", "data[province2]", "data[district2]",
)
_LABELS = {
    "data[birthday]": "Ngày sinh người nộp",
    "data[phoneNumber]": "Số điện thoại",
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

    owner_name = _text(values.get("ChuHoSo_HoTen"))
    who = applicant(values)
    area = who["area"]
    add("data[ownerFullname]", owner_name)
    add("data[fullname]", who["name"])
    add("data[birthday]", who["birthday"])
    add("data[gender]", who["gender"])
    add("data[email]", who["email"])
    add("data[phoneNumber]", who["phone"])
    add("data[identityNumber]", who["number"])
    add("data[identityDate]", who["issued"])
    add("data[identityAgency]", who["issuer"])
    add("data[noidungyeucaugiaiquyet]", _text(values.get("Don_NoiDungDeNghi")))
    if _is_to_chuc(values.get("ChuHoSo_LoaiChuThe"), owner_name):
        add("data[chonDoiTuong]", "Tổ chức")
    else:
        add("data[chonDoiTuong]", "Cá nhân", default=True)
    add("data[hinhThucNop]", "Trực tuyến", default=True)
    add("data[nation]", (area or {}).get("quocGia") or "Việt Nam", default=True)
    if area:
        add("data[province]", province_label(area.get("tinh")))
        add("data[district]", _text(area.get("xa")))
        add("data[address]", _text(area.get("diaChi")))

    add("data[SoThuTuThua]", _parcel_number(values.get("ThuaDat_SoThua")))
    add("data[SoHieuToBanDo]", _parcel_number(values.get("ThuaDat_SoTo")))
    parcel = parcel_area(values)
    add("data[diaChiThuaDat1]", place_text(parcel))
    add("data[nation2]", (parcel or {}).get("quocGia") or "Việt Nam", default=True)
    if parcel:
        add("data[province2]", province_label(parcel.get("tinh")))
        add("data[district2]", _text(parcel.get("xa")))

    warnings = [] if owner_name else [MISSING_OWNER]
    warnings.extend(cleared_warning(clear_missing(out, seen, _CLEARABLE, UI_COMP_BY_NAME), _LABELS))
    return out, warnings
