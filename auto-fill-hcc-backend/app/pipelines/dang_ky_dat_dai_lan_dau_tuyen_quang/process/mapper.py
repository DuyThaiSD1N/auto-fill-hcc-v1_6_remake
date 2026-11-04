"""Map facts nguồn sang form "5 bước 20 ngày" của đăng ký đất đai lần đầu — cổng iGate Tuyên Quang (1.013978).

Cùng khung Form.io với form 1 của đính chính GCN / giao đất Tuyên Quang nên dùng lại hàm xếp vai của các pipeline đó:
không có văn bản ủy quyền thì Phần I là chủ hồ sơ, Phần II trống; có thì Phần I là bên được ủy quyền, Phần II là chủ
hồ sơ. Form không có ô thửa đất. ``parcel_area`` dùng chung cho form iLis / VBDLIS.
"""

from __future__ import annotations

from typing import Any

from app.pipelines._shared.area_remap import province_for_ward, province_label
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.process.mapper import (
    PART_ONE_LABELS,
    PART_ONE_NAMES,
    _area,
    _by_name,
    _text,
    clear_missing,
    cleared_warning,
)
from app.pipelines.giao_thue_chuyen_muc_dich_dat_giao_rung_gia_han_tuyen_quang.process.mapper import (
    applicant,
    authorized,
    person,
    place_text,
)

from .schema import UI_COMP_BY_NAME

MISSING_OWNER = "Thiếu tên chủ hồ sơ (người sử dụng đất đứng Đơn đăng ký đất đai)."


def parcel_area(values: dict) -> dict | None:
    """Địa chỉ thửa đất đã chuẩn hóa. Đơn mục 2b hay chỉ ghi phường/xã: LLM bỏ trống tỉnh thì lấy tỉnh DUY NHẤT có
    phường/xã đó trong danh mục; tên trùng nhiều tỉnh thì để trống cho cán bộ chọn (cổng đổ sẵn tỉnh Tuyên Quang)."""
    area = _area(values.get("ThuaDat_DiaChi"))
    if area and _text(area.get("xa")) and not _text(area.get("tinh")):
        found = province_for_ward(area["xa"])
        if found:
            area = {**area, "tinh": found[0], "xa": found[1]}
    return area


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
    add("data[fullname]", who["name"])
    add("data[identityNumber]", who["number"])
    add("data[gender]", who["gender"])
    add("data[birthday]", who["birthday"])
    add("data[identityDate]", who["issued"])
    add("data[identityAgency]", who["issuer"])
    add("data[nation]", (area or {}).get("quocGia") or "Việt Nam", default=True)
    if area:
        add("data[province]", province_label(area.get("tinh")))
        add("data[district]", _text(area.get("xa")))
        add("data[address]", _text(area.get("diaChi")))
    add("data[phoneNumber]", who["phone"])
    add("data[email]", who["email"])
    add("data[hinhThucNop]", "Trực tuyến", default=True)

    if authorized(values):
        owner = person(values, "ChuHoSo")
        add("data[Hovaten]", owner["name"])
        add("data[Sogiaytotuythan]", owner["number"])
        add("data[sodienthoai]", owner["phone"])
        add("data[diachi]", place_text(owner["area"]))

    warnings = [] if _text(values.get("ChuHoSo_HoTen")) else [MISSING_OWNER]
    # Ô Phần I không có nguồn → xoá trắng: cổng điền sẵn theo TÀI KHOẢN (giới tính, ngày sinh, tỉnh).
    warnings.extend(cleared_warning(clear_missing(out, seen, PART_ONE_NAMES, UI_COMP_BY_NAME), PART_ONE_LABELS))
    return out, warnings
