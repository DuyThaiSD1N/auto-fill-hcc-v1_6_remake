"""Phân vai hồ sơ đăng ký lại khai sinh trước bước trích field.

Agent chỉ trả text phân vai. Python kiểm tra lại mỏ neo người, giới tính, thế hệ
và loại tài liệu trước khi cho kết quả này điều khiển agent trích xuất.
"""

import re
import unicodedata

from app.config import settings
from app.pipelines._shared.compact_agent.issuer import (
    ISSUER_BO_CONG_AN,
    ISSUER_CUC,
    normalize_issuer,
)
from app.pipelines._shared.area_remap import (
    canonical_province,
    is_current_area,
    remap_area,
)
from app.pipelines._shared.formatting import normalize_date
from app.services.llm import client

_REASON_MAX_TOKENS = 1100
_FAMILY_TAGS = ("con", "me", "cha")
_ROLE_PREFIX = {
    "con": "Subject_",
    "me": "Mother_",
    "cha": "Father_",
}
_FULL_NAME_FIELD = {
    "con": "Subject_FullName",
    "me": "Mother_FullName",
    "cha": "Father_FullName",
}
_ID_FIELD = {
    "con": "Subject_IdNumber",
    "me": "Mother_IdNumber",
    "cha": "Father_IdNumber",
}
_CONTEXT_EVIDENCE_FIELDS = {
    "Subject_Ethnicity": ("con", "Dân tộc"),
    "Subject_Nationality": ("con", "Quốc tịch"),
    "Mother_Ethnicity": ("me", "Dân tộc"),
    "Mother_Nationality": ("me", "Quốc tịch"),
    "Father_Ethnicity": ("cha", "Dân tộc"),
    "Father_Nationality": ("cha", "Quốc tịch"),
}
_ROLE_TAGS = (
    "nguoi_yeu_cau",
    "con",
    "me",
    "cha",
    "dang_ky_khai_sinh_truoc_day",
    "to_khai_dang_ky_lai",
    "quan_he_nguoi_yeu_cau",
)
_IDENTITY_MARKERS = (
    "can cuoc cong dan",
    "citizen identity card",
    "can cuoc",
    "identity card",
    "chung minh nhan dan",
)

