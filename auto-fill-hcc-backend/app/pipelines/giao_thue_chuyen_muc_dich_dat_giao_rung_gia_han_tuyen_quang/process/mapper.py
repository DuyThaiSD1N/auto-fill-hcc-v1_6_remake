"""Map facts nguồn sang form 1 cổng iGate Tuyên Quang (giao đất, cho thuê đất, chuyển mục đích sử dụng đất).

Các hàm ghép câu (person, place_text, gcn_text, dong_su_dung_text…) dùng chung cho form 2 (process_vbdlis).
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.area_remap import province_label
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.process.mapper import (
    PART_ONE_LABELS,
    PART_ONE_NAMES,
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


def authorized(values: dict) -> bool:
    """Có giấy ủy quyền: bên được ủy quyền khác chủ hồ sơ → người nộp là bên được ủy quyền."""
    agent = _text(values.get("NguoiNop_HoTen"))
    return bool(agent and _fold(agent) != _fold(_text(values.get("ChuHoSo_HoTen"))))


def person(values: dict, role: str) -> dict[str, Any]:
    """Thuộc tính đã chuẩn hóa của một vai (ChuHoSo / NguoiNop); ngày, nơi cấp phải đi được với số giấy tờ."""
    number = _identity(values.get(f"{role}_SoDinhDanh"))
    issued, issuer = _id_issued(number, values.get(f"{role}_NgayCap"), values.get(f"{role}_NoiCap"))
    return {
        "name": _text(values.get(f"{role}_HoTen")),
        "number": number,
        "gender": _gender(values.get(f"{role}_GioiTinh")),
        "birthday": _date(values.get(f"{role}_NgaySinh")),
        "issued": issued,
        "issuer": issuer,
        "area": _area(values.get(f"{role}_NoiCuTru")),
        "phone": _phone(values.get(f"{role}_DienThoai")),
        "email": _text(values.get(f"{role}_Email")),
    }


def applicant(values: dict) -> dict[str, Any]:
    """Người nộp: bên được ủy quyền nếu có giấy ủy quyền, không thì chủ hồ sơ. Bên được ủy quyền không ghi số điện
    thoại thì dùng số liên hệ trên Đơn (file mapping: số duy nhất của hồ sơ, cán bộ thay nếu người nộp có số khác)."""
    if not authorized(values):
        return person(values, "ChuHoSo")
    data = person(values, "NguoiNop")
    data["phone"] = data["phone"] or _phone(values.get("ChuHoSo_DienThoai"))
    return data


def _inline(text: str | None) -> str | None:
    """Tên đơn vị hành chính giữa câu: "Xã Nghĩa Hưng" -> "xã Nghĩa Hưng"."""
    if text and re.match(r"(Xã|Phường|Thị trấn|Đặc khu|Tỉnh|Thành phố)\b", text):
        return text[:1].lower() + text[1:]
    return text


def place_text(area: dict | None) -> str | None:
    """Địa chỉ một dòng: chi tiết, phường/xã, tỉnh (vd "Thôn Đông, xã Hòa Bình, tỉnh Ninh Bình")."""
    if not area:
        return None
    parts = [_text(area.get("diaChi")), _inline(_text(area.get("xa"))), _inline(province_label(area.get("tinh")))]
    return ", ".join(part for part in parts if part) or None


def gcn_text(values: dict, *, with_agency: bool) -> str | None:
    """"Giấy chứng nhận số …, số vào sổ cấp …, [do <cơ quan> ]cấp ngày …"."""
    number, book = _text(values.get("GCN_So")), _text(values.get("GCN_SoVaoSo"))
    if not (number or book):
        return None
    agency, issued = _text(values.get("GCN_CoQuanCap")), _date(values.get("GCN_NgayCap"))
    parts = [f"Giấy chứng nhận số {number}" if number else "Giấy chứng nhận"]
    if book:
        parts.append(f"số vào sổ cấp {book}")
    issue = " ".join(part for part in (f"do {agency}" if with_agency and agency else "",
                                       f"cấp ngày {issued}" if issued else "") if part)
    if issue:
        parts.append(issue)
    return ", ".join(parts)


def parcel_text(values: dict) -> str | None:
    """"thửa đất số …, tờ bản đồ số …, địa điểm …"."""
    parts = []
    if _text(values.get("ThuaDat_SoThua")):
        parts.append(f"thửa đất số {_text(values.get('ThuaDat_SoThua'))}")
    if _text(values.get("ThuaDat_SoTo")):
        parts.append(f"tờ bản đồ số {_text(values.get('ThuaDat_SoTo'))}")
    where = place_text(_area(values.get("ThuaDat_DiaChi")))
    if where:
        parts.append(f"địa điểm {where}")
    return ", ".join(parts) or None


def dong_su_dung_text(values: dict) -> str | None:
    """"Người đồng sử dụng: bà …, sinh ngày …, CCCD …, do … cấp ngày …." — form không có ô riêng cho người này."""
    name = _text(values.get("DongSuDung_HoTen"))
    if not name:
        return None
    title = {"Nam": "ông", "Nữ": "bà"}.get(_gender(values.get("DongSuDung_GioiTinh")) or "")
    number = _identity(values.get("DongSuDung_SoDinhDanh"))
    issued, issuer = _id_issued(number, values.get("DongSuDung_NgayCap"), values.get("DongSuDung_NoiCap"))
    birthday = _date(values.get("DongSuDung_NgaySinh"))
    parts = [f"{title} {name}" if title else name]
    if birthday:
        parts.append(f"sinh ngày {birthday}")
    if number:
        parts.append(f"CCCD {number}")
    issue = " ".join(part for part in (f"do {issuer}" if issuer else "", f"cấp ngày {issued}" if issued else "") if part)
    if issue:
        parts.append(f"{issue} cấp" if issuer and not issued else issue)
    return "Người đồng sử dụng: " + ", ".join(parts) + "."


def sentence(*parts: str | None) -> str | None:
    """Nối các ý bằng "; " rồi chấm câu."""
    text = "; ".join(part.rstrip(" .;") for part in parts if part)
    return f"{text}." if text else None


def request_lead(values: dict) -> str | None:
    """Tiêu đề Đơn thành câu đề nghị: "ĐƠN ĐỀ NGHỊ CHO PHÉP …" -> "Đề nghị cho phép …"."""
    title = _text(values.get("Don_TieuDe"))
    if not title:
        return None
    text = re.sub(r"^đơn\s+", "", title.lower()).strip()
    return text[:1].upper() + text[1:] if text else None


def ghi_chu_khac(values: dict) -> str | None:
    """Ô "Ghi chú Khác" form 1: nội dung đề nghị, thửa đất, Giấy chứng nhận, hình thức sử dụng, người đồng sử dụng."""
    usage = _text(values.get("Don_HinhThucSuDung"))
    main = sentence(_text(values.get("Don_NoiDungDeNghi")), parcel_text(values), gcn_text(values, with_agency=False),
                    f"hình thức sử dụng đất: {usage}" if usage else None)
    return " ".join(part for part in (main, dong_su_dung_text(values)) if part) or None


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
    add("data[tenHoSo]", _text(values.get("Don_TieuDe")))
    add("data[textField]", ghi_chu_khac(values))

    if authorized(values):
        owner = person(values, "ChuHoSo")
        add("data[Hovaten]", owner["name"])
        add("data[Sogiaytotuythan]", owner["number"])
        add("data[sodienthoai]", owner["phone"])
        add("data[diachi]", place_text(owner["area"]))

    # Ô Phần I không có nguồn → xoá trắng: cổng điền sẵn theo TÀI KHOẢN (giới tính "Nam", ngày sinh).
    return out, cleared_warning(clear_missing(out, seen, PART_ONE_NAMES, UI_COMP_BY_NAME), PART_ONE_LABELS)
