"""Map compact OCR facts for civil-status extract copy to legacy x-* UI fields."""

import re
import unicodedata
from datetime import date

from app.pipelines.trich_luc.process.schema import UI_ALIASES, UI_COMP_BY_NAME

_BIRTH_LOAI_YEU_CAU = "Giấy khai sinh bản sao/Trích lục ghi vào Sổ hộ tịch việc khai sinh (bản sao)"
_MARRIAGE_LOAI_YEU_CAU = "Trích lục kết hôn (bản sao)/ Trích lục ghi chú kết hôn (bản sao)"
_DEATH_LOAI_YEU_CAU = "Trích lục khai tử (bản sao)"
from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type, normalize_issuer
from app.pipelines._shared.area_remap import remap_area

# Luật Căn cước: dưới 14 tuổi chưa bắt buộc có thẻ căn cước. Số 12 chữ số của các em là
# SỐ ĐỊNH DANH CÁ NHÂN, không phải số giấy tờ tùy thân.
_CAN_CUOC_MIN_AGE = 14


def _is_under_14(value) -> bool:
    """Ngày/năm sinh cho thấy người này CHƯA đủ 14 tuổi. Không đọc được → False."""
    raw = str(value or "").strip()
    today = date.today()
    full = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", raw)
    if full:
        day, month, year = (int(part) for part in full.groups())
        try:
            born = date(year, month, day)
        except ValueError:
            return False
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return age < _CAN_CUOC_MIN_AGE
    year_only = re.match(r"^(\d{4})$", raw)
    if year_only:
        # Chỉ có năm sinh → chỉ kết luận khi CHẮC CHẮN chưa tới 14 tuổi.
        return today.year - int(year_only.group(1)) < _CAN_CUOC_MIN_AGE
    return False


_EVENT_TO_OPTION = {
    "birth": _BIRTH_LOAI_YEU_CAU,
    "marriage": _MARRIAGE_LOAI_YEU_CAU,
    "death": _DEATH_LOAI_YEU_CAU,
}

_EVENT_TO_DOCUMENT_NAME = {
    "birth": "Giấy khai sinh",
    "marriage": "Giấy chứng nhận kết hôn",
    "death": "Trích lục khai tử",
}

_HCM_PROVINCE_KEYS = {
    "hochiminh",
    "tphochiminh",
    "thanhphohochiminh",
    "tphcm",
    "hcm",
}

# Danh sách dân tộc biểu mẫu cho phép chọn trực tiếp. Giá trị ngoài danh sách phải chọn "Khác"
# rồi điền nguyên văn vào NDK_DanTocKhac; không để extension thử khớp một option không tồn tại.
_FORM_ETHNICITIES = {
    "ba na",
    "bo y",
    "brau",
    "bru-van kieu",
    "cham",
    "cho ro",
    "chu ru",
    "chut",
    "co",
    "co ho",
    "co lao",
    "co tu",
    "cong",
    "dao",
    "e de",
    "gia rai",
    "giay",
    "gie trieng",
    "ha nhi",
    "hoa",
    "hre",
    "khang",
    "khmer",
    "kho mu",
    "kinh",
    "la chi",
    "la ha",
    "la hu",
    "lao",
    "lo lo",
    "lu",
    "ma",
    "mang",
    "mnong",
    "mong",
    "mong (hmong)",
    "muong",
    "ngai",
    "nung",
    "o du",
    "pa then",
    "phu la",
    "pu peo",
    "ra glai",
    "ro mam",
    "san chay",
    "san diu",
    "si la",
    "ta oi",
    "tay",
    "thai",
    "tho",
    "xo dang",
    "xtieng",
}


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _copy_quantity(value) -> str:
    digits = _digits(value)
    return str(int(digits)) if digits and int(digits) > 0 else ""


# Quan hệ trên tờ khai được chuẩn hóa về đúng nhãn radio trên cổng. Không nhận "ba" trần vì sau
# khi fold dấu nó có thể là "bà" hoặc cách gọi "bố"; bỏ trống an toàn hơn tick nhầm quan hệ.
_QUANHE_OPTIONS = {
    "ban than": "Bản thân", "chinh minh": "Bản thân", "tu khai": "Bản thân",
    "tu ban than": "Bản thân", "con": "Con Đẻ", "con de": "Con Đẻ",
    "con ruot": "Con Đẻ", "con nuoi": "Con nuôi", "vo": "Vợ", "chong": "Chồng",
    "bo": "Bố Đẻ", "cha": "Bố Đẻ", "bo de": "Bố Đẻ", "cha de": "Bố Đẻ",
    "bo ruot": "Bố Đẻ", "cha ruot": "Bố Đẻ", "bo nuoi": "Bố nuôi",
    "cha nuoi": "Bố nuôi", "me": "Mẹ đẻ", "me de": "Mẹ đẻ",
    "me ruot": "Mẹ đẻ", "me nuoi": "Mẹ nuôi", "ba noi": "Bà", "ba ngoai": "Bà",
    "ong": "Ông", "ong noi": "Ông", "ong ngoai": "Ông", "anh": "Anh ruột",
    "anh ruot": "Anh ruột", "anh trai": "Anh ruột", "chi": "Chị ruột",
    "chi ruot": "Chị ruột", "chi gai": "Chị ruột", "chau": "Cháu ruột",
    "chau ruot": "Cháu ruột", "chau noi": "Cháu ruột", "chau ngoai": "Cháu ruột",
    "khac": "Khác",
}


