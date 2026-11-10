"""Dịch dữ kiện đã trích sang ô SurveyJS của biểu mẫu cấp bản sao trích lục (Cổng DVC quốc gia mới)."""

import re
import unicodedata
from datetime import date

from app.pipelines._shared.area_remap import drop_fabricated_province, is_current_area, province_for_ward, remap_area
from app.pipelines._shared.cccd import id_birth_year, id_gender
from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type, normalize_issuer
from app.pipelines._shared.ethnic_normalize import co_ho_local_group
from app.pipelines._shared.formatting import upper_person_name

from .reason import QUAN_HE_OPTIONS, labeled_value, name_match, requester_context, section
from .schema import UI_COMP_BY_NAME

# Nhãn option "Loại trích lục bản sao cần cấp" giữ theo eForm hộ tịch; extension khớp gần đúng
# với option thật của cổng (đã fold dấu, so theo cụm từ).
_EVENT_TO_OPTION = {
    "birth": "Giấy khai sinh bản sao/Trích lục ghi vào Sổ hộ tịch việc khai sinh (bản sao)",
    "marriage": "Trích lục kết hôn (bản sao)/ Trích lục ghi chú kết hôn (bản sao)",
    "death": "Trích lục khai tử (bản sao)",
    "guardianship": "Trích lục đăng ký giám hộ (bản sao)",
    "guardianship_end": "Trích lục đăng ký chấm dứt giám hộ (bản sao)",
    "parent_child": "Trích lục đăng ký nhận cha, mẹ, con (bản sao)",
    "adoption": "Trich lục ghi vào Sổ hộ tịch việc nuôi con nuôi (bản sao)",
    "civil_change": "Trích lục thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc (bản sao)",
    "divorce": "Trích lục ghi chú ly hôn (bản sao)",
    "supervision": "Trích lục đăng ký giám sát giám hộ (bản sao)",
    "supervision_end": "Trích lục đăng ký chấm dứt giám sát giám hộ (bản sao)",
}
_EVENT_TO_DOCUMENT_NAME = {
    "birth": "Giấy khai sinh",
    "marriage": "Giấy chứng nhận kết hôn",
    "death": "Trích lục khai tử",
}
_EVENT_FROM_REASON = {
    "khai sinh": "birth", "ket hon": "marriage", "khai tu": "death", "giam ho": "guardianship",
    "cham dut giam ho": "guardianship_end", "nhan cha me con": "parent_child", "nuoi con nuoi": "adoption",
    "thay doi cai chinh": "civil_change", "ghi chu ly hon": "divorce", "giam sat giam ho": "supervision",
    "cham dut giam sat giam ho": "supervision_end",
}
# Cụm nhận loại trong chữ chép nguyên từ mục yêu cầu tờ khai; cụm dài đứng trước để "chấm dứt giám hộ" không
# bị đếm thêm thành "giám hộ".
_DECLARED_EVENT_PHRASES = (
    ("cham dut giam sat giam ho", "supervision_end"), ("giam sat giam ho", "supervision"),
    ("cham dut giam ho", "guardianship_end"), ("giam ho", "guardianship"),
    ("nhan cha me con", "parent_child"), ("nuoi con nuoi", "adoption"),
    ("thay doi", "civil_change"), ("cai chinh", "civil_change"), ("xac dinh lai dan toc", "civil_change"),
    ("ly hon", "divorce"), ("ket hon", "marriage"), ("khai tu", "death"), ("khai sinh", "birth"),
)
_GIAY_TO_DETAIL_KEYS = ("GiayTo_TenGiayTo", "GiayTo_CoQuanDangKy", "GiayTo_So", "GiayTo_QuyenSo", "GiayTo_NgayDangKy")

# Cách gọi khác của cùng một nhãn quan hệ trên cổng. "ba" trần không nhận: fold dấu rồi không
# phân biệt được "bà" với cách gọi bố.
_QUAN_HE_ALIASES = {
    "chinh minh": "Bản thân", "con": "Con đẻ", "con ruot": "Con đẻ", "bo": "Bố đẻ", "cha": "Bố đẻ",
    "cha de": "Bố đẻ", "bo ruot": "Bố đẻ", "cha ruot": "Bố đẻ", "cha nuoi": "Bố nuôi", "me": "Mẹ đẻ",
    "me ruot": "Mẹ đẻ", "ong noi": "Ông", "ong ngoai": "Ông", "ba noi": "Bà", "ba ngoai": "Bà",
    "anh": "Anh ruột", "anh trai": "Anh ruột", "chi": "Chị ruột", "chi gai": "Chị ruột",
    "chau": "Cháu ruột", "chau noi": "Cháu ruột", "chau ngoai": "Cháu ruột",
}
_SELF = "Bản thân"
_OTHER = "Khác"

