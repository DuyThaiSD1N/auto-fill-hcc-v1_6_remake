"""Map facts nguồn sang form 2 (quy trình VBDLIS) của thủ tục giao đất, cho thuê đất, chuyển mục đích — Tuyên Quang."""

from __future__ import annotations

from typing import Any

from app.pipelines._shared.area_remap import province_label

from ..process.mapper import (
    _area,
    _by_name,
    _text,
    applicant,
    clear_missing,
    cleared_warning,
    dong_su_dung_text,
    gcn_text,
    place_text,
    request_lead,
    sentence,
)
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
    "data[province2]": "Tỉnh/TP thửa đất",
}


def noi_dung_yeu_cau(values: dict) -> str | None:
    """"Đề nghị cho phép chuyển mục đích sử dụng đất: <nội dung>; Giấy chứng nhận số …, do … cấp ngày …"."""
    request = _text(values.get("Don_NoiDungDeNghi"))
    lead = request_lead(values)
    head = f"{lead}: {request}" if lead and request else (request or lead)
    return sentence(head, gcn_text(values, with_agency=True))


def ghi_chu(values: dict) -> str | None:
    """Ô "Ghi chú": người đồng sử dụng + hình thức sử dụng đất (form không có ô riêng)."""
    usage = _text(values.get("Don_HinhThucSuDung"))
    parts = [dong_su_dung_text(values), f"Hình thức sử dụng đất: {usage.rstrip('.')}." if usage else None]
    return " ".join(part for part in parts if part) or None


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

    who = applicant(values)
    area = who["area"]
    add("data[ownerFullname]", _text(values.get("ChuHoSo_HoTen")))
    add("data[fullname]", who["name"])
    add("data[birthday]", who["birthday"])
    add("data[gender]", who["gender"])
    add("data[email]", who["email"])
    add("data[phoneNumber]", who["phone"])
    add("data[identityNumber]", who["number"])
    add("data[identityDate]", who["issued"])
    add("data[identityAgency]", who["issuer"])
    add("data[note]", ghi_chu(values))
    add("data[noidungyeucaugiaiquyet]", noi_dung_yeu_cau(values))
    add("data[chonDoiTuong]", "Cá nhân", default=True)
    add("data[hinhThucNop]", "Trực tuyến", default=True)
    add("data[nation]", (area or {}).get("quocGia") or "Việt Nam", default=True)
    if area:
        add("data[province]", province_label(area.get("tinh")))
        add("data[district]", _text(area.get("xa")))
        add("data[address]", _text(area.get("diaChi")))
    add("data[tenHoSo]", _text(values.get("Don_TieuDe")))

    add("data[SoThuTuThua]", _text(values.get("ThuaDat_SoThua")))
    add("data[SoHieuToBanDo]", _text(values.get("ThuaDat_SoTo")))
    parcel = _area(values.get("ThuaDat_DiaChi"))
    add("data[diaChiThuaDat1]", place_text(parcel))
    add("data[nation2]", (parcel or {}).get("quocGia") or "Việt Nam", default=True)
    if parcel:
        add("data[province2]", province_label(parcel.get("tinh")))
        add("data[district2]", _text(parcel.get("xa")))

    return out, cleared_warning(clear_missing(out, seen, _CLEARABLE, UI_COMP_BY_NAME), _LABELS)