_ROLE_PROMPT = """
Bạn là agent PHÂN VAI hồ sơ ĐĂNG KÝ LẠI KHAI SINH. Chỉ xác định:
- người yêu cầu;
- người được đăng ký lại khai sinh (CON);
- MẸ;
- CHA;
- QUAN HỆ giữa người yêu cầu và người được đăng ký lại khai sinh;
- hồ sơ có hay không có tài liệu ghi nhận ĐĂNG KÝ KHAI SINH trước đây.

Đọc toàn bộ OCR, không trích field biểu mẫu, không trả JSON.

THỨ TỰ PHÂN VAI — TỜ KHAI TRƯỚC, GIẤY TỜ KHÁC CHỈ LÀ NGUỒN BÙ:
0. HỒ SƠ CÓ TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH thì TỜ KHAI CHỐT VAI, không giấy tờ nào lật ngược được:
   - mục "Đề nghị cơ quan đăng ký lại khai sinh cho người có tên dưới đây" → <con>;
   - "Họ, chữ đệm, tên người mẹ" → <me>; "Họ, chữ đệm, tên người cha" → <cha>;
   - "Họ, chữ đệm, tên người yêu cầu" → <nguoi_yeu_cau>.
   Lấy ĐÚNG người ghi ở từng mục, kể cả khi tờ khai viết tay/OCR mờ hoặc thiếu số định danh.
   CCCD/CMND và trích lục khai tử chỉ dùng để BÙ các mục tờ khai bỏ trống (số định danh, ngày-nơi
   cấp, dân tộc, nơi cư trú) cho CHÍNH người đó, TUYỆT ĐỐI không dùng để đổi người giữa các vai.
   Quy tắc suy vai theo giới tính/thế hệ ở mục 3, 4b CHỈ áp dụng khi hồ sơ KHÔNG có tờ khai.
   Tờ khai ghi "Nơi cư trú: Đã chết" cho cha/mẹ → Trạng thái của vai đó là "đã chết".
1. Không có tờ khai thì mới xét nhãn rõ trên giấy khai sinh cũ hoặc trích lục khai sinh:
   "người được khai sinh/con", "mẹ", "cha".
2. Giấy khai tử chỉ chứng minh danh tính, năm sinh, giới tính và trạng thái đã chết của người trên giấy.
   KHÔNG mặc định người trong giấy khai tử là cha/mẹ. Chỉ gán cha/mẹ khi có quan hệ rõ hoặc khi quy tắc
   thế hệ tại mục 3 xác định được duy nhất.
3. Khi không có nhãn quan hệ nhưng hồ sơ thể hiện đúng một gia đình hợp lý:
   - người có năm sinh lớn nhất/gần hiện tại nhất là con;
   - người nam lớn hơn con ít nhất khoảng 15 tuổi là cha;
   - người nữ lớn hơn con ít nhất khoảng 15 tuổi là mẹ.
   Chỉ áp dụng khi mỗi vai có đúng một ứng viên và con trùng họ với ít nhất một người thuộc thế hệ trước;
   mơ hồ thì ghi "Không xác định".
   Người trẻ nhất KHÔNG trùng họ với người nam nào lớn hơn thì chưa chắc là con (thường là người đi nộp
   hộ): khi đó con là người CÒN SỐNG có thẻ, trùng họ với đúng một người nam lớn hơn ≥15 tuổi (kể cả
   người trong giấy khai tử) — người nam đó là cha.
4. CCCD/CMND chỉ cho biết thông tin của chính người trên thẻ. Tên file và thứ tự tải lên chỉ là tín hiệu
   phụ, không đủ để tự gán vai.
4b. Hồ sơ KHÔNG có tờ khai, chỉ có ĐÚNG MỘT thẻ căn cước/CMND và không tài liệu nào chỉ đích danh
   người được đăng ký lại khai sinh: người trên thẻ đó CHÍNH LÀ CON (người được đăng ký lại khai sinh) — người lớn tự
   đi đăng ký lại cho mình. Đổ TOÀN BỘ nhân thân đọc được trên thẻ vào <con>. Từ HAI thẻ trở lên thì
   KHÔNG áp dụng quy tắc này, phải phân vai theo nhãn hoặc theo thế hệ ở mục 3.
5. Người yêu cầu:
   - CÓ TỜ KHAI/ĐƠN đăng ký lại khai sinh: lấy ĐÚNG người ghi ở mục người yêu cầu trên tờ khai.
     TUYỆT ĐỐI KHÔNG lấy theo requester_context — đó chỉ là tài khoản VNeID đang đăng nhập cổng,
     rất thường là người nộp hộ và KHÁC người ghi trên tờ khai.
   - KHÔNG có tờ khai: không giấy tờ nào nói ai là người yêu cầu → ghi "Không xác định" cho cả khối
     <nguoi_yeu_cau>; KHÔNG dựng nhân thân người yêu cầu từ CCCD của con/cha/mẹ trong hồ sơ.
   Người yêu cầu có thể đồng thời là con, cha hoặc mẹ.
6. Vợ/chồng, người ký, chủ hộ, người nhận công văn không tự động là cha/mẹ/con. Bên ĐƯỢC ỦY QUYỀN
   trên giấy ủy quyền là người đi nộp hộ, không tự động là cha/mẹ/con.
7. Một người không được đồng thời là con và cha/mẹ. Không ghép tên, số định danh, ngày sinh hoặc nguồn
   của hai người khác nhau.
8. "Số/ngày đăng ký trước đây" chỉ hợp lệ khi thuộc GIẤY KHAI SINH, TRÍCH LỤC KHAI SINH hoặc
   TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH. Số/ngày trên giấy khai tử, kết hôn, CCCD không hợp lệ.

QUAN HỆ NGƯỜI YÊU CẦU — BẮT BUỘC kết luận, đây là căn cứ để tích ô trên biểu mẫu:
Đối chiếu HAI người với nhau: NGƯỜI YÊU CẦU và NGƯỜI ĐƯỢC ĐĂNG KÝ LẠI KHAI SINH. Theo thứ tự:
a. CÓ TỜ KHAI/ĐƠN đăng ký lại khai sinh: lấy đúng dòng "Quan hệ với người được khai sinh" (hoặc
   "Quan hệ với người được đăng ký lại khai sinh"). Ghi "Bản thân"/"Tự khai"/"Chính mình" → bản thân;
   ghi cha/bố → cha; ghi mẹ → mẹ; ghi ông/bà/anh/chị/em/con/cháu/người được ủy quyền → khác.
   Dòng này thắng mọi suy luận khác.
b. Tờ khai KHÔNG ghi rõ quan hệ nhưng có họ tên người yêu cầu: so họ tên + số định danh của người
   yêu cầu với <con>, <cha>, <me>. Trùng <con> → bản thân; trùng <cha> → cha; trùng <me> → mẹ;
   không trùng ai → khác.
c. KHÔNG CÓ TỜ KHAI/ĐƠN, hồ sơ chỉ có CCCD/CMND (kèm hoặc không kèm giấy khai sinh cũ):
   KẾT LUẬN "khác". Không có giấy tờ nào nói ai đang đi nộp hồ sơ, nên không được suy người yêu cầu
   là con/cha/mẹ. Cổng đã tự điền khối người yêu cầu từ tài khoản VNeID đăng nhập; phần mềm chỉ tích
   ô "Khác" rồi đổ dữ liệu quét được vào các khối con/cha/mẹ.
d. Không dùng nhãn "không xác định" khi hồ sơ không có tờ khai — trường hợp đó luôn là "khác".

Chỉ trả TEXT theo đúng năm khối sau, không markdown/code fence và không thêm JSON:
Mỗi nhãn đúng một dòng; "Căn cứ phân vai" tối đa 20 từ. Chỉ ghi KẾT LUẬN, không trình bày chuỗi suy luận.
<nguoi_yeu_cau>
Họ tên: ...
Số CCCD/CMND: ...
Ngày sinh: ...
Giới tính: ...
Dân tộc: ...
Quốc tịch: ...
Nguồn: ...
Căn cứ phân vai: ...
Vai trò đồng thời: con|mẹ|cha|không xác định
</nguoi_yeu_cau>
<con>
Họ tên: ...
Số CCCD/CMND: ...
Ngày sinh: ...
Giới tính: ...
Dân tộc: ...
Quốc tịch: ...
Trạng thái: còn sống|đã chết|không xác định
Nguồn: ...
Căn cứ phân vai: ...
</con>
<me>
Họ tên: ...
Số CCCD/CMND: ...
Ngày sinh: ...
Giới tính: ...
Dân tộc: ...
Quốc tịch: ...
Trạng thái: còn sống|đã chết|không xác định
Nguồn: ...
Căn cứ phân vai: ...
</me>
<cha>
Họ tên: ...
Số CCCD/CMND: ...
Ngày sinh: ...
Giới tính: ...
Dân tộc: ...
Quốc tịch: ...
Trạng thái: còn sống|đã chết|không xác định
Nguồn: ...
Căn cứ phân vai: ...
</cha>
<quan_he_nguoi_yeu_cau>
Người yêu cầu: ...
Người được đăng ký lại khai sinh: ...
Kết luận: bản thân|cha|mẹ|khác|không xác định
Căn cứ: ...
</quan_he_nguoi_yeu_cau>
<dang_ky_khai_sinh_truoc_day>
Có tài liệu khai sinh hợp lệ: Có|Không
Nguồn: ...
Căn cứ: ...
</dang_ky_khai_sinh_truoc_day>
""".strip()


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d").lower()
    return re.sub(r"\s+", " ", text).strip()


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _syllable_close(a: str, b: str) -> bool:
    """Hai tiếng chỉ lệch đúng MỘT ký tự (thêm/bớt/thay) — mức sai lệch của OCR chữ viết tay."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    short, long = (a, b) if len(a) < len(b) else (b, a)
    return any(long[:i] + long[i + 1:] == short for i in range(len(long)))


def _names_align(a, b) -> bool:
    """Cùng một người nhưng tên bị ghi lệch nhẹ ở MỘT tiếng.

    Tên trên tờ khai là chữ viết tay, OCR hay rụng/thêm một ký tự so với CCCD
    ("Vũ Huy Hoà" ↔ "Vũ Huy Hoàn", "Ngô Thị Hồng Thiệu" ↔ "Ngô Thị Hồng Thêu").
    Bắt buộc phải so khớp lỏng ở mức này, nếu không cả vai cha/mẹ bị coi là hai
    người khác nhau rồi bị xoá sạch field. Chỉ nới ở tên — mọi nơi gọi hàm này
    đều còn chốt thêm bằng số định danh hoặc năm sinh.
    """
    folded_a = _fold(split_name_note(a)[0])
    folded_b = _fold(split_name_note(b)[0])
    if not folded_a or not folded_b:
        return False
    if folded_a == folded_b:
        return True
    words_a, words_b = folded_a.split(), folded_b.split()
    if len(words_a) != len(words_b) or len(words_a) < 2:
        return False
    diff = [(x, y) for x, y in zip(words_a, words_b) if x != y]
    return len(diff) == 1 and _syllable_close(*diff[0])


def _one_syllable_apart(a, b) -> bool:
    """Hai tên cùng số tiếng và chỉ khác ĐÚNG MỘT tiếng."""
    words_a = _fold(split_name_note(a)[0]).split()
    words_b = _fold(split_name_note(b)[0]).split()
    if len(words_a) < 2 or len(words_a) != len(words_b):
        return False
    return sum(1 for x, y in zip(words_a, words_b) if x != y) == 1


def _document_hits(name, documents: list[dict]) -> int:
    """Số TÀI LIỆU trong hồ sơ có chứa nguyên văn họ tên này."""
    folded = _fold(name)
    if not folded:
        return 0
    return sum(1 for document in documents if folded in _fold(document.get("text")))


def _self_name_consensus(requester_name, subject_name, documents: list[dict]) -> str:
    """Người yêu cầu CHÍNH LÀ người được đăng ký lại → hai mục trên tờ khai phải cùng một tên.

    Tờ khai viết tay nên OCR đọc hỏng đúng một mục là chuyện thường ("Nguyễn Thị Thu Hà" ở dòng
    người yêu cầu, "Nguyễn Thị Ha Hà" ở mục người được đăng ký lại). Bản thân tờ khai không phân
    xử được ai đúng, nên đếm số TÀI LIỆU trong hồ sơ ghi đúng từng tên: tên còn nằm trên CCCD,
    giấy chứng nhận kết hôn, bản tường trình... là tên thật; tên chỉ xuất hiện ở đúng một dòng
    của tờ khai là dòng bị đọc hỏng.

    Chỉ nới ở mức LỆCH MỘT TIẾNG: lệch nhiều hơn thì đó là hai cái tên khác nhau (vd tên khai
    sinh cũ khác tên đang dùng), không được tự ý gộp.
    """
    if not _one_syllable_apart(requester_name, subject_name):
        return ""
    requester_hits = _document_hits(requester_name, documents)
    subject_hits = _document_hits(subject_name, documents)
    if requester_hits > subject_hits:
        return str(requester_name).strip()
    if subject_hits > requester_hits:
        return str(subject_name).strip()
    return ""


def _self_card_name(requester_section: str, subject_section: str, documents: list[dict]) -> str:
    """Người tự đi đăng ký lại cho mình: họ tên lấy theo CCCD của CHÍNH người đó.

    Tờ khai viết tay hay bị OCR đọc lệch tên ("Tôn chủ Kim nhung" ↔ thẻ "TÔN NỮ KIM NHUNG"), lệch
    quá một ký tự thì phép so tên lỏng không bắt được. SỐ ĐỊNH DANH trùng với tấm thẻ mới là bằng
    chứng chắc chắn cùng người, và tên IN trên thẻ là tên chuẩn cho cả người yêu cầu lẫn người được
    đăng ký lại. Nhiều thẻ khác tên cùng khớp số thì không chốt.
    """
    ids = {_role_id(requester_section), _role_id(subject_section)} - {""}
    if not ids:
        return ""
    names = {
        _fold(person["name"]): str(person["name"]).strip()
        for document in _identity_units(documents)
        if (person := _person_from_document(document))
        and person.get("is_identity")
        and person.get("id") in ids
    }
    return next(iter(names.values())) if len(names) == 1 else ""


def _section(text: str, tag: str) -> str:
    raw = str(text or "")
    opening = re.search(rf"<{tag}>\s*", raw, flags=re.IGNORECASE)
    if not opening:
        return ""
    remainder = raw[opening.end():]
    closing = re.search(rf"\s*</{tag}>", remainder, flags=re.IGNORECASE)
    if closing:
        return remainder[:closing.start()].strip()

    # Model có thể hết max_tokens trước thẻ đóng. Vẫn lấy đến khối kế tiếp/EOF
    # để một khối cuối bị cụt không làm mất toàn bộ kết quả phân vai.
    other_tags = "|".join(re.escape(item) for item in _ROLE_TAGS if item != tag)
    next_opening = re.search(rf"\s*<(?:{other_tags})>", remainder, flags=re.IGNORECASE)
    return remainder[:next_opening.start()].strip() if next_opening else remainder.strip()


def _labeled_value(section: str, label: str) -> str:
    match = re.search(
        rf"(?im)^\s*{re.escape(label)}\s*:\s*(.*?)\s*$",
        section,
    )
    return match.group(1).strip() if match else ""


def _requester_context(options: dict | None) -> tuple[str, str]:
    ctx = (options or {}).get("formContext") or {}
    return (
        str(ctx.get("applicantFullname") or "").strip(),
        _digits(ctx.get("applicantIdentityNumber")),
    )


# Người dân gạch mục cha/mẹ trống bằng chính chữ "Không có" trên tờ khai. Đó là LỜI KHAI KHÔNG
# CÓ NGƯỜI, không phải họ tên — không chặn thì cả khối cha/mẹ được dựng cho một người tên "Không có".
_UNKNOWN_NAME_VALUES = {"khong", "khong co", "khong ro", "chua xac dinh", "khuyet danh"}


def _is_unknown(section: str) -> bool:
    if not section:
        return True
    name = _fold(split_name_note(_labeled_value(section, "Họ tên"))[0])
    return not name or "khong xac dinh" in name or name in _UNKNOWN_NAME_VALUES


def _role_name(section: str) -> str:
    if _is_unknown(section):
        return ""
    return split_name_note(_labeled_value(section, "Họ tên"))[0]


def _role_id(section: str) -> str:
    value = _digits(_labeled_value(section, "Số CCCD/CMND"))
    return value if len(value) in {9, 12} else ""


def _role_year(section: str) -> int | None:
    value = _labeled_value(section, "Ngày sinh")
    years = re.findall(r"(?<!\d)(?:18|19|20)\d{2}(?!\d)", value)
    return int(years[-1]) if years else None


def _year_of(value) -> int | None:
    """Năm sinh đọc từ một giá trị field thô ("1970", "10/05/2000", "Không xác định")."""
    years = re.findall(r"(?<!\d)(?:18|19|20)\d{2}(?!\d)", str(value or ""))
    return int(years[-1]) if years else None


# Số CCCD 12 chữ số: chữ số thứ 4 mã hoá giới tính + thế kỷ sinh, hai chữ số kế tiếp là năm sinh.
_ID_CENTURY_BY_CODE = {"0": 1900, "1": 1900, "2": 2000, "3": 2000, "4": 2100, "5": 2100, "8": 1800, "9": 1800}


def _id_birth_year(id_number, gender=None) -> int | None:
    """Năm sinh mã hoá trong số CCCD; None nếu không đọc được hoặc giới tính mã hoá lệch thẻ.

    Giới tính in trên thẻ lệch với mã trong số thì chính con số đang bị OCR đọc sai → không tin.
    """
    digits = _digits(id_number)
    if len(digits) != 12 or digits[3] not in _ID_CENTURY_BY_CODE:
        return None
    folded_gender = _fold(gender)
    id_is_female = int(digits[3]) % 2 == 1
    if folded_gender in {"nam", "male"} and id_is_female:
        return None
    if folded_gender in {"nu", "female"} and not id_is_female:
        return None
    return _ID_CENTURY_BY_CODE[digits[3]] + int(digits[4:6])


def reconcile_birth_with_id(birth, id_number, gender=None):
    """Sửa NĂM sinh OCR đọc lệch theo năm mã hoá trong số CCCD, giữ nguyên ngày/tháng.

    req_f0fa659d2248: mặt trước thẻ của bà DƯƠNG THỊ VẬY bị OCR đọc "01/01/1994", trong khi số
    027139005852 (và MRZ "390101") nói sinh 1939. Năm sai làm bà thành người trẻ nhất hồ sơ → bị
    phân nhầm làm CON thay vì MẸ, cả khối cha/mẹ sụp theo.
    """
    year = _id_birth_year(id_number, gender)
    text = str(birth or "").strip()
    if not year:
        return birth
    if not text:
        return str(year)
    years = list(re.finditer(r"(?<!\d)(?:18|19|20|21)\d{2}(?!\d)", text))
    if not years:
        return birth
    last = years[-1]
    if int(last.group(0)) == year:
        return birth
    return text[:last.start()] + str(year) + text[last.end():]


def _role_is_subject(values: dict, prefix: str) -> bool:
    """Vai cha/mẹ vừa trích ra có ĐÚNG LÀ chính người con hay không.

    CHA VÀ CON TRÙNG TÊN LÀ CHUYỆN THƯỜNG ở hồ sơ hộ tịch (con trai đặt trùng tên bố), nên chỉ
    riêng tên trùng thì CHƯA đủ để kết luận agent chép nhầm dữ liệu con sang vai cha — xoá theo
    tên trùng là mất trắng toàn bộ Father_*/Mother_* của một người có thật. Đúng luật đang dùng ở
    bước phân vai (_validate_family_sections): số định danh, năm sinh hoặc giới tính khác nhau là
    bằng chứng chắc chắn đây là hai người, phải giữ vai lại.
    """
    subject_name = _fold(str(values.get("Subject_FullName") or ""))
    role_name = _fold(str(values.get(f"{prefix}FullName") or ""))
    if not subject_name or not role_name or role_name != subject_name:
        return False

    subject_id = _digits(values.get("Subject_IdNumber"))
    role_id = _digits(values.get(f"{prefix}IdNumber"))
    if subject_id and role_id:
        return subject_id == role_id

    subject_year = _year_of(values.get("Subject_BirthDate")) or _year_of(
        values.get("Subject_BirthDateFromId")
    )
    role_year = _year_of(values.get(f"{prefix}BirthDateOrYear"))
    if subject_year and role_year and subject_year != role_year:
        return False

    subject_gender = _fold(values.get("Subject_Gender"))
    role_gender = _fold(values.get(f"{prefix}Gender"))
    if subject_gender and role_gender and subject_gender != role_gender:
        return False

    # Không có gì phân biệt được hai người: giữ nguyên cách xử lý thận trọng cũ.
    return True


# Khối vai dựng từ nhãn quan hệ IN SẴN trên tờ khai ("Người cha:", "Người mẹ:"). Cả hai pipeline
# khai sinh đều ghi câu căn cứ bắt đầu bằng cụm này.
_DECLARATION_BASIS_PREFIX = "Nhãn quan hệ in sẵn trên tờ khai"


def _from_declaration_label(section: str) -> bool:
    """Vai này có được chốt từ một nhãn quan hệ in sẵn trên tờ khai hay không."""
    return _labeled_value(section, "Căn cứ phân vai").startswith(_DECLARATION_BASIS_PREFIX)


def _unknown_role_section(reason: str) -> str:
    return (
        "Họ tên: Không xác định\n"
        "Số CCCD/CMND: Không xác định\n"
        "Ngày sinh: Không xác định\n"
        "Giới tính: Không xác định\n"
        "Dân tộc: Không xác định\n"
        "Quốc tịch: Không xác định\n"
        "Trạng thái: Không xác định\n"
        "Nguồn: Không xác định\n"
        f"Căn cứ phân vai: {reason}"
    )


def _as_family_section(section: str, basis: str) -> str:
    if not _labeled_value(section, "Trạng thái"):
        section += "\nTrạng thái: Không xác định"
    return section + f"\nCăn cứ kiểm tra thế hệ: {basis}"


def _first_match(text: str, patterns: tuple[str, ...]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""


# ---------------------------------------------------------------------------
# GIẤY TỜ TÙY THÂN CỦA CHA/MẸ — SỐ, NGÀY CẤP, NƠI CẤP LUÔN ĐỌC TỪ CHÍNH TẤM THẺ
#
# Ba ô này là thuộc tính CỦA TẤM THẺ, không phải của con người: tờ khai chỉ chép tay lại,
# mà chữ viết tay bị OCR đọc lệch số hoặc bỏ trống là chuyện thường. Vì vậy khi trong hồ sơ
# có CCCD/CMND mang đúng họ tên cha (hoặc mẹ) mà tờ khai ghi, thì số định danh/ngày cấp/nơi
# cấp phải lấy theo tấm thẻ đó, không lấy theo tờ khai.
# ---------------------------------------------------------------------------

# "Ngày, tháng, năm sinh" và "Ngày, tháng, năm hết hạn" dùng CHUNG cụm mở đầu với ngày cấp
# in ở mặt sau thẻ, nên phải loại hai nhãn đó ra trước khi bắt ngày.
_ISSUE_DATE_PATTERNS = (
    r"Ng[aà]y\s*c[aấ]p(?:\s*/\s*Date\s+of\s+issue)?\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
    # Thẻ căn cước mẫu 2024: "Ngày, tháng, năm cấp / Date of issue:" rồi xuống dòng mới tới ngày.
    r"Ng[aà]y,?\s*th[aá]ng,?\s*n[aă]m\s*c[aấ]p(?:\s*/\s*Date\s+of\s+issue)?\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
    r"Date\s+of\s+issue\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
    r"Ng[aà]y,?\s*th[aá]ng,?\s*n[aă]m(?!\s*(?:sinh|h[eế]t\s+h[aạ]n))"
    r"(?:\s*/\s*Date,?\s*month,?\s*year)?\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
)


def _card_issue_date(text: str) -> str:
    return normalize_date(_first_match(text, _ISSUE_DATE_PATTERNS))


def _card_issue_place(text: str) -> str:
    """Cơ quan cấp in trên thẻ. CMND ghi "Công an tỉnh ..."; CCCD/căn cước ghi Cục/Bộ."""
    explicit = _first_match(text, (
        r"N[oơ]i\s*c[aấ]p(?:\s*/\s*Place\s+of\s+issue)?\s*:?\s*([^\n\r]+)",
    ))
    if explicit:
        return normalize_issuer(explicit)
    police = _first_match(text, (
        r"(C[oô]ng\s+an\s+(?:t[iỉ]nh|th[aà]nh\s+ph[oố])[^\n\r]*)",
    ))
    if police:
        return police.strip(" .,;:-")
    folded = _fold(text)
    # Mặt sau CCCD hay bị OCR nuốt mất chữ "Cục trưởng Cục Cảnh sát", chỉ còn phần đuôi.
    if "cuc canh sat" in folded or "quan ly hanh chinh" in folded or "qlhc" in folded:
        return ISSUER_CUC
    if "bo cong an" in folded:
        return ISSUER_BO_CONG_AN
    return ""


# ---------------------------------------------------------------------------
# MẶT SAU CCCD/CĂN CƯỚC GHÉP VỚI NGƯỜI BẰNG MRZ, KHÔNG BẰNG THỨ TỰ TRANG
#
# Mặt sau thẻ không in họ tên nên không biết là của ai — trừ dải MRZ in ở CUỐI mặt sau, dòng 1
# mang đủ 12 số định danh. Người dân hay scan dồn mọi mặt trước lên một trang, mọi mặt sau xuống
# trang kế (req_e30f70b0d62b: trang 2 ba mặt trước con/mẹ/cha, trang 3 ba mặt sau), nên ghép theo
# vị trí trang là ghép sai người: agent đã tráo ngày cấp/nơi cấp của con và mẹ. Ngày cấp, nơi
# cấp in NGAY TRÊN dải MRZ của chính tấm thẻ đó.
# ---------------------------------------------------------------------------

# Dòng 1 MRZ: "IDVNM" + 9 ký tự số thẻ + 1 check digit + 12 số định danh + "<<". OCR hay đọc số 0
# thành chữ O ("IDVNMO62009749902706...") nên nhận cả chữ rồi mới chuẩn hoá.
_MRZ_ID_LINE_RE = re.compile(r"IDVNM[0-9A-Z]{10}([0-9OQDIl]{12})<", flags=re.IGNORECASE)
_MRZ_DIGIT_FIXES = str.maketrans({"O": "0", "o": "0", "Q": "0", "D": "0", "I": "1", "l": "1"})
_ISSUE_PLACE_MARKERS = (
    ("bo cong an", ISSUER_BO_CONG_AN),
    ("cuc canh sat", ISSUER_CUC),
    ("quan ly hanh chinh ve trat tu", ISSUER_CUC),
)


def _last_issue_date(text: str) -> str:
    """Ngày cấp GẦN dải MRZ nhất — đoạn phía trên có thể còn đuôi của thẻ trước."""
    found = [
        (match.start(), match.group(1))
        for pattern in _ISSUE_DATE_PATTERNS
        for match in re.finditer(pattern, text, flags=re.IGNORECASE)
    ]
    return normalize_date(max(found)[1]) if found else ""


def _last_issue_place(text: str) -> str:
    folded = _fold(text)
    found = [
        (folded.rfind(marker), issuer)
        for marker, issuer in _ISSUE_PLACE_MARKERS
        if marker in folded
    ]
    return max(found)[1] if found else ""


def _mrz_card_backs(documents: list[dict]) -> dict[str, dict]:
    """Số định danh → ngày cấp/nơi cấp đọc từ mặt sau thẻ có dải MRZ mang đúng số đó.

    Đoạn mặt sau của một thẻ = từ sau dải MRZ trước đó (hoặc đầu trang) tới dòng 1 MRZ của nó.
    Cùng một số mà hai mặt sau ghi khác nhau thì không chốt được — bỏ số đó.
    """
    backs: dict[str, dict] = {}
    conflicted: set[str] = set()
    for document in documents:
        for page in _PAGE_BREAK_RE.split(str(document.get("text") or "")):
            start = 0
            for match in _MRZ_ID_LINE_RE.finditer(page):
                segment, start = page[start:match.start()], match.end()
                identity = match.group(1).translate(_MRZ_DIGIT_FIXES)
                if not identity.isdigit():
                    continue
                card = {
                    "issue_date": _last_issue_date(segment),
                    "issue_place": _last_issue_place(segment),
                }
                if not any(card.values()):
                    continue
                if identity in backs and backs[identity] != card:
                    conflicted.add(identity)
                backs[identity] = card
    return {identity: card for identity, card in backs.items() if identity not in conflicted}


# ---------------------------------------------------------------------------
# TÁCH TRANG TRƯỚC KHI ĐỌC NHÂN THÂN GIẤY TỜ
#
# Người dân hay scan CẢ TẬP hồ sơ thành MỘT file: tờ khai, bản cam đoan, CCCD con, CCCD mẹ,
# CCCD cha, giấy kết hôn, bằng cấp... nằm chung một chuỗi OCR. Đọc nguyên chuỗi đó thì
# _person_from_document chỉ ra ĐÚNG MỘT người — và thường là người sai, vì regex bắt trúng
# dòng "Họ và tên" đầu tiên của trang đầu. Hệ quả: CCCD của cha ở trang giữa không bao giờ
# được nhìn thấy. Tách theo mốc trang OCR rồi mới đọc từng tấm thẻ.
# ---------------------------------------------------------------------------

_PAGE_BREAK_RE = re.compile(
    r"^[─━\-]{3,}\s*Trang\s+(\d+)\s*/\s*\d+\s*[─━\-]{3,}$",
    flags=re.IGNORECASE | re.MULTILINE,
)

# Trang MỞ ĐẦU một giấy tờ mới luôn có dòng họ tên của chính giấy tờ đó. Trang không có dòng
# này là phần nối tiếp (mặt sau CCCD, trang trắng) nên phải gộp vào giấy tờ ngay trước nó —
# nếu không, ngày cấp in ở mặt sau bị tách rời khỏi họ tên in ở mặt trước.
_UNIT_NAME_LINE_RE = re.compile(
    r"^\s*H[oọ][,.]?\s*(?:v[aà]\s+)?(?:ch[uữ]\s*[dđ][eệ]m[,.]?\s*(?:v[aà]\s+)?)?t[eê]n",
    flags=re.IGNORECASE | re.MULTILINE,
)


def _document_pages(document: dict) -> list[dict]:
    """Cắt một tài liệu OCR nhiều trang thành từng giấy tờ riêng."""
    text = str(document.get("text") or "")
    parts = _PAGE_BREAK_RE.split(text)
    if len(parts) < 3:
        return [document]

    name = document.get("name") or "(không tên)"
    units: list[dict] = []
    for position in range(1, len(parts) - 1, 2):
        page, body = parts[position], parts[position + 1].strip()
        if not body:
            continue
        if units and not _UNIT_NAME_LINE_RE.search(body):
            units[-1]["text"] += "\n" + body
            continue
        units.append({**document, "name": f"{name} (trang {page})", "text": body})
    return units or [document]


def _identity_units(documents: list[dict]) -> list[dict]:
    return [unit for document in documents for unit in _document_pages(document)]


def _person_from_document(document: dict) -> dict | None:
    """Đọc nhân thân chính của CCCD hoặc người được khai tử ngay từ OCR."""
    text = str(document.get("text") or "")
    folded = _fold(text)
    is_identity = any(marker in folded for marker in _IDENTITY_MARKERS)
    death_match = re.search(
        r"Phần\s+ghi\s+về\s+người\s+được\s+khai\s+tử\s*:",
        text,
        flags=re.IGNORECASE,
    )
    is_death = bool(
        death_match
        or "trich luc khai tu" in folded
        or "giay bao tu" in folded
    )
    if not is_identity and not is_death:
        return None

    # Với sổ/trích lục khai tử, chỉ đọc phần người được khai tử; không lấy người
    # đi khai tử, người ký hay cán bộ xuất hiện phía sau.
    block = text[death_match.end():] if death_match else text
    # Thẻ căn cước mẫu 2024 ghi nhãn song ngữ "Họ, chữ đệm và tên khai sinh / Full name:" và in giá
    # trị ở DÒNG DƯỚI; không nhận dạng này thì cả tấm thẻ bị bỏ qua khi phân vai (req_f0fa659d2248).
    name = _first_match(block, (
        r"^\s*Họ\s+và\s+tên(?:\s*/\s*Full\s*name)?\s*:\s*([^\n\r]+)",
        r"^\s*Họ,\s*chữ\s*đệm(?:,\s*|\s+và\s+)tên(?:\s+khai\s+sinh)?(?:\s*/\s*Full\s*name)?\s*:\s*([^\n\r]+)",
        r"^\s*Họ,\s*chữ\s*đệm,\s*tên\s*:\s*([^\n\r]+)",
    ))
    birth = _first_match(block, (
        r"^\s*Ngày\s+sinh(?:\s*/\s*Date\s+of\s+birth)?\s*:\s*([^\n\r]+)",
        r"^\s*Ngày,\s*tháng,\s*năm\s+sinh(?:\s*/\s*Date\s+of\s+birth)?\s*:\s*([^\n\r]+)",
    ))
    gender = _first_match(block, (
        r"Giới\s*tính(?:\s*/\s*Sex)?\s*:\s*(Nam|Nữ|Male|Female)",
    ))
    id_number = _first_match(block, (
        r"Số\s*/\s*No\.?\s*:\s*([0-9 ]{9,})",
        r"Số\s+định\s+danh\s+cá\s+nhân(?:\s*/[^:\n]+)?\s*:\s*([0-9 ]{9,})",
    ))
    ethnicity = _first_match(block, (
        r"Dân\s*tộc\s*:\s*([^\n\r]+?)(?=\s+Quốc\s*tịch|$)",
    ))
    nationality = _first_match(block, (
        r"Quốc\s*tịch(?:\s*/\s*Nationality)?\s*:?\s*([^\n\r]+)",
    ))
    if not name or not birth or not gender:
        return None
    if is_identity:
        birth = reconcile_birth_with_id(birth, id_number, gender)

    status = "đã chết" if is_death else "không xác định"
    section = (
        f"Họ tên: {name}\n"
        f"Số CCCD/CMND: {_digits(id_number) or 'Không xác định'}\n"
        f"Ngày sinh: {birth}\n"
        f"Giới tính: {gender}\n"
        f"Dân tộc: {ethnicity or 'Không xác định'}\n"
        f"Quốc tịch: {nationality or 'Không xác định'}\n"
        f"Trạng thái: {status}\n"
        f"Nguồn: {document.get('name') or '(không tên)'}\n"
        "Căn cứ phân vai: Nhân thân chính đọc trực tiếp từ OCR của tài liệu."
    )
    return {
        "section": section,
        "name": name,
        "year": _role_year(section),
        "gender": _fold(gender),
        "score": 10,
        "is_identity": is_identity,
        # Ba khoá dưới chỉ có nghĩa với CCCD/CMND — trích lục khai tử không cấp giấy tờ tùy thân.
        "id": _digits(id_number) if is_identity else "",
        "issue_date": _card_issue_date(block) if is_identity else "",
        "issue_place": _card_issue_place(block) if is_identity else "",
        "source": str(document.get("name") or "(không tên)"),
    }


# ---------------------------------------------------------------------------
# TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH — NGUỒN SỐ 1 CỦA PHÂN VAI
#
# Tờ khai là giấy tờ DUY NHẤT trong hồ sơ ghi thẳng quan hệ ("người mẹ", "người cha",
# "người được đăng ký lại khai sinh"). CCCD/CMND chỉ nói về CHÍNH người trên thẻ, không
# nói vai, nên chỉ dùng để BÙ field tờ khai bỏ trống/mờ. Python tự đọc tờ khai để một
# lượt phân vai hỏng của LLM không làm mất trắng khối con/cha/mẹ — sanitize_extracted_fields
# xoá sạch field của vai bị ghi "Không xác định".
# ---------------------------------------------------------------------------

# Mỗi dòng chỉ khớp MỘT nhãn; thứ tự trong tuple là thứ tự thử: nhãn "người yêu cầu"/
# "người mẹ"/"người cha" phải thử TRƯỚC nhãn trần "Họ, chữ đệm, tên:" của người được đăng ký lại.
_NAME_LABEL = r"H[oọ][,.]?(?:\s*ch[uữ]\s*[dđ][eệ]m)?[,.]?\s*(?:v[aà]\s+)?t[eê]n"
_DECLARATION_ANCHORS = (
    ("nguoi_yeu_cau", rf"^\s*{_NAME_LABEL}\s+(?:c[uủ]a\s+)?(?:ng[uư][oờ]i\s+)?y[eê]u\s*c[aầ]u\s*:\s*(.*)$"),
    ("me", rf"^\s*{_NAME_LABEL}\s+(?:c[uủ]a\s+)?(?:ng[uư][oờ]i\s+)?m[eẹ]\s*:\s*(.*)$"),
    ("cha", rf"^\s*{_NAME_LABEL}\s+(?:c[uủ]a\s+)?(?:ng[uư][oờ]i\s+)?(?:cha|b[oố])\s*:\s*(.*)$"),
    ("con", rf"^\s*{_NAME_LABEL}\s*:\s*(.*)$"),
)
# Hết phần khai nhân thân — không để khối cha/mẹ nuốt sang mục đăng ký trước đây/cam đoan.
_DECLARATION_TERMINATORS = (
    r"^\s*[DĐ][aã]\s+[dđ][aă]ng\s+k[yý]\s+khai\s+sinh\s+t[aạ]i",
    r"^\s*T[oô]i\s+cam\s+[dđ]oan",
    r"^\s*[DĐ][eề]\s+ngh[iị]\s+c[aấ]p\s+b[aả]n\s+sao",
    r"^\s*Gi[aấ]y\s+khai\s+sinh\s+s[oố]",
)


def _strip_marker(value) -> str:
    """Bỏ chú thích chân trang "(2)", "(5)" biểu mẫu in sẵn đứng trước giá trị thật."""
    return re.sub(r"^(?:\s*\(\d+\))+\s*", "", str(value or "")).strip()


# Người dân rất hay ghi chú trạng thái ngay sau họ tên cha/mẹ trên tờ khai: "Hồ Bá Thích (Mất)",
# "Nguyễn Văn A (đã chết)". Chú thích đó KHÔNG phải một phần họ tên: giữ lại thì tên lệch hẳn một
# tiếng so với CCCD/trích lục khai tử nên khối vai không bù được số định danh/giới tính, rồi
# sanitize_extracted_fields coi vai đó là người lạ và xoá trắng toàn bộ Father_*/Mother_*.
_DEATH_NOTE_RE = re.compile(r"\b(?:da\s+chet|da\s+mat|chet|mat|tu\s+tran|qua\s+doi)\b")


def split_name_note(value) -> tuple[str, str]:
    """Tách "Hồ Bá Thích (Mất)" thành ("Hồ Bá Thích", "Mất")."""
    text = str(value or "").strip()
    note = " ".join(found.strip() for found in re.findall(r"\(([^)]*)\)", text))
    name = re.sub(r"\s*\([^)]*\)", " ", text)
    return re.sub(r"\s+", " ", name).strip(" .,;:-"), note.strip()


def _cut_at(value, stops: tuple[str, ...]) -> str:
    """Một dòng tờ khai thường gộp nhiều nhãn ("Năm sinh: ... Dân tộc: ... Quốc tịch: ...")."""
    text = str(value or "")
    for stop in stops:
        match = re.search(stop, text, flags=re.IGNORECASE)
        if match:
            text = text[:match.start()]
    return text.strip(" .,;:-")


# ---------------------------------------------------------------------------
# GIẤY ỦY QUYỀN — NGƯỜI ĐƯỢC ỦY QUYỀN LÀ NGƯỜI YÊU CẦU
#
# Hồ sơ có giấy ủy quyền nghĩa là người đi nộp là BÊN ĐƯỢC ỦY QUYỀN, nên khối "Thông tin người yêu
# cầu" phải mang nhân thân người đó (ô quan hệ tích "Khác"), không phải người được đăng ký lại.
# Python đọc thẳng mục "Bên được ủy quyền" từ OCR để không phụ thuộc agent trích xuất.
# ---------------------------------------------------------------------------

_AUTHORIZED_TAG = "nguoi_duoc_uy_quyen"
_AUTHORIZED_BASIS = 'Mục "Bên được ủy quyền" trên giấy ủy quyền, Python đọc trực tiếp OCR.'

# Dòng MỞ mục người được ủy quyền. Neo đầu dòng để không bắt nhầm câu cam kết "... giữa bên ủy
# quyền và bên được ủy quyền" hay dòng chữ ký "BÊN ỦY QUYỀN   BÊN ĐƯỢC ỦY QUYỀN".
_AUTHORIZED_HEADER_RE = re.compile(
    r"^(?:[ivx]+\s*[.)/]\s*|\d+\s*[.)/]\s*|[a-d]\s*[.)]\s*|[-+*•]\s*)?(?:ben\s+b\s*[(:-]?\s*)?"
    r"(?:ben|nguoi)\s+(?:duoc|nhan)\s+uy\s+quyen\b\s*(?:\(\s*ben\s+b\s*\))?\)?\s*:?\s*(.*)$"
)
# Dòng mở mục khác → hết mục người được ủy quyền.
_AUTHORIZED_BLOCK_END_RE = re.compile(
    r"^(?:[ivx]+\s*[.)/]|\d+\s*[.)/])\s|"
    r"^(?:ben\s+uy\s+quyen|nguoi\s+uy\s+quyen|noi\s+dung|pham\s+vi|thoi\s+han|cam\s+ket)\b|"
    r"^[─━\-]{3,}\s*trang\b"
)
_AUTHORIZED_NAME_LABEL_RE = re.compile(
    r"^[-+*•]?\s*(?:ong\s*/\s*ba|ong\s*\(\s*ba\s*\)|ong|ba|anh|chi|"
    r"ho\s*,?\s*(?:va\s+)?(?:chu\s*dem\s*,?\s*(?:va\s+)?)?ten|ten)\s*:"
)
_AUTHORIZED_RESIDENCE_LABEL_RE = re.compile(
    r"^[-+*•]?\s*(?:noi\s*(?:dang\s*ky\s*)?(?:thuong\s*tru|cu\s*tru|o(?:\s*hien\s*nay)?)|dia\s*chi|"
    r"(?:ho\s*khau\s*)?thuong\s*tru|hktt|cho\s*o(?:\s*hien\s*nay)?)\b[^:]*:"
)
_AUTHORIZED_NAME_STOPS = (
    r"\bsinh\s+n[aă]m\b", r"\bn[aă]m\s+sinh\b", r"\bng[aà]y\s+sinh\b", r"\bsinh\s+ng[aà]y\b",
    r"\bs[oố]\s+(?:CCCD|CMND|c[aă]n\s+c[uư][oớ]c|đ[iị]nh\s+danh)", r"\bCCCD\b", r"\bCMND\b",
    r"\bgi[oớ]i\s+t[ií]nh\b", r"[,;(]",
)
_HONORIFIC_RE = re.compile(r"^(?:ông\s*/\s*bà|ông|bà|anh|chị)\s*[:.]?\s+", re.IGNORECASE)
_AUTHORIZED_ID_RE = re.compile(
    r"(?:cccd|cmnd|can\s*cuoc(?:\s*cong\s*dan)?|dinh\s*danh(?:\s*ca\s*nhan)?|chung\s*minh\s*nhan\s*dan)"
    r"[^\d\n]{0,25}?(\d[\d .]{7,18}\d)"
)
_AUTHORIZED_BIRTH_RE = re.compile(
    r"(?:sinh\s*nam|nam\s*sinh|ngay\s*sinh|sinh\s*ngay)[^\d\n]{0,6}(\d{1,2}[/.-]\d{1,2}[/.-]\d{4}|\d{4})"
)
_AUTHORIZED_ISSUE_DATE_RE = re.compile(
    r"(?:ngay\s*cap|cap\s*ngay)[^\d\n]{0,6}(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})"
)


def _authorized_block_lines(text: str) -> list[str]:
    """Các dòng thuộc mục "Bên được ủy quyền" đầu tiên có dữ liệu; rỗng nếu không có giấy ủy quyền."""
    lines = str(text or "").splitlines()
    for index, line in enumerate(lines):
        header = _AUTHORIZED_HEADER_RE.match(_fold(line))
        if not header:
            continue
        block: list[str] = []
        # Giá trị có thể viết liền trên dòng mở mục: "Bên được ủy quyền: Ông Nguyễn Văn A, sinh năm ..."
        inline = line[line.find(":") + 1:].strip() if ":" in line else ""
        if inline:
            block.append(inline)
        for follow in lines[index + 1:index + 12]:
            folded = _fold(follow)
            if _AUTHORIZED_BLOCK_END_RE.match(folded):
                break
            if follow.strip():
                block.append(follow.strip())
        if block:
            return block
    return []


def _authorized_person_from_lines(block: list[str]) -> dict:
    name = residence = issue_place = ""
    for index, line in enumerate(block):
        folded = _fold(line)
        value = line[line.find(":") + 1:].strip() if ":" in line else ""
        if not name and (_AUTHORIZED_NAME_LABEL_RE.match(folded) or (index == 0 and not value)):
            candidate = value or line
            name = _HONORIFIC_RE.sub("", _cut_at(_HONORIFIC_RE.sub("", candidate), _AUTHORIZED_NAME_STOPS))
        elif not residence and _AUTHORIZED_RESIDENCE_LABEL_RE.match(folded):
            residence = value
        elif not issue_place and re.match(r"^[-+*•]?\s*noi\s*cap\b", folded):
            issue_place = value
    joined = _fold("\n".join(block))
    id_match = _AUTHORIZED_ID_RE.search(joined)
    birth_match = _AUTHORIZED_BIRTH_RE.search(joined)
    issue_match = _AUTHORIZED_ISSUE_DATE_RE.search(joined)
    # Họ tên phải có ít nhất hai tiếng chữ cái — dòng trống "Ông/bà: ......" không phải họ tên.
    if len(re.findall(r"[^\W\d_]{1,}", name)) < 2:
        name = ""
    return {
        "name": re.sub(r"\s+", " ", name).strip(" .,;:-"),
        "id": _digits(id_match.group(1)) if id_match else "",
        "birth": birth_match.group(1) if birth_match else "",
        "issue_date": issue_match.group(1) if issue_match else "",
        "issue_place": _cut_at(issue_place, (r"[,;]",)),
        "residence": residence,
    }


def _authorized_person(documents: list[dict]) -> dict | None:
    """Người được ủy quyền ghi trên giấy ủy quyền trong hồ sơ; None nếu không có."""
    for document in documents:
        text = str(document.get("text") or "")
        if "uy quyen" not in _fold(text):
            continue
        person = _authorized_person_from_lines(_authorized_block_lines(text))
        if person["name"] or person["id"]:
            return {**person, "source": document.get("name") or "(không tên)"}
    return None


def _render_authorized(documents: list[dict]) -> str:
    person = _authorized_person(documents)
    if not person:
        return ""
    lines = [
        f"Họ tên: {person['name'] or 'Không xác định'}",
        f"Năm sinh: {person['birth'] or 'Không xác định'}",
        f"Số CCCD/CMND: {person['id'] or 'Không xác định'}",
        f"Ngày cấp: {person['issue_date'] or 'Không xác định'}",
        f"Nơi cấp: {person['issue_place'] or 'Không xác định'}",
        f"Nơi cư trú: {person['residence'] or 'Không xác định'}",
        f"Nguồn: {person['source']}",
        f"Căn cứ: {_AUTHORIZED_BASIS}",
    ]
    return (
        f"<{_AUTHORIZED_TAG}>\n"
        + "\n".join(lines)
        + f"\n</{_AUTHORIZED_TAG}>\n"
        "Hồ sơ có GIẤY ỦY QUYỀN: người đi nộp là người trong khối <nguoi_duoc_uy_quyen>. BẮT BUỘC trả "
        "Authorized_* theo đúng người đó (ngày cấp/nơi cấp/nơi cư trú bù từ CCCD của chính người đó nếu "
        "có trong hồ sơ). Người được ủy quyền KHÔNG phải con/cha/mẹ trừ khi trùng cả họ tên lẫn số định "
        "danh với vai đó.\n"
    )


def authorized_residence_area(line) -> dict | None:
    """Dòng nơi cư trú trên giấy ủy quyền -> object địa bàn; giấy ủy quyền hay ngăn bằng gạch ngang."""
    return _residence_from_declaration_line(re.sub(r"\s+[-–]\s+", ", ", str(line or "")))


def _declaration_documents(documents: list[dict]) -> list[dict]:
    return [
        document
        for document in documents
        if "to khai" in _fold(document.get("text"))
        and "dang ky lai khai sinh" in _fold(document.get("text"))
    ]


def _declaration_start(lines: list[str]) -> int:
    """Dòng tiêu đề "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH" — mốc mở đầu phần khai nhân thân.

    Người dân hay nộp cả tập scan thành MỘT file, nên trước tờ khai còn bản cam đoan, đơn từ.
    Bản cam đoan cũng có dòng "Họ tên Cha: ..." nên quét từ đầu file thì vai cha bị chốt theo
    bản cam đoan, rồi nuốt luôn số CCCD ở mục "Các giấy tờ cá nhân của tôi" — vốn là của CON.
    """
    for index, line in enumerate(lines):
        if "to khai" not in _fold(line):
            continue
        window = _fold(" ".join(lines[index:index + 3]))
        if "dang ky lai" in window and "khai sinh" in window:
            return index
    return 0


def _declaration_blocks(text) -> dict[str, str]:
    """Cắt tờ khai thành từng khối theo nhãn quan hệ in sẵn trên biểu mẫu."""
    lines = str(text or "").splitlines()
    lines = lines[_declaration_start(lines):]
    anchors: list[tuple[int, str, str]] = []
    stop_index = len(lines)
    # "Đề nghị ... đăng ký lại khai sinh cho người có tên dưới đây" mở đầu khối người được đăng ký
    # lại. Nhãn trần "Họ, chữ đệm, tên:" đứng TRƯỚC dòng này vẫn thuộc người yêu cầu (OCR hay rụng
    # mất chữ "người yêu cầu"), nên không được nhận nhầm thành <con>.
    subject_start = next(
        (
            index
            for index, line in enumerate(lines)
            if re.search(
                r"[dđ][aă]ng\s+k[yý]\s+l[aạ]i\s+khai\s+sinh\s+cho\s+ng[uư][oờ]i",
                line,
                flags=re.IGNORECASE,
            )
        ),
        -1,
    )
    for index, line in enumerate(lines):
        matched = False
        for tag, pattern in _DECLARATION_ANCHORS:
            found = re.match(pattern, line, flags=re.IGNORECASE)
            if found:
                if tag == "con" and 0 <= subject_start > index:
                    break
                anchors.append((index, tag, _strip_marker(found.group(1))))
                matched = True
                break
        if matched or index == 0:
            continue
        if any(re.match(pattern, line, flags=re.IGNORECASE) for pattern in _DECLARATION_TERMINATORS):
            stop_index = min(stop_index, index)

    blocks: dict[str, str] = {}
    for position, (index, tag, name) in enumerate(anchors):
        if index >= stop_index or tag in blocks:
            continue
        end = anchors[position + 1][0] if position + 1 < len(anchors) else len(lines)
        blocks[tag] = "\n".join([name, *lines[index + 1:min(end, stop_index)]])
    return blocks


# Câu "Căn cứ phân vai" của khối vai dựng TẤT ĐỊNH từ tờ khai. Dùng làm dấu nhận biết: chỉ khối
# mang đúng căn cứ này mới đủ chắc để dựng lại vai khi bước lọc đã xoá trắng field trích xuất.
_DECLARATION_ROLE_BASIS = f"{_DECLARATION_BASIS_PREFIX} đăng ký lại khai sinh."


def _person_from_declaration_block(tag: str, block: str, source: str) -> dict | None:
    head = block.splitlines()[0] if block else ""
    name, name_note = split_name_note(
        _strip_marker(_cut_at(head, (r"Ng[aà]y[,\s]", r"N[aă]m\s+sinh", r"Sinh\s+ng[aà]y")))
    )
    if len(_fold(name).split()) < 2:
        return None

    birth = _cut_at(
        _strip_marker(_first_match(block, (
            r"Ng[aà]y,?\s*th[aá]ng,?\s*n[aă]m\s+sinh\s*:\s*([^\n\r]+)",
            r"Ng[aà]y\s+sinh\s*:\s*([^\n\r]+)",
            r"N[aă]m\s+sinh\s*:\s*([^\n\r]+)",
        ))),
        (r"ghi\s+b[aằ]ng\s+ch[uữ]", r"D[aâ]n\s*t[oộ]c", r"Gi[oớ]i\s*t[ií]nh", r"Qu[oố]c\s*t[iị]ch"),
    )
    gender = _first_match(block, (r"Gi[oớ]i\s*t[ií]nh\s*:?\s*(?:\(\d+\))?\s*(Nam|N[uữ])",))
    ethnicity = _cut_at(
        _strip_marker(_first_match(block, (r"D[aâ]n\s*t[oộ]c\s*:?\s*([^\n\r]+)",))),
        (r"Qu[oố]c\s*t[iị]ch",),
    )
    nationality = _cut_at(
        _strip_marker(_first_match(block, (r"Qu[oố]c\s*t[iị]ch\s*:?\s*([^\n\r]+)",))),
        (r"N[oơ]i\s+sinh", r"D[aâ]n\s*t[oộ]c"),
    )
    identity = _digits(_first_match(block, (
        r"S[oố]\s+[dđ][iị]nh\s+danh[^:\n]*:?\s*([0-9][0-9 ]{8,})",
        r"(?:CCCD|CMND|C[aă]n\s+c[uư][oớ]c|Ch[uứ]ng\s+minh)[^0-9\n]{0,40}?([0-9][0-9 ]{8,})",
    )))
    residence = _strip_marker(_first_match(block, (r"N[oơ]i\s+c[uư]\s+tr[uú]\s*:?\s*([^\n\r]+)",)))

    # "Nơi cư trú: Đã chết" là cách tờ khai ghi cha/mẹ đã mất (biểu mẫu không có ô trạng thái);
    # cách còn lại là chú thích ngay sau họ tên — "Hồ Bá Thích (Mất)".
    if tag == "con":
        status = "còn sống"
    elif any(keyword in _fold(residence) for keyword in ("da chet", "da mat", "tu tran")):
        status = "đã chết"
    elif _DEATH_NOTE_RE.search(_fold(name_note)):
        status = "đã chết"
    else:
        status = "không xác định"

    section = (
        f"Họ tên: {name}\n"
        f"Số CCCD/CMND: {identity or 'Không xác định'}\n"
        f"Ngày sinh: {birth or 'Không xác định'}\n"
        f"Giới tính: {gender or 'Không xác định'}\n"
        f"Dân tộc: {ethnicity or 'Không xác định'}\n"
        f"Quốc tịch: {nationality or 'Không xác định'}\n"
        f"{_RESIDENCE_LABEL}: {residence or 'Không xác định'}\n"
        f"Trạng thái: {status}\n"
        f"Nguồn: {source}\n"
        f"Căn cứ phân vai: {_DECLARATION_ROLE_BASIS}"
    )
    return {"section": section, "name": name, "id": identity}


def _set_role_label(section: str, label: str, value: str) -> str:
    """Trả khối vai với MỘT nhãn được đặt lại, giữ nguyên các nhãn còn lại."""
    lines = []
    for line in section.splitlines():
        name, separator, _ = line.partition(":")
        if separator and name.strip() == label:
            line = f"{label}: {value}"
        lines.append(line)
    return "\n".join(lines)


def _blank_identity_line(section: str) -> str:
    """Trả khối vai với dòng "Số CCCD/CMND" bị xoá về "Không xác định"."""
    return _set_role_label(section, "Số CCCD/CMND", "Không xác định")


def _drop_shared_declaration_ids(roles: dict[str, dict]) -> dict[str, dict]:
    """Số định danh mà tờ khai ghi cho NHIỀU vai gia đình thì không định danh được ai → bỏ hẳn.

    Người dân rất hay chép số CCCD của CHÍNH MÌNH xuống cả dòng "Giấy tờ tùy thân" của mục
    người cha và người mẹ. Giữ số đó lại thì <cha>/<me> mang số (và qua bước bù nhân thân là
    cả GIỚI TÍNH) của con, rồi bị _validate_family_sections xoá trắng vì "trùng con" /
    "cha có giới tính Nữ" — mất sạch khối cha/mẹ dù hồ sơ có CCCD riêng của họ đọc được.
    Bỏ số đi thì phần bù theo HỌ TÊN + năm sinh vẫn ghép đúng người từ CCCD thật.

    Chỉ đếm trong _FAMILY_TAGS: một người KHÔNG thể vừa là con vừa là cha/mẹ, nhưng người yêu
    cầu trùng con/cha/mẹ là chuyện bình thường nên <nguoi_yeu_cau> giữ nguyên số.
    """
    counts: dict[str, int] = {}
    for tag, person in roles.items():
        if tag in _FAMILY_TAGS and person.get("id"):
            counts[person["id"]] = counts.get(person["id"], 0) + 1
    shared = {identity for identity, count in counts.items() if count > 1}
    if not shared:
        return roles

    cleaned: dict[str, dict] = {}
    for tag, person in roles.items():
        if tag in _FAMILY_TAGS and person.get("id") in shared:
            person = {**person, "id": "", "section": _blank_identity_line(person["section"])}
        cleaned[tag] = person
    return cleaned


def _declaration_roles(documents: list[dict]) -> dict[str, dict]:
    """Người yêu cầu/con/cha/mẹ đọc TẤT ĐỊNH từ tờ khai — không qua LLM, không phụ thuộc CCCD."""
    roles: dict[str, dict] = {}
    for document in _declaration_documents(documents):
        source = str(document.get("name") or "(không tên)")
        for tag, block in _declaration_blocks(document.get("text")).items():
            if tag in roles:
                continue
            person = _person_from_declaration_block(tag, block, source)
            if person:
                roles[tag] = person
    return _drop_shared_declaration_ids(roles)


def _declaration_relation(documents: list[dict]) -> str:
    """Dòng "Quan hệ với người được khai sinh" in sẵn trên tờ khai — căn cứ mạnh nhất của ô (5)."""
    for document in _declaration_documents(documents):
        value = _first_match(str(document.get("text") or ""), (
            r"Quan\s*h[eệ]\s+v[oớ]i\s+ng[uư][oờ]i\s+[dđ][uư][oợ]c\s+(?:khai\s+sinh|"
            r"[dđ][aă]ng\s+k[yý]\s+l[aạ]i[^:\n]*)\s*:\s*([^\n\r]+)",
        ))
        relation = _normalized_relation(_strip_marker(value))
        if relation:
            return relation
    return ""


def _same_role_person(section: str, person: dict) -> bool:
    """Khối vai này có đúng là người mà tờ khai đã chốt hay không.

    Không có số định danh hai bên thì so tên — nhưng CHA VÀ CON TRÙNG TÊN LÀ CHUYỆN
    THƯỜNG, nên tên khớp mà năm sinh lệch nhau thì chắc chắn là hai người khác nhau.
    """
    section_id, person_id = _role_id(section), str(person.get("id") or "")
    if section_id and len(person_id) in {9, 12}:
        return section_id == person_id
    if not _names_align(_role_name(section), person.get("name")):
        return False
    section_year = _role_year(section)
    person_year = _role_year(person.get("section") or "")
    return not (section_year and person_year and section_year != person_year)


_MERGE_PROTECTED_LABELS = {"Họ tên", "Nguồn", "Căn cứ phân vai"}


def _merge_role_section(primary: str, secondary: str) -> str:
    """Giữ nguyên giá trị tờ khai; chỉ nhãn còn trống mới lấy bù từ nguồn phụ (CCCD/khai tử)."""
    if not secondary:
        return primary
    merged: list[str] = []
    for line in primary.splitlines():
        label, separator, value = line.partition(":")
        label = label.strip()
        if separator and label not in _MERGE_PROTECTED_LABELS and "khong xac dinh" in _fold(value):
            fallback = _labeled_value(secondary, label)
            if fallback and "khong xac dinh" not in _fold(fallback):
                line = f"{label}: {fallback}"
        merged.append(line)
    return "\n".join(merged)


def _repair_family_from_declaration(
    sections: dict[str, str],
    documents: list[dict],
) -> dict[str, str]:
    """Tờ khai thắng; CCCD/trích lục khai tử chỉ bù field còn trống của CHÍNH người đó."""
    roles = _declaration_roles(documents)
    if not roles:
        return sections

    # Nguồn bù: nhân thân LLM đã phân vai + nhân thân Python đọc thẳng từ CCCD/trích lục khai tử.
    # Chỉ được dùng cho đúng người mà tờ khai đã chốt vai, không dùng để đổi vai.
    fallbacks = [section for section in sections.values() if section and not _is_unknown(section)]
    fallbacks += [
        person["section"]
        for document in _identity_units(documents)
        if (person := _person_from_document(document))
    ]

    result = dict(sections)
    for tag, person in roles.items():
        if tag not in _FAMILY_TAGS:
            continue
        existing = result.get(tag) or ""
        # Vai đã có sẵn ĐÚNG người thì xếp lên đầu hàng bù; agent gán nhầm người khác vào vai này
        # thì bỏ hẳn kết quả đó — tờ khai là nguồn số 1.
        ordered = fallbacks
        if not _is_unknown(existing) and _same_role_person(existing, person):
            ordered = [existing, *fallbacks]

        merged = person["section"]
        for candidate in ordered:
            if _same_role_person(candidate, person):
                merged = _merge_role_section(merged, candidate)
        result[tag] = merged
    return result


def _requester_section(person: dict, sections: dict[str, str]) -> str:
    """Đổi khối người yêu cầu đọc từ tờ khai sang shape <nguoi_yeu_cau> (có "Vai trò đồng thời")."""
    role = next(
        (tag for tag in _FAMILY_TAGS if _same_role_person(sections.get(tag) or "", person)),
        "",
    )
    label = {"con": "con", "cha": "cha", "me": "mẹ"}.get(role, "không xác định")
    body = "\n".join(
        line for line in person["section"].splitlines() if not line.startswith("Trạng thái:")
    )
    return f"{body}\nVai trò đồng thời: {label}"


def _repair_family_by_generation(
    raw: str,
    sections: dict[str, str],
    documents: list[dict],
) -> dict[str, str]:
    """Chốt ca đúng ba người khi nhãn quan hệ thiếu nhưng thế hệ xác định duy nhất.

    Mỗi người có thể xuất hiện hai lần (người yêu cầu đồng thời là cha/mẹ/con),
    nên gom theo họ tên trước khi xét năm sinh.
    """
    # Ưu tiên nhân thân được Python đọc trực tiếp từ từng tài liệu. Nhờ vậy raw
    # reason dài/bị cụt vẫn không làm mất người trẻ nhất hoặc nhầm giấy khai tử.
    document_candidates = [
        person
        for document in _identity_units(documents)
        if (person := _person_from_document(document))
    ]
    candidates = {
        _fold(person["name"]): person
        for person in document_candidates
        if person.get("year")
    }

    if len(candidates) != 3:
        candidates = {}
        for tag in ("nguoi_yeu_cau", *_FAMILY_TAGS):
            section = _section(raw, tag)
            name = _role_name(section)
            year = _role_year(section)
            gender = _fold(_labeled_value(section, "Giới tính"))
            if not name or not year or gender not in {"nam", "nu", "male", "female"}:
                continue
            key = _fold(name)
            current = candidates.get(key)
            score = sum(bool(_labeled_value(section, label)) for label in (
                "Số CCCD/CMND", "Ngày sinh", "Giới tính", "Trạng thái", "Nguồn",
            ))
            if not current or score > current["score"]:
                candidates[key] = {
                    "section": section,
                    "name": name,
                    "year": year,
                    "gender": gender,
                    "score": score,
                }

    if len(candidates) != 3:
        return sections

    ordered = sorted(candidates.values(), key=lambda item: item["year"])
    youngest = ordered[-1]
    older = ordered[:-1]
    if youngest["year"] - max(item["year"] for item in older) < 15:
        return sections
    child_surname = _fold(youngest["name"]).split(" ", 1)[0]
    older_surnames = {_fold(item["name"]).split(" ", 1)[0] for item in older}
    if not child_surname or child_surname not in older_surnames:
        return sections

    men = [item for item in older if item["gender"] in {"nam", "male"}]
    women = [item for item in older if item["gender"] in {"nu", "female"}]
    if len(men) != 1 or len(women) != 1:
        return sections

    basis = "Đúng ba người, người trẻ nhất là con; hai người lớn hơn thuộc hai giới và cách ít nhất 15 năm."
    return {
        "con": _as_family_section(youngest["section"], basis),
        "cha": _as_family_section(men[0]["section"], basis),
        "me": _as_family_section(women[0]["section"], basis),
    }


def _repair_single_identity_as_subject(
    sections: dict[str, str],
    documents: list[dict],
) -> dict[str, str]:
    """Hồ sơ chỉ có ĐÚNG MỘT thẻ căn cước/CMND → người trên thẻ là NGƯỜI ĐƯỢC ĐĂNG KÝ LẠI.

    Người lớn tự đi đăng ký lại khai sinh cho chính mình thường chỉ nộp thẻ của họ. Khi đó không có
    nhãn quan hệ nào để phân vai, quy tắc thế hệ (cần đúng ba người) cũng không chạy được, nên <con>
    rỗng và CẢ khối "người được đăng ký lại khai sinh" trên biểu mẫu bị bỏ trắng dù hồ sơ có đủ nhân
    thân của chính người đó.

    CHỈ áp dụng khi có ĐÚNG MỘT thẻ: từ hai thẻ trở lên là hồ sơ có người thân đi nộp hộ, phải phân
    vai theo nhãn hoặc theo thế hệ chứ không được gán bừa. Caller cũng chỉ gọi khi <con> còn trống —
    giấy khai sinh cũ/tờ khai đã chỉ đích danh người được đăng ký lại thì giữ nguyên kết quả đó.
    """
    cards = [
        person
        for document in _identity_units(documents)
        if (person := _person_from_document(document)) and person.get("is_identity")
    ]
    if len(cards) != 1:
        return sections
    basis = "Hồ sơ chỉ có một thẻ căn cước/CMND và không có vai nào khác được xác định."
    return {**sections, "con": _as_family_section(cards[0]["section"], basis)}


def _fill_missing_roles_by_generation(
    raw: str,
    sections: dict[str, str],
    documents: list[dict],
) -> dict[str, str]:
    """Hồ sơ không tờ khai, agent đã chốt một phần vai → bù vai còn trống theo quy tắc thế hệ.

    req_f0fa659d2248: agent (và bước ghép dòng họ) chốt con NGUYỄN ĐĂNG THÚC + cha NGUYỄN ĐĂNG KY
    nhưng bỏ trống mẹ, dù hồ sơ có đúng ba người và thẻ nữ DƯƠNG THỊ VẬY (1939) chỉ có thể là mẹ.
    Chỉ nhận khi mọi vai ĐÃ CÓ người khớp đúng người quy tắc thế hệ chọn — không bao giờ đổi vai.
    """
    if _declaration_source_names(documents):
        return sections
    if all(not _is_unknown(sections.get(tag) or "") for tag in _FAMILY_TAGS):
        return sections
    generated = _repair_family_by_generation(raw, sections, documents)
    if generated is sections:
        return sections
    result = dict(sections)
    for tag in _FAMILY_TAGS:
        current = sections.get(tag) or ""
        if _is_unknown(current):
            result[tag] = generated[tag]
        elif not _names_align(_role_name(current), _role_name(generated[tag])):
            return sections
    return result


def _surname(name) -> str:
    return _fold(name).split(" ", 1)[0]


def _lineage_suspect(sections: dict[str, str]) -> bool:
    """Kết quả phân vai đáng ngờ về dòng họ: không có cha/mẹ nào, hoặc cha khác họ con."""
    father = sections.get("cha") or ""
    if _is_unknown(father):
        return _is_unknown(sections.get("me") or "")
    child_name = _role_name(sections.get("con") or "")
    return bool(child_name) and _surname(child_name) != _surname(_role_name(father))


def _repair_family_by_lineage(
    sections: dict[str, str],
    documents: list[dict],
) -> dict[str, str]:
    """Hồ sơ không có tờ khai/giấy khai sinh, agent không ghép được cha/mẹ nào → ghép theo DÒNG HỌ.

    Quy tắc "người trẻ nhất là con" gãy khi hồ sơ kèm thẻ của người nộp hộ khác họ. req_f0fa659d2248:
    thẻ NGUYỄN ĐĂNG THÚC (1965), thẻ DƯƠNG THỊ VẬY (1994), trích lục khai tử NGUYỄN ĐĂNG KY (1933).
    Agent chọn người trẻ nhất (Vậy) làm con, không ai cùng họ để làm cha → xoá cả khối cha, biểu mẫu
    gần như trắng. Con theo họ cha, nên cặp duy nhất "người còn sống có thẻ + người nam cùng họ lớn
    hơn ≥15 tuổi" mới là con/cha thật (Thúc ← Ky); người lẻ còn lại chỉ là người đi nộp hộ.

    Chỉ chốt khi có ĐÚNG MỘT cặp như vậy — nhiều cặp (ông/cha/cháu cùng họ) là mơ hồ, giữ nguyên.
    Mẹ không xét: mẹ giữ họ riêng nên dòng họ không nói được gì về mẹ.
    """
    if _declaration_source_names(documents) or _valid_birth_source_names(documents):
        return sections
    people: dict[str, dict] = {}
    for document in _identity_units(documents):
        person = _person_from_document(document)
        if not person or not person.get("year"):
            continue
        key = _fold(person["name"])
        # Cùng một người vừa có thẻ vừa xuất hiện ở giấy khác: giữ bản đọc từ thẻ.
        if key not in people or (person.get("is_identity") and not people[key].get("is_identity")):
            people[key] = person

    pairs = [
        (child, father)
        for child in people.values()
        if child.get("is_identity")
        for father in people.values()
        if father is not child
        and father["gender"] in {"nam", "male"}
        and child["year"] - father["year"] >= 15
        and _surname(child["name"]) == _surname(father["name"])
    ]
    if len(pairs) != 1:
        return sections
    child, father = pairs[0]
    basis = "Không có tờ khai; cặp duy nhất cùng họ, cha là nam hơn con ít nhất 15 tuổi."
    repaired = {
        **sections,
        "con": _as_family_section(child["section"], basis),
        "cha": _as_family_section(father["section"], basis),
    }
    # Đổi sang người con khác thì người mẹ agent ghép cho người con cũ không còn căn cứ.
    if not _names_align(_role_name(sections.get("con") or ""), child["name"]):
        repaired["me"] = _unknown_role_section("Người con được chốt lại theo dòng họ; không có căn cứ về mẹ.")
    return repaired


def _valid_birth_source_names(documents: list[dict]) -> list[str]:
    """Chỉ nhận tài liệu thực sự ghi nhận khai sinh, không nhận giấy khai tử/kết hôn."""
    names: list[str] = []
    for document in documents:
        folded = _fold(document.get("text"))
        is_birth_record = (
            "giay khai sinh" in folded
            or "giay khai sanh" in folded
            or "trich luc khai sinh" in folded
            or (
                "to khai" in folded
                and "dang ky lai" in folded
                and "khai sinh" in folded
            )
        )
        if is_birth_record:
            names.append(str(document.get("name") or "(không tên)"))
    return names


def _declaration_source_names(documents: list[dict]) -> list[str]:
    """Chỉ nhận TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH — nguồn duy nhất chốt ô quan hệ người yêu cầu.

    Giấy khai sinh cũ, trích lục và tờ khai cấp bản sao trích lục KHÔNG tính: chúng không có
    dòng "Quan hệ với người được khai sinh".
    """
    names: list[str] = []
    for document in documents:
        folded = _fold(document.get("text"))
        if "to khai" in folded and "dang ky lai khai sinh" in folded:
            names.append(str(document.get("name") or "(không tên)"))
    return names


_RELATION_LABELS = ("bản thân", "cha", "mẹ", "khác")


def _normalized_relation(value: str) -> str:
    """Quy kết luận quan hệ của agent về đúng một nhãn; không khớp thì trả rỗng."""
    folded = _fold(value)
    if not folded or "khong xac dinh" in folded:
        return ""
    if "ban than" in folded or "chinh minh" in folded or "tu khai" in folded:
        return "bản thân"
    words = folded.split()
    if "me" in words:
        return "mẹ"
    if "cha" in words or "bo" in words:
        return "cha"
    if "khac" in words:
        return "khác"
    return ""


def _anchor_is_role(applicant: tuple[str, str], section: str) -> bool:
    """Người đang đăng nhập cổng có đúng là người trong khối vai này không.

    Khớp số định danh trước; chỉ khi một bên thiếu số mới so họ tên (hai người trùng tên là
    chuyện thường, nhưng số định danh khác nhau thì chắc chắn là hai người).
    """
    name, ident = applicant
    if _is_unknown(section):
        return False
    role_id = _role_id(section)
    if ident and role_id:
        return ident == role_id
    role_name = _role_name(section)
    return bool(name and role_name and _fold(name) == _fold(role_name))


def _validated_relation(
    raw: str,
    sections: dict[str, str],
    has_declaration: bool,
    applicant: tuple[str, str] = ("", ""),
    documents: list[dict] | None = None,
) -> tuple[str, str]:
    """Chốt quan hệ người yêu cầu <-> người được đăng ký lại khai sinh.

    KHÔNG CÓ TỜ KHAI thì kết luận tất định theo mỏ neo VNeID của cổng: người đang đăng nhập TRÙNG
    <con> nghĩa là chính chủ tự đi làm cho mình → "bản thân"; không trùng thì không tài liệu nào
    nói ai đang đi nộp → "khác", và phần mềm chỉ tích "Khác" để tách khối người yêu cầu (cổng đã
    điền sẵn từ VNeID) khỏi khối người được đăng ký lại khai sinh.

    CÓ TỜ KHAI thì agent đọc và tư duy trước; Python chỉ chặn kết luận không đứng vững: chọn cha/mẹ
    trong khi chính khối <cha>/<me> lại Không xác định.
    """
    if not has_declaration:
        if _anchor_is_role(applicant, sections.get("con", "")):
            return "bản thân", (
                "Hồ sơ không có tờ khai, nhưng người đang đăng nhập cổng trùng người được đăng ký "
                "lại khai sinh → chính chủ tự đi làm cho mình."
            )
        return "khác", (
            "Hồ sơ không có tờ khai đăng ký lại khai sinh và người đăng nhập cổng không phải người "
            "được đăng ký lại khai sinh; giữ nguyên khối người yêu cầu do cổng điền từ VNeID."
        )

    section = _section(raw, "quan_he_nguoi_yeu_cau")
    # Ưu tiên số 1: chính dòng "Quan hệ với người được khai sinh" trên tờ khai, Python tự đọc.
    # Kết luận của agent chỉ dùng khi tờ khai không đọc được dòng này.
    declared = _declaration_relation(documents or [])
    relation = declared or _normalized_relation(_labeled_value(section, "Kết luận"))
    basis = (
        'Dòng "Quan hệ với người được khai sinh" trên tờ khai.'
        if declared
        else (_labeled_value(section, "Căn cứ") or "Agent không nêu căn cứ.")
    )

    if relation in {"cha", "mẹ"}:
        tag = "cha" if relation == "cha" else "me"
        if _is_unknown(sections.get(tag, "")):
            relation, basis = "", f"Agent kết luận {relation} nhưng khối <{tag}> Không xác định."

    if not relation:
        if not _is_unknown(sections.get("con", "")):
            return "bản thân", (
                f"{basis} Mặc định nghiệp vụ: người được đăng ký lại khai sinh tự đi làm cho chính mình."
            )
        return "không xác định", basis

    return relation, basis


def _source_hints(documents: list[dict], options: dict | None) -> str:
    requester_name, requester_id = _requester_context(options)
    valid_sources = _valid_birth_source_names(documents)
    declaration_sources = _declaration_source_names(documents)
    return (
        "<requester_context>\n"
        "Đây là TÀI KHOẢN VNeID đang đăng nhập cổng, KHÔNG phải kết luận về người yêu cầu: "
        "hồ sơ CÓ tờ khai thì lấy người ghi trên tờ khai, hồ sơ KHÔNG có tờ khai thì để "
        "Không xác định.\n"
        f'Họ tên trên cổng: "{requester_name or "không có"}"\n'
        f'Số định danh trên cổng: "{requester_id or "không có"}"\n'
        "</requester_context>\n"
        "<declaration_source_check>\n"
        "Tờ khai đăng ký lại khai sinh được Python nhận diện: "
        + (", ".join(declaration_sources) if declaration_sources else "Không có")
        + "\n</declaration_source_check>\n"
        "<birth_registration_source_check>\n"
        "Tài liệu khai sinh hợp lệ được Python nhận diện: "
        + (", ".join(valid_sources) if valid_sources else "Không có")
        + "\n</birth_registration_source_check>"
    )


def _build_user_content(documents: list[dict], options: dict | None) -> str:
    body = "\n\n---\n\n".join(
        f"===== Tài liệu {index}: {document.get('name') or '(không tên)'} =====\n"
        f"{str(document.get('text') or '').strip()}"
        for index, document in enumerate(documents, start=1)
    )
    return f"{_source_hints(documents, options)}\n\nOCR hồ sơ:\n\n{body}"


def _validated_requester(section: str, options: dict | None, has_declaration: bool) -> str:
    """Chốt khối <nguoi_yeu_cau> trước khi ghim vào prompt trích xuất.

    CÓ TỜ KHAI: tờ khai là nguồn duy nhất — giữ nguyên kết quả agent, KHÔNG so với mỏ neo của cổng.
    Mỏ neo đó là tài khoản VNeID đang đăng nhập (thường là người nộp hộ), so vào sẽ xoá oan người
    thật ghi trên tờ khai rồi làm khối người yêu cầu bị chắp vá từ nhiều nguồn.

    KHÔNG CÓ TỜ KHAI: không giấy tờ nào nói ai là người yêu cầu, nên chỉ giữ khối này khi nó khớp
    mỏ neo của cổng; lệch thì trả "Không xác định" để không ai bị gán nhầm vai người yêu cầu.
    """
    if has_declaration:
        return section or _unknown_role_section("Agent không đọc được người yêu cầu trên tờ khai.")

    requester_name, requester_id = _requester_context(options)
    if not requester_name and not requester_id:
        return section or _unknown_role_section("Cổng không truyền mỏ neo người yêu cầu.")

    section_id = _role_id(section)
    section_name = _fold(_role_name(section))
    id_matches = bool(requester_id and section_id and requester_id == section_id)
    name_matches = bool(requester_name and section_name and _fold(requester_name) == section_name)
    if id_matches or (not requester_id and name_matches):
        return section

    return (
        "Họ tên: Không xác định\n"
        "Số CCCD/CMND: Không xác định\n"
        "Ngày sinh: Không xác định\n"
        "Giới tính: Không xác định\n"
        "Dân tộc: Không xác định\n"
        "Quốc tịch: Không xác định\n"
        "Nguồn: Không xác định\n"
        "Căn cứ phân vai: Kết quả agent không khớp mỏ neo người yêu cầu trên cổng.\n"
        "Vai trò đồng thời: không xác định"
    )


def _parent_birth_from_documents(section: str, documents, child_year: int) -> str:
    """Ngày/năm sinh của CHÍNH người này đọc từ một giấy tờ khác trong hồ sơ.

    Chỉ gọi khi năm sinh trên tờ khai phi lý (cha/mẹ trẻ hơn con). Dòng năm sinh cha/mẹ là chữ
    VIẾT TAY nên OCR đọc lệch một chữ số là chuyện thường ("1938" → "1981"), trong khi trích lục
    khai tử/CCCD là chữ IN. Nhãn quan hệ in sẵn trên tờ khai đã chốt AI là cha/mẹ, nên gặp đúng
    một giấy mang họ tên đó với năm sinh hợp thế hệ thì lấy năm sinh ấy, thay vì xoá trắng vai và
    mất luôn họ tên, dân tộc, quốc tịch, trạng thái đã chết mà tờ khai ghi rõ.
    """
    if not _from_declaration_label(section):
        return ""
    name = _role_name(section)
    if not name:
        return ""
    found = set()
    for document in _identity_units(documents):
        person = _person_from_document(document)
        if not person or not _names_align(name, person.get("name")):
            continue
        year = person.get("year")
        birth = _labeled_value(person.get("section") or "", "Ngày sinh")
        if year and birth and child_year - year >= 15:
            found.add(birth)
    return found.pop() if len(found) == 1 else ""


def _validate_family_sections(sections: dict[str, str], documents=()) -> dict[str, str]:
    """Loại kết luận tự mâu thuẫn trước khi ghim vào prompt trích xuất."""
    result = dict(sections)

    # Mục cha/mẹ bị gạch "Không có" trên tờ khai phải trả về khối Không xác định, nếu không cả vai
    # đó được dựng cho một người tên "Không có" rồi chảy thẳng ra biểu mẫu.
    for tag in _FAMILY_TAGS:
        declared = split_name_note(_labeled_value(result.get(tag, ""), "Họ tên"))[0]
        if _fold(declared) in _UNKNOWN_NAME_VALUES:
            result[tag] = _unknown_role_section('Tờ khai ghi mục này là "Không có".')

    # Cha/mẹ phải phù hợp giới tính khi OCR đã xác định rõ.
    if _fold(_labeled_value(result.get("cha", ""), "Giới tính")) in {"nu", "female"}:
        result["cha"] = _unknown_role_section("Ứng viên cha có giới tính Nữ.")
    if _fold(_labeled_value(result.get("me", ""), "Giới tính")) in {"nam", "male"}:
        result["me"] = _unknown_role_section("Ứng viên mẹ có giới tính Nam.")
    if "da chet" in _fold(_labeled_value(result.get("con", ""), "Trạng thái")):
        result["con"] = _unknown_role_section("Người được đăng ký lại khai sinh không thể là người đã chết.")

    # Một người không thể vừa là con vừa là cha/mẹ. Nhưng CHA VÀ CON TRÙNG TÊN LÀ CHUYỆN
    # THƯỜNG (tờ khai viết tay còn hay rụng một tiếng: "Vũ Huy Hoàn" → "Vũ Huy Hoà"), nên chỉ
    # riêng tên trùng thì CHƯA đủ: số định danh hoặc năm sinh khác nhau là bằng chứng chắc chắn
    # đây là hai người, không được xoá vai cha/mẹ.
    child_id = _role_id(result.get("con", ""))
    child_name = _fold(_role_name(result.get("con", "")))
    child_year = _role_year(result.get("con", ""))
    child_gender = _fold(_labeled_value(result.get("con", ""), "Giới tính"))
    child_declared = _from_declaration_label(result.get("con", ""))
    for tag in ("cha", "me"):
        parent_id = _role_id(result.get(tag, ""))
        parent_name = _fold(_role_name(result.get(tag, "")))
        parent_year = _role_year(result.get(tag, ""))
        parent_gender = _fold(_labeled_value(result.get(tag, ""), "Giới tính"))
        if child_id and parent_id:
            same_person = child_id == parent_id
        elif child_declared and _from_declaration_label(result.get(tag, "")):
            # Tờ khai in sẵn HAI nhãn quan hệ khác nhau cho hai khối này, nên đây là hai người
            # kể cả khi trùng tên — con trai đặt trùng tên bố là chuyện thường. Xoá vai ở đây là
            # mất trắng khối cha/mẹ mà chính tờ khai đã ghi rõ.
            same_person = False
        else:
            same_person = bool(child_name and parent_name and child_name == parent_name) and not (
                child_year and parent_year and child_year != parent_year
            ) and not (
                child_gender
                and parent_gender
                and "khong xac dinh" not in child_gender
                and "khong xac dinh" not in parent_gender
                and child_gender != parent_gender
            )
        if same_person:
            result[tag] = _unknown_role_section("Trùng chính người đã được phân vai là con.")

    # Nếu có đủ năm sinh, cha/mẹ phải thuộc thế hệ trước con ít nhất khoảng 15 năm.
    if child_year:
        for tag in ("cha", "me"):
            section = result.get(tag, "")
            parent_year = _role_year(section)
            if not parent_year or child_year - parent_year >= 15:
                continue
            birth = _parent_birth_from_documents(section, documents, child_year)
            if birth:
                # Giấy tờ khác của chính người đó chốt được năm sinh hợp lý: sửa mỗi dòng năm
                # sinh, giữ nguyên cả khối để biểu mẫu vẫn có đủ mục cha/mẹ.
                result[tag] = _set_role_label(section, "Ngày sinh", birth)
                continue
            # Không giấy nào cứu được năm sinh thì vẫn xoá vai: khối cha/mẹ sai thế hệ mà không
            # có nguồn nào xác nhận là dữ liệu hỏng, điền ra biểu mẫu còn tệ hơn bỏ trống.
            result[tag] = _unknown_role_section(
                "Năm sinh không tạo được khoảng cách thế hệ cha/mẹ - con hợp lý."
            )
    return result


# Nhãn ghi trong khối vai cho ba ô "Giấy tờ tùy thân". Có dòng "Nguồn giấy tờ tùy thân" nghĩa là
# ba ô này đã được chốt tất định từ một tấm CCCD/CMND đúng người, bước trích xuất không được đổi.
_ID_CARD_SOURCE_LABEL = "Nguồn giấy tờ tùy thân"
_ID_CARD_LABELS = (
    ("Số CCCD/CMND", "id", "IdNumber"),
    ("Ngày cấp", "issue_date", "IdIssueDate"),
    ("Nơi cấp", "issue_place", "IdIssuePlace"),
)


def _card_belongs_to_role(section: str, card: dict) -> bool:
    """Tấm thẻ này có đúng là của người mà khối vai đang nói tới hay không.

    Cha và con trùng tên là chuyện thường nên tên khớp mà năm sinh lệch thì là hai người.
    """
    if not _names_align(_role_name(section), card.get("name")):
        return False
    section_year, card_year = _role_year(section), card.get("year")
    return not (section_year and card_year and section_year != card_year)


def _stamp_identity_card(section: str, card: dict) -> str:
    """Ghi đè ba ô giấy tờ tùy thân của khối vai bằng giá trị đọc thẳng từ tấm thẻ."""
    values = {
        label: str(card.get(key) or "").strip()
        for label, key, _ in _ID_CARD_LABELS
    }
    if not any(values.values()):
        return section

    lines, seen = [], set()
    for line in section.splitlines():
        label, separator, _ = line.partition(":")
        label = label.strip()
        if separator and label in values:
            seen.add(label)
            if values[label]:
                line = f"{label}: {values[label]}"
        lines.append(line)
    lines.extend(
        f"{label}: {value}"
        for label, value in values.items()
        if value and label not in seen
    )
    lines.append(f"{_ID_CARD_SOURCE_LABEL}: {card.get('source') or '(không tên)'}")
    return "\n".join(lines)


def _apply_identity_card_facts(
    sections: dict[str, str],
    documents: list[dict],
) -> dict[str, str]:
    """Số định danh/ngày cấp/nơi cấp của CHA và MẸ lấy theo CCCD, không theo tờ khai.

    Điều kiện áp dụng đúng như nghiệp vụ yêu cầu: họ tên đọc được ở khối vai (nguồn số 1 là
    tờ khai) khớp với họ tên in trên một tấm CCCD/CMND trong hồ sơ. Khớp nhiều hơn một thẻ
    thì không thẻ nào chốt được người, để nguyên tờ khai còn hơn điền nhầm thẻ người khác.

    TRÍCH LỤC KHAI TỬ cũng là giấy tờ nói về CHÍNH người đó, chỉ không cấp số giấy tờ tùy thân.
    Cha/mẹ đã mất thì tờ khai thường bỏ trống hoặc ghi mờ năm sinh, dân tộc, giới tính — những
    nhãn đó phải được bù từ trích lục, bằng không khối cha/mẹ ra biểu mẫu chỉ còn mỗi họ tên.
    """
    people = [
        person
        for document in _identity_units(documents)
        if (person := _person_from_document(document))
    ]
    if not people:
        return sections
    # Mặt sau gộp vào mặt trước theo thứ tự trang có thể là mặt sau của người khác; MRZ thì không.
    backs = _mrz_card_backs(documents)
    for person in people:
        back = backs.get(person.get("id") or "")
        if person.get("is_identity") and back:
            person.update({key: value for key, value in back.items() if value})

    result = dict(sections)
    for tag in ("cha", "me"):
        section = result.get(tag) or ""
        if not section or _is_unknown(section):
            continue
        matched = [person for person in people if _card_belongs_to_role(section, person)]
        if not matched:
            continue
        # Nhân thân: hồ sơ chốt được DUY NHẤT một người khớp vai này thì mọi nhãn tờ khai bỏ
        # trống đều lấy bù (năm sinh, giới tính, dân tộc, quốc tịch...) — tờ khai vẫn thắng ở
        # nhãn nào nó có ghi. Khớp nhiều người thì không ai chốt được, giữ nguyên tờ khai.
        if len(matched) == 1:
            section = _merge_role_section(section, matched[0]["section"])
        # Ba ô giấy tờ tùy thân chỉ CCCD/CMND mới cấp được; trích lục khai tử không chen vào.
        cards = [person for person in matched if person.get("is_identity")]
        if len(cards) == 1:
            section = _stamp_identity_card(_merge_role_section(section, cards[0]["section"]), cards[0])
        result[tag] = section
    return result


# Nhân thân cha/mẹ mà khối phân vai đã chốt sẵn. Dùng để dựng lại vai khi agent trích xuất bỏ
# sót cả khối — hồ sơ scan gộp 20 trang thì agent hay chỉ trả về người xuất hiện ở trang đầu.
_ROLE_CONTEXT_FIELDS = (
    ("Họ tên", "FullName"),
    ("Giới tính", "Gender"),
    ("Ngày sinh", "BirthDateOrYear"),
    ("Dân tộc", "Ethnicity"),
    ("Quốc tịch", "Nationality"),
)


def _identity_card_overrides(context: str, tag: str, rebuild: bool = False) -> dict:
    """Ba ô giấy tờ tùy thân đã chốt từ CCCD trong khối vai → giá trị bắt buộc của bước trích.

    rebuild=True thì lấy thêm cả nhân thân của khối, dùng cho vai agent trả về RỖNG hoàn toàn:
    điền mỗi số định danh mà thiếu họ tên thì biểu mẫu ra một khối cha nửa vời, tệ hơn bỏ trống.
    """
    section = _section(context, tag)
    if not section or _is_unknown(section):
        return {}
    if not _labeled_value(section, _ID_CARD_SOURCE_LABEL):
        return {}
    prefix = _ROLE_PREFIX[tag]
    labels = [(label, suffix) for label, _key, suffix in _ID_CARD_LABELS]
    if rebuild:
        labels += list(_ROLE_CONTEXT_FIELDS)
    overrides = {}
    for label, suffix in labels:
        value = _labeled_value(section, label)
        if value and "khong xac dinh" not in _fold(value):
            overrides[prefix + suffix] = value
    return overrides


def _declaration_role_rebuild(context: str, tag: str) -> dict:
    """Nhân thân cha/mẹ dựng lại từ khối phân vai, CHỈ khi khối đó đọc tất định từ tờ khai.

    Dùng cho vai bị loại vì lệch tên: agent hay lấy tên cha/mẹ từ giấy tờ phụ trong hồ sơ
    (bản cam đoan, trích lục khai tử) trong khi tờ khai — thứ CHỐT VAI — ghi tên khác. Xoá
    trắng cả vai khi đó là mất nhiều hơn được, vì tờ khai vẫn đủ dữ liệu điền khối cha/mẹ.
    Khối phân vai suy ra từ nguồn khác (giấy khai tử, suy theo thế hệ) KHÔNG đủ chắc để
    lật lại kết quả trích xuất nên hàm này bỏ qua.
    """
    section = _section(context, tag)
    if not section or _is_unknown(section):
        return {}
    if _DECLARATION_ROLE_BASIS not in _labeled_value(section, "Căn cứ phân vai"):
        return {}
    prefix = _ROLE_PREFIX[tag]
    labels = list(_ROLE_CONTEXT_FIELDS)
    if _labeled_value(section, _ID_CARD_SOURCE_LABEL):
        labels += [(label, suffix) for label, _key, suffix in _ID_CARD_LABELS]
    values: dict[str, str] = {}
    for label, suffix in labels:
        value = _labeled_value(section, label)
        if value and "khong xac dinh" not in _fold(value):
            values[prefix + suffix] = value
    # Thiếu họ tên thì khối dựng lại chỉ là mảnh vụn (quốc tịch/dân tộc trơ trọi) — thà bỏ trống.
    if not values.get(prefix + "FullName"):
        return {}
    return values


# Nhãn "Nơi cư trú" trong khối vai: dòng đọc TẤT ĐỊNH từ tờ khai, không qua LLM. Có nhãn này
# nghĩa là tờ khai CÓ ghi nơi cư trú của vai đó và bước trích xuất phải dùng đúng nó.
_RESIDENCE_LABEL = "Nơi cư trú"

# Tờ khai ghi cha/mẹ đã mất bằng chính ô nơi cư trú — để nguyên cho nhánh xử lý "đã chết".
_DEAD_RESIDENCE_MARKERS = ("da chet", "da mat", "tu tran")

# Nhãn cấp huyện đứng ngay trước tỉnh. Biểu mẫu chỉ có 2 cấp (xã – tỉnh) nên cụm này phải bỏ.
_DISTRICT_LABEL_RE = re.compile(
    r"^(huyện|huyen|quận|quan|thị xã|thi xa|tp\.?|thành phố|thanh pho)\b",
    re.IGNORECASE,
)


def _area_or_none(tinh: str, xa: str, dia_chi: str, huyen: str = "") -> dict | None:
    """Ghép object địa chỉ rồi CHỈ trả về khi xã/phường thật sự chọn được trên cổng."""
    if not tinh or not xa:
        return None
    # Tờ khai viết "tỉnh Lâm Đồng"/"TP Hà Nội"; danh mục nhận cả nhãn đầy đủ lẫn tên trần, nhưng
    # các field khác của thủ tục này đều đang là tên trần nên dẫn về một kiểu cho khỏi lệch.
    tinh = canonical_province(tinh) or tinh
    area = remap_area(
        {"quocGia": "Việt Nam", "tinh": tinh, "xa": xa, "diaChi": dia_chi},
        huyen_hint=huyen,
    )
    if not isinstance(area, dict):
        return None
    if not str(area.get("xa") or "").strip():
        return None
    return area if is_current_area(str(area.get("tinh") or ""), str(area.get("xa") or "")) else None


def _residence_from_declaration_line(line: str) -> dict | None:
    """Dòng "Nơi cư trú" trên tờ khai -> object {quocGia, tinh, xa, diaChi}.

    Tách bằng cách ĐẾM TỪ CUỐI như quy tắc địa chỉ chung: phần cuối là tỉnh, phần sát trước
    tỉnh là xã (tờ khai hiện hành chỉ còn 2 cấp), mọi phần phía trước là chi tiết. Tờ khai cũ
    còn ghi cấp huyện xen giữa thì bỏ cụm đó — nhận ra bằng nhãn "huyện/quận/TP", hoặc bằng
    chính kết quả tra danh mục khi nhãn bị lược.

    Trả None khi không chắc (thiếu vế, ô ghi "Đã chết", hoặc tách ra một xã KHÔNG có trong danh
    mục hiện hành). Không chắc thì giữ nguyên kết quả bước trích xuất còn hơn điền một ô chết.
    """
    text = " ".join(str(line or "").split())
    folded = _fold(text)
    if not text or "khong xac dinh" in folded:
        return None
    if any(marker in folded for marker in _DEAD_RESIDENCE_MARKERS):
        return None

    parts = [part.strip(" .;") for part in re.split(r"[,\n]", text)]
    parts = [part for part in parts if part]
    if len(parts) < 2:
        return None

    tinh, rest = parts[-1], parts[:-1]
    # Nhãn cấp huyện ghi rõ -> bỏ thẳng, không cần đoán.
    if len(rest) >= 2 and _DISTRICT_LABEL_RE.match(rest[-1]):
        return _area_or_none(tinh, rest[-2], ", ".join(rest[:-2]), huyen=rest[-1])
    # Không có nhãn: thử hiểu phần sát tỉnh là XÃ trước (tờ khai 2 cấp, dạng phổ biến nhất),
    # trượt danh mục thì mới hiểu nó là huyện bị lược nhãn (tờ khai cũ 3 cấp).
    return (
        _area_or_none(tinh, rest[-1], ", ".join(rest[:-1]))
        or (
            _area_or_none(tinh, rest[-2], ", ".join(rest[:-2]), huyen=rest[-1])
            if len(rest) >= 2
            else None
        )
    )


def _declaration_residence_overrides(context: str, tag: str) -> dict:
    """Nơi cư trú của vai này đã chốt từ tờ khai -> giá trị bắt buộc của bước trích xuất."""
    section = _section(context, tag)
    if not section or _is_unknown(section):
        return {}
    if _DECLARATION_ROLE_BASIS not in _labeled_value(section, "Căn cứ phân vai"):
        return {}
    area = _residence_from_declaration_line(_labeled_value(section, _RESIDENCE_LABEL))
    return {_ROLE_PREFIX[tag] + "ResidenceDomestic": area} if area else {}


def _apply_declaration_residence_overrides(
    fields: list[dict],
    context: str,
    invalid_prefixes: set[str],
) -> list[dict]:
    """Đặt lại Nơi cư trú cha/mẹ theo TỜ KHAI, kể cả khi agent đã lấy theo CCCD.

    Mục 1 của <uu_tien_nguon> nói rõ tờ khai là nguồn số 1 cho nơi cư trú, nhưng CCCD cũng IN
    nơi thường trú nên agent rất hay lấy nhầm theo thẻ — và lấy nhầm KHÔNG ĐỀU giữa hai vai
    (req_e783af63a58e: cha đúng theo tờ khai, mẹ lại theo CCCD). Dặn bằng chữ không đủ, nên
    chốt lại bằng Python ở đây.

    Chỉ ghi đè khi CẢ HAI điều kiện đúng: khối vai dựng tất định từ tờ khai, và dòng nơi cư trú
    tách ra được một xã/phường CÓ trong danh mục hiện hành. Thiếu một trong hai thì giữ nguyên
    kết quả của bước trích xuất.
    """
    from app.pipelines.khai_sinh_dang_ky_lai.process.schema import COMPACT_COMP_BY_NAME

    overrides: dict[str, dict] = {}
    for tag in ("cha", "me"):
        if _ROLE_PREFIX[tag] in invalid_prefixes:
            continue
        overrides.update(_declaration_residence_overrides(context, tag))
    if not overrides:
        return fields

    result, seen = [], set()
    for field in fields:
        name = str(field.get("name") or "")
        if name in overrides:
            field = {**field, "value": overrides[name]}
            seen.add(name)
        result.append(field)
    for name, value in overrides.items():
        if name in seen:
            continue
        comp = COMPACT_COMP_BY_NAME.get(name)
        if comp:
            result.append({"name": name, "comp": comp, "value": value})
    return result


def _apply_identity_card_overrides(
    fields: list[dict],
    context: str,
    invalid_prefixes: set[str],
    empty_prefixes: set[str],
) -> list[dict]:
    """Đặt lại ba ô giấy tờ tùy thân của cha/mẹ theo CCCD, kể cả khi agent trả thiếu."""
    from app.pipelines.khai_sinh_dang_ky_lai.process.schema import COMPACT_COMP_BY_NAME

    overrides: dict[str, str] = {}
    for tag in ("cha", "me"):
        prefix = _ROLE_PREFIX[tag]
        if prefix in invalid_prefixes:
            continue
        overrides.update(_identity_card_overrides(context, tag, rebuild=prefix in empty_prefixes))
    if not overrides:
        return fields

    result, seen = [], set()
    for field in fields:
        name = str(field.get("name") or "")
        if name in overrides:
            field = {**field, "value": overrides[name]}
            seen.add(name)
        result.append(field)
    for name, value in overrides.items():
        if name in seen:
            continue
        comp = COMPACT_COMP_BY_NAME.get(name)
        if comp:
            result.append({"name": name, "comp": comp, "value": value})
    return result


_MRZ_BACKS_TAG = "mat_sau_the_theo_mrz"
_MRZ_BACK_LINE_RE = re.compile(r"^(\d{12}) \| Ngày cấp: ([^|]*) \| Nơi cấp: (.*)$", flags=re.MULTILINE)
_MRZ_OVERRIDE_PREFIXES = ("Subject_", "Mother_", "Father_", "Requester_", "Authorized_")


def _render_mrz_backs(documents: list[dict]) -> str:
    lines = [
        f"{identity} | Ngày cấp: {card['issue_date']} | Nơi cấp: {card['issue_place']}"
        for identity, card in _mrz_card_backs(documents).items()
    ]
    if not lines:
        return ""
    return (
        f"<{_MRZ_BACKS_TAG}>\n"
        "Ngày cấp/Nơi cấp đọc từ mặt sau thẻ, ghép với người bằng số định danh trong dải MRZ. "
        "Người có *_IdNumber trùng số nào thì *_IdIssueDate/*_IdIssuePlace BẮT BUỘC lấy đúng dòng "
        "đó, KHÔNG ghép mặt sau theo thứ tự trang.\n"
        + "\n".join(lines)
        + f"\n</{_MRZ_BACKS_TAG}>\n"
    )


def _apply_mrz_issue_overrides(fields: list[dict], context: str) -> list[dict]:
    """Ngày cấp/nơi cấp của MỌI vai theo mặt sau thẻ mang đúng số định danh của vai đó."""
    from app.pipelines.khai_sinh_dang_ky_lai.process.schema import COMPACT_COMP_BY_NAME

    backs = {
        identity: (date.strip(), place.strip())
        for identity, date, place in _MRZ_BACK_LINE_RE.findall(_section(context, _MRZ_BACKS_TAG))
    }
    if not backs:
        return fields
    ids = {
        prefix: _digits(field.get("value"))
        for field in fields
        for prefix in _MRZ_OVERRIDE_PREFIXES
        if field.get("name") == f"{prefix}IdNumber"
    }
    overrides: dict[str, str] = {}
    for prefix, identity in ids.items():
        date, place = backs.get(identity, ("", ""))
        if date:
            overrides[f"{prefix}IdIssueDate"] = date
        if place:
            overrides[f"{prefix}IdIssuePlace"] = place
    if not overrides:
        return fields

    result, seen = [], set()
    for field in fields:
        name = str(field.get("name") or "")
        if name in overrides:
            field = {**field, "value": overrides[name]}
            seen.add(name)
        result.append(field)
    for name, value in overrides.items():
        comp = COMPACT_COMP_BY_NAME.get(name)
        if name not in seen and comp:
            result.append({"name": name, "comp": comp, "value": value})
    return result


def _render_context(raw: str, options: dict | None, documents: list[dict]) -> str:
    """Kiểm tra tất định kết quả LLM rồi ghim vào prompt trích xuất."""
    sections = {tag: _section(raw, tag) for tag in _FAMILY_TAGS}

    # TỜ KHAI TRƯỚC, CCCD SAU: nhãn quan hệ in sẵn trên tờ khai là căn cứ mạnh nhất và Python
    # đọc được tất định, nên chốt vai từ đó trước mọi suy luận dựa trên thẻ căn cước bên dưới.
    sections = _repair_family_from_declaration(sections, documents)

    # Nếu LLM trả không ra ai → thử suy từ thế hệ (3 người, nam/nữ, cách 15 năm).
    if not any(not _is_unknown(s) for s in sections.values()):
        sections = _repair_family_by_generation(raw, sections, documents)

    # Agent không ghép được cha/mẹ nào, hoặc ghép một người cha KHÁC HỌ con → thử ghép theo dòng họ.
    if _lineage_suspect(sections):
        sections = _repair_family_by_lineage(sections, documents)

    # Còn vai trống → bù theo quy tắc thế hệ, chỉ khi kết quả không ngược với vai đã chốt.
    sections = _fill_missing_roles_by_generation(raw, sections, documents)

    # Vẫn chưa có người được đăng ký lại mà hồ sơ chỉ có đúng một thẻ → thẻ đó chính là người đó.
    if _is_unknown(sections.get("con") or ""):
        sections = _repair_single_identity_as_subject(sections, documents)

    if not any(not _is_unknown(s) for s in sections.values()):
        return ""

    sections = _validate_family_sections(sections, documents)

    # Tờ khai chốt AI là cha/mẹ; tấm CCCD của chính người đó chốt SỐ ĐỊNH DANH, NGÀY CẤP, NƠI CẤP.
    sections = _apply_identity_card_facts(sections, documents)

    # Tờ khai quyết định CẢ ô "Quan hệ với người được khai sinh" LẪN nhân thân người yêu cầu;
    # Python tự kiểm tra loại tài liệu, không tin LLM.
    declaration_sources = _declaration_source_names(documents)
    declaration_value = "Có" if declaration_sources else "Không"
    declaration_source = ", ".join(declaration_sources) if declaration_sources else "Không có"

    # Người yêu cầu: có tờ khai thì tờ khai thắng; không có thì mới soi mỏ neo của cổng.
    requester_raw = _section(raw, "nguoi_yeu_cau")
    # Agent bỏ trống người yêu cầu nhưng tờ khai có ghi → dựng tất định từ tờ khai (tờ khai trước,
    # CCCD chỉ bù field trống ở bước trích xuất).
    if _is_unknown(requester_raw):
        declared_requester = _declaration_roles(documents).get("nguoi_yeu_cau")
        if declared_requester:
            requester_raw = _requester_section(declared_requester, sections)
    requester = _validated_requester(requester_raw, options, bool(declaration_sources))

    # Đăng ký khai sinh trước đây: Python tự kiểm tra loại tài liệu (không tin LLM).
    valid_sources = _valid_birth_source_names(documents)
    registration_value = "Có" if valid_sources else "Không"
    source_value = ", ".join(valid_sources) if valid_sources else "Không có"

    relation_value, relation_basis = _validated_relation(
        raw, sections, bool(declaration_sources), _requester_context(options), documents
    )

    # Người yêu cầu và người được đăng ký lại là MỘT người thì chỉ được có MỘT họ tên; tờ khai
    # viết tay hay để OCR đọc lệch một trong hai dòng nên chốt lại bằng số tài liệu ghi đúng tên.
    self_name = (
        _self_card_name(requester, sections.get("con") or "", documents)
        or _self_name_consensus(_role_name(requester), _role_name(sections.get("con") or ""), documents)
        if relation_value == "bản thân"
        else ""
    )
    self_name_line = f"Họ tên thống nhất: {self_name}\n" if self_name else ""

    return (
        "\n\n<phan_vai_da_xac_dinh>\n"
        "Dùng đúng các vai dưới đây; không tự đổi người giữa Subject/Father/Mother.\n"
        "<nguoi_yeu_cau>\n"
        f"{requester}\n"
        "</nguoi_yeu_cau>\n"
        "<con>\n"
        f"{sections.get('con') or _unknown_role_section('Agent không xác định được.')}\n"
        "</con>\n"
        "<me>\n"
        f"{sections.get('me') or _unknown_role_section('Agent không xác định được.')}\n"
        "</me>\n"
        "<cha>\n"
        f"{sections.get('cha') or _unknown_role_section('Agent không xác định được.')}\n"
        "</cha>\n"
        "<dang_ky_khai_sinh_truoc_day>\n"
        f"Có tài liệu khai sinh hợp lệ: {registration_value}\n"
        f"Nguồn: {source_value}\n"
        "Căn cứ: Kết quả kiểm tra trực tiếp loại tài liệu OCR bằng Python.\n"
        "</dang_ky_khai_sinh_truoc_day>\n"
        "<quan_he_nguoi_yeu_cau>\n"
        f"Kết luận: {relation_value}\n"
        f"{self_name_line}"
        f"Căn cứ: {relation_basis}\n"
        "</quan_he_nguoi_yeu_cau>\n"
        "<to_khai_dang_ky_lai>\n"
        f"Có tờ khai đăng ký lại khai sinh: {declaration_value}\n"
        f"Nguồn: {declaration_source}\n"
        "Căn cứ: Kết quả kiểm tra trực tiếp loại tài liệu OCR bằng Python.\n"
        "</to_khai_dang_ky_lai>\n"
        f"{_render_mrz_backs(documents)}"
        f"{_render_authorized(documents)}"
        "Khối <cha>/<me> có dòng \"Nguồn giấy tờ tùy thân\" nghĩa là Số CCCD/CMND, Ngày cấp, "
        "Nơi cấp trong khối đó đã đọc thẳng từ chính tấm CCCD/CMND của người đó: BẮT BUỘC trả "
        "y nguyên vào *_IdNumber, *_IdIssueDate, *_IdIssuePlace, không lấy theo tờ khai.\n"
        "Subject_* chỉ thuộc <con>; Mother_* chỉ thuộc <me>; Father_* chỉ thuộc <cha>. "
        "Nếu một khối ghi Không xác định thì bỏ toàn bộ field của vai đó. "
        "PreviousRegistration_* chỉ được trả khi khối đăng ký khai sinh trước đây ghi Có. "
        "Requester_* chỉ được trả khi khối tờ khai đăng ký lại ghi Có; khi đó BẮT BUỘC trả "
        "Requester_RelationToSubject kể cả khi người yêu cầu trùng <con>/<cha>/<me>. "
        "Khối tờ khai ghi Không thì BỎ TRỐNG toàn bộ Requester_* — cổng giữ nguyên khối người "
        "yêu cầu đã điền sẵn từ tài khoản VNeID.\n"
        "</phan_vai_da_xac_dinh>"
    )


def _context_id_is_shared(context: str, tag: str, expected_id: str) -> bool:
    """Số định danh của vai này còn được gán cho vai gia đình khác trong khối phân vai.

    Tờ khai hay ghi nhầm CCCD của người này sang mục người kia (vd mục "Giấy tờ tùy thân"
    của MẸ chép đúng số CCCD của CHA) và agent phân vai chép y nguyên. Một người không thể
    vừa là cha vừa là mẹ/con, nên số bị trùng vai KHÔNG dùng làm mỏ neo nhận dạng được.
    """
    if not expected_id:
        return False
    return any(
        _role_id(_section(context, other)) == expected_id
        for other in _FAMILY_TAGS
        if other != tag
    )


def _identity_matches(fields_by_name: dict, context: str, tag: str) -> bool:
    section = _section(context, tag)
    if _is_unknown(section):
        return False

    expected_id = _role_id(section)
    actual_id = _digits(fields_by_name.get(_ID_FIELD.get(tag, "")))
    if expected_id and actual_id and not _context_id_is_shared(context, tag, expected_id):
        if expected_id == actual_id:
            return True
        # Số LỆCH chưa đủ để xoá vai. Số trong khối phân vai thường đọc từ tờ khai viết tay —
        # thứ OCR hay rụng/thêm chữ số ("086062010934" ↔ "086063010739") — còn số ở field trích
        # xuất đọc từ CCCD, tức đúng con số ta muốn giữ. Xoá vai vì lệch số là xoá trắng cả khối
        # của đúng người đó. Chỉ chốt "người khác" khi số trích được đang thuộc về MỘT VAI KHÁC
        # trong khối phân vai; ngoài ra để họ tên phân xử.
        if _context_id_is_shared(context, tag, actual_id):
            return False

    # Không có số định danh để đối chiếu thì so tên. Tên trong khối phân vai có thể đọc từ tờ
    # khai viết tay còn field trích xuất đọc từ CCCD, nên phải chấp nhận lệch một tiếng do OCR —
    # bằng không cả vai cha/mẹ bị coi là người lạ rồi bị xoá trắng.
    actual_name = fields_by_name.get(_FULL_NAME_FIELD[tag])
    if _names_align(_role_name(section), actual_name):
        return True
    # Khối phân vai đã chốt tên thật của người tự đi đăng ký lại cho mình (xem _self_name_consensus).
    # Agent trích đúng tên đó thì KHÔNG được coi là người lạ rồi xoá trắng khối con.
    if tag == "con":
        unified = _labeled_value(_section(context, "quan_he_nguoi_yeu_cau"), "Họ tên thống nhất")
        return bool(unified) and _names_align(unified, actual_name)
    return False


# Ô ngày sinh của từng vai + giới tính mặc định của vai (cha nam, mẹ nữ) khi agent không trả *_Gender.
_BIRTH_FIELDS_BY_PREFIX = {
    "Subject_": (("Subject_BirthDate", "Subject_BirthDateFromId"), None),
    "Mother_": (("Mother_BirthDateOrYear",), "Nữ"),
    "Father_": (("Father_BirthDateOrYear",), "Nam"),
}


def _reconcile_birth_fields(fields: list[dict]) -> list[dict]:
    """Ngày sinh agent chép từ mặt trước thẻ phải khớp năm mã hoá trong số CCCD của chính vai đó."""
    values = {field.get("name"): field.get("value") for field in fields if field.get("name")}
    fixes: dict[str, object] = {}
    for prefix, (names, default_gender) in _BIRTH_FIELDS_BY_PREFIX.items():
        id_number = values.get(prefix + "IdNumber")
        gender = values.get(prefix + "Gender") or default_gender
        for name in names:
            if name in values:
                fixed = reconcile_birth_with_id(values[name], id_number, gender)
                if fixed != values[name]:
                    fixes[name] = fixed
    if not fixes:
        return fields
    return [
        {**field, "value": fixes[field["name"]]} if field.get("name") in fixes else field
        for field in fields
    ]


def sanitize_extracted_fields(fields: list[dict], context: str) -> list[dict]:
    """Không cho field của một người chảy sang vai khác sau bước trích xuất.
    
    Bổ sung validation chặt chẽ:
    1. Phát hiện duplicate (cùng tên/CCCD ở Father và Mother)
    2. Kiểm tra giới tính (Father phải Nam, Mother phải Nữ)
    3. Loại bỏ trùng lặp với Subject
    4. Xóa địa chỉ "Đã chết" không hợp lệ từ LLM
    """
    fields = _reconcile_birth_fields(fields)
    values = {
        field.get("name"): field.get("value")
        for field in fields
        if field.get("name")
    }
    
    # ===== BƯỚC 1: PHÁT HIỆN VÀ SỬA DUPLICATE + GIỚI TÍNH SAI =====
    father_name = _fold(str(values.get("Father_FullName") or ""))
    mother_name = _fold(str(values.get("Mother_FullName") or ""))
    father_id = _digits(values.get("Father_IdNumber"))
    mother_id = _digits(values.get("Mother_IdNumber"))
    subject_birth = _fold(str(values.get("Subject_BirthDate") or ""))
    
    # ĐỌC GIỚI TÍNH TRỰC TIẾP TỪ EXTRACTED FIELDS (LLM output)
    father_gender_extracted = _fold(str(values.get("Father_Gender") or ""))
    mother_gender_extracted = _fold(str(values.get("Mother_Gender") or ""))
    
    # Tập các prefix cần XÓA
    invalid_prefixes = set()
    
    # KIỂM TRA 0A: Phát hiện duplicate TÊN giữa Father và Mother TRƯỚC
    # Nếu Father_FullName = Mother_FullName → Chỉ giữ 1, xóa cái còn lại
    if father_name and mother_name and father_name == mother_name:
        # Kiểm tra giới tính để quyết định giữ Father hay Mother
        # Nếu Father có giới tính Nữ → XÓA Father, giữ Mother
        if father_gender_extracted in {"nu", "nữ", "female"}:
            invalid_prefixes.add("Father_")
        # Nếu Mother có giới tính Nam → XÓA Mother, giữ Father
        elif mother_gender_extracted in {"nam", "male"}:
            invalid_prefixes.add("Mother_")
        # Không rõ → ưu tiên XÓA Father (giữ Mother)
        else:
            invalid_prefixes.add("Father_")
    
    # KIỂM TRA 0B: Phát hiện duplicate CCCD
    if father_id and mother_id and father_id == mother_id:
        # Tương tự logic trên
        if father_gender_extracted in {"nu", "nữ", "female"}:
            invalid_prefixes.add("Father_")
        elif mother_gender_extracted in {"nam", "male"}:
            invalid_prefixes.add("Mother_")
        else:
            invalid_prefixes.add("Father_")
    
    # KIỂM TRA 0C: Father có giới tính Nữ (KHÔNG duplicate)
    if father_gender_extracted in {"nu", "nữ", "female"} and father_name and "Father_" not in invalid_prefixes:
        invalid_prefixes.add("Father_")
    
    # KIỂM TRA 0D: Mother có giới tính Nam (KHÔNG duplicate)
    if mother_gender_extracted in {"nam", "male"} and mother_name and "Mother_" not in invalid_prefixes:
        invalid_prefixes.add("Mother_")
    
    # KIỂM TRA 2: Father/Mother CHÍNH LÀ Subject (con) — agent chép nhầm dữ liệu con sang vai đó.
    # Xét TỪNG VAI độc lập (trước đây chỉ cần một vai đã bị loại ở bước trên là cả phép kiểm tra
    # này bị bỏ qua) và chỉ loại khi KHÔNG có bằng chứng nào cho thấy đây là hai người khác nhau
    # — xem _role_is_subject.
    for prefix in ("Father_", "Mother_"):
        if prefix not in invalid_prefixes and _role_is_subject(values, prefix):
            invalid_prefixes.add(prefix)
    
    # KIỂM TRA 2B: cha/mẹ CÙNG ngày sinh với con → chắc chắn là dữ liệu của con bị chép sang vai đó.
    if subject_birth:
        if _fold(str(values.get("Father_BirthDateOrYear") or "")) == subject_birth:
            invalid_prefixes.add("Father_")
        if _fold(str(values.get("Mother_BirthDateOrYear") or "")) == subject_birth:
            invalid_prefixes.add("Mother_")

    # KIỂM TRA 3: vai KHÔNG có nhân thân (không họ tên, không số định danh) thì BỎ HẲN vai đó.
    # Hồ sơ chỉ có con + CCCD mẹ mà LLM vẫn trả rơi rớt Father_QuocTich/Father_ResidenceDomestic sẽ
    # khiến mapper dựng một khối "cha" rỗng với quốc tịch/loại cư trú mặc định — thà bỏ trống.
    # "Rỗng" khác hẳn "sai người": khối phân vai đã chốt được đúng tấm CCCD của vai này thì bước
    # cuối dựng lại vai từ khối đó, thay vì để mất trắng cha/mẹ chỉ vì agent bỏ sót.
    empty_prefixes: set[str] = set()
    for prefix, name_key, id_key in (
        ("Father_", "Father_FullName", "Father_IdNumber"),
        ("Mother_", "Mother_FullName", "Mother_IdNumber"),
    ):
        if not str(values.get(name_key) or "").strip() and not _digits(values.get(id_key)):
            invalid_prefixes.add(prefix)
            empty_prefixes.add(prefix)
    
    # ===== BƯỚC 3: KIỂM TRA CONTEXT MATCHING (logic cũ) =====
    # Vai bị loại ở ĐÂY (người trích ra khác người khối phân vai đã chốt) còn cứu được ở BƯỚC 4B;
    # vai bị loại ở các bước trên là dữ liệu hỏng thật nên phải nhớ riêng để không dựng lại.
    broken_prefixes = set(invalid_prefixes)
    mismatched_prefixes: set[str] = set()
    if context:
        for tag in _FAMILY_TAGS:
            if not _identity_matches(values, context, tag):
                mismatched_prefixes.add(_ROLE_PREFIX[tag])
                invalid_prefixes.add(_ROLE_PREFIX[tag])
    
    has_birth_source = bool(context) and _fold(
        _labeled_value(_section(context, "dang_ky_khai_sinh_truoc_day"), "Có tài liệu khai sinh hợp lệ")
    ) == "co"
    # Không có tờ khai thì Requester_* là do agent tự bịa (hay gặp: "Khác") — lọt xuống mapper là nó
    # coi như có tờ khai rồi ghi đè nơi cư trú người yêu cầu cổng đã điền sẵn từ VNeID thành rỗng.
    no_declaration = bool(context) and _fold(
        _labeled_value(_section(context, "to_khai_dang_ky_lai"), "Có tờ khai đăng ký lại khai sinh")
    ) == "khong"

    # ===== BƯỚC 4: LỌC FIELDS =====
    result: list[dict] = []
    for field in fields:
        name = str(field.get("name") or "")
        value = field.get("value")
        
        # Xóa các prefix không hợp lệ
        if any(name.startswith(prefix) for prefix in invalid_prefixes):
            continue
        
        # KIỂM TRA 5: Xóa địa chỉ "Đã chết" không hợp lệ từ LLM
        if name in ("Father_ResidenceDomestic", "Mother_ResidenceDomestic"):
            if isinstance(value, dict):
                dia_chi = _fold(str(value.get("diaChi") or ""))
                tinh = str(value.get("tinh") or "").strip()
                xa = str(value.get("xa") or "").strip()
                # Nếu LLM tự thêm "Đã chết" nhưng không có tinh/xa → xóa
                if not tinh and not xa and ("da chet" in dia_chi or "chet" in dia_chi):
                    continue
        
        evidence = _CONTEXT_EVIDENCE_FIELDS.get(name) if context else None
        if evidence:
            tag, label = evidence
            ctx_value = _fold(_labeled_value(_section(context, tag), label))
            if not ctx_value or "khong xac dinh" in ctx_value or ctx_value == "khong co":
                continue
        if context and name.startswith("PreviousRegistration_") and not has_birth_source:
            continue
        if no_declaration and name.startswith("Requester_"):
            continue
        result.append(field)

    # ===== BƯỚC 4B: DỰNG LẠI CHA/MẸ BỊ LOẠI VÌ LỆCH TÊN =====
    # Chỉ vai mà tờ khai đã chốt tất định mới được dựng lại, và chỉ khi lý do loại duy nhất là
    # lệch tên. Đánh dấu default để extension tô vàng: hồ sơ đang có hai tên cho cùng một vai,
    # cán bộ phải soát lại chứ không nhận nguyên.
    rebuilt_prefixes: set[str] = set()
    if context:
        from app.pipelines.khai_sinh_dang_ky_lai.process.schema import COMPACT_COMP_BY_NAME

        for tag in ("cha", "me"):
            prefix = _ROLE_PREFIX[tag]
            if prefix not in mismatched_prefixes or prefix in broken_prefixes:
                continue
            rebuilt = _declaration_role_rebuild(context, tag)
            if not rebuilt:
                continue
            for name, value in rebuilt.items():
                comp = COMPACT_COMP_BY_NAME.get(name)
                if comp:
                    result.append({"name": name, "comp": comp, "value": value, "default": True})
            rebuilt_prefixes.add(prefix)
    invalid_prefixes -= rebuilt_prefixes
    empty_prefixes |= rebuilt_prefixes

    # ===== BƯỚC 5: GIẤY TỜ TÙY THÂN CHA/MẸ LẤY THEO CCCD =====
    # Chạy CUỐI CÙNG để giá trị đọc thẳng từ tấm thẻ không bị bước lọc nào phía trên ghi đè.
    if context:
        result = _apply_identity_card_overrides(
            result, context, invalid_prefixes - empty_prefixes, empty_prefixes
        )

    # ===== BƯỚC 6: NƠI CƯ TRÚ CHA/MẸ LẤY THEO TỜ KHAI =====
    # Chạy sau BƯỚC 5 vì hai bước không giẫm ô nhau: bước trên chốt ba ô giấy tờ tùy thân theo
    # CCCD, bước này chốt ô nơi cư trú theo tờ khai — đúng thứ tự nguồn đã quy định.
    if context:
        result = _apply_declaration_residence_overrides(
            result, context, invalid_prefixes - empty_prefixes
        )

    # ===== BƯỚC 7: NGÀY CẤP/NƠI CẤP THEO MRZ MẶT SAU THẺ =====
    # Chạy sau BƯỚC 5: mặt sau ghép bằng số định danh in trong MRZ chắc hơn mọi cách ghép theo
    # vị trí trang, và là căn cứ duy nhất cho CON (BƯỚC 5 chỉ chốt cha/mẹ).
    if context:
        result = _apply_mrz_issue_overrides(result, context)

    return result


async def build_context(documents: list[dict], options: dict | None = None) -> str:
    """OCR docs -> text phân vai đã qua kiểm tra tất định."""
    if not documents:
        return ""
    messages = [
        {"role": "system", "content": _ROLE_PROMPT},
        {"role": "user", "content": _build_user_content(documents, options)},
    ]
    raw = await client.chat(
        messages,
        max_tokens=_REASON_MAX_TOKENS,
        temperature=0,
        enable_thinking=settings.agent_reasoning,
    )
    return _render_context(raw, options, documents)