def _quanhe_option(value) -> str:
    key = _fold(value).strip(".:;,- ")
    # Nhãn trên giấy hộ tịch hay ở dạng "người mẹ"/"người cha" — cùng một vai với "mẹ"/"cha".
    key = re.sub(r"^nguoi\s+", "", key)
    return _QUANHE_OPTIONS.get(key, "")


def _requester_identity(values: dict, options: dict | None) -> tuple[str, str]:
    """Người yêu cầu là ai: TỜ KHAI trước, rồi CCCD trong hồ sơ, cuối cùng mới tới mỏ neo VNeID."""
    ctx = (options or {}).get("formContext") or {}
    number = (
        _digits(values.get("TkNyc_SoGiayToTuyThan"))
        or _digits(values.get("Nyc_SoDinhDanh"))
        or _digits(ctx.get("applicantIdentityNumber"))
    )
    name = (
        _fold(values.get("TkNyc_HoTen"))
        or _fold(values.get("Nyc_HoTen"))
        or _fold(ctx.get("applicantFullname"))
    )
    return name, number


def _subject_identity(values: dict) -> tuple[str, str]:
    """Người được cấp bản sao là ai. HoTich_* đã được _apply_declaration_precedence phủ tờ khai."""
    number = _digits(values.get("HoTich_SoDinhDanh")) or _digits(values.get("ChuThe_SoDinhDanh"))
    name = (
        _fold(values.get("HoTich_HoTenNguoiDuocDangKy"))
        or _fold(values.get("NguoiDuocCap_HoTen"))
        or _fold(values.get("ChuThe_HoTen"))
    )
    return name, number


def _quanhe_from_record(values: dict, options: dict | None) -> tuple[str, bool]:
    """Quan hệ đọc từ CHÍNH GIẤY HỘ TỊCH: người yêu cầu có phải người thân nào ghi trên giấy không.

    Giấy hộ tịch tự nó đã ghi vai của những người thân quanh người được đăng ký (giấy khai sinh ghi
    cha/mẹ, giấy chứng nhận kết hôn ghi vợ/chồng...). Người yêu cầu trùng một trong những người đó
    thì QUAN HỆ ĐÃ CÓ SẴN TRÊN GIẤY — không được rơi xuống bước đối chiếu nhân thân rồi tick "Khác"
    chỉ vì người yêu cầu khác người được đăng ký.

    Trả (nhãn option, khớp bằng số giấy tờ). Khớp bằng số là bằng chứng chắc; khớp bằng họ tên yếu
    hơn (có thể trùng tên) nên caller đánh dấu suy đoán để FE tô vàng cho người dân rà lại.
    """
    rows = values.get("HoTich_NguoiThan")
    if not isinstance(rows, list):
        return "", False

    req_name, req_id = _requester_identity(values, options)
    by_name = ""
    for row in rows:
        if not isinstance(row, dict):
            continue
        option = _quanhe_option(row.get("quanHe"))
        if not option:
            continue
        row_id = _digits(row.get("soGiayTo"))
        if req_id and row_id and req_id == row_id:
            return option, True
        if req_name and not by_name and _fold(row.get("hoTen")) == req_name:
            by_name = option
    return by_name, False


def _resolve_quanhe(values: dict, options: dict | None) -> tuple[str, bool]:
    """Chốt ô tích "(5) Quan hệ với người được cấp bản sao". Trả (nhãn option, là suy đoán).

    Thứ tự nguồn — TỜ KHAI LUÔN ĐỨNG TRƯỚC, giống khai sinh đăng ký lại:
      1. Dòng "Quan hệ với người được cấp bản sao ..." của chính tờ khai: lời khai chính chủ.
      1b. VAI GHI TRÊN CHÍNH GIẤY HỘ TỊCH (cha/mẹ của giấy khai sinh, vợ/chồng của giấy kết hôn...):
         người yêu cầu trùng một người thân ghi trên giấy → lấy đúng vai đó. Phải xét TRƯỚC bước
         đối chiếu bên dưới, nếu không mọi hồ sơ "người thân đi xin hộ" đều bị tick "Khác" dù giấy
         đã ghi rõ vai. Khớp bằng số giấy tờ là chắc; khớp bằng họ tên thì tick viền vàng.
      2. Đối chiếu NGƯỜI YÊU CẦU (mục I) với NGƯỜI ĐƯỢC ĐĂNG KÝ (mục II): trùng người → "Bản thân".
         Số định danh cùng độ dài là bằng chứng chắc; so họ tên yếu hơn nên tick viền vàng.
         CMND 9 số và số định danh 12 số của CÙNG một người vẫn khác chuỗi, nên khác độ dài thì
         KHÔNG được coi là bằng chứng "khác người".
      3. Không kết luận được "Bản thân" nhưng hồ sơ CÓ tờ khai → tick "Khác" (viền vàng): an toàn
         nhất, tách khối người yêu cầu khỏi khối người được đăng ký để cán bộ soát lại.
      4. Không có tờ khai và không đối chiếu được → BỎ TRỐNG, không tick bừa.
    """
    raw_declared = values.get("CopyRequest_QuanHe")
    declared = _quanhe_option(raw_declared)
    if declared:
        return declared, False
    if str(raw_declared or "").strip():
        # Tờ khai CÓ ghi quan hệ nhưng chữ đó không khớp option nào (vd chữ viết tắt/nhập nhằng).
        # Không đoán bừa một vai cụ thể, nhưng cũng KHÔNG để trống ô tích: rơi về "Khác" (tô vàng).
        return "Khác", True

    from_record, matched_by_id = _quanhe_from_record(values, options)
    if from_record:
        return from_record, not matched_by_id

    req_name, req_id = _requester_identity(values, options)
    subj_name, subj_id = _subject_identity(values)

    if req_id and subj_id and len(req_id) == len(subj_id):
        return ("Bản thân" if req_id == subj_id else "Khác"), req_id != subj_id
    if req_name and subj_name:
        return ("Bản thân" if req_name == subj_name else "Khác"), True
    if req_id and subj_id:
        return ("Bản thân" if req_id == subj_id else "Khác"), True

    # Cạn nguồn: không tờ khai, giấy không ghi vai, không đủ nhân thân để đối chiếu. Vẫn phải tick
    # để ô "(5) Quan hệ" không bị bỏ trống — "Khác" là lựa chọn an toàn nhất (tách khối mục I khỏi
    # mục II) và được tô vàng để người dân đổi lại nếu đúng ra là quan hệ khác.
    return "Khác", True


