"""Dựng ô form Cấp thẻ căn cước cho người từ đủ 14 tuổi trở lên (Cổng DVC Bộ Công an) từ dữ kiện compact.

Trang cùng bộ ô với cấp căn cước dưới 14 tuổi nên dùng lại hàm chuẩn hoá của cấp đổi + danh sách cha/mẹ của bản dưới 14
tuổi; khác ở chỗ có radio "Đối tượng kê khai" (người cần cấp tự khai hoặc cha/mẹ/người đại diện khai thay) và ô "Lý do
cấp" phải chọn.
"""

import re
from typing import Any

from app.pipelines.cap_doi_the_can_cuoc.process.mapper import (
    ACCOUNT_AGENCY_OPTION,
    LEVEL_FIELD,
    _area,
    _by_name,
    _date,
    _email,
    _gender,
    _identity,
    _name,
    _phone,
    _words,
)
from app.pipelines.cap_doi_the_can_cuoc.process.schema import (
    AGENCY_CITY_ID,
    AGENCY_FIELD,
    AGENCY_READY_ID,
    AGENCY_WARD_ID,
    LEVEL_PROVINCE,
    LEVEL_WARD,
    RELATION_REPRESENTATIVE,
)
from app.pipelines.cap_the_can_cuoc_duoi_14_tuoi.process.mapper import _relation_people, _unit
from app.pipelines.cap_the_can_cuoc_tu_du_14_tuoi.process.schema import (
    DECLARANT_FIELD,
    DECLARANT_OTHER_BLOCK,
    DECLARANT_OTHER_ID,
    DECLARANT_SELF_ID,
    OTHER_ONLY,
    REASON_CMND9,
    REASON_CMND12,
    REASON_FIRST,
    UI_COMP_BY_NAME,
)
from app.pipelines._shared.formatting import keep_portal_values

