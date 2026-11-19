"""Map compact source facts → Form.io data[...] cho [Lâm Đồng] tính hoặc tính lại tiền sử dụng đất theo NĐ 50/2026/NĐ-CP
(1.115148).

Ba khối theo file mapping: Người nộp (Phần I + Ghi chú) · Thửa đất (Phần II, chỉ Tỉnh + Phường/Xã) · Chủ hồ sơ (Phần
III). Phần IV (mã/ngày/đơn vị cấp giấy phép) không có trong giấy tờ → không điền. Các hàm chuẩn hóa (địa chỉ cũ → mới,
tỉnh, ngày, nơi cấp CCCD, SĐT) dùng lại của các thủ tục cùng form Lâm Đồng.

Người nộp (Phần I) có ba trường hợp:
  1. Hồ sơ có giấy của người nộp thay (Giấy ủy quyền bên B, hoặc CCCD của người KHÁC chủ hồ sơ) → Phần I = người đó,
     Phần III = chủ hồ sơ, không bấm nút "Người nộp là chủ hồ sơ".
  2. Không có giấy người nộp nhưng tài khoản đăng nhập (formContext, cổng đổ sẵn Phần I) là người KHÁC chủ hồ sơ → giữ
     nguyên Phần I của cổng (không ghi đè bằng chủ hồ sơ), tô đỏ ô bắt buộc còn trống, điền thẳng Phần III.
  3. Còn lại (tự nộp) → Phần I = chủ hồ sơ rồi bấm nút để form tự chép xuống Phần III.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines.chuyen_muc_dich_su_dung_dat_lam_dong.process.mapper import (
    _area,
    _by_name,
    _cccd_issuer,
    _date,
    _fold,
    _identity,
    _province,
    _text,
)
from app.pipelines.giao_thue_dat_giao_rung_gia_han_su_dung_dat.process.mapper import _phone

from .schema import UI_COMP_BY_NAME

PORTAL_PROVINCE = "Lâm Đồng"

# Ô người extension CHỊU TRÁCH NHIỆM điền từ CCCD/Đơn. Thiếu dữ liệu → "dom-expect" để FE tô đỏ (không điền).
_EXPECT_APPLICANT = (
    "data[fullname]", "data[birthday]", "data[gender]", "data[identityNumber]",
    "data[identityDate]", "data[identityAgency]", "data[phoneNumber]",
    "data[province]", "data[district]", "data[address]",
)
# Tài khoản là người khác (trường hợp 2): cổng đã đổ họ tên / ngày sinh / số định danh — chỉ nhắc ô bắt buộc cổng để trống.
_EXPECT_ACCOUNT_APPLICANT = ("data[phoneNumber]", "data[province]", "data[district]", "data[address]")
_EXPECT_OWNER = (
    "data[ownerFullname]", "data[ownerBirthday]", "data[gender1]", "data[ownerIdentityNumber]",
    "data[ownerIdentityDate]", "data[ownerIdentityAgency]", "data[ownerPhoneNumber]",
    "data[province1]", "data[district1]", "data[ownerAddress]",
)

_AREA_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _gender(value: Any, identity: str | None) -> str | None:
    """"Nam"/"Nữ" từ giấy tờ ("Ông"/"Bà" trên Đơn cũng nhận); không có thì suy từ chữ số thứ 4 của số định danh 12 chữ
    số (mã giới tính + thế kỷ sinh: chẵn = nam, lẻ = nữ)."""
    folded = _fold(value)
    if folded in ("nam", "ong", "male", "m"):
        return "Nam"
    if folded in ("nu", "ba", "female", "f"):
        return "Nữ"
    if identity and len(identity) == 12:
        return "Nam" if int(identity[3]) % 2 == 0 else "Nữ"
    return None


def _number(value: Any) -> str | None:
    """Số thửa / số tờ bản đồ: chỉ phần số ("Thửa Đất Số 931" → "931", "TBĐ 10" → "10")."""
    match = re.search(r"\d+[A-Za-z]?", _text(value) or "")
    return match.group(0) if match else None


def _land_area(value: Any) -> str | None:
    """Diện tích thửa đất giữ nguyên dấu thập phân của giấy ("520,0 m²" → "520,0")."""
    match = _AREA_NUMBER_RE.search((_text(value) or "").replace(" ", ""))
    return match.group(0) if match else None


def _land(value: Any) -> dict | None:
    """Địa chỉ thửa đất; Đơn chỉ ghi phường/xã mà thiếu tỉnh → tỉnh của cổng (thửa đất nộp tại Lâm Đồng)."""
    if isinstance(value, dict) and not _text(value.get("tinh")) and _text(value.get("xa")):
        value = {**value, "tinh": PORTAL_PROVINCE}
    return _area(value)


def ghi_chu(values: dict, land: dict | None) -> str | None:
    """Ô "Ghi Chú:" — form không có ô số thửa / tờ bản đồ / diện tích nên ghi vào đây (gợi ý của file mapping):
    "Thửa đất số 12, tờ bản đồ số 3, diện tích 250,5 m², Thôn A, Xã B, Tỉnh Lâm Đồng". Chỉ ghép fact đã đọc được."""
    thua = _number(values.get("ThuaDat_SoThua"))
    to_ban_do = _number(values.get("ThuaDat_SoTo"))
    dien_tich = _land_area(values.get("ThuaDat_DienTich"))
    parts: list[str] = []
    if thua:
        parts.append(f"Thửa đất số {thua}")
    if to_ban_do:
        parts.append(f"tờ bản đồ số {to_ban_do}")
    if dien_tich:
        parts.append(f"diện tích {dien_tich} m²")
    if not parts:
        return None
    if land:
        parts.extend(p for p in (_text(land.get("diaChi")), _text(land.get("xa")), _province(land.get("tinh"))) if p)
    text = ", ".join(parts)
    return text[0].upper() + text[1:]


def _account(options: dict | None) -> tuple[str | None, str | None]:
    context = (options or {}).get("formContext") or {}
    return (_identity(context.get("applicantIdentityNumber") or context.get("identityNumber")),
            _text(context.get("applicantFullname") or context.get("fullname")))


def account_is_other_person(options: dict | None, owner_name: str | None, owner_identity: str | None) -> bool:
    """Tài khoản đăng nhập (Phần I cổng đổ sẵn) là người KHÁC chủ hồ sơ. So họ tên trước: số định danh trên Đơn hay viết
    tay, đọc lệch một chữ số không được coi là người khác; không có tên mới so số."""
    account_identity, account_name = _account(options)
    if account_name and owner_name:
        return _fold(account_name) != _fold(owner_name)
    if account_identity and owner_identity:
        return account_identity != owner_identity
    return False


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    def expect(names: tuple[str, ...]) -> None:
        for name in names:
            if name not in seen:
                out.append({"name": name, "comp": "dom-expect", "value": ""})
                seen.add(name)

    owner_name = _text(values.get("ChuHoSo_HoTen"))
    owner_identity = _identity(values.get("ChuHoSo_SoDinhDanh"))
    owner = {
        "name": owner_name,
        "identity": owner_identity,
        "birthday": _date(values.get("ChuHoSo_NgaySinh")),
        "gender": _gender(values.get("ChuHoSo_GioiTinh"), owner_identity),
        "phone": _phone(values.get("ChuHoSo_DienThoai")),
        "email": _text(values.get("ChuHoSo_Email")),
        "id_date": _date(values.get("ChuHoSo_NgayCapCccd")),
        "id_agency": _cccd_issuer(values.get("ChuHoSo_NoiCapCccd"), values.get("ChuHoSo_NgayCapCccd")),
        "residence": _area(values.get("ChuHoSo_ThuongTru")),
    }

    # Người nộp thay chỉ tính khi thật sự là NGƯỜI KHÁC (LLM có lúc chép lại chính chủ hồ sơ vào object).
    rep = values.get("NguoiNopThay")
    rep = rep if isinstance(rep, dict) else {}
    rep_name = _text(rep.get("hoTen"))
    rep_identity = _identity(rep.get("soDinhDanh"))
    same_as_owner = bool((rep_name and owner_name and _fold(rep_name) == _fold(owner_name))
                         or (rep_identity and owner_identity and rep_identity == owner_identity))
    has_rep = bool(rep_name or rep_identity) and not same_as_owner
    account_other = not has_rep and account_is_other_person(options, owner_name, owner_identity)

    # ---- Phần I: Thông tin người nộp ----
    if has_rep:
        # Hai người khác nhau → không mượn SĐT/email/nơi ở của chủ hồ sơ cho người đi nộp thay.
        sub = {
            "name": rep_name,
            "identity": rep_identity,
            "birthday": _date(rep.get("ngaySinh")),
            "gender": _gender(rep.get("gioiTinh"), rep_identity),
            "phone": _phone(rep.get("dienThoai")),
            "email": None,
            "id_date": _date(rep.get("ngayCapCccd")),
            "id_agency": _cccd_issuer(rep.get("noiCapCccd"), rep.get("ngayCapCccd")),
            "residence": _area(rep.get("thuongTru")),
        }
    elif account_other:
        sub = None
    else:
        sub = owner

    if sub is not None:
        add("data[fullname]", sub["name"])
        add("data[birthday]", sub["birthday"])
        add("data[gender]", sub["gender"])
        add("data[phoneNumber]", sub["phone"])
        add("data[email]", sub["email"])
        add("data[identityNumber]", sub["identity"])
        add("data[identityDate]", sub["id_date"])
        add("data[identityAgency]", sub["id_agency"])
        add("data[nation]", "Việt Nam" if sub["name"] or sub["identity"] else None)
        residence = sub["residence"]
        if residence:
            add("data[province]", _province(residence.get("tinh")))
            add("data[district]", _text(residence.get("xa")))
            add("data[address]", _text(residence.get("diaChi")))
    # "Cơ quan/ tổ chức" CHỈ cho hồ sơ PHÁP NHÂN; cá nhân/chủ hộ để trống.
    add("data[organization]", _text(values.get("ToChuc_Ten")))
    land = _land(values.get("ThuaDat_DiaChi"))
    add("data[ghiChu]", ghi_chu(values, land))
    expect(_EXPECT_ACCOUNT_APPLICANT if sub is None else _EXPECT_APPLICANT)

    # ---- Phần II: Thông tin thửa đất (chỉ Tỉnh + Phường/Xã) ----
    if land:
        add("data[province2]", _province(land.get("tinh")))
        add("data[village2]", _text(land.get("xa")))

    # ---- Phần III: Thông tin chủ hồ sơ ----
    if sub is owner:
        add("data[BUTTON3]", True)
    else:
        add("data[ownerFullname]", owner["name"])
        add("data[ownerBirthday]", owner["birthday"])
        add("data[gender1]", owner["gender"])
        add("data[ownerPhoneNumber]", owner["phone"])
        add("data[ownerEmail]", owner["email"])
        add("data[ownerIdentityNumber]", owner["identity"])
        add("data[ownerIdentityDate]", owner["id_date"])
        add("data[ownerIdentityAgency]", owner["id_agency"])
        add("data[nation1]", "Việt Nam" if owner["name"] or owner["identity"] else None)
        if owner["residence"]:
            add("data[province1]", _province(owner["residence"].get("tinh")))
            add("data[district1]", _text(owner["residence"].get("xa")))
            add("data[ownerAddress]", _text(owner["residence"].get("diaChi")))
        expect(_EXPECT_OWNER)

    if account_other:
        warnings.append("Tài khoản đăng nhập không phải chủ hồ sơ trên Đơn và hồ sơ không có CCCD / giấy ủy quyền của "
                        "người nộp — giữ Phần I theo tài khoản, điền Phần III theo Đơn; cán bộ nhập số điện thoại và "
                        "địa chỉ của người nộp.")
    if not owner_name or not owner_identity:
        warnings.append("Thiếu họ tên/số định danh chủ hồ sơ từ Đơn hoặc CCCD.")
    if not land:
        warnings.append("Chưa đọc được địa chỉ thửa đất (Phần II) từ Đơn / Giấy chứng nhận.")
    return out, warnings