def _civil_status_document_name(values: dict, event_type: str) -> str:
    """Tờ khai là nguồn yêu cầu, không phải tên giấy hộ tịch cần cấp bản sao."""
    name = str(values.get("HoTich_TenGiayTo") or "").strip()
    if not name or "to khai" in _fold(name) or "ban cam doan" in _fold(name):
        return _EVENT_TO_DOCUMENT_NAME.get(event_type, "")
    return name


def _requester_trusted(values: dict, options: dict | None = None) -> bool:
    """Nyc_* có đúng là giấy tờ của NGƯỜI YÊU CẦU không?

    HỒ SƠ GIẤY là căn cứ, KHÔNG phải tài khoản VNeID đang đăng nhập: thẻ đọc được trong hồ sơ vẫn
    dùng cho mục I kể cả khi khác người đăng nhập (bố/mẹ mang giấy tờ đi làm hộ, tài khoản là người
    khác...). Thứ tự chung của mục I: TỜ KHAI đè lên → CCCD đè lên → không có gì thì để im phần cổng
    đã tự điền từ VNeID.

    Ngoại lệ DUY NHẤT — thẻ trùng CHÍNH người được đăng ký (mục II): lúc đó thẻ có thể là
      (a) hồ sơ tự xin cho mình  → thẻ đúng là của người yêu cầu, vẫn điền mục I; hoặc
      (b) thẻ của người được đăng ký (vd CCCD của con) → đắp sang mục I là SAI NGƯỜI.
    Chỉ mỏ neo VNeID phân biệt được hai ca này, nên riêng ca trùng mới xét tài khoản đăng nhập.
    """
    requester_id = _digits(values.get("Nyc_SoDinhDanh"))
    requester_name = _fold(values.get("Nyc_HoTen"))
    subj_id = _digits(values.get("HoTich_SoDinhDanh"))
    subj_name = _fold(values.get("HoTich_HoTenNguoiDuocDangKy"))
    card_is_subject = (
        bool(requester_id and subj_id and requester_id == subj_id)
        or bool(requester_name and subj_name and requester_name == subj_name)
    )
    if not card_is_subject:
        return True
    return _card_matches_login(values, options)


def _card_matches_login(values: dict, options: dict | None) -> bool:
    """Nyc_* có đúng là thẻ của NGƯỜI ĐANG ĐĂNG NHẬP cổng không (mỏ neo VNeID)?

    CHỈ dùng để suy "tự xin cho chính mình": hồ sơ không có giấy hộ tịch, chỉ một thẻ, mà thẻ đó là
    của người đăng nhập → người yêu cầu cũng chính là người được đăng ký. KHÔNG dùng để quyết định
    có điền mục I hay không (việc đó theo hồ sơ giấy — xem _requester_trusted).
    """
    ctx = (options or {}).get("formContext") or {}
    applicant_id = _digits(ctx.get("applicantIdentityNumber"))
    applicant_name = _fold(ctx.get("applicantFullname"))
    requester_id = _digits(values.get("Nyc_SoDinhDanh"))
    requester_name = _fold(values.get("Nyc_HoTen"))
    if applicant_id and requester_id:
        return applicant_id == requester_id
    if applicant_name and requester_name:
        return applicant_name == requester_name
    return False


def _card_is_requester(values: dict, options: dict | None) -> bool:
    """CCCD Nyc_* có đúng là thẻ của NGƯỜI YÊU CẦU ghi trên tờ khai không?

    Tờ khai đã ghi rõ người yêu cầu → chỉ nhận thẻ trùng người đó (hồ sơ hay có thêm thẻ của người
    được đăng ký). Tờ khai không ghi → quay về mỏ neo VNeID/chủ thể như trước.
    """
    tk_name = _fold(values.get("TkNyc_HoTen"))
    tk_id = _digits(values.get("TkNyc_SoGiayToTuyThan"))
    card_name = _fold(values.get("Nyc_HoTen"))
    card_id = _digits(values.get("Nyc_SoDinhDanh"))
    if tk_id and card_id:
        return tk_id == card_id
    if tk_name and card_name:
        return tk_name == card_name
    return _requester_trusted(values, options)


