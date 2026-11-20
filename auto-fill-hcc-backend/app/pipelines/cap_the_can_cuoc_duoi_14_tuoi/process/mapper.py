"""Dựng ô form Cấp thẻ căn cước cho người dưới 14 tuổi (Cổng DVC Bộ Công an) từ dữ kiện compact.

Trang cùng bộ ô với cấp đổi căn cước (cap_doi_the_can_cuoc) nên dùng lại các hàm chuẩn hoá ở đó; khác ở chỗ người kê
khai luôn là cha/mẹ/người đại diện (không có radio radIsNCC, không có ô Lý do cấp phải chọn).
"""

import re
from typing import Any

from app.pipelines._shared.naming import fold
from app.pipelines.cap_doi_the_can_cuoc.process.mapper import (
    ACCOUNT_AGENCY_OPTION,
    LEVEL_FIELD,
    _address_below_ward,
    _area,
    _by_name,
    _date,
    _email,
    _gender,
    _identity,
    _name,
    _phone,
    _receipt_mode,
    _words,
)
from app.pipelines.cap_doi_the_can_cuoc.process.schema import (
    AGENCY_CITY_ID,
    AGENCY_FIELD,
    AGENCY_READY_ID,
    AGENCY_WARD_ID,
    LEVEL_PROVINCE,
    LEVEL_WARD,
    RELATION_FATHER,
    RELATION_MOTHER,
    RELATION_REPRESENTATIVE,
    RESULT_POST,
)
from app.pipelines.cap_the_can_cuoc_duoi_14_tuoi.process.schema import UI_COMP_BY_NAME
from app.pipelines._shared.formatting import keep_portal_values, only_for_account

