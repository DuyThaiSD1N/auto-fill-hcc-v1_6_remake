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
from app.pipelines._shared.formatting import prefer_printed_street, upper_person_name

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


_CCCD_LEN = 12          # số định danh cá nhân luôn đúng 12 chữ số
_ID_OCR_SLIP_MAX = 2    # số chữ số OCR được phép đọc thừa/thiếu so với thẻ


def _is_subsequence(short: str, long: str) -> bool:
    """`short` có phải `long` sau khi XÓA bớt vài ký tự (giữ nguyên thứ tự) không."""
    it = iter(long)
    return all(ch in it for ch in short)


def _is_ocr_slip_of_card(left_digits: str, right_digits: str) -> bool:
    """Hai chuỗi số là CÙNG một số trên thẻ, chỉ khác vì OCR đọc RƠI (hoặc nhân đôi) vài chữ số.

    Giấy viết tay hay bị OCR nuốt mất một chữ số: "046175013623" ra "04617503623". Chuỗi thiếu số
    đó không phải số định danh hợp lệ của BẤT KỲ ai (không đủ 12 chữ số), nên coi nó là số của một
    người khác là vô nghĩa — nhưng so bằng `==` thì nó vẫn "khác số", và cả khối nhân thân đi theo:
    tên viết tay sai được giữ lại, ô quan hệ tick "Khác", và ô số định danh nhận một chuỗi thiếu số
    mà cổng chắc chắn từ chối.

    Chỉ nhận khi một bên là số thẻ ĐỦ 12 chữ số và chuỗi ngắn hơn nằm gọn trong nó theo đúng thứ tự
    (chỉ XÓA, không đổi chữ số nào) — lệch tối đa 2 chữ số. Ràng buộc này rất chặt: một số 11 chữ số
    ngẫu nhiên chỉ có cỡ 12 phần 10^11 cơ hội lọt qua, nên không thể vô tình ghép nhân thân của hai
    người khác nhau. OCR đọc NHẦM chữ số (5 thành 6) vẫn bị coi là khác người như cũ.
    """
    short, long = sorted((left_digits, right_digits), key=len)
    if len(long) != _CCCD_LEN or len(short) == _CCCD_LEN:
        return False
    if not 0 < len(long) - len(short) <= _ID_OCR_SLIP_MAX:
        return False
    return _is_subsequence(short, long)


def id_match(left, right) -> bool | None:
    """Hai số định danh có cùng một người không; thiếu một bên → None (không kết luận)."""
    left_digits, right_digits = _digits(left), _digits(right)
    if not (left_digits and right_digits):
        return None
    if left_digits == right_digits:
        return True
    return True if _is_ocr_slip_of_card(left_digits, right_digits) else False


def card_name_when_id_matches(card_name, card_id, khai_id):
    """Họ tên lấy theo THẺ CĂN CƯỚC khi số định danh trên giấy viết tay KHỚP số trên thẻ.

    OCR chữ viết tay rất hay sai tên: rơi dấu hoặc đọc nhầm chữ ("Thiết" → "Thiệt", "Tú" → "Tí").
    Thẻ là bản IN, đọc gần như chắc chắn đúng — và đây mới là tên phải khớp với CSDLQG về dân cư.

    Khớp số định danh là bằng chứng CHẮC CHẮN cùng một người (12 chữ số, không phải phép so tên dễ
    đụng hàng), nên lúc đó tên in trên thẻ luôn đáng tin hơn. Thiếu số ở một bên hoặc số của hai
    người khác nhau thì trả None để caller giữ nguyên thứ tự nguồn cũ — KHÔNG đoán, vì mượn tên của
    người khác sang là ghép ra một nhân thân lai.
    """
    if id_match(khai_id, card_id) is not True:
        return None
    return card_name or None


def card_id_when_id_matches(card_id, khai_id):
    """Số định danh điền vào form: số 12 chữ số IN trên thẻ thắng số đọc từ giấy viết tay.

    Cùng lý do như `card_name_when_id_matches`, và ở đây còn bắt buộc: số đọc từ giấy chỉ khác số
    trên thẻ khi OCR rơi mất chữ số (xem `_is_ocr_slip_of_card`), tức là một chuỗi KHÔNG đủ 12 chữ
    số — điền vào cổng là chắc chắn bị chặn. Không khớp thẻ thì giữ nguyên số đọc từ giấy.
    """
    if id_match(khai_id, card_id) is not True:
        return khai_id
    return card_id or khai_id


# Số nhân thân LUÔN là một DÃY SỐ của con người: số định danh 12 chữ số (giấy cũ có thể ghi CMND
# 9 chữ số), hộ chiếu thì chữ + 7 chữ số. Số của CHÍNH tờ giấy hộ tịch ("Số: 51/2020" in ở đầu giấy
# khai sinh) không phải số nhân thân, nhưng LLM rất hay chép nó vào ô số định danh khi dòng "Số định
# danh cá nhân" trên giấy bỏ trống — ô vẫn tô xanh nên cán bộ khó soát ra. Dấu "/" và độ dài là hai
# bằng chứng tất định để loại: không có số thì để TRỐNG, không đoán.
_PERSONAL_ID_MIN_DIGITS = {
    "Nyc_SoDinhDanh": 9,
    "ChuThe_SoDinhDanh": 9,
    "HoTich_SoDinhDanh": 9,
    "ToKhai_SoDinhDanh": 9,
    "HoTich_SoGiayToTuyThan": 7,   # hộ chiếu: 1 chữ cái + 7 chữ số
    "ToKhai_SoGiayToTuyThan": 7,
    "TkNyc_SoGiayToTuyThan": 7,
}
_DOCUMENT_NUMBER_FIELDS = ("HoTich_So", "HoTich_QuyenSo", "ToKhai_So", "ToKhai_QuyenSo")


def _looks_like_person_number(value, min_digits: int) -> bool:
    raw = str(value or "").strip()
    if not raw or "/" in raw:
        return False
    return len(_digits(raw)) >= min_digits


def _drop_document_numbers_from_id_fields(values: dict) -> dict:
    """Bỏ ô số nhân thân đang giữ số của tờ giấy (số đăng ký/quyển số) hoặc một chuỗi không phải số."""
    document_numbers = {_fold(values.get(name)) for name in _DOCUMENT_NUMBER_FIELDS}
    document_numbers.discard("")
    cleaned = dict(values)
    for name, min_digits in _PERSONAL_ID_MIN_DIGITS.items():
        value = cleaned.get(name)
        if value in (None, "", {}, []):
            continue
        if not _looks_like_person_number(value, min_digits) or _fold(value) in document_numbers:
            cleaned.pop(name)
    return cleaned


def _copy_quantity(value) -> str:
    digits = _digits(value)
    return str(int(digits)) if digits and int(digits) > 0 else ""


def _id_doc_type_with_number(number: str, hint, issuer: str = "") -> str:
    """Loại giấy tờ tùy thân kết hợp độ dài số với hint/issuer.

    Số 9 chữ số là CMND (cũ), bất kể hint nói gì — CCCD/Căn cước luôn có 12 chữ số.
    Số 12 chữ số → nhường cho id_doc_type() phán theo nơi cấp.
    """
    d = _digits(number)
    if len(d) == 9:
        return "Chứng minh nhân dân"
    return id_doc_type(hint or "Căn cước", issuer)


