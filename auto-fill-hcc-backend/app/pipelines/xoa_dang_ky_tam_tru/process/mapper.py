"""Dựng ô form Xóa đăng ký tạm trú (Cổng DVC Bộ Công an) từ dữ kiện compact.

Cùng trang + cùng bộ id với Đăng ký tạm trú → dùng lại các hàm chuẩn hoá ô (họ tên, ngày sinh, số định danh, giới
tính, điện thoại, email) của pipeline đó; Cơ quan thực hiện chuẩn hoá theo địa giới mới như Đăng ký thường trú. Thêm
Trường hợp (6 lựa chọn theo lý do + nhân khẩu / hộ), khối chủ hộ tạm trú, bảng thành viên (#listNormal).
"""

from typing import Any

from app.pipelines._shared.naming import fold
from app.pipelines.dang_ky_tam_tru.process.mapper import (
    _by_name,
    _date_parts,
    _email,
    _gender,
    _identity,
    _name,
    _phone,
    _text,
)
from app.pipelines.dang_ky_thuong_tru.process.mapper import ACCOUNT_AGENCY_OPTION, _agency
from app.pipelines.xoa_dang_ky_tam_tru.process.schema import (
    AGENCY_CITY_ID,
    AGENCY_FIELD,
    AGENCY_WARD_ID,
    CASE_ABSENT,
    CASE_ABSENT_HH,
    CASE_NO_HOME,
    CASE_NO_HOME_HH,
    CASE_PERMANENT,
    CASE_PERMANENT_HH,
    CASE_SELECT_ID,
    CASES,
    HOUSEHOLD_HEAD,
    MEMBER_ADD_SELECTOR,
    MEMBER_IDS,
    UI_COMP_BY_NAME,
)
from app.pipelines._shared.formatting import keep_portal_values

PROCEDURE_KEY = "xoa-dang-ky-tam-tru"

