"""Dịch dữ kiện đã trích sang ô SurveyJS của biểu mẫu cấp bản sao trích lục (Cổng DVC quốc gia mới)."""

import re
import unicodedata
from datetime import date

from app.pipelines._shared.area_remap import (accent_only_ward, drop_fabricated_province, is_current_area,
                                              province_for_ward, remap_area)
from app.pipelines._shared.cccd import id_birth_year, id_gender
from app.pipelines._shared.compact_agent.issuer import (
    default_issuer,
    id_doc_type,
    issuer_by_issue_date,
    normalize_issuer,
    short_issuer,
)
from app.pipelines._shared.ethnic_normalize import co_ho_local_group, normalize_ethnic
from app.pipelines._shared.formatting import upper_person_name
from app.pipelines._shared.tai_khoan import account_context, matches_account
from app.pipelines.trich_luc_dvc_moi import che_do_demo

from .reason import QUAN_HE_OPTIONS, labeled_value, name_match, requester_context, section
from .schema import UI_COMP_BY_NAME, UI_REMOVED_BY_PORTAL

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

# Trích lục (bản sao) in hai dòng "Số:": số của bản trích lục đầu giấy ("27/TLKT-BS", "2575/2026/TLKT-BS") và số
# đăng ký gốc "Số: <n> ngày ..." dưới dòng "Đã được đăng ký ... tại". Ô Số đăng ký là số gốc; LLM lúc vớ số đầu giấy,
# lúc lấy đúng dòng gốc nhưng tự ghép năm từ ngày → chốt theo dòng gốc khi dòng đó có và chỉ có một số.
# Chỉ số có đuôi "-BS" mới là số của BẢN SAO trích lục; ".../TLCCHT", ".../TLKT" không đuôi là số của chính việc
# đăng ký ghi trong trích lục đó.
_COPY_NO_RE = re.compile(r"/\s*TL[A-ZĐ]{1,6}\s*-\s*BS\b", re.IGNORECASE)
_REGISTERED_AT_RE = re.compile(
    r"^(?:da (?:duoc )?)?dang ky (khai sinh|khai tu|ket hon|giam ho|nhan cha|nuoi con nuoi|ly hon)?[a-z ]{0,20}\btai\b"
    r"|^noi ghi\b")
_EVENT_WORD = {"birth": "khai sinh", "death": "khai tu", "marriage": "ket hon"}
_BODY_NO_RE = re.compile(r"(quyển\s+)?(?<![^\W\d_])(?:cấp\s+)?số\s*:?\s*(\d{1,6}(?:\s*/\s*\d{4})?)(?![\d/])",
                         re.IGNORECASE)
_BODY_NO_LOOKAHEAD_LINES = 2

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


def _registered_lines(event: str, ocr_text: str) -> list[tuple[list[str], int]]:
    """Các dòng "Đã (được) đăng ký <việc> tại: ..." / "Nơi ghi: ..." đúng loại việc cần cấp (dòng ghi việc khác bỏ)."""
    lines = [line for line in ocr_text.splitlines() if line.strip()]
    out = []
    for index, line in enumerate(lines):
        match = _REGISTERED_AT_RE.match(_fold(line))
        if match and (not match.group(1) or match.group(1) == _EVENT_WORD.get(event, match.group(1))):
            out.append((lines, index))
    return out


def _body_number(event: str, ocr_text: str) -> str:
    """Số đăng ký gốc ở dòng thân trích lục (dòng "đăng ký ... tại" hoặc ngay sau nó). Nhiều số khác nhau (trích lục
    của nhiều người, tờ khai ghi lệch) thì không biết số nào đúng → rỗng."""
    found = set()
    for lines, index in _registered_lines(event, ocr_text):
        window = [lines[index].partition(":")[2] or lines[index]] + lines[index + 1:index + 1 + _BODY_NO_LOOKAHEAD_LINES]
        for line in window:
            match = next((m for m in _BODY_NO_RE.finditer(line) if not m.group(1)), None)
            if match:
                found.add(re.sub(r"\s+", "", match.group(2)))
                break
    return found.pop() if len(found) == 1 else ""


