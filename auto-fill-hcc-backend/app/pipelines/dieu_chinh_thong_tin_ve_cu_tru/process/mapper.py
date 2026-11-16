"""Dựng ô form Điều chỉnh thông tin về cư trú (Cổng DVC Bộ Công an) từ dữ kiện compact.

Cùng trang + cùng bộ id với Đăng ký thường trú → dùng lại các hàm chuẩn hoá ô (họ tên, ngày sinh, số định danh,
giới tính, cơ quan, bảng thành viên) của pipeline đó; chỉ khác danh sách ô và luôn điền khối chủ hộ.
"""

from typing import Any

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
from app.pipelines.dieu_chinh_thong_tin_ve_cu_tru.process.schema import CASE_CHANGE_HEAD, UI_COMP_BY_NAME

PROCEDURE_KEY = "dieu-chinh-thong-tin-ve-cu-tru"


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Bản sao options kèm xã/tỉnh tài khoản: dự phòng ô Cơ quan thực hiện (bắt buộc) khi giấy không ghi."""
    result = dict(options or {})
    if procedure != PROCEDURE_KEY:
        return result
    result.pop(ACCOUNT_AGENCY_OPTION, None)
    if isinstance(user, dict) and user.get("tinh") and user.get("xa"):
        result[ACCOUNT_AGENCY_OPTION] = {"tinh": str(user["tinh"]), "xa": str(user["xa"])}
    return result


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
    picked[CASE_SELECT_ID] = CASE_CHANGE_HEAD

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
    # Khối chủ hộ luôn mở ở thủ tục này: chủ hộ hiện tại trong CSDL (chủ hộ cũ).
    picked["txtHH_HEAD_FULLNAME"] = _name(values.get("ChuHo_HoTen"))
    picked["cboRELATIONSHIP_WITH_HHHEAD_ID"] = _text(values.get("ChuHo_QuanHe"))
    picked["txtID_CARD_NUMBER_HHEAD"] = _identity(values.get("ChuHo_SoDinhDanh"))
    # Bảng "cùng thay đổi" không gồm người đề nghị (đã khai ở trên) và chủ hộ cũ — LLM có chép nhầm thì bỏ theo số
    # định danh trước khi đánh chỉ số dòng.
    excluded = {identity, _identity(values.get("ChuHo_SoDinhDanh"))} - {None}
    listed = values.get("ThanhVien") if isinstance(values.get("ThanhVien"), list) else []
    members = [item for item in listed if not isinstance(item, dict)
               or _identity(item.get("soDinhDanh")) not in excluded]
    rows = _member_rows(members)
    if rows:
        picked["tblNguoi_CUNGTD"] = {"addSelector": MEMBER_ADD_SELECTOR, "rows": rows}
    picked["txtCHANGED_CONTENT_NOTE"] = _text(values.get("NoiDungDeNghi"))

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