# Nhãn khối giấy tờ tùy thân in trên giấy hộ tịch ("Giấy CMND/Giấy tờ hợp lệ thay thế", "Giấy tờ tùy thân"):
# dòng "Số:" ngay dưới là số thẻ của vợ/chồng/người đi khai, không phải số đăng ký.
_ID_LABEL_RE = re.compile(r"cmnd|cccd|can cuoc|chung minh|giay to tuy than|giay to hop le|dinh danh")
_ID_LOOKAHEAD_LINES = 3

# Trích lục khai tử/khai sinh in hai dòng "Số:": số trích lục đầu giấy ("27/TLKT-BS", "2575/2026/TLKT-BS") và
# "Số: <n> ngày ..." dưới nơi đăng ký. Ô Số đăng ký lấy số đầu giấy; LLM hay vớ dòng dưới rồi tự ghép năm, mà
# siết prompt thì các giấy khác mất luôn phần năm → chốt ở đây.
_EXTRACT_NO_RE = re.compile(r"(?<![\d/])(\d{1,6}(?:\s*/\s*\d{4})?\s*/\s*TLK([TS])(?:\s*-\s*[A-Z]{1,3})?)\b")
_EXTRACT_CODE_EVENT = {"T": "death", "S": "birth"}

_RESIDENCE_LABEL_RE = re.compile(r"\b(cu tru|thuong tru|tam tru)\b")

# Luật Căn cước: dưới 14 tuổi chưa bắt buộc có thẻ; số 12 chữ số của trẻ là số định danh, không phải
# số giấy tờ tùy thân.
_CAN_CUOC_MIN_AGE = 14
_HCM_PROVINCE_KEYS = {"hochiminh", "tphochiminh", "thanhphohochiminh", "tphcm", "hcm"}


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _quan_he_option(value) -> str:
    key = re.sub(r"^nguoi\s+", "", _fold(value).strip(".:;,- "))
    for option in QUAN_HE_OPTIONS:
        if _fold(option) == key:
            return option
    return _QUAN_HE_ALIASES.get(key, "")


def _is_under_14(value) -> bool:
    match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", str(value or "").strip())
    if not match:
        return False
    day, month, year = (int(part) for part in match.groups())
    try:
        born = date(year, month, day)
    except ValueError:
        return False
    today = date.today()
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return age < _CAN_CUOC_MIN_AGE


def _date_key(value) -> tuple | None:
    match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", str(value or "").strip())
    return (int(match[3]), int(match[2]), int(match[1])) if match else None


def _card_on_declaration(context: str, name, number: str) -> bool:
    """Tờ khai ghi người yêu cầu trùng tên người được cấp và kèm đúng số thẻ này → thẻ chắc chắn của họ."""
    value = labeled_value(section(context, "quan_he"), "Người yêu cầu tờ khai")
    parts = re.split(r"\s+[—–-]\s+", value, maxsplit=1)
    if len(parts) != 2 or not number:
        return False
    return _digits(parts[1]) == number and bool(parts[0]) and _fold(parts[0]) == _fold(name)


def _card_birth_year_mismatch(number, birth) -> bool:
    card_year = id_birth_year(number)
    birth_year = re.search(r"(\d{4})\s*$", str(birth or ""))
    return bool(card_year and birth_year and card_year != int(birth_year[1]))


def _card_not_recipient(number, birth, gender, issue_date, event: str, event_date,
                        on_declaration: bool = False) -> bool:
    """Thẻ đọc ra mâu thuẫn với chính người được cấp → thẻ của người khác trong hồ sơ bị gán nhầm.

    Số căn cước mã hoá giới tính + năm sinh chủ thẻ; người đã chết không thể được cấp thẻ sau ngày khai tử.
    Tờ khai đã ghép thẻ với đúng tên người được cấp thì lệch năm sinh là do giấy ghi sai ngày sinh, không bỏ thẻ.
    """
    card_gender = id_gender(number)
    if card_gender and _fold(gender) in {"nam", "nu"} and _fold(card_gender) != _fold(gender):
        return True
    if not on_declaration and _card_birth_year_mismatch(number, birth):
        return True
    issued, died = _date_key(issue_date), _date_key(event_date)
    return event == "death" and bool(issued and died) and issued > died