def _id_doc_rank(number) -> int:
    """Thứ hạng giấy tờ tùy thân theo số: CCCD/Căn cước (12 số) > CMND (9 số) > không đọc được."""
    length = len(_digits(number))
    if length == 12:
        return 2
    if length == 9:
        return 1
    return 0


def _id_document_source(card_number, declaration_number) -> str:
    """Cụm giấy tờ tùy thân của mục I lấy từ THẺ trong hồ sơ hay từ ĐƠN — trả "card"/"declaration".

    MỘT NGƯỜI CÓ CẢ CCCD LẪN CMND thì CCCD thắng: số 12 chữ số là giấy tờ đang có hiệu lực và là
    số phải khớp Cơ sở dữ liệu quốc gia về dân cư, còn CMND 9 số chỉ là giấy tờ cũ người dân ghi
    theo thói quen. Hai nguồn CÙNG HẠNG (hoặc chỉ thẻ đọc được số) thì thẻ thắng: số/ngày/nơi cấp
    trên thẻ là bản IN, còn trên đơn là chữ viết tay nên OCR hay sai.

    Caller lấy CẢ CỤM (số, ngày cấp, nơi cấp, loại) từ nguồn thắng — trộn số của CCCD với ngày cấp
    của CMND là dựng ra một giấy tờ không tồn tại.
    """
    if _id_doc_rank(declaration_number) > _id_doc_rank(card_number):
        return "declaration"
    return "card"


def _prefer_cccd_between_cards(values: dict) -> dict:
    """Hồ sơ có cả CCCD lẫn CMND CỦA CÙNG MỘT NGƯỜI thì chỉ giữ CCCD, ở vai người yêu cầu.

    Người dân hay nộp kèm cả thẻ căn cước mới lẫn chứng minh nhân dân cũ. Hai thẻ khác số nên agent
    tưởng là hai người rồi đẩy thẻ thừa sang vai NGƯỜI ĐƯỢC ĐĂNG KÝ (ChuThe_*) theo đúng luật "hai
    thẻ thì thẻ còn lại là chủ thể" — mục II bị điền bằng chính giấy tờ cũ của người yêu cầu.

    Cùng HỌ TÊN mà một thẻ 12 số, một thẻ 9 số thì chắc chắn là một người (không phải phép so tên
    dễ đụng hàng: CMND 9 số chỉ tồn tại như bản cũ của chính chủ thẻ căn cước). Giữ CCCD ở Nyc_*,
    bỏ hẳn CMND để không vai nào bị điền bằng giấy tờ đã hết hiệu lực.
    """
    requester_name = _fold(values.get("Nyc_HoTen"))
    subject_name = _fold(values.get("ChuThe_HoTen"))
    if not (requester_name and subject_name and requester_name == subject_name):
        return values

    requester_rank = _id_doc_rank(values.get("Nyc_SoDinhDanh"))
    subject_rank = _id_doc_rank(values.get("ChuThe_SoDinhDanh"))
    if {requester_rank, subject_rank} != {1, 2}:
        return values

    cleaned = {key: value for key, value in values.items() if not key.startswith("ChuThe_")}
    if subject_rank == 2:
        # CCCD đang nằm ở vai chủ thể, CMND ở vai người yêu cầu → đổi cụm thẻ lấy CCCD.
        for suffix in _CARD_FIELD_SUFFIXES:
            value = values.get(f"ChuThe_{suffix}")
            if value not in (None, "", {}, []):
                cleaned[f"Nyc_{suffix}"] = value
    return cleaned


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
    """Người yêu cầu là ai: TỜ KHAI trước, rồi CCCD trong hồ sơ, cuối cùng mới tới mỏ neo VNeID.

    Thẻ Nyc_* CHỈ được tính khi _card_is_requester() gật — đúng cái guard mà enrich() dùng để quyết
    có ghi đè mục I hay không, nên ô tích và khối mục I luôn nói cùng một chuyện.

    Vì sao phải chặn: hồ sơ chỉ có thẻ của NGƯỜI ĐƯỢC ĐĂNG KÝ thì agent hay gán CÙNG một thẻ vào cả
    Nyc_* lẫn ChuThe_*. Tin thẳng Nyc_* thì hai bên "trùng số" một cách giả tạo → tick "Bản thân",
    trong khi mục I vẫn đang là người đăng nhập KHÁC (mapper không ghi đè vì chính guard này chặn).
    Bỏ thẻ đi thì mỏ neo VNeID lên tiếng, và người đăng nhập mới đúng là người yêu cầu.
    """
    ctx = (options or {}).get("formContext") or {}
    card = values if _card_is_requester(values, options) else {}
    number = (
        _digits(values.get("TkNyc_SoGiayToTuyThan"))
        or _digits(card.get("Nyc_SoDinhDanh"))
        or _digits(ctx.get("applicantIdentityNumber"))
    )
    name = (
        _fold(values.get("TkNyc_HoTen"))
        or _fold(card.get("Nyc_HoTen"))
        or _fold(ctx.get("applicantFullname"))
    )
    return name, number


