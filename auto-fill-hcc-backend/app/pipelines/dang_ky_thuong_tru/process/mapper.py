"""Dựng ô form Đăng ký thường trú (Cổng DVC Bộ Công an) từ dữ kiện compact."""

import re
from typing import Any

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.naming import fold
from app.pipelines.dang_ky_thuong_tru.process.schema import (
    AGENCY_CITY_ID,
    AGENCY_FIELD,
    AGENCY_WARD_ID,
    CASE_FIRST_TIME,
    CASE_SELECT_ID,
    CASES,
    DATE_FORMAT_FULL,
    DATE_FORMAT_MONTH,
    DATE_FORMAT_YEAR,
    HOUSEHOLD_EXISTING,
    HOUSEHOLD_NEW,
    MEMBER_ADD_SELECTOR,
    MEMBER_IDS,
    UI_COMP_BY_NAME,
)

PROCEDURE_KEY = "dang-ky-thuong-tru"
# Xã + tỉnh của tài khoản quầy (server gắn ở app/process/router.py, client không tự gửi được).
ACCOUNT_AGENCY_OPTION = "_accountAgency"

# Đoạn địa chỉ từ cấp xã trở lên — ô "Địa chỉ" nơi đề nghị chỉ nhận phần dưới xã (cổng chặn chữ tên xã/tỉnh).
_AREA_PREFIX = re.compile(r"^(phuong|xa|thi tran|dac khu|quan|huyen|thi xa|thanh pho|tinh|tp)\b")
_EMAIL = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Bản sao options kèm xã/tỉnh tài khoản: dự phòng ô Cơ quan thực hiện (bắt buộc) khi giấy không ghi."""
    result = dict(options or {})
    result.pop(ACCOUNT_AGENCY_OPTION, None)
    if procedure == PROCEDURE_KEY and isinstance(user, dict) and user.get("tinh") and user.get("xa"):
        result[ACCOUNT_AGENCY_OPTION] = {"tinh": str(user["tinh"]), "xa": str(user["xa"])}
    return result


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
    """Giữ phần dưới cấp xã: "Số 12 ngõ 45, phường X, tỉnh Y" → "Số 12 ngõ 45"."""
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


def _agency(values: dict) -> tuple[str | None, str | None]:
    """Tỉnh + Xã của cơ quan đăng ký cư trú theo địa giới hiện hành (nhãn tỉnh đúng danh mục của cổng)."""
    province, ward = _text(values.get("CoQuan_Tinh")), _text(values.get("CoQuan_Xa"))
    if not province:
        return None, None
    area = remap_area({"quocGia": "Việt Nam", "tinh": province, "xa": ward or ""}) or {}
    return province_label(_text(area.get("tinh")) or province), _text(area.get("xa")) or ward


def _household(values: dict, registrant_id: str | None) -> str | None:
    """Nhãn radio Hình thức theo phân loại của LLM; LLM bỏ trống thì suy từ mục 7–9 CT01."""
    picked = fold(_text(values.get("HinhThuc")) or "")
    if "lap ho moi" in picked:
        return HOUSEHOLD_NEW
    if "vao ho" in picked:
        return HOUSEHOLD_EXISTING
    relation = fold(_text(values.get("ChuHo_QuanHe")) or "")
    head_id = _identity(values.get("ChuHo_SoDinhDanh"))
    if relation == "chu ho" or (head_id and head_id == registrant_id):
        return HOUSEHOLD_NEW
    if relation and _text(values.get("ChuHo_HoTen")):
        return HOUSEHOLD_EXISTING
    return None


def _case(value: Any) -> str | None:
    want = fold(_text(value) or "")
    if not want:
        return None
    exact = next((label for label in CASES if fold(label) == want), None)
    if exact:
        return exact
    # LLM hay rút gọn nhãn dài ("lần đầu", "nhân khẩu", "cả hộ") — khớp theo phần đuôi đặc trưng của nhãn.
    for key, label in (("lan dau", CASE_FIRST_TIME), ("nhan khau", CASES[1]), ("ca ho", CASES[0])):
        if key in want:
            return label
    return None


def _member_rows(value: Any) -> list[list[dict]]:
    rows: list[list[dict]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict) or not _name(item.get("hoTen")):
            continue
        identity = _identity(item.get("soDinhDanh"))
        dob = _date_parts(item.get("ngaySinh"))
        values = {
            "hoTen": _name(item.get("hoTen")),
            # Ô ngày sinh của bảng là ô chữ thường (không có ô định dạng) → ghi đúng chữ giấy cho.
            "ngaySinh": dob[1] if dob else None,
            "gioiTinh": _gender(item.get("gioiTinh"), identity),
            "soDinhDanh": identity,
            "quanHeVoiChuHo": _text(item.get("quanHeVoiChuHo")),
        }
        index = len(rows)
        rows.append([
            {"id": f"{prefix}{index}", "comp": comp, "value": values[key]}
            for key, (prefix, comp) in MEMBER_IDS.items() if values[key]
        ])
    return rows


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    values = _by_name(fields)
    picked: dict[str, Any] = {}
    defaults: set[str] = set()

    province, ward = _agency(values)
    if not (province and ward):
        # Ô bắt buộc mà giấy không ghi cơ quan → xã/tỉnh tài khoản quầy, tô vàng để cán bộ soát.
        account = (options or {}).get(ACCOUNT_AGENCY_OPTION) or {}
        fallback = _agency({"CoQuan_Tinh": account.get("tinh"), "CoQuan_Xa": account.get("xa")})
        if fallback[0] and fallback[1]:
            (province, ward), defaults = fallback, {AGENCY_FIELD}
    if province and ward:
        picked[AGENCY_FIELD] = {"province": province, "ward": ward, "cityId": AGENCY_CITY_ID, "wardId": AGENCY_WARD_ID,
                                "readySelect": CASE_SELECT_ID}
    case = _case(values.get("TruongHop"))
    picked[CASE_SELECT_ID] = case

    identity = _identity(values.get("NguoiDangKy_SoDinhDanh"))
    # "Lần đầu" cổng ép "vào hộ đã có" và khoá radio.
    household = HOUSEHOLD_EXISTING if case == CASE_FIRST_TIME else _household(values, identity)
    picked["radIsHouseHold"] = household
    dob = _date_parts(values.get("NguoiDangKy_NgaySinh"))
    if dob:
        # Định dạng phải chọn TRƯỚC: đổi định dạng là cổng xoá ô ngày sinh.
        picked["cboFORMAT_DATE"], picked["txtBIRTH_DATE"] = dob
    picked["txtFULLNAME"] = _name(values.get("NguoiDangKy_HoTen"))
    picked["cboGENDER_ID"] = _gender(values.get("NguoiDangKy_GioiTinh"), identity)
    picked["txtID_CARD_NUMBER"] = identity
    picked["txtPHONE_NUMBER"] = _phone(values.get("NguoiDangKy_SoDienThoai"))
    picked["txtEMAIL"] = _email(values.get("NguoiDangKy_Email"))
    picked["txtSUGGEST_DETAIL_ADDR"] = _address_below_ward(values.get("NoiDangKy_DiaChiChiTiet"))
    picked["txtCHANGED_CONTENT_NOTE"] = _text(values.get("NoiDungDeNghi"))
    if household == HOUSEHOLD_EXISTING:
        # Lập hộ mới: cổng tự đặt "Chủ hộ" + chép người đề nghị vào khối chủ hộ rồi khoá → không điền.
        picked["txtHH_HEAD_FULLNAME"] = _name(values.get("ChuHo_HoTen"))
        picked["cboRELATIONSHIP_WITH_HHHEAD_ID"] = _text(values.get("ChuHo_QuanHe"))
        picked["txtID_CARD_NUMBER_HHEAD"] = _identity(values.get("ChuHo_SoDinhDanh"))
    rows = _member_rows(values.get("ThanhVien"))
    if rows:
        picked["tblNguoi_CUNGTD"] = {"addSelector": MEMBER_ADD_SELECTOR, "rows": rows}

    out = []
    for name, comp in UI_COMP_BY_NAME.items():
        if picked.get(name) in (None, ""):
            continue
        field = {"name": name, "comp": comp, "value": picked[name]}
        if name == AGENCY_FIELD:
            field["onlyIfEmpty"] = True
        if name in defaults:
            field["default"] = True
        out.append(field)
    return out