def _id_card_numbers(values: dict, options: dict) -> set[str]:
    """Số CMND/CCCD có trong hồ sơ: của người được cấp, của tài khoản nộp, và số đứng ngay dưới nhãn giấy tờ
    tùy thân trên giấy (CMND của người vợ trên giấy kết hôn không lọt vào field nào nhưng vẫn là số thẻ)."""
    found = {_digits(values.get("NguoiDuocCap_SoGiayTo")), _digits(values.get("NguoiDuocCap_SoDinhDanh")),
             requester_context(options)[1]}
    lines = [line for line in str(options.get("_ocr_text") or "").splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if not _ID_LABEL_RE.search(_fold(line)):
            continue
        for near in lines[index:index + _ID_LOOKAHEAD_LINES]:
            found.update(n for n in map(_digits, re.findall(r"\d[\d .]{7,}\d", near)) if len(n) in (9, 12))
    return {n for n in found if len(n) in (9, 12)}


def _extract_number(event: str, ocr_text: str) -> str:
    """Số in đầu trích lục đúng loại cần cấp. Hồ sơ có tờ khai thì số theo tờ khai; nhiều số khác nhau (trích lục
    của nhiều người) thì không biết của ai → trả rỗng để giữ số lượt trích đọc ra."""
    if "to khai" in _fold(ocr_text):
        return ""
    found = {re.sub(r"\s+", "", match[1]) for match in _EXTRACT_NO_RE.finditer(ocr_text)
             if _EXTRACT_CODE_EVENT[match[2]] == event}
    return found.pop() if len(found) == 1 else ""


def _labeled_text(lines: list[str], index: int) -> str:
    """Dòng có nhãn, nối thêm dòng kế nếu dòng đó không có nhãn riêng: giấy và OCR có thể xuống dòng giữa địa chỉ.
    "---" là vạch ngăn giữa các tệp OCR, không phải phần tiếp của dòng."""
    following = lines[index + 1].strip() if index + 1 < len(lines) else ""
    if not following or ":" in following or following == "---":
        return lines[index]
    return f"{lines[index]} {following}"


def _copied_from_death_place(value, ocr_text: str) -> bool:
    """Trích lục khai tử chỉ in "Nơi chết", không có dòng cư trú; LLM hay chép địa chỉ đó sang nơi cư trú. Địa chỉ
    có thật dưới một nhãn cư trú (kể cả trùng nơi chết) thì vẫn giữ."""
    if not isinstance(value, dict):
        return False
    parts = [re.sub(r"^(phuong|xa|thi tran)\s+", "", _fold(part))
             for key in ("diaChi", "xa") for part in str(value.get(key) or "").split(",")]
    parts = [part for part in parts if part]
    if not parts:
        return False
    lines = [line for line in ocr_text.splitlines() if line.strip()]
    labeled = [(_fold(line), _fold(_labeled_text(lines, index))) for index, line in enumerate(lines)]
    in_death_place = any("noi chet" in line and all(part in text for part in parts) for line, text in labeled)
    in_residence = any(_RESIDENCE_LABEL_RE.search(line) and all(part in text for part in parts)
                       for line, text in labeled)
    return in_death_place and not in_residence


def _death_registrar(ocr_text: str) -> str:
    """Nguyên dòng "Đã được đăng ký khai tử tại": LLM lúc chép đủ lúc cắt mất huyện/tỉnh. Có tờ khai thì theo tờ khai;
    nhiều nơi khác nhau (trích lục của nhiều người) thì không biết của ai → trả rỗng để giữ giá trị lượt trích."""
    if "to khai" in _fold(ocr_text):
        return ""
    lines = [line for line in ocr_text.splitlines() if line.strip()]
    found = {re.sub(r"\s+", " ", _labeled_text(lines, index).partition(":")[2]).strip()
             for index, line in enumerate(lines) if _fold(line).startswith("da duoc dang ky khai tu tai")}
    found.discard("")
    return found.pop() if len(found) == 1 else ""


def _id_doc_type_with_number(number, hint, issuer: str = "") -> str:
    # Căn cước/CCCD luôn 12 chữ số → số 9 chữ số chỉ có thể là CMND cũ.
    if len(_digits(number)) == 9:
        return "Chứng minh nhân dân"
    return id_doc_type(hint or "Căn cước", issuer)


def _area(value, ocr_text: str = ""):
    if not isinstance(value, dict):
        return None
    # Tờ khai hay chỉ ghi "xã X" không có tỉnh, LLM tự điền một tỉnh không hề có trên giấy
    # → bỏ tỉnh bịa (giữ khi cặp tỉnh/xã có thật) rồi suy lại từ danh mục xã bên dưới.
    value = drop_fabricated_province(value, ocr_text)
    province = str(value.get("tinh") or "").strip()
    if re.sub(r"[^a-z0-9]+", "", _fold(province)) in _HCM_PROVINCE_KEYS:
        province = "Thành phố Hồ Chí Minh"
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": province,
        "xa": str(value.get("xa") or "").strip(),
        "diaChi": str(value.get("diaChi") or "").strip(),
    }
    if not area["tinh"] and not area["xa"] and not area["diaChi"]:
        return None
    huyen = str(value.get("huyen") or "").strip()
    remapped = remap_area({**area, "huyen": huyen} if huyen else dict(area))
    if not isinstance(remapped, dict):
        return area
    # Xã cũ đã sáp nhập sang đơn vị mới khác tên → giữ tên cũ cuối địa chỉ chi tiết để lần ra địa bàn.
    old_name = re.sub(r"^(xã|phường|thị trấn)\s+", "", area["xa"], flags=re.IGNORECASE).strip()
    new_ward = str(remapped.get("xa") or "")
    detail = str(remapped.get("diaChi") or "").strip()
    if old_name and new_ward and _fold(old_name) not in _fold(new_ward) and _fold(old_name) not in _fold(detail):
        remapped = {**remapped, "diaChi": f"{detail}, {area['xa']}" if detail else area["xa"]}
    # Không có tỉnh → tỉnh DUY NHẤT có xã tên này; lấy đủ nhãn danh mục ("Xã ...") để khớp option.
    if not remapped.get("tinh") and remapped.get("xa"):
        found = province_for_ward(remapped["xa"])
        if found:
            remapped = {**remapped, "tinh": found[0], "xa": found[1]}
    # Xã không chọn được trên cổng: extension sẽ vớ nhầm option gần giống hoặc để trống mà không báo.
    # Bỏ trống xã, giữ tên đã đọc ở cuối địa chỉ chi tiết, đánh dấu để tô viền vàng.
    ward = str(remapped.get("xa") or "")
    if ward and not is_current_area(str(remapped.get("tinh") or ""), ward):
        detail = str(remapped.get("diaChi") or "").strip()
        if _fold(ward) not in _fold(detail):
            detail = f"{detail}, {ward}" if detail else ward
        remapped = {**remapped, "xa": "", "diaChi": detail, "_xaChuaChon": True}
    return remapped


