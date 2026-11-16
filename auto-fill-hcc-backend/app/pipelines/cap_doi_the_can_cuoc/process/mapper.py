"""Dựng ô form Cấp đổi thẻ căn cước (Cổng DVC Bộ Công an) từ dữ kiện compact."""

import re
from difflib import SequenceMatcher
from typing import Any

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.naming import fold
from app.pipelines.cap_doi_the_can_cuoc.process.schema import (
    AGENCY_CITY_ID,
    AGENCY_FIELD,
    AGENCY_READY_ID,
    AGENCY_WARD_ID,
    DECLARANT_OTHER,
    DECLARANT_SELF,
    LEVEL_PROVINCE,
    LEVEL_WARD,
    PORTAL_PROVINCES,
    REASONS,
    RELATION_FATHER,
    RELATION_MOTHER,
    RELATION_REPRESENTATIVE,
    RESULT_ORG,
    RESULT_POST,
    UI_COMP_BY_NAME,
)

PROCEDURE_KEY = "cap-doi-the-can-cuoc"
# Xã + tỉnh của tài khoản quầy (server gắn ở app/process/router.py, client không tự gửi được).
ACCOUNT_AGENCY_OPTION = "_accountAgency"
LEVEL_FIELD = "radCapThucHien"

# Đoạn địa chỉ từ cấp xã trở lên — ô "Địa chỉ" nhận kết quả chỉ nhận phần dưới xã (Tỉnh/Xã có ô chọn riêng).
_AREA_PREFIX = re.compile(r"^(phuong|xa|thi tran|dac khu|quan|huyen|thi xa|thanh pho|tinh|tp)\b")
_EMAIL = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
_EMAIL_IN_TEXT = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_EMAIL_FIELDS = ("NguoiCanCap_Email", "NguoiDaiDien_Email")


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Bản sao options kèm xã/tỉnh tài khoản: dự phòng ô Cơ quan thực hiện (bắt buộc) khi giấy không ghi."""
    result = dict(options or {})
    result.pop(ACCOUNT_AGENCY_OPTION, None)
    if procedure == PROCEDURE_KEY and isinstance(user, dict) and user.get("tinh") and user.get("xa"):
        result[ACCOUNT_AGENCY_OPTION] = {"tinh": str(user["tinh"]), "xa": str(user["xa"])}
    return result


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def email_ocr_fallback(raw_fields: Any, documents: list[dict]) -> dict:
    """compact_field_fallback: LLM chép lệch email đều đặn (bỏ một chữ: "dinhvan…" → "dinvan…") dù OCR đọc đúng →
    email LLM trả không có trong chữ OCR thì thay bằng email GẦN NHẤT có trong OCR (giữ nguyên vai người của LLM)."""
    if isinstance(raw_fields, dict):
        fields = dict(raw_fields)
    else:
        fields = {item.get("name"): item.get("value") for item in raw_fields or []
                  if isinstance(item, dict) and item.get("name")}
    found: list[str] = []
    for doc in documents or []:
        for email in _EMAIL_IN_TEXT.findall(str(doc.get("text") or "")):
            if email.lower() not in found:
                found.append(email.lower())
    for name in _EMAIL_FIELDS:
        said = (_text(fields.get(name)) or "").replace(" ", "").lower()
        if not said or not found or said in found:
            continue
        best = max(found, key=lambda email: SequenceMatcher(None, said, email).ratio())
        if SequenceMatcher(None, said, best).ratio() >= 0.8:
            fields[name] = best
    return fields


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.replace("\n", " ").split()).strip(" :;,-")
    # Dòng chấm chấm của mẫu in ("………", "....") là ô trống.
    return text if text and re.search(r"[0-9A-Za-zÀ-ỹ]", text) else None


def _words(value: Any) -> str:
    """fold + bỏ dấu câu: so cụm nhận diện không vướng dấu phẩy ("ngày, tháng, năm sinh")."""
    return " ".join(re.sub(r"[^\w\s]", " ", fold(_text(value) or "")).split())


def _name(value: Any) -> str | None:
    text = _text(value)
    return text.upper() if text else None


def _date(value: Any) -> str | None:
    nums = re.findall(r"\d+", _text(value) or "")
    if len(nums) < 3:
        return None
    day, month, year = nums[0], nums[1], nums[2]
    if len(year) == 4 and 1 <= int(day) <= 31 and 1 <= int(month) <= 12:
        return f"{int(day):02d}/{int(month):02d}/{year}"
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
    """Giữ phần dưới cấp xã: "Số 8, tổ dân phố số 3, phường X, tỉnh Y" → "Số 8, tổ dân phố số 3"."""
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


def _province_core(value: str) -> str:
    return re.sub(r"^(cong an )?(tinh|thanh pho|tp) ", "", _words(value))


def _portal_province(value: str) -> str:
    """Nhãn tỉnh theo danh mục 34 tỉnh của cổng (cổng ghi "Thành phố Đồng Nai" dù nhãn chuẩn là "Tỉnh …")."""
    label = province_label(value) or value
    core = _province_core(label)
    return next((p for p in PORTAL_PROVINCES if _province_core(p) == core), label)


def _area(province: Any, ward: Any) -> tuple[str | None, str | None]:
    """Tỉnh + Xã theo địa giới hiện hành, tỉnh theo nhãn của cổng."""
    province, ward = _text(province), _text(ward)
    if not province:
        return None, None
    area = remap_area({"quocGia": "Việt Nam", "tinh": province, "xa": ward or ""}) or {}
    return _portal_province(_text(area.get("tinh")) or province), _text(area.get("xa")) or ward


def _reason(values: dict) -> str | None:
    """Nhãn option "Lý do cấp": nhãn LLM chép đúng → nhận luôn; lệch chữ → dò cụm đặc trưng (LLM trước, rồi nội dung đề
    nghị mục III.7 DC02)."""
    for raw in (values.get("LyDoCap"), values.get("NoiDungDeNghi")):
        said = _words(raw)
        if not said:
            continue
        exact = next((label for label, _ in REASONS if _words(label) == said), None)
        if exact:
            return exact
        for label, keys in REASONS:
            if any(key in said for key in keys):
                return label
    return None


def _relation(value: Any) -> str | None:
    said = _words(value)
    if not said:
        return None  # không đoán: chọn nhầm Cha/Mẹ là cổng đối chiếu CSDL báo sai quan hệ
    if said in ("cha", "bo", "ba"):
        return RELATION_FATHER
    if said in ("me", "ma"):
        return RELATION_MOTHER
    return RELATION_REPRESENTATIVE


def _by_representative(values: dict, subject_name: str | None, subject_id: str | None) -> bool:
    """Mục II DC02 ghi một người KHÁC người cần cấp đổi → cha/mẹ/người đại diện kê khai thay."""
    rep_name, rep_id = _name(values.get("NguoiDaiDien_HoTen")), _identity(values.get("NguoiDaiDien_SoDinhDanh"))
    if not (rep_name or rep_id):
        return False
    if rep_id and subject_id:
        return rep_id != subject_id
    return not (rep_name and subject_name and fold(rep_name) == fold(subject_name))


def _receipt_mode(value: Any) -> str | None:
    said = _words(value)
    if not said:
        return None
    if "buu" in said or "chuyen phat" in said or "gui ve" in said:
        return RESULT_POST
    if "truc tiep" in said or "co quan" in said or "tai cong an" in said:
        return RESULT_ORG
    return None


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    values = _by_name(fields)
    picked: dict[str, Any] = {}
    defaults: set[str] = set()

    subject_name = _name(values.get("NguoiCanCap_HoTen"))
    subject_id = _identity(values.get("NguoiCanCap_SoDinhDanh"))
    subject_phone = _phone(values.get("NguoiCanCap_SoDienThoai")) or _phone(values.get("NhanKetQua_SoDienThoai"))
    if _by_representative(values, subject_name, subject_id):
        # Phần I là tài khoản của cha/mẹ/người đại diện (cổng khoá) → khai người cần cấp ở Phần II; SĐT/email Phần I
        # là của người kê khai (mục II.5 DC02). Nút "Kiểm tra thông tin trong CSDL…" công dân tự bấm.
        picked["radIsNCC"] = DECLARANT_OTHER
        picked["txtFULLNAME_NCC"] = subject_name
        picked["txtBIRTHDATE_NCC"] = _date(values.get("NguoiCanCap_NgaySinh"))
        picked["cboGENDER_ID_NCC"] = _gender(values.get("NguoiCanCap_GioiTinh"), subject_id)
        picked["txtIDENTIFY_NUMBER_NCC"] = subject_id
        picked["cboRELATIONSHIP_WITH_NDN"] = _relation(values.get("NguoiDaiDien_QuanHe"))
        picked["txtPHONE_NUMBER_NDN"] = _phone(values.get("NguoiDaiDien_SoDienThoai"))
        picked["txtEMAIL_ADDRESS_NDN"] = _email(values.get("NguoiDaiDien_Email"))
    else:
        picked["radIsNCC"] = DECLARANT_SELF
        picked["txtPHONE_NUMBER_NDN"] = subject_phone
        picked["txtEMAIL_ADDRESS_NDN"] = _email(values.get("NguoiCanCap_Email"))
    picked["cboLyDoCap"] = _reason(values)

    province, ward = _area(values.get("CoQuan_Tinh"), values.get("CoQuan_Xa"))
    if not province:
        # Ô bắt buộc mà giấy không ghi cơ quan → Công an xã/tỉnh của tài khoản quầy, tô vàng để cán bộ soát.
        account = (options or {}).get(ACCOUNT_AGENCY_OPTION) or {}
        province, ward = _area(account.get("tinh"), account.get("xa"))
        if province and ward:
            defaults = {LEVEL_FIELD, AGENCY_FIELD}
        else:
            province = ward = None
    if province:
        # Không có cấp xã trên giấy = nộp tại Công an tỉnh/thành phố → radio Cấp Tỉnh, extension chỉ chọn ô tỉnh.
        picked[LEVEL_FIELD] = LEVEL_WARD if ward else LEVEL_PROVINCE
        picked[AGENCY_FIELD] = {"province": province, "ward": ward or "", "cityId": AGENCY_CITY_ID,
                                "wardId": AGENCY_WARD_ID, "readySelect": AGENCY_READY_ID, "readyPick": True}

    # Nhóm nhận kết quả: cổng chỉ hiện với vài lý do cấp (vd sắp xếp ĐVHC); ẩn thì giá trị nằm im, không ảnh hưởng.
    mode = _receipt_mode(values.get("NhanKetQua_HinhThuc"))
    picked["radNhanKetQua"] = mode
    if mode == RESULT_POST:
        city, village = _area(values.get("NhanKetQua_Tinh"), values.get("NhanKetQua_Xa"))
        picked["cboGET_RESULT_CITY_ADDR"] = city
        picked["cboGET_RESULT_VILLAGE_ADDR"] = village if city else None
        picked["txtGET_RESULT_DETAIL_ADDR"] = _address_below_ward(values.get("NhanKetQua_DiaChiChiTiet"))
        # Mục IV không ghi người nhận riêng → người cần cấp đổi nhận.
        picked["txtFULLNAME_NN"] = _name(values.get("NhanKetQua_HoTen")) or subject_name
        picked["txtPHONE_NUMBER_NN"] = _phone(values.get("NhanKetQua_SoDienThoai")) or subject_phone

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