# Giấy mẫu cũ in số và quyển số chung một ô "Số: 359,Q.S: 03" ("Q.S" / "QS" = quyển số).
_BOOK_IN_NO_RE = re.compile(r"\s*[,;/]?\s*(?:quyển\s*số|q\.?\s*s)\s*[:.]?\s*(\S+)\s*$", re.IGNORECASE)


def _split_book_no(value) -> tuple[str, str]:
    """(số đăng ký, quyển số) khi lượt trích chép cả quyển số vào ô số."""
    text = " ".join(str(value or "").split())
    match = _BOOK_IN_NO_RE.search(text)
    if not match or not text[:match.start()].strip():
        return text, ""
    return text[:match.start()].strip(" ,;/"), match.group(1).strip(" .,;")


def _registration_number(event: str, value, ocr_text: str) -> str:
    """Số đăng ký gốc thay cho số lượt trích khi lượt trích bỏ trống, lấy số của bản trích lục ("-BS"), hoặc chép
    lẫn cả chữ "ngày ..." của dòng gốc. Số khác (kể cả cách ghi "<số>/<năm>" quen dùng) thì giữ."""
    text = " ".join(str(value or "").split())
    body = _body_number(event, ocr_text)
    if not body:
        return text
    leading = re.match(r"\d+", text)
    if not text or _COPY_NO_RE.search(text):
        return body
    if leading and "ngay" in _fold(text) and leading.group(0).lstrip("0") == body.split("/")[0].lstrip("0"):
        return body
    return text


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


def _died_at_home(ocr_text: str) -> bool:
    """Dòng "Nơi chết" ghi chết TẠI NHÀ ("Tại nhà", "Tại nhà riêng", "Tại gia đình", "Tại nhà ở …"): nhà đó là nơi người chết ở, dùng
    được làm nơi cư trú (giá trị suy ra). Chết ở bệnh viện / nơi khác thì không."""
    lines = [line for line in str(ocr_text or "").splitlines() if line.strip()]
    for index, line in enumerate(lines):
        folded = _fold(_labeled_text(lines, index))
        if "noi chet" in folded and re.match(r"\W*tai (?:nha|gia)\b", folded.split("noi chet", 1)[1].lstrip(" :.-")):
            return True
    return False


def _death_registrar(ocr_text: str) -> str:
    """Nguyên dòng "Đã được đăng ký khai tử tại": LLM lúc chép đủ lúc cắt mất huyện/tỉnh. Có tờ khai thì theo tờ khai;
    nhiều nơi khác nhau (trích lục của nhiều người) thì không biết của ai → trả rỗng để giữ giá trị lượt trích."""
    if "to khai" in _fold(ocr_text):
        return ""
    lines = [line for line in ocr_text.splitlines() if line.strip()]
    found = {_agency_part(_labeled_text(lines, index).partition(":")[2])
             for index, line in enumerate(lines) if _fold(line).startswith("da duoc dang ky khai tu tai")}
    found.discard("")
    return found.pop() if len(found) == 1 else ""


def _agency_part(text: str) -> str:
    """Phần cơ quan của dòng "đăng ký ... tại": dòng in liền / nối dòng kế "<cơ quan>. Số: <n> ngày ..." hay "Nơi ghi:
    <cơ quan>, Sổ đăng ký ..." → dừng trước chữ "Số" / "Sổ"."""
    text = re.split(r"(?i)\s*[,;.]?\s*(?<![^\W\d_])(?:quyển\s+số|số|sổ)\b", text)[0]
    return " ".join(text.split()).strip(" ,.;")


