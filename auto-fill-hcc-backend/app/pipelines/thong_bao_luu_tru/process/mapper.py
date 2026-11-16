"""Dựng ô form Thông báo lưu trú (Cổng DVC Bộ Công an) từ dữ kiện compact.

Danh sách người lưu trú ra MỘT field comp "bca-guest-list": value là list người, mỗi người
{"hoTen", "soDinhDanh", "fields": [{"id", "comp", "value"[, "default"]}]} — `id` là id ô trong modal "Thêm mới người
lưu trú", thứ tự trong `fields` là thứ tự extension điền (Quốc tịch trước Tỉnh/Xã vì chọn quốc tịch Việt Nam thì cổng
mới mở khối địa chỉ trong nước; Định dạng ngày sinh trước ô ngày sinh vì đổi định dạng là đổi lịch của ô đó).
"""

import re
from typing import Any

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.naming import fold
from app.pipelines.thong_bao_luu_tru.process.schema import (
    ACCOMMODATION_TYPES,
    AGENCY_FIELD,
    ACCOMMODATION_TYPES_LISTED,
    DOB_FMT_FULL,
    DOB_FMT_MONTH,
    DOB_FMT_YEAR,
    RESIDENCE_TYPES,
    UI_COMP_BY_NAME,
    VIET_NAM,
)

# Đoạn địa chỉ từ cấp xã trở lên — ô "Địa chỉ" chỉ nhận phần dưới xã (Tỉnh/Xã cơ sở lưu trú cổng tự chép).
_AREA_PREFIX = re.compile(r"^(phuong|xa|thi tran|dac khu|quan|huyen|thi xa|thanh pho|tinh|tp)\b")


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
            return DOB_FMT_FULL, f"{int(day):02d}/{int(month):02d}/{year}"
        return None
    if len(nums) == 2 and len(nums[1]) == 4 and 1 <= int(nums[0]) <= 12:
        return DOB_FMT_MONTH, f"{int(nums[0]):02d}/{nums[1]}"
    if len(nums) == 1 and len(nums[0]) == 4:
        return DOB_FMT_YEAR, nums[0]
    return None


def _full_date(value: Any) -> str | None:
    parts = _date_parts(value)
    return parts[1] if parts and parts[0] == DOB_FMT_FULL else None


def _identity(value: Any) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    # Ô ĐDCN/CCCD/CMND của cổng nhận 12 số (căn cước) hoặc 9 số (CMND).
    return digits if len(digits) in (9, 12) else None


def _passport(value: Any) -> str | None:
    text = re.sub(r"\s+", "", _text(value) or "").upper()
    return text if re.fullmatch(r"[A-Z0-9]{6,30}", text) and re.search(r"[A-Z]", text) else None


def _gender(value: Any, identity: str | None) -> str | None:
    folded = fold(str(value or ""))
    if folded in ("nam", "male"):
        return "Nam"
    if folded in ("nu", "female"):
        return "Nữ"
    # Không đọc được giới tính: chữ số thứ 4 của số định danh 12 số mã hoá giới tính (chẵn = nam, lẻ = nữ).
    if identity and len(identity) == 12:
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


def _address_below_ward(value: Any) -> str | None:
    """Giữ phần dưới cấp xã: "Số 12 ngõ 45, phường X, thành phố Y" → "Số 12 ngõ 45"."""
    if isinstance(value, dict):
        return _text(value.get("diaChi") or value.get("chiTietDuoiXa"))
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


def _accommodation_type(value: Any) -> str | None:
    want = fold(_text(value) or "")
    return next((label for label in ACCOMMODATION_TYPES if fold(label) == want), None) if want else None


def _residence(value: Any) -> dict:
    """noiCuTru → (tỉnh, xã, chi tiết) theo địa giới hiện hành; giấy ghi địa giới cũ thì quy đổi."""
    if not isinstance(value, dict):
        return {}
    area = {
        "quocGia": value.get("quocGia") or VIET_NAM,
        "tinh": value.get("tinh") or "",
        "xa": value.get("xa") or "",
        "diaChi": value.get("diaChi") or value.get("chiTietDuoiXa") or "",
    }
    if value.get("huyen"):
        area["huyen"] = value["huyen"]
    area = remap_area(area) or {}
    return {
        "province": province_label(_text(area.get("tinh"))),
        "ward": _text(area.get("xa")),
        "detail": _text(area.get("diaChi")),
    }