PROCEDURE_KEY = "cap-the-can-cuoc-tu-du-14-tuoi"
# CMND thôi cấp từ 01/7/2021: sinh sau giữa năm 2007 thì đủ 14 tuổi khi đã hết cấp CMND → không thể "chuyển từ CMND".
_LAST_CMND_BIRTH_YEAR = 2007


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Bản sao options kèm xã/tỉnh tài khoản: dự phòng ô Cơ quan thực hiện (bắt buộc) khi giấy không ghi."""
    result = dict(options or {})
    if procedure != PROCEDURE_KEY:
        return result
    result.pop(ACCOUNT_AGENCY_OPTION, None)
    if isinstance(user, dict) and user.get("tinh") and user.get("xa"):
        result[ACCOUNT_AGENCY_OPTION] = {"tinh": str(user["tinh"]), "xa": str(user["xa"])}
    return result


def _reason(values: dict) -> tuple[str, bool]:
    """(nhãn "Lý do cấp", có phải mặc định không có căn cứ). Giấy ghi rõ chuyển từ CMND → theo giấy; có số CMND 9 số
    của chính người cần cấp (và tuổi còn kịp được cấp CMND) → chuyển từ CMND 9 số; còn lại cấp lần đầu."""
    said = _words(values.get("LoaiCap"))
    if "cmnd" in said or "chung minh" in said:
        return (REASON_CMND12 if "12 so" in said else REASON_CMND9), False
    birth = _date(values.get("NguoiCanCap_NgaySinh"))
    cmnd = re.sub(r"\D", "", str(values.get("NguoiCanCap_SoCMND") or ""))
    if len(cmnd) == 9 and (not birth or int(birth[-4:]) <= _LAST_CMND_BIRTH_YEAR):
        return REASON_CMND9, False
    return REASON_FIRST, not any(key in said for key in ("lan dau", "cap moi", "moi"))


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    values = _by_name(fields)
    picked: dict[str, Any] = {}
    defaults: set[str] = set()

    subject_name = _name(values.get("NguoiCanCap_HoTen"))
    subject_id = _identity(values.get("NguoiCanCap_SoDinhDanh"))
    adult_ids = {_identity(values.get(k)) for k in ("NguoiDaiDien_SoDinhDanh", "Cha_SoDinhDanh", "Me_SoDinhDanh")}
    if subject_id and subject_id in adult_ids:
        subject_id = None  # LLM chép nhầm số của cha/mẹ sang người cần cấp — để trống, đừng khai sai người
    if subject_name or subject_id:
        # Người kê khai = TÀI KHOẢN VNeID đang đăng nhập (Phần I cổng khoá), không phải người ký trên giấy: extension so
        # Phần I với người cần cấp rồi chọn radio; khác người mới mở và điền khối Phần II (ô bcaOtherOnly).
        picked[DECLARANT_FIELD] = {"selfId": DECLARANT_SELF_ID, "otherId": DECLARANT_OTHER_ID,
                                   "otherBlock": DECLARANT_OTHER_BLOCK, "accountNameId": "txtFULLNAME_NDN",
                                   "accountIdId": "txtIDENTIFY_NUMBER_NDN",
                                   "subject": {k: v for k, v in (("name", subject_name), ("id", subject_id)) if v}}
        picked["txtFULLNAME_NCC"] = subject_name
        picked["txtBIRTHDATE_NCC"] = _date(values.get("NguoiCanCap_NgaySinh"))
        picked["cboGENDER_ID_NCC"] = _gender(values.get("NguoiCanCap_GioiTinh"), subject_id)
        picked["txtIDENTIFY_NUMBER_NCC"] = subject_id
        people = _relation_people(values)
        if people:
            picked["cboRELATIONSHIP_WITH_NDN"] = {"target": "cboRELATIONSHIP_WITH_NDN",
                                                  "accountNameId": "txtFULLNAME_NDN",
                                                  "accountIdId": "txtIDENTIFY_NUMBER_NDN", "people": people,
                                                  "fallback": RELATION_REPRESENTATIVE}

    # SĐT / email Phần I: của người kê khai thay nếu giấy ghi người đó, không thì của người cần cấp (mục 18–19 CC01).
    on_paper_rep = bool(_name(values.get("NguoiDaiDien_HoTen")) or _identity(values.get("NguoiDaiDien_SoDinhDanh")))
    phones = [_phone(values.get("NguoiDaiDien_SoDienThoai")), _phone(values.get("NguoiCanCap_SoDienThoai"))]
    emails = [_email(values.get("NguoiDaiDien_Email")), _email(values.get("NguoiCanCap_Email"))]
    if not on_paper_rep:
        phones.reverse()
        emails.reverse()
    picked["txtPHONE_NUMBER_NDN"] = next((p for p in phones if p), None)
    picked["txtEMAIL_ADDRESS_NDN"] = next((e for e in emails if e), None)

    reason, reason_default = _reason(values)
    picked["cboLyDoCap"] = reason
    if reason_default:
        defaults.add("cboLyDoCap")

    province, ward = _area(_unit(values.get("CoQuan_Tinh")), _unit(values.get("CoQuan_Xa")))
    if not province:
        # Ô bắt buộc mà giấy không ghi cơ quan → Công an xã/tỉnh của tài khoản quầy, tô vàng để cán bộ soát.
        account = (options or {}).get(ACCOUNT_AGENCY_OPTION) or {}
        province, ward = _area(account.get("tinh"), account.get("xa"))
        if province and ward:
            defaults |= {LEVEL_FIELD, AGENCY_FIELD}
        else:
            province = ward = None
    if ward:
        ward = ward[:1].upper() + ward[1:]  # "Công an xã X" bỏ "Công an" còn "xã X" → "Xã X" như danh mục cổng
    if province:
        # Có cấp xã = mã 1.014061 (radio Cấp Xã); chỉ Công an tỉnh/thành phố = mã 2.000200 (Cấp Tỉnh, chỉ chọn ô tỉnh).
        picked[LEVEL_FIELD] = LEVEL_WARD if ward else LEVEL_PROVINCE
        picked[AGENCY_FIELD] = {"province": province, "ward": ward or "", "cityId": AGENCY_CITY_ID,
                                "wardId": AGENCY_WARD_ID, "readySelect": AGENCY_READY_ID, "readyPick": True}

    out = []
    for name, comp in UI_COMP_BY_NAME.items():
        if picked.get(name) in (None, ""):
            continue
        field = {"name": name, "comp": comp, "value": picked[name]}
        if name in OTHER_ONLY:
            field["bcaOtherOnly"] = True
        if name == AGENCY_FIELD:
            field["onlyIfEmpty"] = True
        if name in defaults:
            field["default"] = True
        out.append(field)
    # Ô Phần I người kê khai = chủ tài khoản VNeID: cổng đổ sẵn thì giữ nguyên, trống mới điền theo giấy (user 20/11/2026).
    keep_portal_values(out, ('txtPHONE_NUMBER_NDN', 'txtEMAIL_ADDRESS_NDN'))
    return out