def _declared_event(context: str) -> str:
    """Loại ghi ở mục yêu cầu tờ khai — chỉ nhận khi chữ chép ra nêu đúng MỘT loại."""
    text = " " + re.sub(r"[^a-z]+", " ", _fold(labeled_value(section(context, "giay_to_ho_tich"),
                                                             "Loại ghi trên tờ khai"))) + " "
    found = set()
    for phrase, code in _DECLARED_EVENT_PHRASES:
        if f" {phrase} " in text:
            found.add(code)
            text = text.replace(f" {phrase} ", "  ")
    return found.pop() if len(found) == 1 else ""


def _event_type(values: dict, context: str) -> str:
    # Mục yêu cầu tờ khai thắng giấy hộ tịch kèm theo: xin bản sao khai sinh kèm trích lục khai tử (mở thừa
    # kế) vẫn là khai sinh, dù lượt phân vai/trích có kết luận theo giấy kèm.
    declared = _declared_event(context)
    if declared:
        return declared
    event = str(values.get("GiayTo_LoaiSuKien") or "").strip().lower()
    if event in _EVENT_TO_OPTION:
        return event
    reason_event = re.sub(r"[^a-z ]+", " ", _fold(labeled_value(section(context, "giay_to_ho_tich"), "Loại trích lục cần cấp")))
    reason_event = re.sub(r"\s+", " ", reason_event).strip()
    return _EVENT_FROM_REASON.get(reason_event, "")