def _strip_admin_prefix(value):
    """Giữ tên theo contract cũ, riêng phường hiện hành cần tiền tố để khớp option."""
    text = str(value or "").strip()
    if _fold(text) in {"phuong xuan huong", "p. xuan huong", "p xuan huong"}:
        return "Phường Xuân Hương"
    return re.sub(r"^(xã|phường|thị trấn|tt\.?)\s+", "", text, flags=re.IGNORECASE).strip()


def _area(value):
    if not isinstance(value, dict):
        return None
    province = str(value.get("tinh") or value.get("tỉnh") or "").strip()
    province_key = re.sub(r"[^a-z0-9]+", "", _fold(province))
    if province_key in _HCM_PROVINCE_KEYS:
        province = "Thành phố Hồ Chí Minh"
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": province,
        "xa": _strip_admin_prefix(value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường")),
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    return remap_area(out)


def _chu_the_matches_hotich(values: dict) -> bool:
    """ChuThe_* có khớp chủ thể trên giấy/tờ khai hộ tịch hay không."""
    subject_card_id = _digits(values.get("ChuThe_SoDinhDanh"))
    subject_card_name = _fold(values.get("ChuThe_HoTen"))
    subj_id = _digits(values.get("HoTich_SoDinhDanh"))
    subj_name = _fold(values.get("HoTich_HoTenNguoiDuocDangKy"))
    requester_id = _digits(values.get("Nyc_SoDinhDanh"))

    if subject_card_id and requester_id and subject_card_id == requester_id:
        return False
    if subject_card_id and subj_id:
        return subject_card_id == subj_id
    if subject_card_name and subj_name:
        return subject_card_name == subj_name
    # Không có mỏ neo chủ thể trong giấy hộ tịch: vẫn giữ ChuThe_* đã được prompt phân vai
    # từ quy tắc hai CCCD (một thẻ khớp formContext, thẻ còn lại là chủ thể).
    return bool(subject_card_id or subject_card_name) and not (subj_id or subj_name)


def _event_type(values: dict) -> str:
    raw = str(values.get("HoTich_LoaiSuKien") or "").strip().lower()
    if raw in _EVENT_TO_OPTION:
        return raw
    title = str(values.get("HoTich_TenGiayTo") or "").lower()
    if "kết hôn" in title or "ket hon" in title:
        return "marriage"
    if "khai tử" in title or "khai tu" in title or "chứng tử" in title or "chung tu" in title:
        return "death"
    if "khai sinh" in title:
        return "birth"
    return ""


_DECLARATION_TO_HOTICH = {
    "ToKhai_LoaiSuKien": "HoTich_LoaiSuKien",
    "ToKhai_TenGiayTo": "HoTich_TenGiayTo",
    "ToKhai_HoTenNguoiDuocCap": "HoTich_HoTenNguoiDuocDangKy",
    "ToKhai_NgaySinh": "HoTich_NgaySinh",
    "ToKhai_GioiTinh": "HoTich_GioiTinh",
    "ToKhai_DanToc": "HoTich_DanToc",
    "ToKhai_QuocTich": "HoTich_QuocTich",
    "ToKhai_SoDinhDanh": "HoTich_SoDinhDanh",
    "ToKhai_LoaiGiayToTuyThan": "HoTich_LoaiGiayToTuyThan",
    "ToKhai_SoGiayToTuyThan": "HoTich_SoGiayToTuyThan",
    "ToKhai_NgayCapGiayToTuyThan": "HoTich_NgayCapGiayToTuyThan",
    "ToKhai_NoiCapGiayToTuyThan": "HoTich_NoiCapGiayToTuyThan",
    "ToKhai_NoiCuTru": "HoTich_NoiCuTru",
    "ToKhai_CoQuanDangKy": "HoTich_CoQuanDangKy",
    "ToKhai_So": "HoTich_So",
    "ToKhai_QuyenSo": "HoTich_QuyenSo",
    "ToKhai_NgayDangKy": "HoTich_NgayDangKy",
}


def _event_from_title(title) -> str:
    folded = _fold(title)
    if "ket hon" in folded:
        return "marriage"
    if "khai tu" in folded or "chung tu" in folded:
        return "death"
    if "khai sinh" in folded:
        return "birth"
    return ""


def _same_registered_person(declared_name, document_name) -> bool:
    declared = _fold(declared_name)
    document = _fold(document_name)
    return bool(declared and document and (declared == document or declared in document or document in declared))


def _apply_declaration_precedence(values: dict) -> dict:
    """Tờ khai là khóa yêu cầu; giấy đính kèm chỉ bổ sung khi đúng cả loại và chủ thể."""
    merged = dict(values)
    # Tên giấy ghi nguyên văn ở mục (4) đáng tin hơn mã phân loại do model suy ra.
    declared_event = _event_from_title(values.get("ToKhai_TenGiayTo"))
    if not declared_event:
        raw_declared_event = str(values.get("ToKhai_LoaiSuKien") or "").strip().lower()
        declared_event = raw_declared_event if raw_declared_event in _EVENT_TO_OPTION else ""
    declared_name = values.get("ToKhai_HoTenNguoiDuocCap")

    if declared_event and declared_name:
        document_event = str(values.get("HoTich_LoaiSuKien") or "").strip().lower()
        if not document_event:
            document_event = _event_from_title(values.get("HoTich_TenGiayTo"))
        document_matches = (
            document_event == declared_event
            and _same_registered_person(declared_name, values.get("HoTich_HoTenNguoiDuocDangKy"))
        )
        if not document_matches:
            # Xóa toàn bộ fact của giấy sai loại/sai người trước khi phủ dữ liệu tờ khai.
            merged = {key: value for key, value in merged.items() if not key.startswith("HoTich_")}

    for declaration_name, hotich_name in _DECLARATION_TO_HOTICH.items():
        if declaration_name == "ToKhai_LoaiSuKien":
            continue
        value = values.get(declaration_name)
        if declaration_name == "ToKhai_SoDinhDanh" and len(_digits(value)) != 12:
            continue
        if value not in (None, "", {}, []):
            merged[hotich_name] = value
    if declared_event:
        merged["HoTich_LoaiSuKien"] = declared_event
    return merged


def _strip_role_label(text: str) -> str:
    return re.sub(
        r"^\s*(họ[, ]*chữ đệm[, ]*tên\s*)?(chồng|bên nam|nam|người chồng)\s*[:：-]?\s*",
        "",
        str(text or "").strip(),
        flags=re.IGNORECASE,
    ).strip()


def _ethnicity(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    simplified = (
        text.lower().replace("'", "").replace("’", "").replace("`", "")
        .replace("ỗ", "ô").replace("hmỗng", "hmông")
    )
    # CHỈ biến thể HMÔNG (có "H" đứng đầu) → "Mông (Hmông)". Dân tộc "Mông" thường GIỮ NGUYÊN "Mông".
    if "hmong" in simplified or "hmông" in simplified or "h mong" in simplified or "h mông" in simplified:
        return "Mông (Hmông)"
    if simplified in ("mong", "mông"):
        return "Mông"
    return text


def _ethnicity_for_form(value: str) -> tuple[str, str]:
    """Trả (giá trị dropdown, giá trị nhập tay khi dropdown là Khác)."""
    text = _ethnicity(value)
    if not text:
        return "", ""
    if _fold(text) in _FORM_ETHNICITIES:
        return text, ""
    return "Khác", text


def _registered_person_name(values: dict, event_type: str) -> str:
    raw = str(values.get("HoTich_HoTenNguoiDuocDangKy") or "").strip()
    if event_type != "marriage" or not raw:
        return raw

    parts = [p.strip() for p in re.split(r"[;\n|]+", raw) if p.strip()]
    for part in parts:
        if re.search(r"\b(chồng|bên nam|người chồng)\b", part, flags=re.IGNORECASE):
            return _strip_role_label(part)
    if len(parts) >= 2:
        return _strip_role_label(parts[-1])
    return _strip_role_label(raw)


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    """Derive deterministic UI fields from compact source facts."""
    values = _apply_declaration_precedence(_by_name(fields))
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if name in UI_ALIASES:
            field["aliases"] = UI_ALIASES[name]
        if default:
            field["default"] = True  # extension tô VIỀN VÀNG (giá trị mặc định, không từ giấy tờ)
        out.append(field)
        seen.add(name)

    has_requester = bool(values.get("Nyc_SoDinhDanh") or values.get("Nyc_HoTen"))
    # Tờ khai ghi rõ người yêu cầu → điền khối này bất kể CCCD có khớp tài khoản VNeID hay không
    # (người nộp hộ/tài khoản dịch vụ vẫn phải ra đúng người yêu cầu trên giấy).
    # Bất kỳ dữ kiện TkNyc_* nào cũng là bằng chứng tờ khai đã ghi người yêu cầu — kể cả khi tờ khai
    # chỉ đọc được ngày/nơi cấp giấy tờ. Có thông tin thì phát đủ field để extension ghi đè khối cổng
    # đã tự điền từ tài khoản VNeID (người nộp hộ thường KHÁC người ghi trên tờ khai).
    has_tk_requester = any(
        values.get(name) not in (None, "", {}, [])
        for name in values
        if name.startswith("TkNyc_")
    )
    has_subject_card = bool(values.get("ChuThe_SoDinhDanh") or values.get("ChuThe_HoTen"))
    has_hotich = any(
        name in values
        for name in (
            "HoTich_LoaiSuKien",
            "HoTich_TenGiayTo",
            "HoTich_HoTenNguoiDuocDangKy",
            "HoTich_CoQuanDangKy",
            "HoTich_So",
            "HoTich_NgayDangKy",
        )
    )
    has_subject_support = any(
        values.get(name)
        for name in (
            "NguoiDuocCap_HoTen",
            "NguoiDuocCap_NgaySinh",
            "NguoiDuocCap_GioiTinh",
        )
    )

    def _fill_requester() -> None:
        """Khối người yêu cầu: TỜ KHAI trước, CCCD chỉ bù field tờ khai không có.

        Cổng điền sẵn khối này theo tài khoản VNeID đang đăng nhập; hồ sơ giấy mới là căn cứ nên
        mapper luôn phát đủ field để extension GHI ĐÈ lên dữ liệu đăng nhập.
        Chỉ dùng CCCD khi thẻ đó đúng là của người yêu cầu (_card_is_requester) — nếu không, thẻ trong
        hồ sơ có thể là của người được đăng ký, ghép vào đây là sai người.
        """
        card = values if _card_is_requester(values, options) else {}
        so_giay_to = values.get("TkNyc_SoGiayToTuyThan") or card.get("Nyc_SoDinhDanh")
        ngay_cap = values.get("TkNyc_NgayCapGiayToTuyThan") or card.get("Nyc_NgayCap")
        requester_issuer = (
            normalize_issuer(values.get("TkNyc_NoiCapGiayToTuyThan"))
            or normalize_issuer(card.get("Nyc_NoiCap"))
            or default_issuer(ngay_cap)
        )
        add("HoVaTenC", values.get("TkNyc_HoTen") or card.get("Nyc_HoTen"))
        add("SoDinhDanhC", so_giay_to)
        # Loại giấy tờ theo nơi cấp: Bộ Công an → "Thẻ Căn cước"; Cục Cảnh sát → "Thẻ căn cước công dân".
        add("LoaiGiayToDinhDanhC",
            id_doc_type(values.get("TkNyc_LoaiGiayToTuyThan") or "Căn cước", requester_issuer))
        add("NYC_SoGiayToTuyThan", so_giay_to)
        add("NgayCapDDC", ngay_cap)
        add("NoiCapDDC", requester_issuer)
        add("NYC_LoaiCuTru", "Thường trú")
        area = _area(values.get("TkNyc_NoiCuTru")) or _area(card.get("Nyc_NoiCuTru"))
        if area:
            add("NYC_NoiCuTru", "1")
            add("NYC_NoiCuTru_TrongNuoc", area)

    def _fill_subject_from_card() -> None:
        subject_issuer = normalize_issuer(values.get("ChuThe_NoiCap")) or default_issuer(values.get("ChuThe_NgayCap"))
        add("NDK_HoVaTen", values.get("ChuThe_HoTen"))
        add("NDK_NgaySinh", values.get("ChuThe_NgaySinh"))
        add("NDK_GioiTinh", values.get("ChuThe_GioiTinh"))
        add("NDK_QuocTich", values.get("ChuThe_QuocTich") or "Việt Nam")
        add("NDK_SoDinhDanh", values.get("ChuThe_SoDinhDanh"))
        if values.get("ChuThe_SoDinhDanh"):
            add(
                "NDK_LoaiGiayToTuyThan",
                id_doc_type(values.get("ChuThe_LoaiGiayTo") or "Căn cước", subject_issuer),
            )
        add("NDK_SoGiayToTuyThan", values.get("ChuThe_SoDinhDanh"))
        add("NDK_NgayCap", values.get("ChuThe_NgayCap"))
        add("NDK_NoiCap", subject_issuer)
        add("NDK_LoaiCuTru", "Thường trú")
        area = _area(values.get("ChuThe_NoiCuTru"))
        if area:
            add("NDK_NoiCuTru", "1")
            add("NDK_NoiCuTru_TrongNuoc", area)

    def _fill_subject_from_requester() -> None:
        """Một CCCD khớp formContext và không có chủ thể khác → người yêu cầu tự xin cho mình."""
        requester_issuer = normalize_issuer(values.get("Nyc_NoiCap")) or default_issuer(values.get("Nyc_NgayCap"))
        add("NDK_HoVaTen", values.get("Nyc_HoTen"))
        add("NDK_NgaySinh", values.get("Nyc_NgaySinh"))
        add("NDK_GioiTinh", values.get("Nyc_GioiTinh"))
        add("NDK_QuocTich", "Việt Nam")
        add("NDK_SoDinhDanh", values.get("Nyc_SoDinhDanh"))
        if values.get("Nyc_SoDinhDanh"):
            add("NDK_LoaiGiayToTuyThan", id_doc_type("Căn cước", requester_issuer))
        add("NDK_SoGiayToTuyThan", values.get("Nyc_SoDinhDanh"))
        add("NDK_NgayCap", values.get("Nyc_NgayCap"))
        add("NDK_NoiCap", requester_issuer)
        add("NDK_LoaiCuTru", "Thường trú")
        area = _area(values.get("Nyc_NoiCuTru"))
        if area:
            add("NDK_NoiCuTru", "1")
            add("NDK_NoiCuTru_TrongNuoc", area)

    def _fill_ndk_from_support() -> None:
        """Tài liệu bổ trợ chỉ đủ chứng minh ba dữ kiện cơ bản của người ở mục II."""
        add("NDK_HoVaTen", values.get("NguoiDuocCap_HoTen"))
        add("NDK_NgaySinh", values.get("NguoiDuocCap_NgaySinh"))
        add("NDK_GioiTinh", values.get("NguoiDuocCap_GioiTinh"))
        add("NDK_QuocTich", "Việt Nam")

    requester_ready = has_tk_requester or (has_requester and _requester_trusted(values, options))

    # BƯỚC 1 BẮT BUỘC: chốt ô tích "(5) Quan hệ với người được cấp bản sao" TRƯỚC khi điền nhân thân.
    # eForm legacy dựng lại cả khối người yêu cầu (mục I) lẫn khối người được đăng ký (mục II) mỗi
    # lần ô tích này đổi, nên điền họ tên/CCCD trước rồi mới tick sẽ bị cổng xóa sạch. Field phải
    # đứng ĐẦU danh sách trả về để extension tick xong mới đổ dữ liệu đè lên khối cổng tự điền.
    quanhe, quanhe_guessed = _resolve_quanhe(values, options)
    if quanhe:
        add("NYC_QuanHe", quanhe, default=quanhe_guessed)

    if has_hotich:
        # Có giấy hộ tịch: khối người yêu cầu lấy tờ khai (CCCD bù thiếu); chủ thể lấy từ HoTich_*
        # và bổ sung bằng ChuThe_*.
        if requester_ready:
            _fill_requester()

        event_type = _event_type(values)

        has_person_info = has_subject_support or any(
            values.get(name)
            for name in (
                "HoTich_HoTenNguoiDuocDangKy",
                "HoTich_NgaySinh",
                "HoTich_GioiTinh",
                "HoTich_DanToc",
                "HoTich_SoDinhDanh",
                "HoTich_SoGiayToTuyThan",
                "HoTich_NoiCuTru",
                "ChuThe_HoTen",
                "ChuThe_SoDinhDanh",
            )
        )
        if has_person_info:
            subject_card = has_subject_card and _chu_the_matches_hotich(values)

            def _ct(name):
                return values.get(name) if subject_card else None

            add(
                "NDK_HoVaTen",
                _registered_person_name(values, event_type)
                or values.get("NguoiDuocCap_HoTen")
                or _ct("ChuThe_HoTen"),
            )
            add(
                "NDK_NgaySinh",
                values.get("HoTich_NgaySinh")
                or values.get("NguoiDuocCap_NgaySinh")
                or _ct("ChuThe_NgaySinh"),
            )
            add(
                "NDK_GioiTinh",
                values.get("HoTich_GioiTinh")
                or values.get("NguoiDuocCap_GioiTinh")
                or _ct("ChuThe_GioiTinh")
                or ("Nam" if event_type == "marriage" else None),
            )
            ethnicity, other_ethnicity = _ethnicity_for_form(values.get("HoTich_DanToc"))
            add("NDK_DanToc", ethnicity)
            add("NDK_DanTocKhac", other_ethnicity)
            add("NDK_QuocTich", values.get("HoTich_QuocTich") or _ct("ChuThe_QuocTich") or "Việt Nam")
            # Sau bước khóa nguồn, HoTich_* có thể là fact từ tờ khai đã được phủ sang
            # hoặc từ đúng giấy hộ tịch khớp loại + chủ thể.
            is_birth = event_type == "birth"
            ht_loai = values.get("HoTich_LoaiGiayToTuyThan")
            ht_so = values.get("HoTich_SoGiayToTuyThan")
            ht_ngay = values.get("HoTich_NgayCapGiayToTuyThan")
            ht_noi = values.get("HoTich_NoiCapGiayToTuyThan")

            # Guard hẹp cho giấy khai sinh cũ: nếu giấy tờ tùy thân không trùng số định
            # danh của trẻ thì đó có thể là giấy tờ người đi khai sinh, không được dùng.
            if is_birth and ht_so and values.get("HoTich_SoDinhDanh"):
                if _digits(ht_so) != _digits(values.get("HoTich_SoDinhDanh")):
                    ht_loai = ht_so = ht_ngay = ht_noi = None

            # Giấy tờ tùy thân RIÊNG của chính người được đăng ký (thẻ căn cước/CCCD của họ) —
            # chỉ là nguồn BÙ THIẾU: tờ khai/giấy hộ tịch ghi gì thì ưu tiên cái đó.
            ct_loai = _ct("ChuThe_LoaiGiayTo")
            ct_so = _ct("ChuThe_SoDinhDanh")
            ct_ngay = _ct("ChuThe_NgayCap")
            ct_noi = _ct("ChuThe_NoiCap")

            # Guard cuối: không chấp nhận cùng một số cho Nyc_* và ChuThe_*.
            _ct_d = _digits(ct_so)
            _subj_d = _digits(values.get("HoTich_SoDinhDanh"))
            _req_d = _digits(values.get("Nyc_SoDinhDanh"))
            _ct_valid = bool(_ct_d) and (
                _ct_d == _subj_d if _subj_d else _ct_d != _req_d
            )
            if not _ct_valid:
                ct_loai = ct_so = ct_ngay = ct_noi = None
            
            # FALLBACK: Khi không có ChuThe_* hợp lệ VÀ không có tờ khai giấy tờ,
            # kiểm tra Nyc_* (người yêu cầu) có TRÙNG chủ thể → fallback Nyc_* cho NDK_*
            if not ct_so and not ht_so:
                nyc_id = values.get("Nyc_SoDinhDanh")
                nyc_name = _fold(values.get("Nyc_HoTen"))
                subj_name = _fold(values.get("HoTich_HoTenNguoiDuocDangKy"))
                
                # Kiểm tra Nyc_* có khớp chủ thể không (so sánh tên vì không có số định danh trong giấy khai sinh)
                nyc_matches_subject = False
                if nyc_name and subj_name and nyc_name == subj_name:
                    nyc_matches_subject = True
                # Hoặc nếu có số định danh ở cả 2 bên
                if nyc_id and _subj_d and _digits(nyc_id) == _subj_d:
                    nyc_matches_subject = True
                
                # Nếu khớp → fallback Nyc_* cho giấy tờ của NDK
                if nyc_matches_subject and nyc_id:
                    ct_so = nyc_id
                    ct_loai = "Căn cước"  # Fallback từ CCCD người yêu cầu
                    ct_ngay = values.get("Nyc_NgayCap")
                    ct_noi = values.get("Nyc_NoiCap")

            # THỨ TỰ ƯU TIÊN: 
            # 1. Tờ khai/giấy hộ tịch (ht_*) - nguồn CHÍNH
            # 2. Thẻ căn cước của chủ thể (ct_*) - fallback khi tờ khai thiếu
            
            # Số định danh: Ưu tiên HoTich_SoDinhDanh từ tờ khai, fallback ht_so (giấy tờ tùy thân trong giấy HT), cuối cùng mới CCCD
            add("NDK_SoDinhDanh", values.get("HoTich_SoDinhDanh") or ht_so or ct_so)

            # Trẻ DƯỚI 14 TUỔI chưa bắt buộc có thẻ căn cước: số 12 chữ số của các em là SỐ ĐỊNH
            # DANH CÁ NHÂN (đã điền ở trên), KHÔNG phải số giấy tờ tùy thân → bỏ trống cả cụm
            # giấy tờ tùy thân. Em nào đã có thẻ thật và nộp kèm (ChuThe_*) thì vẫn điền bình thường.
            ndk_ngay_sinh = (
                values.get("HoTich_NgaySinh")
                or values.get("NguoiDuocCap_NgaySinh")
                or _ct("ChuThe_NgaySinh")
            )
            has_no_id_card = _is_under_14(ndk_ngay_sinh) and not ct_so

            if not has_no_id_card:
                # Số giấy tờ tùy thân: giống logic trên nhưng loại trừ số định danh khai sinh
                add(
                    "NDK_SoGiayToTuyThan",
                    (ht_so if not is_birth else None) or values.get("HoTich_SoDinhDanh") or ct_so,
                )

                # Ngày cấp: Ưu tiên tờ khai trước
                ndk_ngaycap = ht_ngay or ct_ngay
                add("NDK_NgayCap", ndk_ngaycap)

                # Nơi cấp: Ưu tiên tờ khai trước
                ndk_noicap = normalize_issuer(ht_noi) or normalize_issuer(ct_noi)
                if not ndk_noicap and ndk_ngaycap:
                    ndk_noicap = default_issuer(ndk_ngaycap)
                add("NDK_NoiCap", ndk_noicap)

                # Loại giấy tờ: Ưu tiên tờ khai trước
                id_hint = ht_loai or ct_loai
                if not id_hint and (ht_so or ct_so):
                    id_hint = "Căn cước"  # có số nhưng LLM ko trả loại → để nơi cấp quyết
                add("NDK_LoaiGiayToTuyThan", id_doc_type(id_hint, ndk_noicap or "") if id_hint else None)
            add("NDK_LoaiCuTru", "Thường trú")
            ndk_area = _area(values.get("HoTich_NoiCuTru")) or _area(_ct("ChuThe_NoiCuTru"))
            # Fallback nơi cư trú từ Nyc_NoiCuTru khi không có từ giấy hộ tịch/ChuThe
            # Kiểm tra nếu ct_so được set từ Nyc (fallback case) hoặc không có nơi cư trú nào
            if not ndk_area:
                # Kiểm tra nếu đã có fallback từ Nyc_* (ct_so mà không phải từ ChuThe_*)
                if ct_so and not _ct("ChuThe_SoDinhDanh"):
                    ndk_area = _area(values.get("Nyc_NoiCuTru"))
            if ndk_area:
                add("NDK_NoiCuTru", "1")
                add("NDK_NoiCuTru_TrongNuoc", ndk_area)

        add("HoSo_LoaiYeuCau", _EVENT_TO_OPTION.get(event_type))
        add("HoSo_CoQuanDangKy", values.get("HoTich_CoQuanDangKy"))
        add("HoSo_TenGiayTo", _civil_status_document_name(values, event_type))
        add("HoSo_So", values.get("HoTich_So"))
        add("HoSo_QuyenSo", values.get("HoTich_QuyenSo"))
        add("HoSo_NgayCapSo", values.get("HoTich_NgayDangKy"))
        add("PhuongThucNhanKQ", "2")
    elif has_subject_support:
        # Tờ khai/CCCD cho người yêu cầu; giấy chứng sinh/CT01 xác định người mục II.
        if requester_ready:
            _fill_requester()
        _fill_ndk_from_support()
    else:
        # Không có giấy hộ tịch: hai nhóm đã được phân vai độc lập trong prompt.
        if requester_ready:
            _fill_requester()
        if has_subject_card:
            _fill_subject_from_card()
        elif has_requester and _card_matches_login(values, options):
            # Chỉ có một CCCD và thẻ đó khớp người đăng nhập: tự làm cho chính mình.
            # Ở ĐÂY mới cần mỏ neo VNeID — vì phải chắc chắn người yêu cầu CŨNG là người được đăng ký.
            _fill_subject_from_requester()

    # Không bịa default cho NYC_*: chỉ phát field đọc được từ tờ khai/CCCD. Có dữ liệu thì extension
    # GHI ĐÈ lên thông tin VNeID điền sẵn; không có thì giữ nguyên phần cổng đã tự điền.

    # Form chỉ có ô số lượng, không có radio Có/Không cấp bản sao.
    copy_quantity = _copy_quantity(values.get("CopyRequest_Quantity"))
    if copy_quantity:
        add("SoLuong", copy_quantity)

    return out