PROCEDURE_KEY = "cap-the-can-cuoc-duoi-14-tuoi"


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Bản sao options kèm xã/tỉnh tài khoản: dự phòng ô Cơ quan thực hiện (bắt buộc) khi giấy không ghi."""
    result = dict(options or {})
    if procedure != PROCEDURE_KEY:
        return result
    result.pop(ACCOUNT_AGENCY_OPTION, None)
    if isinstance(user, dict) and user.get("tinh") and user.get("xa"):
        result[ACCOUNT_AGENCY_OPTION] = {"tinh": str(user["tinh"]), "xa": str(user["xa"])}
    return result


def _unit(value: Any) -> Any:
    """ "Đơn vị lập" CC01 / bìa hồ sơ ghi "Công an phường X" → "phường X" (danh mục địa giới không có chữ "Công an")."""
    return re.sub(r"^\s*c[oô]ng\s+an\s+", "", value, flags=re.IGNORECASE) if isinstance(value, str) else value


def _same_person(left: Any, right: Any) -> bool:
    a, b = _words(left), _words(right)
    return bool(a) and a == b


def _relation_word(value: Any) -> str | None:
    """Chữ quan hệ trên giấy → nhãn option ("Mẹ – người đại diện hợp pháp" vẫn là Mẹ; "Bà nội" không phải Cha)."""
    said = _words(value)
    if not said:
        return None
    first = said.split()[0]
    if first in ("me", "ma"):
        return RELATION_MOTHER
    if first in ("cha", "bo") or said == "ba":
        return RELATION_FATHER
    if "dai dien" in said or "giam ho" in said:
        return RELATION_REPRESENTATIVE
    return None


def _relation_people(values: dict) -> list[dict]:
    """Ai là cha, mẹ (và người đại diện khác cha mẹ) theo giấy tờ — extension so với tài khoản VNeID ở Phần I.

    Ô "Mối quan hệ của người kê khai…" nói về NGƯỜI ĐANG ĐĂNG NHẬP (Phần I cổng khoá theo tài khoản), không phải người ký
    trên giấy: giấy ghi mẹ là người đại diện mà tài khoản là người khác thì chọn "Mẹ" là sai, cổng đối chiếu CSDL báo lỗi.
    """
    people = {
        RELATION_MOTHER: {"relation": RELATION_MOTHER, "name": _name(values.get("Me_HoTen")),
                          "id": _identity(values.get("Me_SoDinhDanh"))},
        RELATION_FATHER: {"relation": RELATION_FATHER, "name": _name(values.get("Cha_HoTen")),
                          "id": _identity(values.get("Cha_SoDinhDanh"))},
    }
    rep_name = _name(values.get("NguoiDaiDien_HoTen"))
    rep_id = _identity(values.get("NguoiDaiDien_SoDinhDanh"))
    rep_relation = _relation_word(values.get("NguoiDaiDien_QuanHe"))
    if rep_name or rep_id:
        # Người kê khai trên giấy trùng tên cha/mẹ → bù số định danh (thẻ căn cước nộp kèm) cho dòng đó.
        same = next((p for p in people.values() if _same_person(rep_name, p["name"])), None)
        if same is None and rep_relation in people:
            same = people[rep_relation]
        if same is not None:
            same["name"] = same["name"] or rep_name
            same["id"] = same["id"] or rep_id
        elif rep_relation == RELATION_REPRESENTATIVE:
            people[RELATION_REPRESENTATIVE] = {"relation": RELATION_REPRESENTATIVE, "name": rep_name, "id": rep_id}
    out = []
    for person in people.values():
        if person["name"] or person["id"]:
            out.append({k: v for k, v in person.items() if v})
    return out


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    values = _by_name(fields)
    picked: dict[str, Any] = {}
    defaults: set[str] = set()

    # Phần II: trẻ cần cấp căn cước (Phần I là tài khoản cha/mẹ, cổng khoá). Nút "Kiểm tra thông tin trong CSDL…"
    # công dân tự bấm.
    child_id = _identity(values.get("NguoiCanCap_SoDinhDanh"))
    adult_ids = {_identity(values.get(k)) for k in ("NguoiDaiDien_SoDinhDanh", "Cha_SoDinhDanh", "Me_SoDinhDanh")}
    if child_id and child_id in adult_ids:
        child_id = None  # LLM chép nhầm số của cha/mẹ sang trẻ — để trống cho cán bộ nhập, đừng khai sai người
    picked["txtFULLNAME_NCC"] = _name(values.get("NguoiCanCap_HoTen"))
    picked["txtBIRTHDATE_NCC"] = _date(values.get("NguoiCanCap_NgaySinh"))
    picked["cboGENDER_ID_NCC"] = _gender(values.get("NguoiCanCap_GioiTinh"), child_id)
    picked["txtIDENTIFY_NUMBER_NCC"] = child_id
    people = _relation_people(values)
    if people:
        # Không trùng ai trên giấy → "Người đại diện hợp pháp" (option còn lại), không tô vàng (user 16/11).
        picked["cboRELATIONSHIP_WITH_NDN"] = {"target": "cboRELATIONSHIP_WITH_NDN", "accountNameId": "txtFULLNAME_NDN",
                                              "accountIdId": "txtIDENTIFY_NUMBER_NDN", "people": people,
                                              "fallback": RELATION_REPRESENTATIVE}
    declarant_phone = _phone(values.get("NguoiDaiDien_SoDienThoai"))
    picked["txtPHONE_NUMBER_NDN"] = declarant_phone
    picked["txtEMAIL_ADDRESS_NDN"] = _email(values.get("NguoiDaiDien_Email"))

    province, ward = _area(_unit(values.get("CoQuan_Tinh")), _unit(values.get("CoQuan_Xa")))
    if not province:
        # Ô bắt buộc mà giấy không ghi cơ quan → Công an xã/tỉnh của tài khoản quầy, tô vàng để cán bộ soát.
        account = (options or {}).get(ACCOUNT_AGENCY_OPTION) or {}
        province, ward = _area(account.get("tinh"), account.get("xa"))
        if province and ward:
            defaults = {LEVEL_FIELD, AGENCY_FIELD}
        else:
            province = ward = None
    if province:
        # Có cấp xã = mã 1.014062 (radio Cấp Xã); chỉ Công an tỉnh/thành phố = mã 1.012549 (Cấp Tỉnh, chỉ chọn ô tỉnh).
        picked[LEVEL_FIELD] = LEVEL_WARD if ward else LEVEL_PROVINCE
        picked[AGENCY_FIELD] = {"province": province, "ward": ward or "", "cityId": AGENCY_CITY_ID,
                                "wardId": AGENCY_WARD_ID, "readySelect": AGENCY_READY_ID, "readyPick": True}

    mode = _receipt_mode(values.get("NhanKetQua_HinhThuc"))
    picked["radNhanKetQua"] = mode
    if mode == RESULT_POST:
        city, village = _area(values.get("NhanKetQua_Tinh"), values.get("NhanKetQua_Xa"))
        picked["cboGET_RESULT_CITY_ADDR"] = city
        picked["cboGET_RESULT_VILLAGE_ADDR"] = village if city else None
        picked["txtGET_RESULT_DETAIL_ADDR"] = _address_below_ward(values.get("NhanKetQua_DiaChiChiTiet"))
        # Giấy không ghi người nhận riêng → người kê khai (cha/mẹ) nhận thay trẻ.
        picked["txtFULLNAME_NN"] = _name(values.get("NhanKetQua_HoTen")) or _name(values.get("NguoiDaiDien_HoTen"))
        picked["txtPHONE_NUMBER_NN"] = _phone(values.get("NhanKetQua_SoDienThoai")) or declarant_phone

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
    # Ô Phần I người kê khai = chủ tài khoản VNeID: cổng đổ sẵn thì giữ nguyên, trống mới điền theo giấy (user 20/11/2026).
    keep_portal_values(out, ('txtPHONE_NUMBER_NDN', 'txtEMAIL_ADDRESS_NDN'))
    # SĐT / email ở mục II DC02 là của người ký mục II: chỉ ghi khi tài khoản đăng nhập đúng là người đó (user 20/11/2026).
    return only_for_account(out, ('txtPHONE_NUMBER_NDN', 'txtEMAIL_ADDRESS_NDN'),
                            name=_name(values.get("NguoiDaiDien_HoTen")),
                            id=_identity(values.get("NguoiDaiDien_SoDinhDanh")))