def _guest(item: Any) -> dict | None:
    if not isinstance(item, dict):
        return None
    name = _name(item.get("hoTen"))
    if not name:
        return None
    identity = _identity(item.get("soDinhDanh"))
    passport = _passport(item.get("soHoChieu")) or (None if identity else _passport(item.get("soDinhDanh")))
    nationality = _text(item.get("quocTich"))
    nationality_default = False
    if nationality and fold(nationality) in ("viet nam", "vietnam", "vietnamese", "viet nam (vnm)"):
        nationality = VIET_NAM
    # Số định danh cá nhân 12 số chỉ cấp cho công dân Việt Nam → quốc tịch Việt Nam (tô vàng để soát).
    if not nationality and identity and len(identity) == 12:
        nationality, nationality_default = VIET_NAM, True
    residence = _residence(item.get("noiCuTru")) if nationality == VIET_NAM else {}
    dob = _date_parts(item.get("ngaySinh"))

    rows: list[tuple[str, str, Any]] = [("guest_txtCITIZENNAME", "dom-input", name)]
    if dob:
        rows += [("guest_cboDOB_FMT", "dom-select", dob[0]), ("guest_txtDOB", "dom-date", dob[1])]
    rows += [
        ("guest_cboGENDER_ID", "dom-select", _gender(item.get("gioiTinh"), identity)),
        ("guest_txtIDCARD_NUMBER", "dom-input", identity),
        ("guest_txtPASSPORT_NO", "dom-input", passport),
        ("guest_txtPHONE_NUMBER", "dom-input", _phone(item.get("soDienThoai"))),
        ("guest_txtPLACE_OF_WORK", "dom-input", _text(item.get("noiLamViec"))),
        ("guest_mulNATIONALITY", "dom-select", nationality),
        ("guest_cboETHNIC_ID", "dom-select", _text(item.get("danToc")) if nationality == VIET_NAM else None),
        ("guest_radADDRESS_TYPE", "dom-radio", RESIDENCE_TYPES.get(fold(_text(item.get("loaiCuTru")) or ""))),
        ("guest_cboRDPROVINCE_ID", "dom-select", residence.get("province")),
        ("guest_cboRDADDRESS_ID", "dom-select", residence.get("ward") if residence.get("province") else None),
        ("guest_txtRDADDRESS", "dom-input", residence.get("detail")),
        ("guest_txtREASON", "dom-input", _text(item.get("lyDo"))),
        ("guest_txtSTART_DATE", "dom-date", _full_date(item.get("tuNgay"))),
        ("guest_txtEND_DATE", "dom-date", _full_date(item.get("denNgay"))),
        ("guest_txtROOM", "dom-input", _text(item.get("soPhong"))),
    ]
    fields = []
    for field_id, comp, value in rows:
        if value in (None, ""):
            continue
        field = {"id": field_id, "comp": comp, "value": value}
        if field_id == "guest_mulNATIONALITY" and nationality_default:
            field["default"] = True
        fields.append(field)
    return {"hoTen": name, "soDinhDanh": identity or passport or "", "fields": fields}


def _guests(value: Any) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for item in value if isinstance(value, list) else []:
        guest = _guest(item)
        if not guest:
            continue
        # Cùng một người lặp lại (Phiếu + thẻ đọc thành hai item) → cổng báo "đã tồn tại", chỉ giữ lần đầu.
        key = guest["soDinhDanh"] or fold(guest["hoTen"])
        if key in seen:
            continue
        seen.add(key)
        out.append(guest)
    return out


PROCEDURE_KEY = "thong-bao-luu-tru"
# Xã + tỉnh của tài khoản quầy (server gắn ở app/process/router.py, client không tự gửi được).
ACCOUNT_AGENCY_OPTION = "_accountAgency"


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Bản sao options kèm xã/tỉnh tài khoản: dự phòng ô Cơ quan thực hiện (bắt buộc) khi giấy không ghi."""
    result = dict(options or {})
    result.pop(ACCOUNT_AGENCY_OPTION, None)
    if procedure == PROCEDURE_KEY and isinstance(user, dict) and user.get("tinh") and user.get("xa"):
        result[ACCOUNT_AGENCY_OPTION] = {"tinh": str(user["tinh"]), "xa": str(user["xa"])}
    return result


def _agency(values: dict) -> tuple[str | None, str | None]:
    """Tỉnh + Xã của cơ quan tiếp nhận theo địa giới hiện hành (nhãn tỉnh đúng danh mục của cổng)."""
    province, ward = _text(values.get("CoQuan_Tinh")), _text(values.get("CoQuan_Xa"))
    if not province:
        return None, None
    area = remap_area({"quocGia": VIET_NAM, "tinh": province, "xa": ward or ""}) or {}
    return province_label(_text(area.get("tinh")) or province), _text(area.get("xa")) or ward


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    values = _by_name(fields)
    picked: dict[str, Any] = {}
    defaults: set[str] = set()
    province, ward = _agency(values)
    if not (province and ward):
        # Ô bắt buộc mà giấy không ghi cơ quan tiếp nhận → xã/tỉnh tài khoản quầy, tô vàng để cán bộ soát.
        account = (options or {}).get(ACCOUNT_AGENCY_OPTION) or {}
        fallback = _agency({"CoQuan_Tinh": account.get("tinh"), "CoQuan_Xa": account.get("xa")})
        if fallback[0] and fallback[1]:
            (province, ward), defaults = fallback, {AGENCY_FIELD}
    picked[AGENCY_FIELD] = {"province": province, "ward": ward} if province and ward else None
    accommodation = _accommodation_type(values.get("CoSo_LoaiHinh"))
    picked["accomStay_cboACCOMMODATION_TYPE"] = accommodation
    if accommodation not in ACCOMMODATION_TYPES_LISTED:
        picked["accomStay_txtNAME_T"] = _text(values.get("CoSo_Ten"))
    picked["accomStay_txtADDRESS"] = _address_below_ward(values.get("CoSo_DiaChi"))
    picked["listTTNguoiLuuTru"] = _guests(values.get("NguoiLuuTru")) or None

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
