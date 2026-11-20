"""Dựng ô form Tách hộ (Cổng DVC Bộ Công an) từ dữ kiện compact.

Cùng trang + cùng bộ id với Đăng ký thường trú → dùng lại các hàm chuẩn hoá ô (họ tên, ngày sinh, số định danh,
giới tính, cơ quan, địa chỉ dưới cấp xã, bảng thành viên) của pipeline đó; chỉ khác danh sách ô, Trường hợp cố định
và không có khối chủ hộ (người đề nghị chính là chủ hộ mới).
"""

import re
from typing import Any

from app.pipelines._shared.naming import fold
from app.pipelines.dang_ky_thuong_tru.process.mapper import (
    ACCOUNT_AGENCY_OPTION,
    _address_below_ward,
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
from app.pipelines.tach_ho.process.schema import CASE_SPLIT, UI_COMP_BY_NAME
from app.pipelines._shared.formatting import keep_portal_values

PROCEDURE_KEY = "tach-ho"
ADDRESS_ID = "txtSUGGEST_DETAIL_ADDR"
CONTENT_ID = "txtCHANGED_CONTENT_NOTE"

# "Đề nghị tách hộ tại Tổ dân phố 5, xã …" → phần sau chữ "tại" là nơi tách hộ.
_AT_PLACE = re.compile(r"\btại\s+(.+)$", re.IGNORECASE)


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Bản sao options kèm xã/tỉnh tài khoản: dự phòng ô Cơ quan thực hiện (bắt buộc) khi giấy không ghi."""
    result = dict(options or {})
    if procedure != PROCEDURE_KEY:
        return result
    result.pop(ACCOUNT_AGENCY_OPTION, None)
    if isinstance(user, dict) and user.get("tinh") and user.get("xa"):
        result[ACCOUNT_AGENCY_OPTION] = {"tinh": str(user["tinh"]), "xa": str(user["xa"])}
    return result


def _address(values: dict, content: str | None) -> str | None:
    """Địa chỉ dưới cấp xã nơi tách hộ; LLM bỏ trống thì cắt từ nội dung đề nghị ("… tại Tổ dân phố 5, xã …")."""
    address = _address_below_ward(values.get("NoiTachHo_DiaChiChiTiet"))
    if address or not content:
        return address
    match = _AT_PLACE.search(content)
    return _address_below_ward(match.group(1)) if match else None


def _members(values: dict, applicant_id: str | None, applicant_name: str | None) -> list:
    """Thành viên tách theo: bỏ người đề nghị (đơn xác nhận hay ghi cả dòng "Chủ hộ") trước khi đánh chỉ số dòng."""
    listed = values.get("ThanhVien") if isinstance(values.get("ThanhVien"), list) else []
    kept = []
    for item in listed:
        if isinstance(item, dict):
            identity = _identity(item.get("soDinhDanh"))
            if applicant_id and identity == applicant_id:
                continue
            if fold(_text(item.get("quanHeVoiChuHo")) or "") == "chu ho":
                continue
            if not identity and applicant_name and _name(item.get("hoTen")) == applicant_name:
                continue
        kept.append(item)
    return kept


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
    picked[CASE_SELECT_ID] = CASE_SPLIT

    identity = _identity(values.get("NguoiDeNghi_SoDinhDanh"))
    full_name = _name(values.get("NguoiDeNghi_HoTen"))
    dob = _date_parts(values.get("NguoiDeNghi_NgaySinh"))
    if dob:
        # Định dạng phải chọn TRƯỚC: đổi định dạng là cổng xoá ô ngày sinh.
        picked["cboFORMAT_DATE"], picked["txtBIRTH_DATE"] = dob
    picked["txtFULLNAME"] = full_name
    picked["cboGENDER_ID"] = _gender(values.get("NguoiDeNghi_GioiTinh"), identity)
    picked["txtID_CARD_NUMBER"] = identity
    picked["txtPHONE_NUMBER"] = _phone(values.get("NguoiDeNghi_SoDienThoai"))
    picked["txtEMAIL"] = _email(values.get("NguoiDeNghi_Email"))

    content = _text(values.get("NoiDungDeNghi"))
    address = _address(values, content)
    picked[ADDRESS_ID] = address
    if not content and (address or ward):
        # Ô bắt buộc mà không có CT01 → câu đề nghị dựng từ nơi tách hộ, tô vàng để người dân soát lại cho khớp tờ khai.
        content = "Đề nghị tách hộ tại " + ", ".join(part for part in (address, ward, province) if part)
        defaults.add(CONTENT_ID)
    picked[CONTENT_ID] = content

    rows = _member_rows(_members(values, identity, full_name))
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
    # Ô người đề nghị = chủ tài khoản VNeID: cổng đổ sẵn thì giữ nguyên, trống mới điền theo giấy (user 20/11/2026).
    keep_portal_values(out, ('txtPHONE_NUMBER', 'txtEMAIL'))
    return out
