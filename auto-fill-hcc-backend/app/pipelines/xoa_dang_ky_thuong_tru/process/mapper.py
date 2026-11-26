"""Dựng ô form Xóa đăng ký thường trú (Cổng DVC Bộ Công an) từ dữ kiện compact.

Cùng trang + cùng bộ id với Đăng ký thường trú → dùng lại các hàm chuẩn hoá ô (họ tên, ngày sinh, số định danh, giới
tính, điện thoại, email, cơ quan, bảng thành viên) của pipeline đó; cơ quan khi CT01 chỉ ghi xã lấy tỉnh theo tài khoản
như Xóa đăng ký tạm trú. Thêm Trường hợp (lý do × cả hộ / nhân khẩu), khối chủ hộ, Nội dung đề nghị chỉ khi tờ khai ghi
đúng nội dung xóa.
"""

from typing import Any

from app.pipelines._shared.formatting import keep_portal_values
from app.pipelines._shared.naming import fold
from app.pipelines.dang_ky_thuong_tru.process.mapper import (
    ACCOUNT_AGENCY_OPTION,
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
from app.pipelines.xoa_dang_ky_tam_tru.process.mapper import _agency_pick
from app.pipelines.xoa_dang_ky_thuong_tru.process.schema import (
    CASE_ABROAD,
    CASE_ABROAD_HH,
    CASE_ABSENT,
    CASE_ABSENT_HH,
    CASE_NO_HOME,
    CASE_NO_HOME_HH,
    CASES,
    CONTENT_ID,
    HOUSEHOLD_HEAD,
    UI_COMP_BY_NAME,
)

PROCEDURE_KEY = "xoa-dang-ky-thuong-tru"

# (cụm chữ của lý do, nhãn nhân khẩu, nhãn cả hộ) — xét theo thứ tự: định cư trước (câu đó hay nhắc "vắng mặt"), rồi
# vắng mặt, cuối cùng không còn chỗ ở.
_REASONS = (
    (("dinh cu", "nuoc ngoai"), CASE_ABROAD, CASE_ABROAD_HH),
    (("vang mat", "12 thang", "muoi hai thang"), CASE_ABSENT, CASE_ABSENT_HH),
    (("cho o hop phap", "ban nha", "chuyen nhuong", "het han hop dong", "thanh ly hop dong", "khong con o",
      "thu hoi", "giai toa", "pha do"), CASE_NO_HOME, CASE_NO_HOME_HH),
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


def _case(values: dict, applicant_is_head: bool) -> str | None:
    """Nhãn Trường hợp: lý do theo nhãn LLM (khớp trọn / viết tắt) rồi theo nội dung đề nghị; không căn cứ → None.

    Cả hộ khi nhãn / nội dung nói "cả hộ", hoặc người đề nghị là chủ hộ: nhóm "Nhân khẩu" của cổng bỏ "Chủ hộ" khỏi danh
    mục quan hệ với chủ hộ (mapping 24/11/2026) nên chủ hộ không khai được ở trường hợp nhân khẩu.
    """
    want = fold(_text(values.get("TruongHop")) or "")
    exact = next((label for label in CASES if fold(label) == want), None)
    content = fold(_text(values.get("NoiDungDeNghi")) or "")
    household = applicant_is_head or want.startswith(("ca ho", "ho do")) or "ca ho" in content
    if exact:
        return next(household_case if household else person_case
                    for _, person_case, household_case in _REASONS if exact in (person_case, household_case))
    # Nhãn LLM viết tắt xét TRƯỚC câu nội dung đề nghị (câu đó có thể nhắc nhiều lý do).
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


def _members(listed: Any, excluded: set[str]) -> list:
    """Thành viên cùng thay đổi: bỏ người đề nghị / chủ hộ (LLM hay chép cả dòng "Chủ hộ") trước khi đánh chỉ số dòng."""
    kept = []
    for item in listed if isinstance(listed, list) else []:
        if not isinstance(item, dict):
            continue
        if _identity(item.get("soDinhDanh")) in excluded or fold(_text(item.get("quanHeVoiChuHo")) or "") == "chu ho":
            continue
        kept.append({**item, "quanHeVoiChuHo": _relation(item.get("quanHeVoiChuHo"))})
    return kept


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    values = _by_name(fields)
    picked: dict[str, Any] = {}
    defaults: set[str] = set()

    province, ward, fallback = _agency_pick(values, options)
    if province and ward:
        picked[AGENCY_FIELD] = {"province": province, "ward": ward, "cityId": AGENCY_CITY_ID, "wardId": AGENCY_WARD_ID,
                                "readySelect": CASE_SELECT_ID}
        if fallback:
            defaults.add(AGENCY_FIELD)

    identity = _identity(values.get("NguoiDeNghi_SoDinhDanh"))
    full_name = _name(values.get("NguoiDeNghi_HoTen"))
    head_id = _identity(values.get("ChuHo_SoDinhDanh"))
    head_name = _name(values.get("ChuHo_HoTen"))
    relation = _relation(values.get("ChuHo_QuanHe"))
    if identity and head_id == identity:
        # Người đề nghị chính là chủ hộ.
        relation = HOUSEHOLD_HEAD
    if relation == HOUSEHOLD_HEAD:
        head_name, head_id = head_name or full_name, head_id or identity

    # Trợ lý đã hỏi công dân chọn Trường hợp (case_pipeline_options → options.bcaCase) → giữ đúng lựa chọn đó.
    chosen = (options or {}).get("bcaCase")
    picked[CASE_SELECT_ID] = chosen if chosen in CASES else _case(values, relation == HOUSEHOLD_HEAD)

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
    # Chọn Trường hợp là cổng tự sinh "Xóa đăng ký thường trú - <trường hợp>". Tờ khai hay chép nhầm nội dung thủ tục khác
    # (mapping 24/11/2026: "Cấp cho nhân khẩu thường trú…") → chỉ ghi đè khi câu của tờ khai đúng là đề nghị xóa.
    if content and "xoa" in fold(content):
        picked[CONTENT_ID] = content

    picked["txtHH_HEAD_FULLNAME"] = head_name
    picked["cboRELATIONSHIP_WITH_HHHEAD_ID"] = relation
    picked["txtID_CARD_NUMBER_HHEAD"] = head_id

    rows = _member_rows(_members(values.get("ThanhVien"), {identity, head_id} - {None}))
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
