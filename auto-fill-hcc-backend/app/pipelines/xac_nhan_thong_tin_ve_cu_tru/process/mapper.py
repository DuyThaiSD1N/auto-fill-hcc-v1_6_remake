"""Dựng ô form Xác nhận thông tin về cư trú (Cổng DVC Bộ Công an) từ dữ kiện compact.

Cùng trang + cùng bộ id với Đăng ký thường trú → dùng lại các hàm chuẩn hoá ô (họ tên, ngày sinh, số định danh,
giới tính, cơ quan, bảng thành viên) của pipeline đó; chỉ khác danh sách ô, Trường hợp chọn theo nơi thường trú và
thêm Hình thức nhận kết quả.
"""

import re
from typing import Any

from app.pipelines._shared.naming import fold
from app.pipelines.dang_ky_thuong_tru.process.mapper import (
    ACCOUNT_AGENCY_OPTION,
    _agency,
    _by_name,
    _date_parts,
    _email,
    _gender,
    _identity,
    _member_rows,
    _name,
    _phone,
    _text,
)
from app.pipelines.dang_ky_thuong_tru.process.schema import (
    AGENCY_CITY_ID,
    AGENCY_FIELD,
    AGENCY_WARD_ID,
    CASE_SELECT_ID,
    MEMBER_ADD_SELECTOR,
)
from app.pipelines.xac_nhan_thong_tin_ve_cu_tru.process.schema import (
    CASE_IN_AREA,
    CASE_OUT_AREA,
    RESULT_DIRECT,
    RESULT_PORTAL,
    RESULT_POST,
    UI_COMP_BY_NAME,
)

PROCEDURE_KEY = "xac-nhan-thong-tin-ve-cu-tru"
RESULT_SELECT_ID = "cboTYPE_GET_RESULT"
RESULT_COUNT_ID = "txtNUMBER_OF_RESULT"

_WARD_PREFIX = re.compile(r"^(phuong|xa|thi tran|dac khu)\s+")


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Bản sao options kèm xã/tỉnh tài khoản: dự phòng ô Cơ quan thực hiện (bắt buộc) khi giấy không ghi."""
    result = dict(options or {})
    if procedure != PROCEDURE_KEY:
        return result
    result.pop(ACCOUNT_AGENCY_OPTION, None)
    if isinstance(user, dict) and user.get("tinh") and user.get("xa"):
        result[ACCOUNT_AGENCY_OPTION] = {"tinh": str(user["tinh"]), "xa": str(user["xa"])}
    return result


def _place_key(value: Any) -> str:
    """Tên đơn vị hành chính để so: bỏ dấu, bỏ tiền tố cấp xã (LLM hay chép "Đoàn Kết" thay cho "Phường Đoàn Kết")."""
    return _WARD_PREFIX.sub("", fold(_text(value) or ""))


def _case(values: dict, province: str | None, ward: str | None) -> tuple[str, bool]:
    """(nhãn Trường hợp, có phải mặc định không): nơi thường trú cùng xã với cơ quan tiếp nhận → trên địa bàn."""
    home_province, home_ward = _agency({"CoQuan_Tinh": values.get("NoiThuongTru_Tinh"),
                                        "CoQuan_Xa": values.get("NoiThuongTru_Xa")})
    home_ward = home_ward or _text(values.get("NoiThuongTru_Xa"))
    if not (home_ward and ward):
        # Giấy không cho biết nơi thường trú: người dân thường xin xác nhận ngay tại Công an xã nơi mình thường trú.
        return CASE_IN_AREA, True
    same_ward = _place_key(home_ward) == _place_key(ward)
    same_province = not (home_province and province) or _place_key(home_province) == _place_key(province)
    return (CASE_IN_AREA if same_ward and same_province else CASE_OUT_AREA), False


def _result_type(value: Any) -> str | None:
    text = fold(_text(value) or "")
    if not text:
        return None
    if "buu chinh" in text or "buu dien" in text:
        return RESULT_POST
    if "truc tiep" in text:
        return RESULT_DIRECT
    if any(key in text for key in ("cong", "truc tuyen", "dien tu", "vneid")):
        return RESULT_PORTAL
    return None


def _count(value: Any) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    return str(int(digits)) if digits and len(digits) <= 2 and int(digits) > 0 else None


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
    picked[CASE_SELECT_ID], case_default = _case(values, province, ward)
    if case_default:
        defaults.add(CASE_SELECT_ID)

    identity = _identity(values.get("NguoiDeNghi_SoDinhDanh"))
    dob = _date_parts(values.get("NguoiDeNghi_NgaySinh"))
    if dob:
        # Định dạng phải chọn TRƯỚC: đổi định dạng là cổng xoá ô ngày sinh.
        picked["cboFORMAT_DATE"], picked["txtBIRTH_DATE"] = dob
    picked["txtFULLNAME"] = _name(values.get("NguoiDeNghi_HoTen"))
    picked["cboGENDER_ID"] = _gender(values.get("NguoiDeNghi_GioiTinh"), identity)
    picked["txtID_CARD_NUMBER"] = identity
    picked["txtPHONE_NUMBER"] = _phone(values.get("NguoiDeNghi_SoDienThoai"))
    picked["txtEMAIL"] = _email(values.get("NguoiDeNghi_Email"))
    # Khối chủ hộ luôn mở ở thủ tục này (mục 7–9 CT01).
    head_id = _identity(values.get("ChuHo_SoDinhDanh"))
    picked["txtHH_HEAD_FULLNAME"] = _name(values.get("ChuHo_HoTen"))
    picked["cboRELATIONSHIP_WITH_HHHEAD_ID"] = _text(values.get("ChuHo_QuanHe"))
    picked["txtID_CARD_NUMBER_HHEAD"] = head_id
    # Bảng "cùng thay đổi" không gồm người đề nghị và chủ hộ — LLM có chép nhầm thì bỏ theo số định danh.
    excluded = {identity, head_id} - {None}
    listed = values.get("ThanhVien") if isinstance(values.get("ThanhVien"), list) else []
    members = [item for item in listed if not isinstance(item, dict)
               or _identity(item.get("soDinhDanh")) not in excluded]
    rows = _member_rows(members)
    if rows:
        picked["tblNguoi_CUNGTD"] = {"addSelector": MEMBER_ADD_SELECTOR, "rows": rows}
    picked["txtCHANGED_CONTENT_NOTE"] = _text(values.get("NoiDungDeNghi"))

    # Hình thức nhận kết quả: chỉ đổi khi giấy ghi rõ, không thì giữ mặc định của cổng (nhận qua cổng thông tin).
    result = _result_type(values.get("HinhThucNhanKetQua"))
    picked[RESULT_SELECT_ID] = result
    count = _count(values.get("SoLuongPhieu"))
    if not count and result in (RESULT_DIRECT, RESULT_POST):
        # Nhận bản giấy mà giấy không ghi số lượng phiếu (ô bắt buộc khi hiện) → 1 phiếu, tô vàng.
        count = "1"
        defaults.add(RESULT_COUNT_ID)
    picked[RESULT_COUNT_ID] = count

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