def _full_registrar(event: str, value, ocr_text: str) -> str:
    """Cơ quan ở dòng "đăng ký ... tại" của trích lục khi lượt trích bỏ trống hoặc chỉ chép phần đầu của chính dòng
    đó (cắt mất huyện / tỉnh). Có tờ khai, hoặc nhiều nơi khác nhau → giữ lượt trích."""
    text = " ".join(str(value or "").split())
    if "to khai" in _fold(ocr_text):
        return text
    found = set()
    for lines, index in _registered_lines(event, ocr_text):
        found.add(_agency_part(_labeled_text(lines, index).partition(":")[2]))
    found.discard("")
    if len(found) != 1:
        return text
    full = found.pop()
    key = lambda v: re.sub(r"\bubnd\b", "uy ban nhan dan", _fold(v)).replace(",", " ").split()
    return full if not text or (key(full)[:len(key(text))] == key(text) and len(key(full)) > len(key(text))) else text


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
    # Không có tỉnh → tỉnh DUY NHẤT có xã tên này; lấy đủ nhãn danh mục ("Xã ...") để khớp option.
    if not remapped.get("tinh") and remapped.get("xa"):
        found = province_for_ward(remapped["xa"])
        if found:
            remapped = {**remapped, "tinh": found[0], "xa": found[1]}
    ward = str(remapped.get("xa") or "")
    if ward and not is_current_area(str(remapped.get("tinh") or ""), ward):
        # Tên xã chỉ lệch dấu thanh với một xã hiện hành của tỉnh (OCR chữ viết tay đọc nhầm dấu) → xã đó.
        ward = accent_only_ward(str(remapped.get("tinh") or ""), ward) or ward
        remapped = {**remapped, "xa": ward}
    # Xã không chọn được trên cổng: extension sẽ vớ nhầm option gần giống hoặc để trống mà không báo.
    # Bỏ trống xã, đánh dấu để tô viền vàng + cảnh báo cán bộ chọn lại. Không nối tên xã đã đọc vào địa chỉ chi
    # tiết: ô đó chỉ ghi số nhà / đường / thôn, xã cũ nằm thêm ở đó là thừa (người dùng báo 13/11).
    ward = str(remapped.get("xa") or "")
    if ward and not is_current_area(str(remapped.get("tinh") or ""), ward):
        remapped = {**remapped, "xa": "", "_xaChuaChon": True}
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


def _number_on_paper(number: str, ocr_text: str) -> bool:
    """Số 12 chữ số có in nguyên dãy trên giấy (bỏ dấu chấm / khoảng trắng chen giữa)."""
    if len(number) != 12 or not ocr_text:
        return False
    return re.search(rf"(?<!\d){number}(?!\d)", re.sub(r"(?<=\d)[ .](?=\d)", "", ocr_text)) is not None


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
        # Họ tên trên giấy cũ / viết tay lệch một chữ cái so với tài khoản, số trên giấy là CMND cũ: vẫn cùng người
        # khi chính số định danh của tài khoản có in trên giấy tờ trong hồ sơ (thẻ căn cước của người đó).
        near_self = bool(account_name and subject_name) and bool(name_match(account_name, str(subject_name))) and (
            _number_on_paper(account_id, str((options or {}).get("_ocr_text") or "")))
        if near_self:
            id_matches = True
        if deceased or (account_id and subject_id and not id_matches) or not (id_matches or same_name):
            return _OTHER, "", ("Phân vai kết luận \"Bản thân\" nhưng người nộp không khớp người được cấp — đã "
                                "chọn \"Khác\", cán bộ kiểm tra lại ô Quan hệ.")
    # Cổng không cho để trống ô Quan hệ: không xác định được thì chọn "Khác".
    if not relation or (relation == _OTHER and not other):
        return _OTHER, "", ("Chưa xác định được quan hệ của người nộp với người được cấp (tờ khai không ghi) — "
                            "đã chọn \"Khác\", cán bộ kiểm tra lại ô Quan hệ.")
    return relation, other if relation == _OTHER else "", ""


