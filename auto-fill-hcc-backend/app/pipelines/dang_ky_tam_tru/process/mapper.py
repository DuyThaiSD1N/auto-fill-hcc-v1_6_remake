"""Dựng ô form Đăng ký tạm trú (Cổng DVC Bộ Công an) từ dữ kiện compact."""

import re
from typing import Any

from app.pipelines._shared.naming import fold
from app.pipelines.dang_ky_tam_tru.process.schema import (
    DATE_FORMAT_FULL,
    DATE_FORMAT_MONTH,
    DATE_FORMAT_YEAR,
    HOUSEHOLD_HEAD,
    ROLE_OWNER,
    UI_COMP_BY_NAME,
)

# Đoạn địa chỉ từ cấp xã trở lên — cắt khỏi ô "Địa chỉ" (txtSUGGEST_ADDRESS) vì Tỉnh/Xã đã có ô chọn riêng.
_AREA_PREFIX = re.compile(r"^(phuong|xa|thi tran|dac khu|quan|huyen|thi xa|thanh pho|tinh|tp)\b")
_EMAIL = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.replace("\n", " ").split()).strip(" :;,-")
    # Dòng chấm chấm của mẫu in ("………", "....") là ô trống.
    return text if text and re.search(r"[0-9A-Za-zÀ-ỹ]", text) else None


def _name(value: Any) -> str | None:
    text = _text(value)
    return text.upper() if text else None


def _date_parts(value: Any) -> tuple[str, str] | None:
    """→ (định dạng trên cổng, giá trị ô ngày) theo lượng thông tin giấy ghi được."""
    text = _text(value)
    if not text:
        return None
    nums = re.findall(r"\d+", text)
    if len(nums) >= 3:
        day, month, year = nums[0], nums[1], nums[2]
        if len(year) == 4 and 1 <= int(day) <= 31 and 1 <= int(month) <= 12:
            return DATE_FORMAT_FULL, f"{int(day):02d}/{int(month):02d}/{year}"
        return None
    if len(nums) == 2 and len(nums[1]) == 4 and 1 <= int(nums[0]) <= 12:
        return DATE_FORMAT_MONTH, f"{int(nums[0]):02d}/{nums[1]}"
    if len(nums) == 1 and len(nums[0]) == 4:
        return DATE_FORMAT_YEAR, nums[0]
    return None


def _full_date(value: Any) -> str | None:
    parts = _date_parts(value)
    return parts[1] if parts and parts[0] == DATE_FORMAT_FULL else None


def _identity(value: Any) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits if len(digits) == 12 else None


def _gender(value: Any, identity: str | None) -> str | None:
    folded = fold(str(value or ""))
    if folded in ("nam", "male"):
        return "Nam"
    if folded in ("nu", "female"):
        return "Nữ"
    # Không đọc được giới tính: chữ số thứ 4 của số định danh mã hoá giới tính (chẵn = nam, lẻ = nữ).
    if identity:
        return "Nữ" if int(identity[3]) % 2 else "Nam"
    return None


def _phone(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text.upper().replace("O", "0"))
    if digits.startswith("84") and len(digits) == 11:
        digits = "0" + digits[2:]
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    return digits if len(digits) == 10 and digits.startswith("0") else None


def _email(value: Any) -> str | None:
    text = (_text(value) or "").replace(" ", "").lower()
    return text if _EMAIL.match(text) else None


def _address_below_ward(value: Any) -> str | None:
    """Giữ phần dưới cấp xã: "Số 12 ngõ 45, phường X, thành phố Y" → "Số 12 ngõ 45"."""
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"\(.*?\)", "", text)  # ghi chú địa giới cũ trong ngoặc
    kept: list[str] = []
    for part in (p.strip() for p in text.split(",")):
        if not part:
            continue
        if _AREA_PREFIX.match(fold(part)):
            break
        kept.append(part)
    return ", ".join(kept).strip(" ,.") or None


def _owner_consent_row(values: dict, registrant_id: str | None, registrant_name: str | None) -> dict:
    """Dòng 0 "Danh sách người cần xin ý kiến" (xác nhận tờ khai qua VNeID) = chủ sở hữu chỗ ở hợp pháp.

    Chỉ điền khi chủ sở hữu là người KHÁC người đăng ký (thuê/mượn/ở nhờ, ở nhà người thân); tự là chủ sở hữu thì
    không ai cần xin ý kiến. Ngày sinh chỉ điền khi đủ dd/mm/yyyy — GCN thường chỉ ghi năm sinh, để trống (ô đỏ) cho
    công dân bổ sung theo CCCD của chủ sở hữu thay vì bịa ngày.
    """
    name = _name(values.get("ChuSoHuu_HoTen"))
    if not name:
        return {}
    owner_id = _identity(values.get("ChuSoHuu_SoDinhDanh"))
    same_person = (owner_id == registrant_id) if (owner_id and registrant_id) else fold(name) == fold(registrant_name or "")
    if same_person:
        return {}
    return {
        "txtFULLNAME0": name,
        "txtCITIZENNUMBER0": owner_id,
        "txtDOB0": _full_date(values.get("ChuSoHuu_NgaySinh")),
        "cboROLESID0": ROLE_OWNER,
    }


def enrich(fields: list[dict]) -> list[dict]:
    values = _by_name(fields)
    picked: dict[str, Any] = {}

    identity = _identity(values.get("NguoiDangKy_SoDinhDanh"))
    picked["txtFULLNAME"] = _name(values.get("NguoiDangKy_HoTen"))
    dob = _date_parts(values.get("NguoiDangKy_NgaySinh"))
    if dob:
        # Định dạng phải chọn TRƯỚC: ô ngày sinh của cổng đổi mặt nạ nhập theo ô này.
        picked["cboDATE_FORMAT"], picked["txtDOB"] = dob
    picked["cboGENDER_CODE"] = _gender(values.get("NguoiDangKy_GioiTinh"), identity)
    picked["txtIDENTIFIER_NUMBER"] = identity
    picked["txtPHONE_NUMBER"] = _phone(values.get("NguoiDangKy_SoDienThoai"))
    picked["txtEMAIL"] = _email(values.get("NguoiDangKy_Email"))
    picked["txtSUGGEST_ADDRESS"] = _address_below_ward(values.get("NoiTamTru_DiaChiChiTiet"))
    picked["txtCHANGED_NOTE"] = _text(values.get("NoiDungDeNghi"))
    picked["txtTEMP_RESIDENT_TO"] = _full_date(values.get("ThoiHan_DenNgay"))
    relation = _text(values.get("ChuHo_QuanHe"))
    # Form mặc định "lập hộ mới": người đăng ký là chủ hộ tạm trú. CT01 ghi quan hệ khác thì vẫn chọn "Chủ hộ"
    # (lập hộ mới chỉ có chủ hộ) nhưng tô vàng, cũng như khi giấy không ghi.
    picked["cboHH_PERSON_RELATIONSHIP_CODE"] = HOUSEHOLD_HEAD
    defaults = set() if relation and fold(relation) == fold(HOUSEHOLD_HEAD) else {"cboHH_PERSON_RELATIONSHIP_CODE"}
    picked.update(_owner_consent_row(values, identity, picked.get("txtFULLNAME")))

    out = []
    for name, comp in UI_COMP_BY_NAME.items():
        if picked.get(name) in (None, ""):
            continue
        field = {"name": name, "comp": comp, "value": picked[name]}
        if name in defaults:
            field["default"] = True
        out.append(field)
    return out
