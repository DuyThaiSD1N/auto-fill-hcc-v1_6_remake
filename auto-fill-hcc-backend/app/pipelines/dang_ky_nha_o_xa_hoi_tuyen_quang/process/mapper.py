"""Map compact source facts → Form.io data[...] cho "Tuyên Quang - Đăng ký mua, thuê mua, thuê nhà ở xã hội…".

Người kê khai đứng cả form 1 (người nộp) lẫn form 2 (Giấy xác nhận về điều kiện nhà ở).

Cổng đổ sẵn ngày sinh theo tài khoản, ngày hôm nay vào hai ô ngày cấp của vợ/chồng, thành viên và ô ngày ký. Ô chữ/ngày
không có dữ liệu phải phát clear để trả về trống, trừ khi tài khoản chính là người nộp thì giữ form 1 của cổng. Ô chọn
không clear vì engine trợ lý chưa bỏ chọn được.

Thành viên hộ: CT07 ghi quan hệ với CHỦ HỘ, còn ô trên form chỉ nhận vợ/chồng, cha, mẹ, con của NGƯỜI KÊ KHAI cùng thường
trú nên phải đổi quan hệ theo vị trí của người kê khai trong hộ. Anh chị em của chủ hộ khi người kê khai là cha/mẹ của chủ
hộ chỉ là suy luận, luôn kèm cảnh báo.
"""

from __future__ import annotations

import re
from typing import Any

from app.locations.catalog import find_province
from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.process.mapper import (
    _area,
    _by_name,
    _date,
    _fold,
    _gender_from_cccd,
    _identity,
    _issuer,
    _item_text,
    _phone,
    _phone_from_ocr,
    _province_label,
    _text,
)
from app.pipelines.dang_ky_dat_dai_lan_dau_khanh_hoa.process.mapper import account_is_applicant
from app.pipelines.dang_ky_nha_o_xa_hoi_tuyen_quang.process.schema import _PANEL, UI_COMP_BY_NAME

_DEFAULT_PROVINCE = "Tỉnh Tuyên Quang"

_PART_ONE_BLANK = (
    "data[fullname]", "data[birthday]", "data[identityNumber]", "data[identityDate]", "data[phoneNumber]",
    "data[address]",
)
_PART_TWO_BLANK = (
    f"{_PANEL}[identityDate1]", f"{_PANEL}[identityDate2]", f"{_PANEL}[TDTTK]", f"{_PANEL}[nguoiLamDon]",
)
_REQUIRED_BLANK = {
    "data[fullname]", "data[identityNumber]", "data[phoneNumber]", f"{_PANEL}[TDTTK]", f"{_PANEL}[nguoiLamDon]",
}

_ADDRESS_WORDS = re.compile(r"\b(Nhà|Ngách|Ngõ|Hẻm|Đường|Phố|Thôn|Xóm)\b")

_RELATION_BY_FIRST_WORD = {
    "vo": "spouse", "chong": "spouse", "me": "parent", "bo": "parent", "cha": "parent", "con": "child",
    "anh": "sibling", "chi": "sibling", "em": "sibling",
}


def _address_case(value: str) -> str:
    """CT07 in hoa phần số nhà/đường: đưa từng đoạn in hoa về cách viết thường của tờ khai."""
    def fix(chunk: str) -> str:
        if not chunk.isupper():
            return chunk
        titled = _ADDRESS_WORDS.sub(lambda match: match.group().lower(), chunk.title())
        return titled[:1].upper() + titled[1:]

    return ", ".join(fix(chunk.strip()) for chunk in value.split(","))


def _area_of(value: Any) -> dict | None:
    if isinstance(value, dict) and not value.get("diaChi") and value.get("chiTietDuoiXa"):
        value = {**value, "diaChi": value["chiTietDuoiXa"]}
    area = _area(value)
    if area and area.get("diaChi"):
        return {**area, "diaChi": _address_case(str(area["diaChi"]))}
    return area