def _subject_identity(values: dict) -> tuple[str, str]:
    """Người được cấp bản sao là ai. HoTich_* đã được _apply_declaration_precedence phủ tờ khai.

    Thẻ ChuThe_* CHỈ được tính khi _chu_the_matches_hotich() gật — đúng cái guard mà enrich() dùng
    để quyết có đắp thẻ vào mục II hay không, nhờ vậy ô tích và khối mục II luôn nói cùng một chuyện.

    Vì sao phải chặn: chủ thể không có thẻ riêng (trích lục khai tử của người đã mất, trên giấy chỉ
    còn CMND cũ) thì agent hay gán CÙNG thẻ của NGƯỜI YÊU CẦU vào cả Nyc_* lẫn ChuThe_*. Tin thẳng
    ChuThe_* thì hai mục "trùng số" một cách giả tạo → tick "Bản thân" cho hồ sơ xin hộ người khác.
    """
    card = values if _chu_the_matches_hotich(values) else {}
    number = _digits(values.get("HoTich_SoDinhDanh")) or _digits(card.get("ChuThe_SoDinhDanh"))
    name = (
        _fold(values.get("HoTich_HoTenNguoiDuocDangKy"))
        or _fold(values.get("NguoiDuocCap_HoTen"))
        or _fold(card.get("ChuThe_HoTen"))
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
        if id_match(req_id, row_id) is True:
            return option, True
        if req_name and not by_name and _fold(row.get("hoTen")) == req_name:
            by_name = option
    return by_name, False


_HOTICH_FACT_NAMES = (
    "HoTich_LoaiSuKien", "HoTich_TenGiayTo", "HoTich_HoTenNguoiDuocDangKy",
    "HoTich_CoQuanDangKy", "HoTich_So", "HoTich_NgayDangKy",
)


def _has_hotich_facts(values: dict) -> bool:
    """Hồ sơ có đọc được GIẤY HỘ TỊCH (hoặc tờ khai đã phủ sang HoTich_*) không."""
    return any(name in values for name in _HOTICH_FACT_NAMES)


def _has_subject_card(values: dict) -> bool:
    """Có CCCD RIÊNG của người được đăng ký (ChuThe_*) không."""
    return bool(values.get("ChuThe_SoDinhDanh") or values.get("ChuThe_HoTen"))


def _has_requester_card(values: dict) -> bool:
    """Có CCCD của người yêu cầu (Nyc_*) không."""
    return bool(values.get("Nyc_SoDinhDanh") or values.get("Nyc_HoTen"))


def _subject_is_requester_card(values: dict, options: dict | None) -> bool:
    """Mục II SẼ ĐƯỢC ĐẮP TỪ CHÍNH THẺ của người yêu cầu → mục I và mục II là MỘT người.

    Soi đúng điều kiện nhánh "tự xin cho chính mình" ở cuối enrich(): không giấy hộ tịch, không thẻ
    riêng của chủ thể, chỉ MỘT thẻ và thẻ đó khớp tài khoản VNeID đang đăng nhập. Ca này người dân
    KHÔNG nộp tờ khai lẫn giấy hộ tịch nên chẳng có số/tên nào ở mục II để đối chiếu — thiếu nhánh
    này thì mọi hồ sơ "tự đi xin bản sao của mình" đều bị tick "Khác" dù mục II vừa được điền bằng
    đúng thẻ của họ.
    """
    if _has_hotich_facts(values) or _has_subject_card(values):
        return False
    # Hồ sơ CÓ nêu tên/số người ở mục II (vd giấy tờ bổ trợ) → nhường bước đối chiếu bên dưới,
    # không vơ thành "Bản thân".
    subj_name, subj_id = _subject_identity(values)
    if subj_name or subj_id:
        return False
    if not _has_requester_card(values):
        return False
    return _card_matches_login(values, options)


def _same_person_by_id(values: dict, options: dict | None) -> bool | None:
    """Người yêu cầu (mục I) và người được cấp bản sao (mục II) có CÙNG số giấy tờ không.

    Trả True/False khi hai số ĐỦ SỨC phân xử, None khi không kết luận được. CMND 9 số và số định
    danh 12 số của CÙNG một người vẫn là hai chuỗi khác nhau, nên khác độ dài thì không phân xử —
    để bước so họ tên quyết định thay vì kết luận nhầm "khác người".
    """
    _, req_id = _requester_identity(values, options)
    _, subj_id = _subject_identity(values)
    # OCR rơi chữ số vẫn là cùng một người — phải xét trước phép so độ dài bên dưới, nếu không
    # chuỗi thiếu số sẽ bị coi là "khác độ dài" rồi rơi xuống bước so tên viết tay vốn cũng sai.
    if id_match(req_id, subj_id) is True:
        return True
    if req_id and subj_id and len(req_id) == len(subj_id):
        return req_id == subj_id
    return None


def _resolve_quanhe(values: dict, options: dict | None) -> tuple[str, bool]:
    """Chốt ô tích "(5) Quan hệ với người được cấp bản sao". Trả (nhãn option, là suy đoán).

    Thứ tự nguồn:
      1. Dòng "Quan hệ với người được cấp bản sao ..." của chính tờ khai: lời khai chính chủ.
      1b. Hồ sơ chỉ có MỘT thẻ và mục II sẽ được đắp từ chính thẻ đó (tự xin cho mình, có mỏ neo
         VNeID xác nhận) → "Bản thân". Ca này mục II chưa có số/tên nào để bước 2 đối chiếu.
      2. SỐ ĐỊNH DANH/CCCD của mục I trùng mục II → "Bản thân". Số là bằng chứng chắc nhất nên
         phải xét TRƯỚC mọi suy đoán khác: người dân tự đi xin bản sao của chính mình là ca phổ
         biến nhất, không được để nó rơi xuống nhánh "Khác" chỉ vì tờ khai ghi chữ khó đọc hay
         giấy hộ tịch có ghi kèm cha/mẹ. So số cùng độ dài; khác độ dài thì nhường bước 5.
      3. Tờ khai CÓ ghi quan hệ nhưng chữ không khớp option nào → "Khác" (viền vàng).
      4. VAI GHI TRÊN CHÍNH GIẤY HỘ TỊCH (cha/mẹ của giấy khai sinh, vợ/chồng của giấy kết hôn...):
         người yêu cầu trùng một người thân ghi trên giấy → lấy đúng vai đó, nếu không mọi hồ sơ
         "người thân đi xin hộ" đều bị tick "Khác" dù giấy đã ghi rõ vai. Khớp bằng số giấy tờ là
         chắc; khớp bằng họ tên thì tick viền vàng.
      5. HỌ TÊN mục I trùng mục II → "Bản thân" (viền vàng, vì tên có thể trùng). Chỉ chạy khi số
         không phân xử được, và xếp sau bước 4 để cha/con trùng tên vẫn ra đúng vai trên giấy.
      6. Không kết luận được "Bản thân" → tick "Khác" (viền vàng): an toàn nhất, tách khối người
         yêu cầu khỏi khối người được đăng ký để cán bộ soát lại.
    """
    raw_declared = values.get("CopyRequest_QuanHe")
    declared = _quanhe_option(raw_declared)
    # "Bản thân" mà số giấy tờ hai mục khác nhau là tự mâu thuẫn (vd giấy ủy quyền không có dòng quan
    # hệ, agent tự điền) → không tin, để các bước đối chiếu bên dưới quyết định.
    if declared == "Bản thân" and _same_person_by_id(values, options) is False:
        declared = ""
    if declared:
        return declared, False

    if _subject_is_requester_card(values, options):
        return "Bản thân", False

    same_by_id = _same_person_by_id(values, options)
    if same_by_id is True:
        return "Bản thân", False

    if str(raw_declared or "").strip():
        # Tờ khai CÓ ghi quan hệ nhưng chữ đó không khớp option nào (vd chữ viết tắt/nhập nhằng).
        # Không đoán bừa một vai cụ thể, nhưng cũng KHÔNG để trống ô tích: rơi về "Khác" (tô vàng).
        return "Khác", True

    from_record, matched_by_id = _quanhe_from_record(values, options)
    if from_record:
        return from_record, not matched_by_id

    if same_by_id is False:
        return "Khác", True

    req_name, req_id = _requester_identity(values, options)
    subj_name, subj_id = _subject_identity(values)
    if req_name and subj_name:
        return ("Bản thân" if req_name == subj_name else "Khác"), True
    if req_id and subj_id:
        return ("Bản thân" if req_id == subj_id else "Khác"), True

    # Cạn nguồn: không tờ khai, giấy không ghi vai, không đủ nhân thân để đối chiếu. Vẫn phải tick
    # để ô "(5) Quan hệ" không bị bỏ trống — "Khác" là lựa chọn an toàn nhất (tách khối mục I khỏi
    # mục II) và được tô vàng để người dân đổi lại nếu đúng ra là quan hệ khác.
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
        id_match(requester_id, subj_id) is True
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

    Khớp MỘT trong hai (số hoặc tên) là đủ: số trên tờ khai là chữ viết tay, OCR sai vài chữ số là
    chuyện thường. Bắt khớp cả hai thì đúng cái thẻ cần dùng để SỬA số sai lại bị loại, và mục I
    giữ nguyên số hỏng của tờ khai. Chỉ khi cả số lẫn tên đều so được mà đều lệch mới kết luận thẻ
    này là của người khác.
    """
    tk_name = _fold(values.get("TkNyc_HoTen"))
    tk_id = _digits(values.get("TkNyc_SoGiayToTuyThan"))
    card_name = _fold(values.get("Nyc_HoTen"))
    card_id = _digits(values.get("Nyc_SoDinhDanh"))
    if id_match(tk_id, card_id) is True:
        return True
    if tk_name and card_name and tk_name == card_name:
        return True
    # Không có cặp nào so được (tờ khai trống, hoặc thẻ thiếu đúng ô để đối chiếu) → mỏ neo cũ.
    if not ((tk_id and card_id) or (tk_name and card_name)):
        return _requester_trusted(values, options)
    return False


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
    remapped = remap_area(dict(out))
    # CCCD in địa chỉ không nhãn "Phúc Thắng / Danh Thắng, Hiệp Hòa, Bắc Giang" hay bị agent đảo thôn
    # với xã. Xã trả về không khớp danh mục mà phần chi tiết là một TÊN trần (không số, không phẩy)
    # khớp được xã → đảo lại. Không khớp thì giữ nguyên kết quả cũ.
    dia_chi = str(out["diaChi"] or "").strip()
    if (
        out["xa"] and isinstance(remapped, dict) and not remapped.get("xa")
        and dia_chi and not re.search(r"[\d,;/]", dia_chi)
    ):
        swapped = remap_area({**out, "xa": dia_chi, "diaChi": out["xa"]})
        if isinstance(swapped, dict) and swapped.get("xa"):
            return swapped
    return remapped


def _chu_the_matches_hotich(values: dict) -> bool:
    """ChuThe_* có khớp chủ thể trên giấy/tờ khai hộ tịch hay không."""
    subject_card_id = _digits(values.get("ChuThe_SoDinhDanh"))
    subject_card_name = _fold(values.get("ChuThe_HoTen"))
    subj_id = _digits(values.get("HoTich_SoDinhDanh"))
    subj_name = _fold(values.get("HoTich_HoTenNguoiDuocDangKy"))
    requester_id = _digits(values.get("Nyc_SoDinhDanh"))

    if id_match(subject_card_id, requester_id) is True:
        return False
    if subject_card_id and subj_id:
        return id_match(subject_card_id, subj_id) is True
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


# Các ô nhân thân của MỘT thẻ căn cước, dùng để đổi vai cả cụm giữa Nyc_* và ChuThe_*.
_CARD_FIELD_SUFFIXES = (
    "HoTen", "SoDinhDanh", "NgaySinh", "GioiTinh", "QuocTich",
    "LoaiGiayTo", "NgayCap", "NoiCap", "NoiCuTru",
)


def _rescue_requester_card(values: dict) -> dict:
    """Thẻ bị agent gán nhầm vào ChuThe_* trong khi nó là thẻ của NGƯỜI YÊU CẦU → trả lại Nyc_*.

    Ca điển hình: TRÍCH LỤC KHAI TỬ của người đã mất + CCCD của người thân đi xin bản sao, tài khoản
    VNeID đăng nhập lại là người thứ ba (nộp hộ). Agent không thấy thẻ nào khớp CONTEXT nên rơi vào
    luật "chỉ có 1 CCCD, không có mỏ neo → giữ ChuThe_*". Hậu quả: mục I không có gì để ghi đè, cổng
    giữ nguyên người đăng nhập, còn thẻ duy nhất trong hồ sơ thì bị vứt — sai người yêu cầu.

    Chỉ đổi vai khi CHẮC CHẮN: giấy hộ tịch đã nêu rõ chủ thể, thẻ lệch hẳn chủ thể đó (so được ít
    nhất một cặp số hoặc tên và đều không khớp), và hồ sơ chưa có thẻ người yêu cầu nào để tranh chấp.
    """
    if _has_requester_card(values) or not _has_subject_card(values):
        return values

    subject_ids = {value for value in (
        _digits(values.get("HoTich_SoDinhDanh")),
        _digits(values.get("HoTich_SoGiayToTuyThan")),
    ) if value}
    subject_name = _fold(values.get("HoTich_HoTenNguoiDuocDangKy"))
    card_id = _digits(values.get("ChuThe_SoDinhDanh"))
    card_name = _fold(values.get("ChuThe_HoTen"))

    if card_id and any(id_match(card_id, subject_id) is True for subject_id in subject_ids):
        return values  # đúng là thẻ của chủ thể
    if subject_name and card_name and subject_name == card_name:
        return values
    # Không so được cặp nào (giấy hộ tịch không nêu tên/số, hoặc thẻ thiếu đúng ô để đối chiếu)
    # → không đủ căn cứ đổi vai, giữ nguyên phân vai của agent.
    if not ((subject_ids and card_id) or (subject_name and card_name)):
        return values

    moved = {key: value for key, value in values.items() if not key.startswith("ChuThe_")}
    for suffix in _CARD_FIELD_SUFFIXES:
        value = values.get(f"ChuThe_{suffix}")
        if value not in (None, "", {}, []):
            moved[f"Nyc_{suffix}"] = value
    return moved


def _rescue_subject_card(values: dict) -> dict:
    """Thẻ bị agent gán vào Nyc_* nhưng giấy (tờ khai/giấy ủy quyền) đã ghi người yêu cầu là NGƯỜI KHÁC
    → đó là thẻ của người được cấp bản sao, chuyển sang ChuThe_*.

    Ca điển hình: giấy ủy quyền + CCCD của BÊN ỦY QUYỀN. Người yêu cầu (bên được ủy quyền) đã có ở
    TkNyc_*, còn thẻ duy nhất lại nằm ở Nyc_*. Mapper loại thẻ vì lệch người yêu cầu → mục II trống,
    cổng giữ nguyên dữ liệu tài khoản VNeID đang đăng nhập.

    Chỉ đổi khi CHẮC: chưa có thẻ chủ thể, và so được ít nhất một cặp số/tên mà mọi cặp đều lệch.
    """
    if _has_subject_card(values) or not _has_requester_card(values):
        return values
    tk_name = _fold(values.get("TkNyc_HoTen"))
    tk_id = _digits(values.get("TkNyc_SoGiayToTuyThan"))
    card_name = _fold(values.get("Nyc_HoTen"))
    card_id = _digits(values.get("Nyc_SoDinhDanh"))
    comparable = bool((tk_id and card_id) or (tk_name and card_name))
    if not comparable:
        return values
    if id_match(tk_id, card_id) is True or (tk_name and card_name and tk_name == card_name):
        return values

    moved = {key: value for key, value in values.items() if not key.startswith("Nyc_")}
    for suffix in _CARD_FIELD_SUFFIXES:
        value = values.get(f"Nyc_{suffix}")
        if value not in (None, "", {}, []):
            moved[f"ChuThe_{suffix}"] = value
    return moved


def _drop_duplicated_requester_card(values: dict, options: dict | None) -> dict:
    """Agent chép CÙNG MỘT thẻ vào cả Nyc_* lẫn ChuThe_* → chỉ giữ ở vai người yêu cầu khi thẻ đó
    đúng là của người đang đăng nhập; còn lại bỏ Nyc_* để thẻ chỉ điền mục II.

    Lỗi thật (req_55aa47ae0dba): tài khoản đăng nhập là người khác, hồ sơ chỉ có CCCD của người được
    đăng ký, agent trả thẻ đó ở cả hai nhóm. Không có giấy hộ tịch để đối chiếu nên _requester_trusted
    tin Nyc_* → thẻ GHI ĐÈ lên người yêu cầu cổng đã điền sẵn. Agent lúc trả một nhóm, lúc trả cả hai,
    nên kết quả chập chờn giữa các lần chạy.

    Cùng thẻ = trùng số (kể cả OCR rơi chữ số), hoặc trùng họ tên khi một bên không đọc được số.
    Thẻ khớp người đăng nhập (tự xin cho mình) thì giữ nguyên cả hai nhóm như cũ.
    """
    if not (_has_requester_card(values) and _has_subject_card(values)):
        return values
    req_id, subj_id = _digits(values.get("Nyc_SoDinhDanh")), _digits(values.get("ChuThe_SoDinhDanh"))
    req_name, subj_name = _fold(values.get("Nyc_HoTen")), _fold(values.get("ChuThe_HoTen"))
    same_by_id = id_match(req_id, subj_id)
    same_card = same_by_id is True or (
        same_by_id is None and bool(req_name and subj_name and req_name == subj_name)
    )
    if not same_card or _card_matches_login(values, options):
        return values
    return {key: value for key, value in values.items() if not key.startswith("Nyc_")}


def _rescue_single_card_not_login(values: dict, options: dict | None) -> dict:
    """Hồ sơ chỉ có MỘT thẻ, agent xếp vào Nyc_* nhưng thẻ LỆCH người đang đăng nhập → thẻ của người
    được đăng ký, chuyển sang ChuThe_* để điền mục "Thông tin về giấy tờ hộ tịch đã đăng ký".

    Ca điển hình: người dân đăng nhập VNeID rồi chỉ upload CCCD của người cần cấp bản sao (con, bố/mẹ
    già...). Mục I cổng đã tự điền đúng người đăng nhập; tin Nyc_* thì thẻ đó GHI ĐÈ lên người yêu cầu,
    còn mục II bỏ trống.

    Không đổi vai khi:
      - tờ khai đã ghi người yêu cầu (TkNyc_*) → _rescue_subject_card lo;
      - không có mỏ neo đăng nhập hoặc không so được cặp số/tên nào với nó;
      - giấy hộ tịch nêu rõ chủ thể mà thẻ lệch hẳn chủ thể đó → thẻ đúng là người yêu cầu nộp hộ
        (vd trích lục khai tử + CCCD người thân), giữ nguyên như _rescue_requester_card.
    """
    if _has_subject_card(values) or not _has_requester_card(values):
        return values
    if any(str(key).startswith("TkNyc_") and values.get(key) not in (None, "", {}, []) for key in values):
        return values

    ctx = (options or {}).get("formContext") or {}
    login_id = _digits(ctx.get("applicantIdentityNumber"))
    login_name = _fold(ctx.get("applicantFullname"))
    card_id = _digits(values.get("Nyc_SoDinhDanh"))
    card_name = _fold(values.get("Nyc_HoTen"))
    if not ((login_id and card_id) or (login_name and card_name)):
        return values
    if id_match(login_id, card_id) is True or (login_name and card_name and login_name == card_name):
        return values

    subject_ids = {value for value in (
        _digits(values.get("HoTich_SoDinhDanh")),
        _digits(values.get("HoTich_SoGiayToTuyThan")),
    ) if value}
    subject_name = _fold(values.get("HoTich_HoTenNguoiDuocDangKy"))
    card_is_subject = (
        (card_id and any(id_match(card_id, subject_id) is True for subject_id in subject_ids))
        or bool(subject_name and card_name and subject_name == card_name)
    )
    subject_comparable = bool((subject_ids and card_id) or (subject_name and card_name))
    if subject_comparable and not card_is_subject:
        return values

    moved = {key: value for key, value in values.items() if not key.startswith("Nyc_")}
    for suffix in _CARD_FIELD_SUFFIXES:
        value = values.get(f"Nyc_{suffix}")
        if value not in (None, "", {}, []):
            moved[f"ChuThe_{suffix}"] = value
    return moved


# Nhân thân của người được đăng ký, đổ từ THẺ/khối người yêu cầu khi đổi vai vợ ↔ chồng.
_SUBJECT_FROM_REQUESTER = {
    "HoTich_HoTenNguoiDuocDangKy": "Nyc_HoTen",
    "HoTich_NgaySinh": "Nyc_NgaySinh",
    "HoTich_GioiTinh": "Nyc_GioiTinh",
    "HoTich_SoDinhDanh": "Nyc_SoDinhDanh",
    "HoTich_SoGiayToTuyThan": "Nyc_SoDinhDanh",
    "HoTich_NgayCapGiayToTuyThan": "Nyc_NgayCap",
    "HoTich_NoiCapGiayToTuyThan": "Nyc_NoiCap",
    "HoTich_NoiCuTru": "Nyc_NoiCuTru",
}
_SPOUSE_ROLES = {"vo": "Chồng", "chong": "Vợ"}


def _prefer_requester_as_marriage_subject(values: dict, options: dict | None) -> dict:
    """Giấy kết hôn có HAI chủ thể; người đăng nhập VNeID là một trong hai thì CHÍNH HỌ là mục II.

    Mặc định agent lấy bên nam làm người được đăng ký. Nhưng khi tài khoản VNeID (hoặc thẻ người yêu
    cầu trong hồ sơ) chính là người vợ ghi trên giấy, người đó vừa là NGƯỜI YÊU CẦU vừa là NGƯỜI ĐƯỢC
    ĐĂNG KÝ — trích lục là của cuộc hôn nhân của chính họ. Để nguyên bên nam thì mục II ra người khác
    và ô "(5) Quan hệ" bị tick "Vợ"/"Chồng" thay vì "Bản thân".

    Chỉ đảo khi CHẮC: đúng sự kiện kết hôn, giấy ghi rõ vai vợ/chồng của người yêu cầu, và hồ sơ
    KHÔNG có tờ khai nêu người được cấp (tờ khai là lời khai chính chủ, nó chỉ định ai thì theo).
    Field nào không có nguồn cho người mới (vd dân tộc) thì XÓA, không giữ lại của người cũ.
    """
    event = str(values.get("HoTich_LoaiSuKien") or "").strip().lower()
    if not event:
        event = _event_from_title(values.get("HoTich_TenGiayTo"))
    if event != "marriage":
        return values

    # Tờ khai đã nêu người yêu cầu → chính chủ tự khai xin bản sao cho ai, không đoán thay.
    if any(str(key).startswith("TkNyc_") and values.get(key) not in (None, "", {}, []) for key in values):
        return values

    rows = values.get("HoTich_NguoiThan")
    if not isinstance(rows, list):
        return values

    ctx = (options or {}).get("formContext") or {}
    req_ids = {value for value in (
        _digits(values.get("Nyc_SoDinhDanh")),
        _digits(ctx.get("applicantIdentityNumber")),
    ) if value}
    req_names = {value for value in (
        _fold(values.get("Nyc_HoTen")),
        _fold(ctx.get("applicantFullname")),
    ) if value}
    if not req_ids and not req_names:
        return values

    matched = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        role = _fold(row.get("quanHe")).strip(".:;,- ")
        role = re.sub(r"^nguoi\s+", "", role)
        if role not in _SPOUSE_ROLES:
            continue
        row_id = _digits(row.get("soGiayTo"))
        if (row_id and row_id in req_ids) or (_fold(row.get("hoTen")) in req_names and req_names):
            matched = (row, role)
            break
    if not matched:
        return values

    row, role = matched
    subject_id = _digits(values.get("HoTich_SoDinhDanh"))
    if subject_id and subject_id in req_ids:
        return values  # agent đã lấy đúng người rồi

    swapped = dict(values)
    # Bên còn lại (người đang bị agent đặt nhầm vào mục II) lùi về danh sách người thân, giữ đúng vai.
    old_subject = str(values.get("HoTich_HoTenNguoiDuocDangKy") or "").strip()
    if old_subject:
        swapped["HoTich_NguoiThan"] = [{
            "quanHe": _SPOUSE_ROLES[role],
            "hoTen": old_subject,
            "soGiayTo": values.get("HoTich_SoGiayToTuyThan") or values.get("HoTich_SoDinhDanh") or "",
        }]
    else:
        swapped["HoTich_NguoiThan"] = []

    for target, source in _SUBJECT_FROM_REQUESTER.items():
        value = values.get(source)
        if value in (None, "", {}, []):
            swapped.pop(target, None)
        else:
            swapped[target] = value
    # Giấy kết hôn ghi "Thẻ căn cước công dân số ..." → suy ra loại giấy tờ; dân tộc thì không có
    # nguồn nào cho người mới nên phải bỏ, tránh đội dân tộc của người kia sang.
    swapped.pop("HoTich_DanToc", None)
    swapped.pop("HoTich_LoaiGiayToTuyThan", None)
    if len(_digits(values.get("Nyc_SoDinhDanh"))) == 12:
        swapped["HoTich_LoaiGiayToTuyThan"] = "Căn cước công dân"
    # Người yêu cầu CHÍNH LÀ người được đăng ký → ô "(5) Quan hệ" phải là "Bản thân".
    swapped["CopyRequest_QuanHe"] = "Bản thân"
    return swapped


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
    facts = _drop_document_numbers_from_id_fields(_by_name(fields))
    values = _prefer_requester_as_marriage_subject(
        _rescue_single_card_not_login(
            _rescue_subject_card(
                _rescue_requester_card(
                    # Bỏ CMND cũ và thẻ chép lặp TRƯỚC các bước cứu vai: các bước đó đọc "có thẻ chủ
                    # thể hay không", mà thẻ thừa lại đang chiếm đúng ô đó.
                    _drop_duplicated_requester_card(
                        _prefer_cccd_between_cards(_apply_declaration_precedence(facts)),
                        options,
                    )
                )
            ),
            options,
        ),
        options,
    )
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

    has_requester = _has_requester_card(values)
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
    has_subject_card = _has_subject_card(values)
    has_hotich = _has_hotich_facts(values)
    has_subject_support = any(
        values.get(name)
        for name in (
            "NguoiDuocCap_HoTen",
            "NguoiDuocCap_NgaySinh",
            "NguoiDuocCap_GioiTinh",
        )
    )

    def _fill_requester() -> None:
        """Khối người yêu cầu: TỜ KHAI trước (trừ số giấy tờ), CCCD bù, VNeID là fallback cuối.

        Cổng điền sẵn khối này theo tài khoản VNeID đang đăng nhập; hồ sơ giấy mới là căn cứ nên
        mapper luôn phát đủ field để extension GHI ĐÈ lên dữ liệu đăng nhập.
        Thứ tự ưu tiên mỗi field: tờ khai → CCCD (nếu đúng người) → VNeID (formContext).
        NGOẠI LỆ ô SỐ GIẤY TỜ TUỲ THÂN: CCCD đi trước và ghi đè tờ khai (số in sẵn trên thẻ chắc
        hơn số viết tay bị OCR sai), tờ khai chỉ bù khi không có thẻ khớp người yêu cầu.
        Kể cả khi field tờ khai/CCCD trống thì vẫn phát field từ VNeID để ghi đè.
        Chỉ dùng CCCD khi thẻ đó đúng là của người yêu cầu (_card_is_requester) — nếu không, thẻ trong
        hồ sơ có thể là của người được đăng ký, ghép vào đây là sai người.
        """
        ctx = (options or {}).get("formContext") or {}
        card = values if _card_is_requester(values, options) else {}
        # Họ tên: THẺ → tờ khai → VNeID. Thẻ chỉ tới được đây sau _card_is_requester (đã khớp số
        # hoặc khớp tên với người yêu cầu trên tờ khai) nên chắc chắn cùng một người, mà tên IN
        # trên thẻ mới là tên phải khớp CSDLQG về dân cư — tên viết tay trên đơn hay bị OCR rơi dấu.
        ho_ten = (
            card.get("Nyc_HoTen")
            or values.get("TkNyc_HoTen")
            or ctx.get("applicantFullname")
        )

        # Cụm GIẤY TỜ TÙY THÂN (loại, số, ngày cấp, nơi cấp) phải đi NGUYÊN KHỐI từ MỘT giấy tờ.
        # Trộn nguồn là dựng ra giấy tờ không tồn tại: số của thẻ căn cước mới đi kèm ngày/nơi cấp
        # của chứng minh nhân dân cũ ghi trên đơn.
        card_number = card.get("Nyc_SoDinhDanh")
        declaration_number = values.get("TkNyc_SoGiayToTuyThan")
        # Gộp hai nguồn khi KHÔNG có bằng chứng chúng là hai giấy tờ khác nhau: số khớp nhau, hoặc
        # cả hai bên đều không đọc được số (tờ khai chỉ còn ngày/nơi cấp). Lúc đó thẻ thắng từng ô,
        # đơn bù ô nào thẻ không đọc được.
        merge_sources = id_match(card_number, declaration_number) is True or not (
            _id_doc_rank(card_number) or _id_doc_rank(declaration_number)
        )
        if merge_sources or _id_document_source(card_number, declaration_number) == "card":
            so_giay_to = card_number or (declaration_number if merge_sources else None)
            ngay_cap = card.get("Nyc_NgayCap")
            noi_cap = card.get("Nyc_NoiCap")
            loai_hint = card.get("Nyc_LoaiGiayTo")
            if merge_sources:
                ngay_cap = ngay_cap or values.get("TkNyc_NgayCapGiayToTuyThan")
                noi_cap = noi_cap or values.get("TkNyc_NoiCapGiayToTuyThan")
                loai_hint = loai_hint or values.get("TkNyc_LoaiGiayToTuyThan")
        else:
            # Đơn ghi CCCD trong khi thẻ trong hồ sơ chỉ là CMND cũ → cả cụm lấy theo đơn.
            so_giay_to = declaration_number
            ngay_cap = values.get("TkNyc_NgayCapGiayToTuyThan")
            noi_cap = values.get("TkNyc_NoiCapGiayToTuyThan")
            loai_hint = values.get("TkNyc_LoaiGiayToTuyThan")
        so_giay_to = so_giay_to or ctx.get("applicantIdentityNumber")
        requester_issuer = normalize_issuer(noi_cap) or default_issuer(ngay_cap)
        add("HoVaTenC", upper_person_name(ho_ten))
        add("SoDinhDanhC", so_giay_to)
        # Loại giấy tờ: kết hợp số chữ số — 9 số → CMND; 12 số → CCCD/Căn cước theo nơi cấp.
        add("LoaiGiayToDinhDanhC",
            _id_doc_type_with_number(so_giay_to or "", loai_hint, requester_issuer))
        add("NYC_SoGiayToTuyThan", so_giay_to)
        add("NgayCapDDC", ngay_cap)
        add("NoiCapDDC", requester_issuer)
        add("NYC_LoaiCuTru", "Thường trú")
        # Nơi cư trú: tờ khai → thẻ; tên đường viết tay sửa theo địa chỉ IN trên thẻ của chính người đó.
        area = _area(values.get("TkNyc_NoiCuTru")) or _area(card.get("Nyc_NoiCuTru"))
        if card:
            area = prefer_printed_street(area, _area(card.get("Nyc_NoiCuTru")))
        if area:
            add("NYC_NoiCuTru", "1")
            add("NYC_NoiCuTru_TrongNuoc", area)

    def _fill_subject_from_card() -> None:
        subject_issuer = normalize_issuer(values.get("ChuThe_NoiCap")) or default_issuer(values.get("ChuThe_NgayCap"))
        add("NDK_HoVaTen", upper_person_name(values.get("ChuThe_HoTen")))
        add("NDK_NgaySinh", values.get("ChuThe_NgaySinh"))
        add("NDK_GioiTinh", values.get("ChuThe_GioiTinh"))
        add("NDK_QuocTich", values.get("ChuThe_QuocTich") or "Việt Nam")
        add("NDK_SoDinhDanh", values.get("ChuThe_SoDinhDanh"))
        if values.get("ChuThe_SoDinhDanh"):
            add(
                "NDK_LoaiGiayToTuyThan",
                _id_doc_type_with_number(
                    values.get("ChuThe_SoDinhDanh"), values.get("ChuThe_LoaiGiayTo"), subject_issuer),
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
        add("NDK_HoVaTen", upper_person_name(values.get("Nyc_HoTen")))
        add("NDK_NgaySinh", values.get("Nyc_NgaySinh"))
        add("NDK_GioiTinh", values.get("Nyc_GioiTinh"))
        add("NDK_QuocTich", "Việt Nam")
        add("NDK_SoDinhDanh", values.get("Nyc_SoDinhDanh"))
        if values.get("Nyc_SoDinhDanh"):
            add("NDK_LoaiGiayToTuyThan",
                _id_doc_type_with_number(values.get("Nyc_SoDinhDanh"), None, requester_issuer))
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
        add("NDK_HoVaTen", upper_person_name(values.get("NguoiDuocCap_HoTen")))
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

            # Thẻ căn cước của chính người được đăng ký khớp SỐ với tờ khai/giấy hộ tịch → ngày sinh,
            # giới tính, ngày/nơi cấp lấy bản IN trên thẻ (cùng quy tắc với họ tên, số định danh).
            card_same_as_record = id_match(
                _ct("ChuThe_SoDinhDanh"),
                values.get("HoTich_SoDinhDanh") or values.get("HoTich_SoGiayToTuyThan"),
            ) is True

            def _ct_same(name):
                return _ct(name) if card_same_as_record else None

            # Tên người được đăng ký: THẺ CĂN CƯỚC của chính họ thắng tờ khai/giấy hộ tịch khi số
            # định danh hai bên khớp nhau — cùng người thì bản IN đáng tin hơn bản viết tay, và đó
            # mới là tên cổng đối chiếu với CSDLQG về dân cư. Khác số thì giữ nguyên thứ tự cũ.
            add(
                "NDK_HoVaTen",
                upper_person_name(
                    card_name_when_id_matches(
                        _ct("ChuThe_HoTen"),
                        _ct("ChuThe_SoDinhDanh"),
                        values.get("HoTich_SoDinhDanh") or values.get("HoTich_SoGiayToTuyThan"),
                    )
                    or _registered_person_name(values, event_type)
                    or values.get("NguoiDuocCap_HoTen")
                    or _ct("ChuThe_HoTen")
                ),
            )
            add(
                "NDK_NgaySinh",
                _ct_same("ChuThe_NgaySinh")
                or values.get("HoTich_NgaySinh")
                or values.get("NguoiDuocCap_NgaySinh")
                or _ct("ChuThe_NgaySinh"),
            )
            add(
                "NDK_GioiTinh",
                _ct_same("ChuThe_GioiTinh")
                or values.get("HoTich_GioiTinh")
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
                if id_match(ht_so, values.get("HoTich_SoDinhDanh")) is False:
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
                id_match(_ct_d, _subj_d) is True if _subj_d else id_match(_ct_d, _req_d) is not True
            )
            if not _ct_valid:
                ct_loai = ct_so = ct_ngay = ct_noi = None
            
            # FALLBACK: Khi không có ChuThe_* hợp lệ VÀ không có tờ khai giấy tờ,
            # kiểm tra Nyc_* (người yêu cầu) có TRÙNG chủ thể → fallback Nyc_* cho NDK_*
            #
            # Mở rộng cho ca NGƯỜI TỰ XIN BẢN SAO CỦA MÌNH: tờ khai ghi CMND 9 số cũ (người dân
            # chép theo thói quen) trong khi hồ sơ có thẻ căn cước 12 số của đúng người đó ở Nyc_*.
            # Không xét thẻ ở đây thì cả mục II bị điền bằng CMND đã hết hiệu lực.
            if not ct_so and (
                not ht_so
                or (_id_doc_rank(values.get("Nyc_SoDinhDanh")) == 2 and _id_doc_rank(ht_so) == 1)
            ):
                nyc_id = values.get("Nyc_SoDinhDanh")
                nyc_name = _fold(values.get("Nyc_HoTen"))
                subj_name = _fold(values.get("HoTich_HoTenNguoiDuocDangKy"))
                
                # Kiểm tra Nyc_* có khớp chủ thể không (so sánh tên vì không có số định danh trong giấy khai sinh)
                nyc_matches_subject = False
                if nyc_name and subj_name and nyc_name == subj_name:
                    nyc_matches_subject = True
                # Hoặc nếu có số định danh ở cả 2 bên
                if id_match(nyc_id, _subj_d) is True:
                    nyc_matches_subject = True
                
                # Nếu khớp → fallback Nyc_* cho giấy tờ của NDK
                if nyc_matches_subject and nyc_id:
                    ct_so = nyc_id
                    # KHÔNG chốt cứng "Căn cước": các cụ nhiều người chỉ có CMND 9 số, gán nhãn
                    # căn cước cho số đó là dựng ra một tấm thẻ không tồn tại. Để trống thì
                    # _id_doc_type_with_number tự suy theo SỐ CHỮ SỐ (9 → CMND, 12 → căn cước
                    # theo nơi cấp), đúng cho cả hai loại.
                    ct_loai = None
                    ct_ngay = values.get("Nyc_NgayCap")
                    ct_noi = values.get("Nyc_NoiCap")

            # THỨ TỰ ƯU TIÊN:
            # 1. Tờ khai/giấy hộ tịch (ht_*) - nguồn CHÍNH
            # 2. Thẻ căn cước của chủ thể (ct_*) - fallback khi tờ khai thiếu
            #
            # NGOẠI LỆ — MỘT NGƯỜI CÓ CẢ CCCD LẪN CMND: thẻ 12 số thắng số 9 số ghi trên tờ khai/
            # giấy hộ tịch, và thắng CẢ CỤM (số, ngày cấp, nơi cấp, loại). CMND chỉ là giấy tờ cũ
            # của chính người đó; trộn số thẻ với ngày/nơi cấp của CMND là dựng ra giấy tờ không
            # tồn tại. Chỉ so LỆCH HẠNG, hai nguồn cùng hạng vẫn giữ nguyên thứ tự cũ.
            card_beats_record = _id_doc_rank(ct_so) == 2 and _id_doc_rank(ht_so) == 1

            # SỐ ĐỊNH DANH CÁ NHÂN (12 số in trên giấy hộ tịch) VÀ CMND (9 số trên thẻ) LÀ HAI THỨ
            # KHÁC NHAU, không phải hai phiên bản của một giấy tờ. Rất nhiều cụ đã có số định danh
            # nhưng chưa đi làm thẻ căn cước, giấy tờ tùy thân duy nhất vẫn là CMND cũ. Lúc đó ô
            # "số định danh" lấy số 12 chữ số, còn CẢ CỤM giấy tờ tùy thân (số, ngày cấp, nơi cấp,
            # loại) phải lấy theo tấm CMND — nếu không sẽ ra số căn cước 12 số đi kèm ngày/nơi cấp
            # của CMND, một giấy tờ không tồn tại.
            card_is_cmnd_beside_personal_id = (
                _id_doc_rank(ct_so) == 1
                and _id_doc_rank(values.get("HoTich_SoDinhDanh")) == 2
            )
            card_wins_id_block = card_beats_record or card_is_cmnd_beside_personal_id

            # Số định danh: Ưu tiên HoTich_SoDinhDanh từ tờ khai, fallback ht_so (giấy tờ tùy thân trong giấy HT), cuối cùng mới CCCD
            add(
                "NDK_SoDinhDanh",
                card_id_when_id_matches(ct_so, values.get("HoTich_SoDinhDanh"))
                or (ct_so if card_beats_record else None)
                or ht_so
                or ct_so,
            )

            # Trẻ DƯỚI 14 TUỔI chưa bắt buộc có thẻ căn cước: số 12 chữ số của các em là SỐ ĐỊNH
            # DANH CÁ NHÂN (đã điền ở trên), KHÔNG phải số giấy tờ tùy thân → bỏ trống cả cụm
            # giấy tờ tùy thân. Em nào đã có thẻ thật và nộp kèm (ChuThe_*) thì vẫn điền bình thường.
            ndk_ngay_sinh = (
                _ct_same("ChuThe_NgaySinh")
                or values.get("HoTich_NgaySinh")
                or values.get("NguoiDuocCap_NgaySinh")
                or _ct("ChuThe_NgaySinh")
            )
            has_no_id_card = _is_under_14(ndk_ngay_sinh) and not ct_so

            if not has_no_id_card:
                # Số giấy tờ tùy thân: giống logic trên nhưng loại trừ số định danh khai sinh
                # Chot cuoi "or ht_so": khi ca ba nguon tren deu rong ma to khai VAN ghi so giay
                # to tuy than thi dien no. Ho so nay la vi du: so 11 chu so (OCR roi mat 1 so) bi
                # chan 12-chu-so gat khoi HoTich_SoDinhDanh, con ct_so bi guard "Nyc trung ChuThe"
                # gat vi nguoi yeu cau CHINH LA chu the -> o (9) trong tron, trong khi o (8) So dinh
                # danh lai da dien dung so do qua ht_so. Cung mot nguoi, cung mot the: de lech nhu
                # vay thi can bo phai go tay lai o (9).
                add(
                    "NDK_SoGiayToTuyThan",
                    (ct_so if card_wins_id_block else None)
                    or (ht_so if not is_birth else None)
                    or values.get("HoTich_SoDinhDanh")
                    or ct_so
                    or ht_so,
                )

                # Ngày cấp: Ưu tiên tờ khai trước
                # Ngày/nơi cấp: thẻ khớp số (hoặc thẻ là CCCD còn tờ khai ghi CMND cũ) thì bản IN
                # trên thẻ thắng; không thì tờ khai/giấy hộ tịch trước.
                card_wins_issue = card_same_as_record or card_wins_id_block
                ndk_ngaycap = ((ct_ngay if card_wins_issue else None) or ht_ngay or ct_ngay)
                add("NDK_NgayCap", ndk_ngaycap)

                # Nơi cấp: Ưu tiên tờ khai trước
                ndk_noicap = (
                    (normalize_issuer(ct_noi) if card_wins_issue else None)
                    or normalize_issuer(ht_noi) or normalize_issuer(ct_noi)
                )
                if not ndk_noicap and ndk_ngaycap:
                    ndk_noicap = default_issuer(ndk_ngaycap)
                add("NDK_NoiCap", ndk_noicap)

                # Loại giấy tờ: Ưu tiên tờ khai trước.
                #
                # SỐ CHỮ SỐ là bằng chứng mạnh hơn cả chữ OCR đọc được: căn cước/CCCD LUÔN 12 chữ số,
                # nên số 9 chữ số chỉ có thể là CMND cũ. Giấy hộ tịch cũ (trích lục khai tử của người
                # sinh trước 1960...) hay ghi CMND 9 số, mà OCR thì hay rơi mất chữ "CMND" — thiếu
                # luật này thì id_hint rơi về mặc định "Căn cước" rồi chọn nhầm option "Thẻ Căn cước"
                # cho một số 9 chữ số, sai hiển nhiên mà nhìn vẫn hợp lệ.
                id_hint = (ct_loai if card_wins_id_block else None) or ht_loai or ct_loai
                ndk_so_giay_to = ((ct_so if card_wins_id_block else None)
                                  or (ht_so if not is_birth else None)
                                  or values.get("HoTich_SoDinhDanh") or ct_so or ht_so)
                if id_hint or ndk_so_giay_to:
                    add("NDK_LoaiGiayToTuyThan",
                        _id_doc_type_with_number(ndk_so_giay_to, id_hint, ndk_noicap or ""))
            add("NDK_LoaiCuTru", "Thường trú")
            ndk_area = _area(values.get("HoTich_NoiCuTru")) or _area(_ct("ChuThe_NoiCuTru"))
            # Fallback nơi cư trú từ Nyc_NoiCuTru khi không có từ giấy hộ tịch/ChuThe
            # Kiểm tra nếu ct_so được set từ Nyc (fallback case) hoặc không có nơi cư trú nào
            if not ndk_area:
                # Kiểm tra nếu đã có fallback từ Nyc_* (ct_so mà không phải từ ChuThe_*)
                if ct_so and not _ct("ChuThe_SoDinhDanh"):
                    ndk_area = _area(values.get("Nyc_NoiCuTru"))
            if card_same_as_record:
                ndk_area = prefer_printed_street(ndk_area, _area(_ct("ChuThe_NoiCuTru")))
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
