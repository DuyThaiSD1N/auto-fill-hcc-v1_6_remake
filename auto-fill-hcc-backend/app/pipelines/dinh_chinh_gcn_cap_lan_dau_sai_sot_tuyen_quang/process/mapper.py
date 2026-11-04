"""Map facts nguồn sang Form.io cổng iGate Tuyên Quang (đính chính GCN đã cấp lần đầu có sai sót)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date

from .schema import TEN_HO_SO, UI_COMP_BY_NAME


def _by_name(fields: list[dict]) -> dict[str, Any]:
    return {item["name"]: item.get("value") for item in fields if item.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" ,;:")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _identity(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", _text(value) or "")
    return digits or None


def _phone(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", (_text(value) or "").upper().replace("O", "0"))
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = re.fullmatch(r"\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})\s*", text)
    return normalize_date(match.group(0).replace("-", "/")) if match else None


def _gender(value: Any) -> str | None:
    folded = _fold(value)
    if folded in ("nam", "male", "m"):
        return "Nam"
    if folded in ("nu", "female", "f"):
        return "Nữ"
    return None


def _area(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("chiTietDuoiXa") or value.get("diaChi") or value.get("chiTiet") or "",
    }
    return remap_area(area) if any((area["tinh"], area["xa"], area["diaChi"])) else None


def _id_issued(number: str | None, date: Any, issuer: Any) -> tuple[str | None, str | None]:
    """Ngày cấp + nơi cấp đi được với số giấy tờ, hoặc (None, None).

    Hồ sơ đính chính hay chỉ có số 12 chữ số trên Đơn mà hợp đồng/trích lục lại ghi CMND 9 số CŨ kèm ngày, nơi cấp —
    LLM dễ ghép hai thứ đó vào nhau. Số 12 chữ số chỉ cấp từ 2012 nên ngày cấp trước 2012 là của giấy cũ: bỏ cả ngày
    lẫn nơi cấp. Nơi cấp giấy tờ tùy thân luôn là cơ quan công an; giá trị khác (UBND, Sở...) là đọc nhầm, bỏ.
    """
    issued = _date(date)
    if number and len(number) == 12 and issued and int(issued[-4:]) < 2012:
        return None, None
    text = _text(issuer)
    folded = _fold(text)
    police = bool(text and (re.search(r"\b(cong an|canh sat)\b", folded) or re.match(r"ca\b", folded)))
    return issued, normalize_issuer(text) if police else None


def clear_missing(out: list[dict], seen: set[str], names: tuple[str, ...], ui: dict[str, str]) -> list[str]:
    """Ô giấy tờ không có nguồn → cờ clear: extension XÓA TRẮNG ô (cổng hay đổ sẵn theo tài khoản đăng nhập: ngày sinh,
    giới tính, nơi cấp, tỉnh…) và tô đỏ để cán bộ nhập tay, thay vì để nguyên giá trị sai. Trả các ô đã xoá."""
    cleared = [name for name in names if name not in seen and name in ui]
    out.extend({"name": name, "comp": ui[name], "value": "", "clear": True, "markEmpty": True} for name in cleared)
    seen.update(cleared)
    return cleared


def cleared_warning(cleared: list[str], labels: dict[str, str]) -> list[str]:
    """Nhắc cán bộ những ô quan trọng đã bị xoá trắng vì giấy tờ không có thông tin."""
    names = [labels[name] for name in cleared if name in labels]
    if not names:
        return []
    return ["Giấy tờ không có thông tin: " + "; ".join(names)
            + " — đã xoá giá trị cổng điền sẵn theo tài khoản, để trống cho cán bộ nhập tay."]


def _area_text(area: dict | None) -> str | None:
    """Địa chỉ một dòng cho ô text "Địa chỉ" của Phần II: chi tiết, phường/xã, tỉnh."""
    if not area:
        return None
    parts = [_text(area.get("diaChi")), _text(area.get("xa")), province_label(area.get("tinh"))]
    return ", ".join(part for part in parts if part) or None


# Ô cá nhân Phần I của form 1 (dùng chung với thủ tục giao đất Tuyên Quang): không có nguồn thì xoá trắng.
PART_ONE_NAMES = (
    "data[fullname]", "data[identityNumber]", "data[gender]", "data[birthday]", "data[identityDate]",
    "data[identityAgency]", "data[province]", "data[district]", "data[address]", "data[phoneNumber]", "data[email]",
)
PART_ONE_LABELS = {
    "data[gender]": "Giới tính người nộp",
    "data[birthday]": "Ngày sinh người nộp",
    "data[province]": "Tỉnh/TP người nộp",
}


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
    agent_name = _text(values.get("NguoiNop_HoTen"))
    # Có văn bản ủy quyền (bên được ủy quyền khác chủ hồ sơ): Phần I là người nộp, Phần II là bên ủy quyền.
    authorized = bool(agent_name and _fold(agent_name) != _fold(owner_name))
    role = "NguoiNop" if authorized else "ChuHoSo"

    def val(key: str):
        return values.get(f"{role}_{key}")

    area = _area(val("NoiCuTru"))
    number = _identity(val("SoDinhDanh"))
    issued, issuer = _id_issued(number, val("NgayCap"), val("NoiCap"))

    add("data[fullname]", agent_name if authorized else owner_name)
    add("data[identityNumber]", number)
    add("data[gender]", _gender(val("GioiTinh")))
    add("data[birthday]", _date(val("NgaySinh")))
    add("data[identityDate]", issued)
    add("data[identityAgency]", issuer)
    add("data[nation]", (area or {}).get("quocGia") or "Việt Nam", default=True)
    if area:
        add("data[province]", province_label(area.get("tinh")))
        add("data[district]", _text(area.get("xa")))
        add("data[address]", _text(area.get("diaChi")))
    add("data[phoneNumber]", _phone(val("DienThoai")))
    add("data[email]", _text(val("Email")))
    add("data[hinhThucNop]", "Trực tuyến", default=True)
    add("data[tenHoSo]", TEN_HO_SO, default=True)
    add("data[textField]", _text(values.get("Don_NoiDungBienDong")))

    if authorized:
        add("data[Hovaten]", owner_name)
        add("data[Sogiaytotuythan]", _identity(values.get("ChuHoSo_SoDinhDanh")))
        add("data[sodienthoai]", _phone(values.get("ChuHoSo_DienThoai")))
        add("data[diachi]", _area_text(_area(values.get("ChuHoSo_NoiCuTru"))))

    # Ô Phần I không có nguồn → xoá trắng: cổng điền sẵn theo TÀI KHOẢN (giới tính "Nam", ngày sinh, tỉnh Tuyên Quang).
    cleared = clear_missing(out, seen, PART_ONE_NAMES, UI_COMP_BY_NAME)
    warnings.extend(cleared_warning(cleared, PART_ONE_LABELS))
    return out, warnings