def _near_id(a: str, b: str) -> bool:
    # Lệch 1 chữ số mới coi là OCR đọc nhầm: số định danh người thân cùng tỉnh / cùng năm sinh lệch từ 2 chữ số.
    return len(a) == len(b) and sum(x != y for x, y in zip(a, b)) <= 1


# Vai người nộp do phân vai khai → nhãn được phép; dòng căn cứ của các vai này phải chứa tên / số người nộp.
_ROLE_LABELS = {
    "cha": {"Bố đẻ", "Bố nuôi"}, "me": {"Mẹ đẻ", "Mẹ nuôi"}, "vo": {"Vợ"}, "chong": {"Chồng"},
    "con": {"Con đẻ", "Con nuôi"},
}
# Vai mà dòng căn cứ là chính dòng "Quan hệ với ..." (người nộp đã được đối chiếu ở dòng khác) → nhãn nào cũng được.
_ROLE_ANY_LABEL = ("nguoi yeu cau to khai", "nguoi di khai co dong quan he")
_MIN_QUOTE_CHARS = 6


def _alnum(value) -> str:
    return re.sub(r"[^0-9a-z]+", "", _fold(value))


def _stated_relation(block: str, ocr_text: str) -> str:
    """Dòng căn cứ phân vai chép là dòng "Quan hệ với ...: X" có thật trong OCR và X quy được về một nhãn → nhãn đó."""
    quote = labeled_value(block, "Dòng giấy ghi quan hệ").strip(" \"'“”")
    if "quan he" not in _fold(quote) or ":" not in quote:
        return ""
    # Dòng "Quan hệ với ..." là của người đi khai / người yêu cầu: chỉ dùng khi phân vai đã nhận người đó là người nộp.
    role = _fold(labeled_value(block, "Vai người nộp trên giấy"))
    if role not in _ROLE_ANY_LABEL and role not in _ROLE_LABELS:
        return ""
    if _fold(labeled_value(block, "Đối chiếu với người nộp")).startswith("khac nguoi"):
        return ""
    if ocr_text and _alnum(quote) not in _alnum(ocr_text):
        return ""
    option = _quan_he_option(quote.rsplit(":", 1)[1])
    return option if option not in ("", _OTHER) else ""


def _relation_evidence_ok(block: str, relation: str, account_name: str, account_id: str, ocr_text: str) -> bool:
    """Kiểm căn cứ phân vai tự khai cho nhãn quan hệ: dòng chép phải có thật trong OCR, vai phải khớp nhãn, và
    với vai cha / mẹ / vợ / chồng / con thì dòng đó phải ghi tên (lệch ≤1 ký tự) hoặc số của người nộp."""
    role = _fold(labeled_value(block, "Vai người nộp trên giấy"))
    quote = labeled_value(block, "Dòng giấy ghi quan hệ").strip(" \"'“”")
    if len(_alnum(quote)) < _MIN_QUOTE_CHARS or (ocr_text and _alnum(quote) not in _alnum(ocr_text)):
        return False
    if role in _ROLE_ANY_LABEL:
        return True
    if relation not in _ROLE_LABELS.get(role, ()):
        return False
    digits = _digits(quote)
    id_on_line = bool(account_id) and any(
        _near_id(account_id, digits[i:i + len(account_id)]) for i in range(0, len(digits) - len(account_id) + 1))
    return bool(name_match(account_name, quote)) or id_on_line