def _only_account_documents(values: dict, context: str, options: dict | None) -> bool:
    """Hồ sơ không có tờ khai, giấy ủy quyền hay giấy hộ tịch, chỉ có giấy tờ của chủ tài khoản: phân vai khai "Nguồn:
    giấy tờ chủ tài khoản"; hoặc phân vai để trống người được cấp mà thẻ lượt trích đọc ra trùng đúng số định danh và
    họ tên tài khoản."""
    subject = section(context, "nguoi_duoc_cap")
    account_name, account_id = requester_context(options)
    if _fold(labeled_value(subject, "Nguồn")) == "giay to chu tai khoan":
        # Phân vai đôi khi gắn nhãn này cả khi chính nó ghi người được cấp là người KHÁC (thẻ của người khác người nộp):
        # tin nhãn chỉ khi họ tên hoặc số định danh của người được cấp mà phân vai ghi khớp tài khoản.
        subject_name = _fold(labeled_value(subject, "Họ tên"))
        subject_id = _digits(labeled_value(subject, "Số định danh"))
        if not (subject_name or subject_id) or not (account_name or account_id):
            return True
        return bool(account_id and subject_id == account_id) or bool(account_name and subject_name == _fold(account_name))
    papers = section(context, "giay_to_ho_tich")
    if labeled_value(subject, "Họ tên") or labeled_value(papers, "Loại ghi trên tờ khai") or labeled_value(
            papers, "Tài liệu nguồn"):
        return False
    number = _digits(values.get("NguoiDuocCap_SoDinhDanh") or values.get("NguoiDuocCap_SoGiayTo"))
    return bool(account_id) and number == account_id and _fold(account_name) == _fold(values.get("NguoiDuocCap_HoTen"))


def _self_subject_values(values: dict, options: dict | None) -> dict:
    """Field của khối người được cấp khi quan hệ là "Bản thân": khóa nào tài khoản gửi thì lấy theo tài khoản (form
    SurveyJS chỉ đọc được họ tên + số định danh của khối người nộp), khóa còn lại theo giấy tờ.

    Lượt trích có thể đọc khối này theo người KHÁC chủ tài khoản (trích lục kết hôn: vợ nộp, giấy đọc ra chồng) →
    chỉ giữ giá trị đọc từ giấy khi đó đúng là chủ tài khoản, không ghép nhân thân hai người vào một khối."""
    account = account_context(options)
    same_person = matches_account(account, values.get("NguoiDuocCap_HoTen"), values.get("NguoiDuocCap_SoDinhDanh"),
                                  values.get("NguoiDuocCap_NgaySinh"))
    if not same_person:
        values = {key: value for key, value in values.items() if not key.startswith("NguoiDuocCap_")}
    out = {**values, **{f"NguoiDuocCap_{key}": account[key]
                        for key in ("NgaySinh", "GioiTinh", "DanToc", "NgayCap", "NoiCap") if account.get(key)}}
    name = str(account.get("HoTen") or "").strip()
    # Tài khoản lưu tên không dấu thì không đè lên tên có dấu đọc từ giấy.
    if name and not (name.isascii() and not str(values.get("NguoiDuocCap_HoTen") or "x").isascii()):
        out["NguoiDuocCap_HoTen"] = name
    number = _digits(account.get("SoDinhDanh"))
    if len(number) == 12:
        out["NguoiDuocCap_SoDinhDanh"] = out["NguoiDuocCap_SoGiayTo"] = number
    residence = account.get("NoiCuTru")
    if isinstance(residence, dict) and residence.get("tinh") and residence.get("xa"):
        out["NguoiDuocCap_NoiCuTru"] = {"quocGia": "Việt Nam", **residence}
    return out