def _area_line(area: dict | None) -> str | None:
    """Địa chỉ một dòng cho ô chữ ở form 2: chi tiết, phường/xã, tỉnh."""
    if not area:
        return None
    parts = (_text(area.get("diaChi")), _text(area.get("xa")), _province_label(area.get("tinh")))
    return ", ".join(part for part in parts if part) or None


def _sign_province(value: Any) -> str:
    """Ô "Tại" là ô bắt buộc cổng để sẵn tỉnh khác; địa danh ký không ra tỉnh thì lấy tỉnh của thủ tục."""
    province = find_province(_text(value) or "")
    return province["text"] if province else _DEFAULT_PROVINCE


def _relation_group(value: Any) -> str:
    folded = _fold(value)
    if "chu ho" in folded:
        return "head"
    if folded.startswith(("con dau", "con re")):
        return ""
    return _RELATION_BY_FIRST_WORD.get(folded.split(" ")[0], "")


def _relation_to_declarant(declarant: Any, member: Any) -> tuple[str, bool]:
    """Quan hệ của thành viên với người kê khai từ hai quan hệ với chủ hộ. Trả (nhãn, có phải suy luận); nhãn rỗng là
    không thuộc diện liệt kê."""
    own, other = _relation_group(declarant), _relation_group(member)
    written = (_text(member) or "").lower()
    if own == "head":
        return (written, False) if other in ("spouse", "parent", "child") else ("", False)
    if own == "parent":
        return {"head": ("con đẻ", False), "sibling": ("con", True)}.get(other, ("", False))
    if own == "spouse":
        if other == "head":
            return ("chồng" if _fold(declarant).startswith("vo") else "vợ", False)
        return (written, False) if other in ("parent", "child") else ("", False)
    if own == "child":
        return ("cha/mẹ", False) if other in ("head", "spouse") else ("", False)
    return "", False


def _household(
    members: Any, declarant_relation: Any, declarant_name: str | None, declarant_identity: str | None
) -> tuple[list[tuple[str, str, str | None]], list[str]]:
    """Người được liệt kê (tên, quan hệ, số định danh) và tên những người chỉ suy ra được quan hệ."""
    listed: list[tuple[str, str, str | None]] = []
    inferred: list[str] = []
    for member in members if isinstance(members, list) else []:
        name = _item_text(member, "hoTen", "hoVaTen")
        number = _identity(_item_text(member, "soDinhDanh", "soCccd"))
        if not name or (number and number == declarant_identity) or _fold(name) == _fold(declarant_name):
            continue
        direct = _item_text(member, "quanHeVoiNguoiKeKhai")
        if direct:
            label, guessed = direct.lower(), False
        else:
            label, guessed = _relation_to_declarant(declarant_relation, _item_text(member, "quanHeVoiChuHo", "quanHe"))
        if not label:
            continue
        listed.append((name, label, number))
        if guessed:
            inferred.append(name)
    return listed, inferred


def _member_numbers(listed: list[tuple[str, str, str | None]]) -> str | None:
    numbered = [(name, number) for name, _, number in listed if number]
    if len(numbered) == 1:
        return numbered[0][1]
    return "; ".join(f"{number} ({name})" for name, number in numbered) or None