def _relation(values: dict, context: str, options: dict | None, event: str) -> tuple[str, str, str]:
    """(nhãn quan hệ, quan hệ khác, cảnh báo). Số định danh hai phía quyết định "Bản thân"."""
    account_name, account_id = requester_context(options)
    subject = section(context, "nguoi_duoc_cap")
    # Người được cấp lấy theo phân vai trước: lượt trích hay chép thẻ của người nộp vào khối người được cấp.
    reason_name = labeled_value(subject, "Họ tên")
    reason_id = _digits(labeled_value(subject, "Số định danh"))
    extracted_id = _digits(values.get("NguoiDuocCap_SoDinhDanh"))
    subject_id = reason_id or extracted_id
    subject_name = reason_name or values.get("NguoiDuocCap_HoTen")
    same_name = bool(account_name) and _fold(account_name) == _fold(subject_name)
    deceased = event == "death" or _fold(labeled_value(subject, "Trạng thái")) == "da chet"

    block = section(context, "quan_he")
    relation = _quan_he_option(labeled_value(block, "Kết luận"))
    other = labeled_value(block, "Quan hệ khác")
    # Nhãn chi tiết phải có căn cứ kiểm được trên giấy; không đạt là suy đoán (vai người đi khai, cùng họ...)
    # → về nhánh "Khác". Phân vai bản cũ không khai vai thì giữ nguyên.
    has_role_line = re.search(r"(?im)^[ \t]*Vai người nộp trên giấy[ \t]*:", block or "")
    if has_role_line and relation != _SELF and (relation or other):
        ocr_text = str((options or {}).get("_ocr_text") or "")
        stated = _stated_relation(block, ocr_text)
        if stated:
            # Căn cứ là dòng "Quan hệ với ...: X" chép từ giấy → nhãn theo chính chữ X (LLM hay đảo chiều quan hệ).
            relation, other = stated, ""
        elif not _relation_evidence_ok(block, relation, account_name, account_id, ocr_text):
            relation, other = "", ""
    # Phân vai hay để "Khác" + "Mẹ" thay vì nhãn "Mẹ đẻ" của danh mục → quy về nhãn. Và có lúc đã đối chiếu người
    # yêu cầu tờ khai là "cùng người" với người nộp mà vẫn kết luận "Không xác định" → dùng chính kết quả đối chiếu
    # đó cùng quan hệ nó chép từ tờ khai.
    if relation == _OTHER and _quan_he_option(other) not in ("", _OTHER):
        relation, other = _quan_he_option(other), ""
    # Người nộp luôn là chủ tài khoản VNeID nên quan hệ ghi trên tờ khai là quan hệ của tài khoản — chỉ bỏ khi
    # phân vai đối chiếu rõ là khác người. Chữ không có nhãn riêng (em ruột, cô, chú...) → "Khác" + chữ đó.
    declared = labeled_value(block, "Quan hệ ghi trên tờ khai")
    declared_ok = bool(declared) and not _fold(labeled_value(block, "Đối chiếu với người nộp")).startswith("khac nguoi")
    if declared_ok and (not relation or (relation == _OTHER and not other)):
        relation = _quan_he_option(declared) or _OTHER
        other = declared if relation == _OTHER and _quan_he_option(declared) != _OTHER else other

    # Trích lục kết hôn là giấy chung của hai vợ chồng: người nộp là vợ / chồng trên giấy thì chính là người được cấp.
    if event == "marriage" and relation in ("Vợ", "Chồng"):
        return _SELF, "", ""
    # Số trùng tài khoản chỉ tự chốt "Bản thân" khi cùng tên tài khoản (khác tên là thẻ người nộp bị ghép sang
    # người khác), và số của lượt trích chỉ dùng khi phân vai đã xác định được người được cấp (hoặc không chạy):
    # hồ sơ chỉ có CCCD người nộp thì phân vai để trống mà lượt trích vẫn chép thẻ đó vào.
    subject_known = bool(reason_name) or not subject
    if account_id and not deceased and same_name and (
            account_id == reason_id or (account_id == extracted_id and subject_known)):
        return _SELF, "", ""
    if relation == _SELF:
        # Phân vai đã đối chiếu người (số lệch 1 chữ số do OCR / viết tay vẫn là cùng người).
        id_matches = bool(account_id and subject_id) and _near_id(account_id, subject_id)
        if deceased or (account_id and subject_id and not id_matches) or not (id_matches or same_name):
            return _OTHER, "", ("Phân vai kết luận \"Bản thân\" nhưng người nộp không khớp người được cấp — đã "
                                "chọn \"Khác\", cán bộ kiểm tra lại ô Quan hệ.")
    # Cổng không cho để trống ô Quan hệ: không xác định được thì chọn "Khác".
    if not relation or (relation == _OTHER and not other):
        return _OTHER, "", ("Chưa xác định được quan hệ của người nộp với người được cấp (tờ khai không ghi) — "
                            "đã chọn \"Khác\", cán bộ kiểm tra lại ô Quan hệ.")
    return relation, other if relation == _OTHER else "", ""


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = {f.get("name"): f.get("value") for f in fields or [] if isinstance(f, dict)}
    options = options or {}
    context = str(options.get("_reasoning_context") or "")
    ocr_text = str(options.get("_ocr_text") or "")
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        field = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": value}
        if default:
            field["default"] = True  # extension tô viền vàng: giá trị không đọc từ giấy tờ
        out.append(field)
        seen.add(name)

    event = _event_type(values, context)
    extracted_event = str(values.get("GiayTo_LoaiSuKien") or "").strip().lower()
    if extracted_event in _EVENT_TO_OPTION and extracted_event != event:
        # Lượt trích lấy số/ngày/cơ quan từ giấy hộ tịch khác loại tờ khai yêu cầu → không phải nguồn.
        values = {k: v for k, v in values.items() if k not in _GIAY_TO_DETAIL_KEYS}
        warnings.append("Thông tin đăng ký hộ tịch đọc ra thuộc giấy khác loại tờ khai yêu cầu — đã bỏ trống, "
                        "cán bộ nhập số, ngày, nơi đăng ký theo tờ khai.")
    # Phân vai không xác định được người được cấp (vd hồ sơ chỉ có CCCD người nộp) mà lượt trích vẫn điền khối
    # NguoiDuocCap_* → đó là thẻ của người nộp chép sang, không phải người được cấp.
    subject_block = section(context, "nguoi_duoc_cap")
    if subject_block and not labeled_value(subject_block, "Họ tên"):
        values = {k: v for k, v in values.items() if not k.startswith("NguoiDuocCap_")}
    # Quan hệ phải chốt TRƯỚC: chọn "Bản thân" thì cổng tự đổ khối người được cấp từ người nộp,
    # chọn khác thì cổng dựng lại khối đó — điền nhân thân trước sẽ bị xóa.
    relation, other, warning = _relation(values, context, options, event)
    if warning:
        warnings.append(warning)
    # "Khác" không kèm chữ là lựa chọn mặc định, không đọc từ giấy → viền vàng.
    add("citizenQuanhe", relation, default=relation == _OTHER and not other)
    add("citizenField8", other)

    if relation != _SELF:
        name = values.get("NguoiDuocCap_HoTen")
        if not name:
            warnings.append("Không đọc được người được cấp bản sao — cán bộ nhập khối người được cấp.")
        add("citizenNDK_HoVaTen", upper_person_name(name))
        personal_id = _digits(values.get("NguoiDuocCap_SoDinhDanh"))
        issue_date = values.get("NguoiDuocCap_NgayCap")
        # Số căn cước/CCCD chính là số định danh 12 số → thiếu số giấy tờ thì lấy số định danh (trẻ dưới 14 tuổi
        # chưa có thẻ được chặn ở dưới).
        card_number = _digits(values.get("NguoiDuocCap_SoGiayTo")) or (personal_id if len(personal_id) == 12 else "")
        # Số trùng tài khoản mà người được cấp đã chết hoặc khác tên chủ tài khoản → thẻ của người nộp bị gán nhầm
        # (hay gặp: trích lục khai tử kèm CCCD người thân, giấy hộ tịch để trống giấy tờ tùy thân) → bỏ cả cụm.
        account_name, account_id = requester_context(options)
        other_person = event == "death" or _fold(account_name) != _fold(name)
        if account_id and account_id in {card_number, personal_id} and other_person:
            warnings.append("Số giấy tờ đọc ra cho người được cấp trùng số của người nộp — đã bỏ trống, cán bộ "
                            "nhập giấy tờ tùy thân của người được cấp.")
            card_number = personal_id = ""
        birth = values.get("NguoiDuocCap_NgaySinh")
        on_declaration = _card_on_declaration(context, name, card_number or personal_id)
        if (card_number or personal_id) and _card_not_recipient(
            card_number or personal_id, birth, values.get("NguoiDuocCap_GioiTinh"), issue_date, event,
            values.get("GiayTo_NgayDangKy"), on_declaration,
        ):
            warnings.append("Giấy tờ tùy thân đọc ra không khớp người được cấp (giới tính/năm sinh trong số thẻ, "
                            "hoặc thẻ cấp sau ngày khai tử) — đã bỏ trống, cán bộ nhập giấy tờ tùy thân của người "
                            "được cấp.")
            card_number = personal_id = ""
        elif on_declaration and _card_birth_year_mismatch(card_number or personal_id, birth):
            warnings.append("Năm sinh mã hoá trong số căn cước lệch ngày sinh người được cấp trên giấy tờ — cán bộ "
                            "kiểm tra lại ngày sinh.")
        add("citizenNDK_SoDinhDanh", personal_id if len(personal_id) == 12 else "")
        add("citizenNDK_NgaySinh", birth)

        # Trẻ dưới 14 tuổi không có thẻ thật (không có ngày cấp) thì bỏ cả cụm giấy tờ tùy thân.
        if card_number and not (_is_under_14(birth) and not issue_date):
            # Mặc định cơ quan cấp theo ngày chỉ đúng với thẻ căn cước 12 số; CMND do công an tỉnh cấp.
            issuer = normalize_issuer(values.get("NguoiDuocCap_NoiCap")) or (
                default_issuer(issue_date) if len(card_number) == 12 else "")
            add("citizenNDK_LoaiGiayToTuyThan",
                _id_doc_type_with_number(card_number, values.get("NguoiDuocCap_LoaiGiayTo"), issuer))
            add("citizenNDK_SoGiayToTuyThan", card_number)
            add("citizenNDK_NoiCap", issuer)
            add("citizenNDK_NgayCap", issue_date)

        add("citizenField13", values.get("NguoiDuocCap_GioiTinh"))
        # Danh mục dân tộc của cổng không có "Khác": nhóm địa phương Cill/K'Ho/Lạch quy về Cơ Ho.
        add("citizenField32", co_ho_local_group(values.get("NguoiDuocCap_DanToc")))
        raw_area = values.get("NguoiDuocCap_NoiCuTru")
        # Nơi chết không phải nơi cư trú: bỏ tỉnh/xã/địa chỉ nhưng vẫn chọn Trong nước để bốn ô hiện ra cho cán bộ nhập.
        if event == "death" and _copied_from_death_place(raw_area, ocr_text):
            area = {"quocGia": raw_area.get("quocGia") or "Việt Nam"}
        else:
            area = _area(raw_area, ocr_text)
        if area:
            add("citizenNDK_LoaiCuTru", "Thường trú", default=True)
            # Radio "Trong nước" phải chọn trước: bốn ô địa chỉ chỉ hiện sau khi chọn.
            add("citizenNDK_Noicutru", "1")
            add("citizenField21", area.get("quocGia") or "Việt Nam")
            add("citizenNDK_TinhThanh", area.get("tinh"))
            add("citizenNDK_PhuongXa", area.get("xa"))
            add("citizenField38", area.get("diaChi"), default=bool(area.get("_xaChuaChon")))
            if area.get("_xaChuaChon") or not area.get("tinh"):
                warnings.append("Chưa chọn được tỉnh/phường, xã nơi cư trú của người được cấp theo danh mục hiện hành — "
                                "cán bộ chọn lại ô Tỉnh/Thành phố và Phường/Xã.")

    add("citizenLoaiViecYeuCau", _EVENT_TO_OPTION.get(event))
    registrar = values.get("GiayTo_CoQuanDangKy")
    if registrar and event == "death":
        registrar = _death_registrar(ocr_text) or registrar
    add("citizenHoSo_CoQuanDangKy", registrar)
    add("citizenTenGiayToHoTich", values.get("GiayTo_TenGiayTo") or _EVENT_TO_DOCUMENT_NAME.get(event))
    # Ô "Số:" góc trên giấy hộ tịch viết tay OCR hay không ra chữ số, LLM vớ sang dòng "Số:" của khối CMND
    # ngay trong thân giấy → số đăng ký trùng số thẻ là đọc nhầm, bỏ trống để cán bộ nhập.
    registration_no = _extract_number(event, ocr_text) or values.get("GiayTo_So")
    if _digits(registration_no) in _id_card_numbers(values, options):
        warnings.append("Số đăng ký đọc ra trùng số CMND/CCCD trong hồ sơ — đã bỏ trống, cán bộ nhập ô Số đăng ký "
                        "theo dòng \"Số:\" ở đầu giấy hộ tịch.")
        registration_no = ""
    add("citizencauhoi3", registration_no)
    add("citizencauhoi4", values.get("GiayTo_QuyenSo"))
    add("citizencauhoi5", values.get("GiayTo_NgayDangKy"))
    quantity = _digits(values.get("SoLuongBanSao"))
    add("citizenSoLuongBanSao", str(int(quantity)) if quantity and int(quantity) > 0 else "")
    return out, warnings