# (cụm chữ của lý do, nhãn nhân khẩu, nhãn hộ) — xét theo thứ tự: "thường trú" trước vì câu lý do đó hay nhắc cả
# "chỗ ở".
_REASONS = (
    (("thuong tru",), CASE_PERMANENT, CASE_PERMANENT_HH),
    (("vang mat", "6 thang", "sau thang"), CASE_ABSENT, CASE_ABSENT_HH),
    (("cho o hop phap", "het han hop dong", "thanh ly hop dong", "chuyen di", "khong con o", "ban nha"),
     CASE_NO_HOME, CASE_NO_HOME_HH),
)


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Bản sao options kèm xã/tỉnh tài khoản: dự phòng ô Cơ quan thực hiện khi giấy không ghi (hoặc chỉ ghi xã)."""
    result = dict(options or {})
    if procedure != PROCEDURE_KEY:
        return result
    result.pop(ACCOUNT_AGENCY_OPTION, None)
    if isinstance(user, dict) and user.get("tinh") and user.get("xa"):
        result[ACCOUNT_AGENCY_OPTION] = {"tinh": str(user["tinh"]), "xa": str(user["xa"])}
    return result


def _agency_pick(values: dict, options: dict | None) -> tuple[str | None, str | None, bool]:
    """(tỉnh, xã, có phải dự phòng không). CT01 hay chỉ ghi "Kính gửi: Công an xã A" → tỉnh lấy theo tài khoản."""
    province, ward = _agency(values)
    if province and ward:
        return province, ward, False
    account = (options or {}).get(ACCOUNT_AGENCY_OPTION) or {}
    paper_ward = _text(values.get("CoQuan_Xa"))
    if paper_ward and account.get("tinh"):
        province, ward = _agency({"CoQuan_Tinh": account["tinh"], "CoQuan_Xa": paper_ward})
        if province and ward:
            return province, ward, True
    province, ward = _agency({"CoQuan_Tinh": account.get("tinh"), "CoQuan_Xa": account.get("xa")})
    return province, ward, bool(province and ward)


def _case(values: dict) -> str | None:
    """Nhãn Trường hợp: nhãn LLM chọn (khớp trọn, bỏ dấu) → không thì suy theo lý do ở nội dung đề nghị."""
    want = fold(_text(values.get("TruongHop")) or "")
    exact = next((label for label in CASES if fold(label) == want), None)
    if exact:
        return exact
    content = fold(_text(values.get("NoiDungDeNghi")) or "")
    household = want.startswith(("ho do", "ca ho")) or "ca ho" in content
    # Nhãn LLM viết tắt xét TRƯỚC câu nội dung đề nghị (câu đó hay nhắc nhiều lý do).
    for text in (want, content):
        for keys, person_case, household_case in _REASONS:
            if text and any(key in text for key in keys):
                return household_case if household else person_case
    return None


def _relation(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return HOUSEHOLD_HEAD if fold(text) == fold(HOUSEHOLD_HEAD) else text[:1].upper() + text[1:]


def _member_rows(listed: Any, excluded: set[str]) -> list[list[dict]]:
    rows: list[list[dict]] = []
    for item in listed if isinstance(listed, list) else []:
        if not isinstance(item, dict) or not _name(item.get("hoTen")):
            continue
        identity = _identity(item.get("soDinhDanh"))
        if identity and identity in excluded:
            continue
        dob = _date_parts(item.get("ngaySinh"))
        cells = {
            "hoTen": _name(item.get("hoTen")),
            "dinhDang": dob[0] if dob else None,
            "ngaySinh": dob[1] if dob else None,
            "gioiTinh": _gender(item.get("gioiTinh"), identity),
            "soDinhDanh": identity,
            "quanHeVoiChuHo": _relation(item.get("quanHeVoiChuHo")),
        }
        index = len(rows)
        rows.append([{"id": f"{prefix}{index}", "comp": comp, "value": cells[key]}
                     for key, (prefix, comp) in MEMBER_IDS.items() if cells[key]])
    return rows


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    values = _by_name(fields)
    picked: dict[str, Any] = {}
    defaults: set[str] = set()

    province, ward, fallback = _agency_pick(values, options)
    if province and ward:
        # Cổng chọn sẵn Hà Nội / Ba Đình → chọn đè (không onlyIfEmpty).
        picked[AGENCY_FIELD] = {"province": province, "ward": ward, "cityId": AGENCY_CITY_ID, "wardId": AGENCY_WARD_ID,
                                "readySelect": CASE_SELECT_ID}
        if fallback:
            defaults.add(AGENCY_FIELD)
    # Trợ lý đã hỏi công dân chọn Trường hợp (case_pipeline_options → options.bcaCase) → giữ đúng lựa chọn đó.
    chosen = (options or {}).get("bcaCase")
    picked[CASE_SELECT_ID] = chosen if chosen in CASES else _case(values)

    identity = _identity(values.get("NguoiDeNghi_SoDinhDanh"))
    picked["txtFULLNAME"] = _name(values.get("NguoiDeNghi_HoTen"))
    dob = _date_parts(values.get("NguoiDeNghi_NgaySinh"))
    if dob:
        # Định dạng phải chọn TRƯỚC: ô ngày sinh của cổng đổi mặt nạ nhập theo ô này.
        picked["cboDATE_FORMAT"], picked["txtDOB"] = dob
    picked["cboGENDER_CODE"] = _gender(values.get("NguoiDeNghi_GioiTinh"), identity)
    picked["txtIDENTIFIER_NUMBER"] = identity
    picked["txtPHONE_NUMBER"] = _phone(values.get("NguoiDeNghi_SoDienThoai"))
    picked["txtEMAIL"] = _email(values.get("NguoiDeNghi_Email"))

    head_id = _identity(values.get("ChuHo_SoDinhDanh"))
    head_name = _name(values.get("ChuHo_HoTen"))
    relation = _relation(values.get("ChuHo_QuanHe"))
    if identity and head_id == identity:
        # Người đề nghị chính là chủ hộ tạm trú.
        relation = HOUSEHOLD_HEAD
    if relation == HOUSEHOLD_HEAD:
        head_name, head_id = head_name or picked["txtFULLNAME"], head_id or identity
    picked["txtHH_PERSON_FULLNAME"] = head_name
    picked["cboHH_PERSON_RELATIONSHIP_CODE"] = relation
    picked["txtHH_PERSON_IDENTIFIER_NUMBER"] = head_id

    rows = _member_rows(values.get("ThanhVien"), {identity, head_id} - {None})
    if rows:
        picked["listNormal"] = {"addSelector": MEMBER_ADD_SELECTOR, "rows": rows}

    out = []
    for name, comp in UI_COMP_BY_NAME.items():
        if picked.get(name) in (None, ""):
            continue
        field = {"name": name, "comp": comp, "value": picked[name]}
        if name in defaults:
            field["default"] = True
        out.append(field)
    # Ô người đề nghị = chủ tài khoản VNeID: cổng đổ sẵn thì giữ nguyên, trống mới điền theo giấy (user 20/11/2026).
    keep_portal_values(out, ('txtPHONE_NUMBER', 'txtEMAIL'))
    return out