def enrich(
    fields: list[dict], options: dict | None = None, *, ocr_text: str | None = None
) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value: Any, *, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        item = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": value}
        if default:
            item["default"] = True
        out.append(item)
        seen.add(name)

    name = _text(values.get("NguoiKeKhai_HoTen"))
    identity = _identity(values.get("NguoiKeKhai_SoDinhDanh"))
    birthday = _date(values.get("NguoiKeKhai_NgaySinh"))
    issue_date = _date(values.get("NguoiKeKhai_NgayCap"))
    issuer = _issuer(values.get("NguoiKeKhai_NoiCap"))
    phone = _phone(values.get("NguoiKeKhai_DienThoai")) or _phone_from_ocr(ocr_text)
    permanent = _area_of(values.get("NguoiKeKhai_ThuongTru"))
    current = _area_of(values.get("NguoiKeKhai_NoiOHienTai"))
    permanent, current = permanent or current, current or permanent

    if not name:
        warnings.append("Thiếu họ tên người kê khai.")
    if not identity:
        warnings.append("Thiếu số CCCD/định danh người kê khai.")
    if not permanent:
        warnings.append("Thiếu địa chỉ người kê khai (nơi thường trú và nơi ở hiện tại đều không đọc được).")
    if not phone:
        warnings.append("Giấy tờ không có số điện thoại người nộp — ô bắt buộc, cán bộ nhập tay.")

    # === Form 1: người nộp ===
    add("data[chonDoiTuong]", "Cá nhân", default=True)
    add("data[fullname]", name)
    add("data[birthday]", birthday)
    add("data[gender]", _gender_from_cccd(identity) or _text(values.get("NguoiKeKhai_GioiTinh")))
    add("data[identityNumber]", identity)
    add("data[identityDate]", issue_date)
    add("data[identityAgency]", issuer)
    add("data[phoneNumber]", phone)
    add("data[nation]", "Việt Nam", default=True)
    if permanent:
        add("data[province]", _province_label(permanent.get("tinh")))
        add("data[district]", _text(permanent.get("xa")))
        add("data[address]", _text(permanent.get("diaChi")))

    # === Form 2: người kê khai ===
    add(f"{_PANEL}[fullName]", name)
    add(f"{_PANEL}[identityNumber]", identity)
    add(f"{_PANEL}[identityDate]", issue_date)
    add(f"{_PANEL}[identityAgency]", issuer)
    add(f"{_PANEL}[address]", _area_line(current))
    add(f"{_PANEL}[address1]", _area_line(permanent))

    # === Form 2: vợ/chồng ===
    add(f"{_PANEL}[fullName2]", _text(values.get("VoChong_HoTen")))
    add(f"{_PANEL}[identityNumber1]", _identity(values.get("VoChong_SoDinhDanh")))
    add(f"{_PANEL}[identityDate1]", _date(values.get("VoChong_NgayCap")))
    add(f"{_PANEL}[identityAgency1]", _issuer(values.get("VoChong_NoiCap")))
    add(f"{_PANEL}[dangKyKetHon]", _text(values.get("DangKyKetHon_So")))

    # === Form 2: thành viên hộ gia đình ===
    listed, inferred = _household(
        values.get("Ho_ThanhVien"), values.get("NguoiKeKhai_QuanHeChuHo"), name, identity
    )
    add(f"{_PANEL}[thanhVien]", "; ".join(f"{member} ({label})" for member, label, _ in listed))
    add(f"{_PANEL}[identityNumber2]", _member_numbers(listed))
    if inferred:
        warnings.append(
            "CT07 chỉ ghi quan hệ với chủ hộ, quan hệ với người kê khai của " + ", ".join(inferred)
            + " là suy luận — cán bộ xác nhận lại ô thành viên hộ gia đình."
        )

    # === Form 2: đối tượng + ký ===
    add(f"{_PANEL}[doiTuong]", _text(values.get("NguoiKeKhai_DoiTuong")))
    add(f"{_PANEL}[TinTTTe]", _sign_province(values.get("ToKhai_NoiKy")))
    sign_date = _date(values.get("ToKhai_NgayKy"))
    add(f"{_PANEL}[TDTTK]", sign_date)
    add(f"{_PANEL}[nguoiLamDon]", name.title() if name else None)
    if not sign_date:
        warnings.append("Không đọc được ngày ký tờ khai — đã xoá ngày cổng điền sẵn, cán bộ nhập tay.")

    keep_part_one = account_is_applicant(options, identity)
    for blank in () if keep_part_one else _PART_ONE_BLANK:
        _clear(out, seen, blank)
    for blank in _PART_TWO_BLANK:
        _clear(out, seen, blank)
    return out, warnings


def _clear(out: list[dict], seen: set[str], name: str) -> None:
    if name in seen:
        return
    item = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": "", "clear": True}
    if name in _REQUIRED_BLANK:
        item["markEmpty"] = True
    out.append(item)
    seen.add(name)