def _submitter_phone(value, context: str) -> str:
    """Số điện thoại người nộp đọc từ giấy: chỉ khi người nộp có trong hồ sơ và số đúng dạng di động/cố định VN."""
    if _fold(labeled_value(section(context, "nguoi_nop"), "Có trong hồ sơ")) != "co":
        return ""
    digits = _digits(value)
    if digits.startswith("84") and len(digits) in (11, 12):
        digits = "0" + digits[2:]
    return digits if re.fullmatch(r"0\d{9,10}", digits) else ""


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

    # Ô SĐT là ô duy nhất người nộp tự điền trong khối người nộp (khối khóa theo tài khoản).
    add("citizenPhone", _submitter_phone(values.get("NguoiNop_SoDienThoai"), context))
    event = _event_type(values, context)
    extracted_event = str(values.get("GiayTo_LoaiSuKien") or "").strip().lower()
    if extracted_event in _EVENT_TO_OPTION and extracted_event != event:
        # Lượt trích lấy số/ngày/cơ quan từ giấy hộ tịch khác loại tờ khai yêu cầu → không phải nguồn.
        values = {k: v for k, v in values.items() if k not in _GIAY_TO_DETAIL_KEYS}
        warnings.append("Thông tin đăng ký hộ tịch đọc ra thuộc giấy khác loại tờ khai yêu cầu — đã bỏ trống, "
                        "cán bộ nhập số, ngày, nơi đăng ký theo tờ khai.")
    # Hồ sơ chỉ có giấy tờ của chủ tài khoản (không tờ khai / ủy quyền / giấy hộ tịch) → xin bản sao cho bản thân.
    only_account = event != "death" and _only_account_documents(values, context, options)
    # Phân vai không xác định được người được cấp mà lượt trích vẫn điền khối NguoiDuocCap_* (hồ sơ có giấy của người
    # khác) → đó là thẻ của người nộp chép sang, không phải người được cấp.
    subject_block = section(context, "nguoi_duoc_cap")
    if subject_block and not labeled_value(subject_block, "Họ tên") and not only_account:
        values = {k: v for k, v in values.items() if not k.startswith("NguoiDuocCap_")}
    # Quan hệ phải chốt TRƯỚC: chọn "Bản thân" thì cổng tự đổ khối người được cấp từ người nộp,
    # chọn khác thì cổng dựng lại khối đó — điền nhân thân trước sẽ bị xóa.
    relation, other, warning = _relation(values, context, options, event)
    if only_account:
        relation, other = _SELF, ""
        warning = ("Hồ sơ chỉ có giấy tờ của người nộp — đã chọn \"Bản thân\", cán bộ kiểm tra lại ô Quan hệ.")
    if warning:
        warnings.append(warning)
    # "Khác" không kèm chữ / "Bản thân" suy từ giấy tờ của chính người nộp: không đọc từ giấy → viền vàng.
    add("citizenQuanhe", relation, default=(relation == _OTHER and not other) or only_account)
    add("citizenField8", other)

    # "Bản thân": cổng tự chép khối người được cấp từ khối người nộp. Vẫn trả khối này để đối chiếu được dữ liệu: ô nào
    # tài khoản có giá trị thì lấy theo tài khoản, ô tài khoản không gửi mới theo giấy tờ; mọi ô của khối chỉ ghi khi
    # còn trống (onlyIfEmpty) nên không đè lên dữ liệu cổng vừa chép.
    self_filing = relation == _SELF
    if self_filing:
        values = _self_subject_values(values, options)
    block_start = len(out)
    name = values.get("NguoiDuocCap_HoTen")
    if not name and not self_filing:
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
    if not self_filing and account_id and account_id in {card_number, personal_id} and other_person:
        warnings.append("Số giấy tờ đọc ra cho người được cấp trùng số của người nộp — đã bỏ trống, cán bộ "
                        "nhập giấy tờ tùy thân của người được cấp.")
        card_number = personal_id = ""
    birth = values.get("NguoiDuocCap_NgaySinh")
    on_declaration = _card_on_declaration(context, name, card_number or personal_id)
    # "Bản thân": số là của chính chủ tài khoản → không lấy ngày sinh / giới tính đọc từ giấy để loại số đó.
    doubted = "" if self_filing else card_number or personal_id
    if doubted and _card_not_recipient(
        doubted, birth, values.get("NguoiDuocCap_GioiTinh"), issue_date, event,
        values.get("GiayTo_NgayDangKy"), on_declaration,
    ):
        warnings.append("Giấy tờ tùy thân đọc ra không khớp người được cấp (giới tính/năm sinh trong số thẻ, "
                        "hoặc thẻ cấp sau ngày khai tử) — đã bỏ trống, cán bộ nhập giấy tờ tùy thân của người "
                        "được cấp.")
        card_number = personal_id = ""
    elif doubted and on_declaration and _card_birth_year_mismatch(doubted, birth):
        warnings.append("Năm sinh mã hoá trong số căn cước lệch ngày sinh người được cấp trên giấy tờ — cán bộ "
                        "kiểm tra lại ngày sinh.")
    add("citizenNDK_SoDinhDanh", personal_id if len(personal_id) == 12 else "")
    add("citizenNDK_NgaySinh", birth)

    # Trẻ dưới 14 tuổi không có thẻ thật (không có ngày cấp) thì bỏ cả cụm giấy tờ tùy thân.
    if card_number and not (_is_under_14(birth) and not issue_date):
        # Mặc định cơ quan cấp theo ngày chỉ đúng với thẻ căn cước 12 số; CMND do công an tỉnh cấp.
        issuer = normalize_issuer(values.get("NguoiDuocCap_NoiCap")) or (
            default_issuer(issue_date) if len(card_number) == 12 else "")
        # Chốt lại theo ngày cấp trước khi suy loại giấy tờ: tờ khai in sẵn tên Cục, thẻ cấp từ 01/7/2024 là thẻ căn cước.
        issuer = issuer_by_issue_date(issuer, issue_date)
        # "Bản thân" mà không có ngày cấp: số là của tài khoản, còn loại thẻ / nơi cấp chỉ là suy đoán → không trả.
        known_card = not self_filing or bool(issue_date)
        if known_card:
            add("citizenNDK_LoaiGiayToTuyThan",
                _id_doc_type_with_number(card_number, values.get("NguoiDuocCap_LoaiGiayTo"), issuer))
        add("citizenNDK_SoGiayToTuyThan", card_number)
        if known_card:
            # Ô chữ tự do: tên Cục ghi dạng viết tắt như trên thẻ và trên mẫu tờ khai.
            add("citizenNDK_NoiCap", short_issuer(issuer))
        add("citizenNDK_NgayCap", issue_date)

    add("citizenField13", values.get("NguoiDuocCap_GioiTinh"))
    # Danh mục dân tộc của cổng không có "Khác": nhóm địa phương Cill/K'Ho/Lạch quy về Cơ Ho.
    add("citizenField32", normalize_ethnic(co_ho_local_group(values.get("NguoiDuocCap_DanToc"))) or None)
    raw_area = values.get("NguoiDuocCap_NoiCuTru")
    from_home = False
    if event == "death" and _copied_from_death_place(raw_area, ocr_text):
        # Nơi chết không phải nơi cư trú — trừ khi chết TẠI NHÀ: địa chỉ nhà đó là nơi người chết ở → điền, tô vàng
        # cho cán bộ soát. Nơi chết khác: bỏ tỉnh/xã/địa chỉ nhưng vẫn chọn Trong nước để bốn ô hiện ra cho cán bộ nhập.
        from_home = _died_at_home(ocr_text)
        area = _area(raw_area, ocr_text) if from_home else {"quocGia": raw_area.get("quocGia") or "Việt Nam"}
    else:
        area = _area(raw_area, ocr_text)
    if event == "death" and not area:
        # Giấy khai tử không ghi nơi cư trú: vẫn mở bốn ô cho cán bộ nhập (không để cán bộ tự đi bấm "Trong nước").
        area = {"quocGia": "Việt Nam"}
    if area:
        add("citizenNDK_LoaiCuTru", "Thường trú", default=True)
        # Radio "Trong nước" phải chọn trước: bốn ô địa chỉ chỉ hiện sau khi chọn.
        add("citizenNDK_Noicutru", "1")
        add("citizenField21", area.get("quocGia") or "Việt Nam")
        add("citizenNDK_TinhThanh", area.get("tinh"), default=from_home)
        add("citizenNDK_PhuongXa", area.get("xa"), default=from_home)
        add("citizenField38", area.get("diaChi"), default=from_home or bool(area.get("_xaChuaChon")))
        # Khối nơi cư trú không còn trên biểu mẫu thì cảnh báo về các ô đó chỉ làm cán bộ đi tìm ô không có.
        address_on_form = "citizenNDK_TinhThanh" not in UI_REMOVED_BY_PORTAL
        if from_home and address_on_form:
            warnings.append("Giấy khai tử không ghi nơi cư trú; đã lấy địa chỉ nơi chết (chết tại nhà) làm nơi cư trú — "
                            "cán bộ kiểm tra lại.")
        elif event == "death" and not area.get("tinh") and address_on_form:
            warnings.append("Giấy khai tử không ghi nơi cư trú của người chết — cán bộ nhập tay nơi cư trú.")
        if address_on_form and (area.get("_xaChuaChon") or (not area.get("tinh") and event != "death")):
            warnings.append("Chưa chọn được tỉnh/phường, xã nơi cư trú của người được cấp theo danh mục hiện hành — "
                            "cán bộ chọn lại ô Tỉnh/Thành phố và Phường/Xã.")
    # Không đọc ra nơi cư trú vẫn điền "Thường trú" (viền vàng) — trường hợp gần như mọi hồ sơ; để trống thì ô bắt buộc
    # này đỏ mà vòng hỏi bằng giọng nói tiếng Mông chưa hỏi được.
    add("citizenNDK_LoaiCuTru", "Thường trú", default=True)
    if self_filing:
        for field in out[block_start:]:
            field["onlyIfEmpty"] = True

    add("citizenLoaiViecYeuCau", _EVENT_TO_OPTION.get(event))
    registrar = values.get("GiayTo_CoQuanDangKy")
    if registrar and event == "death":
        registrar = _death_registrar(ocr_text) or registrar
    registrar = _full_registrar(event, registrar, ocr_text)
    add("citizenHoSo_CoQuanDangKy", registrar)
    add("citizenHotenCha", upper_person_name(values.get("GiayTo_HoTenCha")))
    add("citizenHotenMe", upper_person_name(values.get("GiayTo_HoTenMe")))
    add("citizenTenGiayToHoTich", values.get("GiayTo_TenGiayTo") or _EVENT_TO_DOCUMENT_NAME.get(event))
    # Ô "Số:" góc trên giấy hộ tịch viết tay OCR hay không ra chữ số, LLM vớ sang dòng "Số:" của khối CMND
    # ngay trong thân giấy → số đăng ký trùng số thẻ là đọc nhầm, bỏ trống để cán bộ nhập.
    registration_no, book_no = _split_book_no(values.get("GiayTo_So"))
    registration_no = _registration_number(event, registration_no, ocr_text)
    if _digits(registration_no) in _id_card_numbers(values, options):
        warnings.append("Số đăng ký đọc ra trùng số CMND/CCCD trong hồ sơ — đã bỏ trống, cán bộ nhập ô Số đăng ký "
                        "theo dòng \"Số:\" ở đầu giấy hộ tịch.")
        registration_no = ""
    add("citizencauhoi3", registration_no)
    add("citizencauhoi4", values.get("GiayTo_QuyenSo") or book_no)
    add("citizencauhoi5", values.get("GiayTo_NgayDangKy"))
    quantity = _digits(values.get("SoLuongBanSao"))
    add("citizenSoLuongBanSao", str(int(quantity)) if quantity and int(quantity) > 0 else "")
    if che_do_demo.BAT:
        add("citizenSoLuongBanSao", "1", default=True)  # giấy không ghi số bản → mặc định 1 (chế độ demo)
    return [field for field in out if field["name"] not in UI_REMOVED_BY_PORTAL], warnings
