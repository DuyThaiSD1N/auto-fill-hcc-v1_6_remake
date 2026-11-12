"""Map compact source facts → Form.io data[...] cho [Lâm Đồng] giao đất, cho thuê đất, chuyển mục đích sử dụng đất,
giao rừng, gia hạn sử dụng đất (1.116366).

Ba khối theo file mapping: Người nộp (Phần I) · Thửa đất (Phần II, chỉ Tỉnh + Phường/Xã) · Chủ hồ sơ (Phần III).
Không có Phần IV Giấy chứng nhận, ô "Ghi chú" để người dân tự ghi. Các hàm chuẩn hóa (địa chỉ cũ → mới, tỉnh, ngày,
nơi cấp CCCD) dùng lại của thủ tục cùng form 1.116365 Lâm Đồng.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines.chuyen_muc_dich_su_dung_dat_lam_dong.process.mapper import (
    _area,
    _by_name,
    _cccd_issuer,
    _date,
    _identity,
    _province,
    _text,
)

from .schema import UI_COMP_BY_NAME

# Ô người extension CHỊU TRÁCH NHIỆM điền từ CCCD/Đơn. Thiếu dữ liệu → "dom-expect" để FE tô đỏ (không điền).
_EXPECT_APPLICANT = (
    "data[fullname]", "data[birthday]", "data[gender]", "data[identityNumber]",
    "data[identityDate]", "data[identityAgency]", "data[phoneNumber]",
)
_EXPECT_OWNER = (
    "data[ownerFullname]", "data[ownerBirthday]", "data[gender1]", "data[ownerIdentityNumber]",
    "data[ownerIdentityDate]", "data[ownerIdentityAgency]", "data[ownerPhoneNumber]",
)

# Đơn hay ghi hai số: "0912345678 (0987654321)", "0912 345 678 / 0987…", "… hoặc …" → cắt ở dấu ngăn, lấy số đầu.
_PHONE_SPLIT_RE = re.compile(r"[(),;/]|\s[-–]\s|\bho[aặ]c\b", re.IGNORECASE)


def _phone(value: Any) -> str | None:
    """Số điện thoại ĐẦU TIÊN 10-11 chữ số bắt đầu bằng 0 (thiếu số 0 đầu thì thêm)."""
    text = _text(value)
    if not text:
        return None
    for chunk in _PHONE_SPLIT_RE.split(text):
        digits = re.sub(r"\D+", "", (chunk or "").upper().replace("O", "0"))
        if not digits:
            continue
        if digits.startswith("84") and len(digits) in (11, 12):
            digits = "0" + digits[2:]
        if len(digits) == 9 and not digits.startswith("0"):
            digits = "0" + digits
        if 10 <= len(digits) <= 11 and digits.startswith("0"):
            return digits
    return None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    del options
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

    # Có ủy quyền: Phần I = người ĐƯỢC ủy quyền (object NguoiDuocUyQuyen, dự phòng DaiDien_*), Phần III = người đề nghị.
    rep = values.get("NguoiDuocUyQuyen")
    rep = rep if isinstance(rep, dict) else {}

    def _rep(obj_key: str, flat_key: str | None = None):
        value = rep.get(obj_key)
        if value in (None, "", {}, []) and flat_key:
            value = values.get(flat_key)
        return value

    rep_name = _text(_rep("hoTen", "DaiDien_HoTen"))
    rep_identity = _identity(_rep("soDinhDanh", "DaiDien_SoDinhDanh"))
    has_uy_quyen = bool(rep_name or rep_identity)

    owner_name = _text(values.get("Nguoi_HoTen"))
    owner_identity = _identity(values.get("Nguoi_SoDinhDanh"))
    owner_birthday = _date(values.get("Nguoi_NgaySinh"))
    owner_gender = _text(values.get("Nguoi_GioiTinh"))
    owner_phone = _phone(values.get("Nguoi_DienThoai"))
    owner_email = _text(values.get("Nguoi_Email"))
    owner_id_date = _date(values.get("Nguoi_NgayCapCccd"))
    owner_id_agency = _cccd_issuer(values.get("Nguoi_NoiCapCccd"), values.get("Nguoi_NgayCapCccd"))
    owner_residence = _area(values.get("Nguoi_ThuongTru"))

    if has_uy_quyen:
        # Hai người khác nhau → không mượn SĐT/email/nơi ở của người đề nghị cho người đi nộp thay.
        sub_name, sub_identity = rep_name, rep_identity
        sub_birthday = _date(_rep("ngaySinh"))
        sub_gender = _text(_rep("gioiTinh"))
        sub_phone = _phone(_rep("dienThoai", "DaiDien_DienThoai"))
        sub_email = _text(values.get("DaiDien_Email"))
        sub_id_date = _date(_rep("ngayCapCccd"))
        sub_id_agency = _cccd_issuer(_rep("noiCapCccd"), _rep("ngayCapCccd"))
        sub_residence = _area(_rep("thuongTru"))
    else:
        sub_name, sub_identity, sub_birthday, sub_gender = owner_name, owner_identity, owner_birthday, owner_gender
        sub_phone, sub_email, sub_id_date, sub_id_agency = owner_phone, owner_email, owner_id_date, owner_id_agency
        sub_residence = owner_residence

    # ---- Phần I: Thông tin người nộp ----
    add("data[fullname]", sub_name)
    add("data[birthday]", sub_birthday)
    add("data[gender]", sub_gender)
    add("data[phoneNumber]", sub_phone)
    add("data[email]", sub_email)
    # "Cơ quan/ tổ chức" CHỈ cho hồ sơ PHÁP NHÂN; cá nhân/hộ gia đình để trống.
    add("data[organization]", _text(values.get("ToChuc_Ten")))
    add("data[identityNumber]", sub_identity)
    add("data[identityDate]", sub_id_date)
    add("data[identityAgency]", sub_id_agency)
    add("data[nation]", "Việt Nam" if sub_name or sub_identity else None)
    if sub_residence:
        add("data[province]", _province(sub_residence.get("tinh")))
        add("data[district]", _text(sub_residence.get("xa")))  # trên form Lâm Đồng data[district] là ô Phường/Xã
        add("data[address]", _text(sub_residence.get("diaChi")))
    expect(_EXPECT_APPLICANT)

    # ---- Phần II: Thông tin thửa đất (chỉ Tỉnh + Phường/Xã) ----
    land = _area(values.get("ThuaDat_DiaChi"))
    if land:
        add("data[province2]", _province(land.get("tinh")))
        add("data[village2]", _text(land.get("xa")))

    # ---- Phần III: Thông tin chủ hồ sơ ----
    # Tự nộp → bấm "Người nộp là chủ hồ sơ" (form tự chép Phần I xuống). Nộp thay → điền thẳng Phần III, không bấm nút.
    if not has_uy_quyen:
        add("data[BUTTON3]", True)
    else:
        add("data[ownerFullname]", owner_name)
        add("data[ownerBirthday]", owner_birthday)
        add("data[gender1]", owner_gender)
        add("data[ownerPhoneNumber]", owner_phone)
        add("data[ownerEmail]", owner_email)
        add("data[ownerIdentityNumber]", owner_identity)
        add("data[ownerIdentityDate]", owner_id_date)
        add("data[ownerIdentityAgency]", owner_id_agency)
        add("data[nation1]", "Việt Nam" if owner_name or owner_identity else None)
        if owner_residence:
            add("data[province1]", _province(owner_residence.get("tinh")))
            add("data[district1]", _text(owner_residence.get("xa")))
            add("data[ownerAddress]", _text(owner_residence.get("diaChi")))
        expect(_EXPECT_OWNER)

    if not owner_name or not owner_identity:
        warnings.append("Thiếu họ tên/số định danh người đề nghị (chủ hồ sơ) từ Đơn hoặc CCCD.")
    if not land:
        warnings.append("Chưa đọc được địa điểm thửa đất (Phần II) từ Đơn / Giấy chứng nhận.")
    return out, warnings
