"""Map compact TTHN facts to legacy x-* UI fields."""

import difflib
import json
import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from app.pipelines.xac_nhan_tthn.process.schema import UI_ALIASES, UI_COMP_BY_NAME

from app.pipelines._shared.compact_agent.issuer import (
    ISSUER_BO_CONG_AN,
    ISSUER_CUC,
    default_issuer,
    id_doc_type,
    normalize_issuer,
)
from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.formatting import normalize_date, prefer_printed_street, upper_person_name
from app.locations.catalog import names_by_code
from app.monitor import recorder as mon
from app.pipelines._shared.ethnic_normalize import normalize_ethnic

_DEFAULT_PURPOSE = "Sử dụng vào mục đích khác"

# Cấu hình theo tài khoản: phường Hiệp Hòa (Bắc Ninh) coi NGƯỜI ỦY QUYỀN là người yêu cầu (mục I,
# quan hệ "Bản thân") khi tờ khai không ghi riêng người yêu cầu; nơi khác mục I vẫn là người được
# ủy quyền đi nộp. Mapper không biết tài khoản nên router (Auto Fill) và pipeline_runner (Handfree)
# gọi with_account_process_options để server tự đặt cờ; cờ luôn bị ghi đè theo tài khoản, client
# không tự bật được cho xã khác.
PROCEDURE_KEY = "xac-nhan-tinh-trang-hon-nhan"
GRANTOR_AS_REQUESTER_OPTION = "grantorAsRequester"
_WARD_PREFIXES = ("xa ", "phuong ", "thi tran ")


def is_bac_ninh_hiep_hoa(user: dict | None) -> bool:
    """True khi tài khoản thuộc phường Hiệp Hòa, Bắc Ninh ("Tỉnh"/"Thành phố Bắc Ninh" đều khớp).

    Xã khớp ĐÚNG tên sau khi bỏ tiền tố (catalog cũ còn ghi "Xã Hiệp Hòa") để không dính nơi khác
    có tên chứa "Hiệp Hòa".
    """
    if not user:
        return False
    tinh = _fold(user.get("tinh") or "")
    xa = _fold(user.get("xa") or "")
    for prefix in _WARD_PREFIXES:
        if xa.startswith(prefix):
            xa = xa[len(prefix):].strip()
            break
    return "bac ninh" in tinh and xa == "hiep hoa"


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Trả bản sao options với cờ người ủy quyền = người yêu cầu do server quyết theo tài khoản."""
    result = dict(options or {})
    result.pop(GRANTOR_AS_REQUESTER_OPTION, None)
    if procedure == PROCEDURE_KEY and is_bac_ninh_hiep_hoa(user):
        result[GRANTOR_AS_REQUESTER_OPTION] = True
    return result


def grantor_as_requester(options: dict | None) -> bool:
    return (options or {}).get(GRANTOR_AS_REQUESTER_OPTION) is True

# Nhãn nguyên văn 6 option "Tình trạng hôn nhân" của cổng, khoá theo MÃ option. Cùng bảng với
# app/pipelines/ket_hon/process/mapper.py (_TINH_TRANG_HON_NHAN) — kể cả khoảng trắng lạ trước
# dấu "…" thứ tư của option 5, đã đối chiếu với DOM thật; sửa cho "gọn" là không khớp option nữa.
_TINH_TRANG_HON_NHAN: dict[str, str] = {
    "1": "Hiện tại đang có vợ/chồng",
    "2": "Hiện tại chưa đăng ký kết hôn với ai",
    "3": "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng đã ly hôn; hiện tại chưa đăng ký kết hôn với ai",
    "4": "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng vợ/chồng đã chết; hiện tại chưa đăng ký kết hôn với ai",
    "5": "Từ ngày… tháng… năm… đến ngày… tháng… năm … chưa đăng ký kết hôn với ai; hiện tại đang có vợ/chồng",
    "6": "Khác",
}
_MARRIED = "1"
_NEVER_MARRIED = "2"
_DIVORCED = "3"
_WIDOWED = "4"
_PERIOD_MARRIED = "5"

def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _date_key(value) -> tuple | None:
    """dd/mm/yyyy -> tuple so sánh được; sai định dạng trả None (không kết luận)."""
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(value or "").strip())
    if not match:
        return None
    day, month, year = match.groups()
    return (int(year), int(month), int(day))


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


# Option "6 = Khác" CỐ Ý không nằm trong bảng tra ngược: chọn nó thì cổng bắt điền thêm ô mô tả
# mà ta không có gì để điền → dropdown đã chọn kèm ô trống bắt buộc, tệ hơn là để trống cho cán
# bộ tự chọn. Không nhận ra thì trả None để còn cơ hội suy từ bản án/giấy chứng tử.
_STATUS_CODE_BY_LABEL = {
    _fold(label): code for code, label in _TINH_TRANG_HON_NHAN.items() if code != "6"
}
# "hiện tại" là chữ chốt: nhãn option 3/4 cũng có cụm "đã có vợ/chồng" nhưng nói về QUÁ KHỨ.
_NOW_MARRIED_MARKERS = (
    "hien tai dang co", "hien tai co vo", "hien tai co chong", "hien tai da ket hon",
    "hien nay dang co", "hien nay co vo", "hien nay co chong", "hien nay da ket hon",
    "dang co vo", "dang co chong",
)
_WIDOW_MARKERS = ("da chet", "da qua doi", "da mat", "goa")
_NEVER_MARRIED_MARKERS = (
    "chua dang ky ket hon", "chua ket hon", "chua co vo", "chua co chong", "doc than",
)


def _status_code(value) -> str | None:
    """Chữ tình trạng hôn nhân (LLM đọc từ tờ khai) -> MÃ option "1".."5"; không chắc -> None.

    VÌ SAO KHÔNG SO BẰNG `==` VỚI NHÃN: bản cũ so nguyên văn với bốn nhãn dài của cổng, nên LLM
    trả rút gọn ("Đã ly hôn"), thừa một dấu chấm cuối, hay đổi cách diễn đạt là phép so trượt —
    mà khối phát field lại xếp `if/elif` nên lượt đó bị "ăn" luôn, không rơi xuống được nhánh
    đọc từ bản án/giấy chứng tử: ô tình trạng hôn nhân LẪN số bản án cùng trắng, không một dòng
    log. Quy về MÃ trước rồi mới phát, và trả None khi không chắc để chỗ gọi đi tiếp xuống fallback.

    Khớp nguyên văn nhãn cổng trước, rồi mới tới từ khoá. Thứ tự từ khoá KHÔNG được đảo: nhãn
    option 3 và 4 đều kết thúc bằng "hiện tại chưa đăng ký kết hôn với ai" nên phải xét "ly
    hôn"/"đã chết" trước "chưa đăng ký"; còn ca "đã ly hôn RỒI CƯỚI LẠI" phải ra mã 1 nên dấu
    hiệu "hiện tại đang có vợ/chồng" xét trước cả hai.
    """
    folded = _fold(value)
    if not folded:
        return None
    exact = _STATUS_CODE_BY_LABEL.get(folded)
    if exact:
        return exact

    now_married = any(marker in folded for marker in _NOW_MARRIED_MARKERS)
    if now_married and "tu ngay" in folded and "den" in folded:
        return _PERIOD_MARRIED
    if now_married:
        return _MARRIED
    if "ly hon" in folded:
        return _DIVORCED
    if any(marker in folded for marker in _WIDOW_MARKERS):
        return _WIDOWED
    if any(marker in folded for marker in _NEVER_MARRIED_MARKERS):
        return _NEVER_MARRIED

    logging.getLogger(__name__).warning(
        "xac_nhan_tthn: khong nhan ra tinh trang hon nhan %r -- bo qua de suy tu giay to", value)
    return None


def _drop_empty(detail: dict) -> dict:
    """Bỏ khoá rỗng của một vùng x-select-area: điền được mảnh nào hay mảnh đó."""
    return {key: value for key, value in detail.items() if value not in (None, "")}


def _normalize_commune_label(value) -> str:
    """Mở rộng viết tắt đơn vị hành chính để khớp option trên cổng."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    for pattern, prefix in (
        (r"^p(?:\.\s*|\s+)(.+)$", "Phường"),
        (r"^x(?:\.\s*|\s+)(.+)$", "Xã"),
    ):
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if match:
            return f"{prefix} {match.group(1).strip()}"
    return text


def _id_doc_type_for(number, issuer) -> str:
    """Loại giấy tờ tùy thân theo SỐ: 9 chữ số là CMND cũ, CCCD/Căn cước luôn 12 chữ số.

    Số 12 chữ số (hoặc chưa rõ) mới phân loại tiếp theo nơi cấp (Bộ Công an → "Thẻ căn cước",
    Cục Cảnh sát → "Căn cước công dân"). Nhãn "Chứng minh nhân dân" giống option của eForm hộ tịch
    đang dùng ở trích lục.
    """
    if len(_digits(number)) == 9:
        return "Chứng minh nhân dân"
    return id_doc_type("Căn cước công dân", issuer or "")


def _is_self_request(options: dict | None, cccd_name, cccd_id) -> bool:
    """Người yêu cầu có TRÙNG người trên CCCD upload không?

    So với tên + CCCD mà cổng đã điền sẵn cho NGƯỜI YÊU CẦU (formContext, lấy từ VNeID).
    Ưu tiên số căn cước; thiếu thì so tên (bỏ dấu). Thiếu cả hai → mặc định coi là bản thân
    (giữ hành vi cũ, an toàn cho ca tự làm phổ biến).
    """
    ctx = (options or {}).get("formContext") or {}
    applicant_id = _digits(ctx.get("applicantIdentityNumber"))
    upload_id = _digits(cccd_id)
    if applicant_id and upload_id:
        return applicant_id == upload_id
    applicant_name = _fold(ctx.get("applicantFullname"))
    upload_name = _fold(cccd_name)
    if applicant_name and upload_name:
        return applicant_name == upload_name
    return True


# Vai HÀNH CHÍNH của cán bộ trên giấy tờ — KHÔNG phải quan hệ nhân thân của người đi xin giấy.
# Giấy XÁC NHẬN TTHN đã cấp mở đầu bằng "Xét đề nghị của ông/bà: <tên>, là công chức tư pháp hộ
# tịch..." — đó là CÁN BỘ đề nghị cấp giấy, không phải người yêu cầu. Agent rất hay bắt nhầm dòng
# này thành ToKhaiYeuCau_*, kéo theo mục I mang tên cán bộ mà số định danh lại của người được cấp.
_OFFICER_RELATION_MARKERS = (
    "cong chuc", "can bo", "chuyen vien", "tu phap ho tich", "ho tich",
    "uy ban nhan dan", "ubnd", "chu tich", "nguoi ky",
)


def _is_officer_relation(value) -> bool:
    """Chữ ở dòng quan hệ là chức danh cán bộ chứ không phải quan hệ nhân thân."""
    folded = _fold(value)
    return bool(folded) and any(marker in folded for marker in _OFFICER_RELATION_MARKERS)


_SELF_RELATION_WORDS = ("ban than", "tu khai")


def _classify_relation(value) -> str | None:
    """Quy đổi CHỮ trên tờ khai (dòng "Quan hệ với người được cấp...") sang mã radio cổng.

    "1" = Bản thân, "2" = Khác (bố/mẹ/con/vợ/chồng/anh/chị/em/cháu/... — bất kỳ chữ nào KHÁC
    "Bản thân"/"Tự khai"). Tờ khai không ghi dòng này thì trả None để caller lùi về so tên/CCCD.
    """
    folded = _fold(value)
    if not folded:
        return None
    if any(word in folded for word in _SELF_RELATION_WORDS):
        return "1"
    return "2"


_CCCD_LEN = 12          # số định danh cá nhân luôn đúng 12 chữ số
_ID_OCR_SLIP_MAX = 2    # số chữ số OCR được phép đọc thừa/thiếu so với thẻ


def _is_subsequence(short: str, long: str) -> bool:
    """`short` có phải `long` sau khi XÓA bớt vài ký tự (giữ nguyên thứ tự) không."""
    it = iter(long)
    return all(ch in it for ch in short)


def _is_ocr_slip_of_card(left_digits: str, right_digits: str) -> bool:
    """Hai chuỗi số là CÙNG một số trên thẻ, chỉ khác vì OCR đọc RƠI (hoặc nhân đôi) vài chữ số.

    Tờ khai viết tay hay bị OCR nuốt mất một chữ số: "046175013623" ra "04617503623". Chuỗi thiếu
    số đó không phải số định danh hợp lệ của BẤT KỲ ai (không đủ 12 chữ số), nên coi nó là số của
    một người khác là vô nghĩa — nhưng so bằng `==` thì nó vẫn "khác số" và kéo theo cả mục I:
    tên viết tay sai được giữ lại, ô quan hệ tick "Khác", và ô số định danh nhận 11 chữ số mà cổng
    chắc chắn từ chối.

    Chỉ nhận khi một bên là số thẻ ĐỦ 12 chữ số và chuỗi ngắn hơn nằm gọn trong nó theo đúng thứ
    tự (chỉ XÓA, không đổi chữ số nào) — lệch tối đa 2 chữ số. Ràng buộc này rất chặt: một số 11
    chữ số ngẫu nhiên chỉ có cỡ 12 phần 10^11 cơ hội lọt qua, nên không thể vô tình ghép nhân thân
    của hai người khác nhau. OCR đọc NHẦM chữ số (5 thành 6) vẫn bị coi là khác người như cũ.
    """
    short, long = sorted((left_digits, right_digits), key=len)
    if len(long) != _CCCD_LEN or len(short) == _CCCD_LEN:
        return False
    if not 0 < len(long) - len(short) <= _ID_OCR_SLIP_MAX:
        return False
    return _is_subsequence(short, long)


def _id_match(left, right) -> bool | None:
    """Hai số định danh có cùng một người không; thiếu một bên → None (không kết luận)."""
    left_digits, right_digits = _digits(left), _digits(right)
    if not (left_digits and right_digits):
        return None
    if left_digits == right_digits:
        return True
    return True if _is_ocr_slip_of_card(left_digits, right_digits) else False


def _is_one_digit_misread(left, right) -> bool:
    """Hai số 12 chữ số chỉ lệch ĐÚNG MỘT vị trí — dấu hiệu OCR đọc nhầm một chữ số viết tay.

    Cố ý KHÔNG gộp vào `_id_match`: ở đó đọc nhầm chữ số vẫn tính là khác người (quyết định quan
    hệ, mượn tên). Hàm này chỉ dùng kèm một bằng chứng độc lập khác (năm sinh / họ) ở chỗ gọi.
    """
    left_digits, right_digits = _digits(left), _digits(right)
    if len(left_digits) != _CCCD_LEN or len(right_digits) != _CCCD_LEN:
        return False
    return sum(a != b for a, b in zip(left_digits, right_digits)) == 1


def _birth_year(value) -> int | None:
    key = _date_key(value)
    if key:
        return key[0]
    match = re.search(r"\b(19|20)\d{2}\b", str(value or ""))
    return int(match.group(0)) if match else None


def _family_name(value) -> str:
    parts = _fold(value).split()
    return parts[0] if parts else ""


def _name_match(left, right) -> bool | None:
    """Hai họ tên có trùng không (bỏ dấu, gộp khoảng trắng); thiếu một bên → None."""
    left_name, right_name = _fold(left), _fold(right)
    if left_name and right_name:
        return left_name == right_name
    return None


def _is_foreign_area(area) -> bool:
    """Dia chi nay o NUOC NGOAI (quoc gia khac Viet Nam)."""
    if not isinstance(area, dict):
        return False
    quoc_gia = _fold(area.get("quocGia"))
    return bool(quoc_gia) and quoc_gia not in ("viet nam", "vietnam", "vn")


_CARD_PREFIXES = ("NguoiDuocCap_", "NguoiYeuCau_")


def _card_prefix_for(values: dict, khai_sdd) -> str | None:
    """Nhóm thẻ (NguoiDuocCap_/NguoiYeuCau_) có số định danh khớp số ``khai_sdd`` ghi ở giấy khác."""
    for prefix in _CARD_PREFIXES:
        if _id_match(khai_sdd, values.get(f"{prefix}SoDinhDanh")) is True:
            return prefix
    return None


def _has_card(values: dict, prefix: str) -> bool:
    return bool(values.get(f"{prefix}SoDinhDanh") or values.get(f"{prefix}HoTen"))


def _move_card(values: dict, source: str, target: str) -> None:
    for key in [k for k in values if k.startswith(source)]:
        values[target + key[len(source):]] = values.pop(key)


def _name_similarity(left, right) -> float:
    left_name, right_name = _fold(left), _fold(right)
    if not (left_name and right_name):
        return 0.0
    return difflib.SequenceMatcher(None, left_name, right_name).ratio()


# Hai tên cùng một người mà OCR lệch vài chữ ("Phan Thị Hiền" / "PHẠM THỊ HIỀN") vẫn trên mức này.
_SAME_NAME_RATIO = 0.8
# Dưới mức này là tên của hai người khác nhau hẳn.
_OTHER_NAME_RATIO = 0.6


def _route_cards(values: dict) -> None:
    """Đưa thẻ về đúng nhóm người khi SỐ ĐỊNH DANH (hoặc tên người ủy quyền) cho thấy LLM đặt nhầm.

    Mapper đọc NguoiDuocCap_* cho mục II và NguoiYeuCau_* cho người đi nộp. Chỉ chuyển khi có bằng
    chứng về chủ thẻ; thiếu bằng chứng thì giữ nguyên.
    """
    poa_id = values.get("PoA_SubjectIdNumber")
    subject_ids = [poa_id, values.get("ToKhai_SoDinhDanh")]
    requester_ids = []
    if _id_match(values.get("ToKhaiYeuCau_SoDinhDanh"), values.get("ToKhai_SoDinhDanh")) is not True:
        requester_ids.append(values.get("ToKhaiYeuCau_SoDinhDanh"))

    def is_subject(card_id) -> bool:
        return any(_id_match(card_id, x) is True for x in subject_ids) or _is_one_digit_misread(card_id, poa_id)

    def is_requester(card_id) -> bool:
        return any(_id_match(card_id, x) is True for x in requester_ids)

    poa_name = values.get("PoA_SubjectName")
    if _has_card(values, "NguoiDuocCap_") and _has_card(values, "NguoiYeuCau_"):
        # Hai thẻ bị đặt NGƯỢC: thẻ ở nhóm người đi nộp mới là của người được cấp. Giấy ủy quyền
        # hay không ghi số, khi đó nhận người ủy quyền theo tên.
        swapped_by_id = (is_subject(values.get("NguoiYeuCau_SoDinhDanh"))
                         and not is_subject(values.get("NguoiDuocCap_SoDinhDanh")))
        swapped_by_name = bool(
            poa_name and not _digits(poa_id)
            and _name_similarity(values.get("NguoiYeuCau_HoTen"), poa_name) >= _SAME_NAME_RATIO
            and _name_similarity(values.get("NguoiDuocCap_HoTen"), poa_name) < _SAME_NAME_RATIO
        )
        if swapped_by_id or swapped_by_name:
            _move_card(values, "NguoiDuocCap_", "_Swap_")
            _move_card(values, "NguoiYeuCau_", "NguoiDuocCap_")
            _move_card(values, "_Swap_", "NguoiYeuCau_")
        return
    subject_card = _digits(values.get("NguoiDuocCap_SoDinhDanh"))
    if subject_card and not _has_card(values, "NguoiYeuCau_") and not is_subject(subject_card):
        # Thẻ người đi nộp hồ sơ ủy quyền, hoặc thẻ người khai hộ, bị đặt vào nhóm người được cấp.
        if is_requester(subject_card) or (_digits(poa_id) and _id_match(subject_card, poa_id) is False):
            _move_card(values, "NguoiDuocCap_", "NguoiYeuCau_")
            return
    requester_card = _digits(values.get("NguoiYeuCau_SoDinhDanh"))
    if requester_card and not _has_card(values, "NguoiDuocCap_") and not is_requester(requester_card):
        # Thẻ duy nhất của hồ sơ không ủy quyền, hoặc thẻ đúng số người ủy quyền: là người được cấp.
        if is_subject(requester_card) or not values.get("PoA_SubjectName"):
            _move_card(values, "NguoiYeuCau_", "NguoiDuocCap_")


# Nơi cấp → ngày cấp của cùng tờ giấy.
_ISSUER_DATE_FIELDS = {
    "NguoiDuocCap_NoiCap": "NguoiDuocCap_NgayCap",
    "NguoiYeuCau_NoiCap": "NguoiYeuCau_NgayCap",
    "ToKhai_NoiCapGiayTo": "ToKhai_NgayCapGiayTo",
    "ToKhaiYeuCau_NoiCapGiayTo": "ToKhaiYeuCau_NgayCapGiayTo",
    "PoA_SubjectIssuer": "PoA_SubjectIdDate",
}
# Thẻ căn cước mẫu mới (Bộ Công an cấp) chỉ có từ ngày này.
_BO_CONG_AN_FROM = (2024, 7, 1)


def _normalize_issuers(values: dict) -> None:
    """Nơi cấp về tên cơ quan chuẩn của dropdown/ô nhập.

    LLM hay chép nguyên văn viết tắt trên thẻ ("CCSQLHC.V.TTXH", "Cục Trưởng cục cảnh sát") hoặc
    đoán "Bộ Công an" cho thẻ CCCD cũ. Thẻ cấp trước 01/7/2024 chỉ có thể do Cục Cảnh sát cấp.
    """
    for issuer_field, date_field in _ISSUER_DATE_FIELDS.items():
        if not values.get(issuer_field):
            continue
        issuer = normalize_issuer(values[issuer_field])
        issued = _date_key(values.get(date_field))
        if issuer == ISSUER_BO_CONG_AN and issued and issued < _BO_CONG_AN_FROM:
            issuer = ISSUER_CUC
        values[issuer_field] = issuer


def _poa_subject_card(values: dict) -> dict:
    """Thẻ căn cước CỦA NGƯỜI ỦY QUYỀN (người cần giấy), gom từ NguoiDuocCap_* hoặc NguoiYeuCau_*.

    Nhận thẻ khi số trên thẻ khớp số trên giấy ủy quyền (trùng hẳn, hoặc OCR rơi/đọc nhầm một
    chữ số), hoặc giấy ủy quyền không ghi số, hoặc họ tên trên thẻ trùng họ tên người ủy quyền —
    giấy ủy quyền hay ghi/OCR sai vài chữ số CCCD trong khi thẻ là bản IN. Số khác hẳn và tên
    cũng khác (hoặc cùng tên nhưng ngày sinh khác) = thẻ của người khác → bỏ, không ghép nhân thân
    hai người.
    """
    poa_id = values.get("PoA_SubjectIdNumber")

    def same_name(card_name, card_dob) -> bool:
        if _name_match(card_name, values.get("PoA_SubjectName")) is not True:
            return False
        card_date, poa_date = _date_key(card_dob), _date_key(values.get("PoA_SubjectDoB"))
        return not (card_date and poa_date and card_date != poa_date)

    def belongs(card_id, card_name, card_dob) -> bool:
        if not _digits(card_id):
            return False
        if not _digits(poa_id):
            return True
        return (_id_match(card_id, poa_id) is True or _is_one_digit_misread(card_id, poa_id)
                or same_name(card_name, card_dob))

    if values.get("NguoiDuocCap_SoDinhDanh") and belongs(
            values.get("NguoiDuocCap_SoDinhDanh"),
            values.get("NguoiDuocCap_HoTen"), values.get("NguoiDuocCap_NgaySinh")):
        return {
            "HoTen": values.get("NguoiDuocCap_HoTen"),
            "SoDinhDanh": values.get("NguoiDuocCap_SoDinhDanh"),
            "NgaySinh": values.get("NguoiDuocCap_NgaySinh"),
            "GioiTinh": values.get("NguoiDuocCap_GioiTinh"),
            "DanToc": values.get("NguoiDuocCap_DanToc"),
            "NgayCap": values.get("NguoiDuocCap_NgayCap"),
            "NoiCap": values.get("NguoiDuocCap_NoiCap") or (
                default_issuer(values.get("NguoiDuocCap_NgayCap"))
                if values.get("NguoiDuocCap_NgayCap") else None),
            "NoiCuTru": _area(values.get("NguoiDuocCap_NoiCuTru")),
        }
    # Agent đôi khi đặt thẻ người ủy quyền vào nhóm người đi nộp (vd hồ sơ chỉ kèm đúng một thẻ): số
    # trùng hẳn số trên giấy ủy quyền (hoặc họ tên trùng người ủy quyền) mới nhận.
    if _digits(values.get("NguoiYeuCau_SoDinhDanh")) and (
            (_digits(poa_id) and _id_match(values.get("NguoiYeuCau_SoDinhDanh"), poa_id) is True)
            or same_name(values.get("NguoiYeuCau_HoTen"), values.get("NguoiYeuCau_NgaySinh"))):
        return {
            "HoTen": values.get("NguoiYeuCau_HoTen"),
            "SoDinhDanh": values.get("NguoiYeuCau_SoDinhDanh"),
            "NgaySinh": values.get("NguoiYeuCau_NgaySinh"),
            "NgayCap": values.get("NguoiYeuCau_NgayCap"),
            "NoiCap": values.get("NguoiYeuCau_NoiCap"),
            "NoiCuTru": _area(values.get("NguoiYeuCau_NoiCuTru")),
        }
    # Không có thẻ người ủy quyền: vẫn dùng địa chỉ in trên giấy của họ nếu agent chỉ trả riêng field
    # đó — trừ khi nhóm này mang số của người khác.
    if _digits(values.get("NguoiDuocCap_SoDinhDanh")):
        return {}
    return {"NoiCuTru": _area(values.get("NguoiDuocCap_NoiCuTru"))}


def _tk_is_poa_subject(values: dict) -> bool:
    """Khối ToKhai_* (mục II tờ khai) có phải chính NGƯỜI ỦY QUYỀN trên giấy ủy quyền không.

    Tờ khai viết tay: OCR hay đọc nhầm MỘT chữ số CCCD ("…3446" → "…3466") và cả tên
    ("Phạm Minh Kha" → "Phạm Nhung Khae"). Lệch đúng một chữ số chỉ được coi là cùng người
    khi có thêm bằng chứng độc lập: cùng năm sinh hoặc cùng họ.
    """
    poa_subject_name = values.get("PoA_SubjectName")
    tk_id = _digits(values.get("ToKhai_SoDinhDanh"))
    poa_id = _digits(values.get("PoA_SubjectIdNumber"))
    tk_year = _birth_year(values.get("ToKhai_NgaySinh"))
    poa_year = _birth_year(values.get("PoA_SubjectDoB"))
    tk_misread_poa_id = _is_one_digit_misread(tk_id, poa_id) and bool(
        (tk_year and poa_year and tk_year == poa_year)
        or (_family_name(values.get("ToKhai_HoTen"))
            and _family_name(values.get("ToKhai_HoTen")) == _family_name(poa_subject_name))
    )
    return bool(
        (_fold(values.get("ToKhai_HoTen"))
         and _fold(values.get("ToKhai_HoTen")) == _fold(poa_subject_name))
        or (tk_id and poa_id and tk_id == poa_id)
        or tk_misread_poa_id
    )


def _add_residence(add, prefix: str, area, default: bool = False) -> None:
    """Phat muc "Noi cu tru" cho mot nguoi (prefix = nyc / nxn).

    Dia chi o NUOC NGOAI phai tick "Khac" (radio "2") roi dien vao o nhap tu do, KHONG tick
    "Trong nuoc": nhanh trong nuoc chi co dropdown Tinh/Xa cua Viet Nam nen "Tokyo"/"Tam A"
    khong khop option nao -- hai dropdown do giu nguyen gia tri cong tu dien san (vd "Phuong
    Tu Liem / Ha Noi"), ra mot dia chi lai vua sai vua trong nhu that.
    """
    if not area:
        add(f"{prefix}NoiCuTru", "1", default=True)
        add(f"{prefix}NoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)
        return
    if _is_foreign_area(area):
        add(f"{prefix}NoiCuTru", "2")
        full_addr = ", ".join(
            part for part in (area.get("diaChi"), area.get("xa"), area.get("tinh")) if part
        )
        add(f"{prefix}NoiCuTru_NuocNgoai", {"quocGia": area.get("quocGia"), "diaChi": full_addr},
            default=default)
        return
    add(f"{prefix}NoiCuTru", "1")
    add(f"{prefix}NoiCuTru_TrongNuoc", area, default=default)


def _card_name_when_same_person(values: dict, khai_sdd, khai_ten=None) -> str | None:
    """Họ tên lấy theo THẺ CĂN CƯỚC khi tờ khai và thẻ nói về CÙNG MỘT CÁI TÊN.

    Tờ khai là bản VIẾT TAY nên OCR tên rất hay sai: rơi dấu hoặc đọc nhầm chữ ("Thiết" → "Thiệt",
    "Phượng" → "Phương", "Tú" → "Tí"). Thẻ căn cước là bản IN, đọc gần như chắc chắn đúng — và đây
    mới là tên phải khớp với CSDLQG về dân cư khi cổng đối chiếu.

    Bằng chứng duy nhất được chấp nhận là SỐ ĐỊNH DANH khớp — 12 chữ số, không phải phép so tên
    dễ đụng hàng. Thiếu số ở một bên hoặc số của hai người khác nhau thì giữ nguyên thứ tự nguồn
    cũ, KHÔNG đoán: mượn tên của người khác sang là ghép ra một nhân thân lai.

    Tên hai bên CHỈ KHÁC DẤU cũng là cùng một cái tên, nhưng KHÔNG dùng làm căn cứ ở đây: bản scan
    mờ thì OCR của chính tấm thẻ cũng đọc sai dấu, mà mapper chỉ thấy field đã trích, không còn tài
    liệu gốc nào để kiểm chứng bản nào mới đúng.
    """
    prefix = _card_prefix_for(values, khai_sdd)
    return values.get(f"{prefix}HoTen") or None if prefix else None


def _card_value_when_same_person(values: dict, khai_sdd, card_field: str):
    """Giá trị IN trên thẻ (ngày sinh, giới tính…) khi số định danh tờ khai trùng số trên thẻ.

    Cùng căn cứ với `_card_name_when_same_person`: chữ viết tay hay bị OCR đọc sai ("02/05" →
    "21/05"), còn thẻ là bản in đúng CSDLQG. Không trùng số → None, caller giữ thứ tự nguồn cũ.
    """
    prefix = _card_prefix_for(values, khai_sdd)
    return values.get(f"{prefix}{card_field}") or None if prefix else None


def _card_id_when_id_matches(values: dict, khai_sdd):
    """Số định danh điền vào form: số 12 chữ số IN trên thẻ thắng số đọc từ tờ khai.

    Cùng lý do như `_card_name_when_same_person`, và ở đây còn bắt buộc: số đọc từ tờ khai chỉ khác
    số trên thẻ khi OCR rơi mất chữ số (xem `_is_ocr_slip_of_card`), tức là một chuỗi KHÔNG đủ 12
    chữ số — điền vào cổng là chắc chắn bị chặn. Không khớp thẻ thì giữ nguyên số trên tờ khai.
    """
    prefix = _card_prefix_for(values, khai_sdd)
    return values.get(f"{prefix}SoDinhDanh") or khai_sdd if prefix else khai_sdd


def _same_person(left_name, left_id, right_name, right_id) -> bool:
    """Hai khối khai có phải CÙNG một người không. Số định danh chốt trước, rồi mới tới tên.

    Thiếu dữ kiện ở một bên → False: chỗ gọi dùng hàm này để MƯỢN dữ liệu từ khối kia, mượn nhầm
    ra nhân thân lai hai người nên phải im lặng bỏ qua thay vì đoán.
    """
    by_id = _id_match(left_id, right_id)
    if by_id is not None:
        return by_id
    return _name_match(left_name, right_name) is True


def _relation_code(req_name, req_id, subject_name, subject_id, declared, fallback_self: bool) -> str | None:
    """Mã ô tích "(5) Quan hệ với người được cấp Giấy XNTTHN": "1" = Bản thân, "2" = Khác.

    Chốt bằng chính hai người ĐANG được điền vào form: mục I (người yêu cầu) so với mục II
    (người được cấp). Trùng người → "Bản thân"; khác người → "Khác" (caller điền thêm chữ
    quan hệ vào ô cạnh option). Thứ tự bằng chứng:

    1. SỐ ĐỊNH DANH — mạnh nhất; hai bên đều có số thì chốt theo số, kể cả khi tên trùng
       (trùng tên khác số là hai người khác nhau, rất phổ biến với tên Việt).
    2. CHỮ QUAN HỆ trên tờ khai (chỉ khi khối "người yêu cầu" đáng tin) — dùng khi thiếu số
       ở một bên, vì lời khai chính chủ đáng tin hơn phép so tên.
    3. HỌ TÊN — chốt cuối khi không có số lẫn chữ quan hệ.
    4. Không có dữ kiện nào → "1" nếu người yêu cầu chính là tài khoản VNeID đang đăng nhập
       (fallback_self), ngược lại None để người dùng tự chọn.
    """
    by_id = _id_match(req_id, subject_id)
    if by_id is not None:
        return "1" if by_id else "2"
    declared_code = _classify_relation(declared)
    if declared_code:
        return declared_code
    by_name = _name_match(req_name, subject_name)
    if by_name is not None:
        return "1" if by_name else "2"
    return "1" if fallback_self else None


# Tick "Khác" là cổng bắt buộc điền chữ quan hệ vào ô kẻ chấm ngay cạnh. Khi hồ sơ chỉ chứng minh
# được "hai người khác nhau" mà không nói quan hệ gì (không tờ khai, hoặc OCR rơi mất dòng quan
# hệ), không có cách nào suy ra quan hệ thật → điền chữ trung tính và đánh dấu default để
# extension tô VIỀN VÀNG cho người dùng sửa lại.
_RELATION_OTHER_FALLBACK = "Người thân"
# Có giấy ủy quyền thì quan hệ suy ra được từ chính tờ giấy, không phải đoán.
_RELATION_OTHER_POA = "Người được ủy quyền"


_RELATION_OTHER_PREFIX_RE = re.compile(r"^(?:là|la)\s+", re.IGNORECASE)


def _relation_other_text(value) -> str:
    """Chữ điền vào ô nhập cạnh option "Khác" của mục quan hệ.

    Giữ nguyên chữ trên tờ khai, chỉ dọn nhiễu OCR của dòng kẻ chấm và bỏ tiền tố "là"
    (nhãn trên cổng đã là "Khác:" nên "là con đẻ" → "Con đẻ"). Quan hệ là bản thân →
    trả "" để không điền gì vào ô "Khác".
    """
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(r"[\s.·•…\-–—]+$", "", text).strip()
    text = _RELATION_OTHER_PREFIX_RE.sub("", text).strip()
    if not text or any(word in _fold(text) for word in _SELF_RELATION_WORDS):
        return ""
    return text[:1].upper() + text[1:]


def _area(value):
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or "",
        "xa": _normalize_commune_label(
            value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or ""
        ),
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    remapped = remap_area(out)
    if isinstance(remapped, dict):
        remapped = {**remapped, "xa": _normalize_commune_label(remapped.get("xa"))}
    return remapped


# =========================================================
# TÀI KHOẢN ĐĂNG NHẬP CỔNG (formContext) — nguồn chuẩn nhất cho người trùng tài khoản
# =========================================================
# Extension đọc từ mục I cổng điền sẵn theo VNeID. Mọi khoá đều tuỳ chọn: bản cũ chỉ gửi tên + số.
_ACCOUNT_KEYS = {
    "HoTen": "applicantFullname",
    "SoDinhDanh": "applicantIdentityNumber",
    "NgaySinh": "applicantBirthday",
    "GioiTinh": "applicantGender",
    "DanToc": "applicantEthnicity",
    "NgayCap": "applicantIdDate",
    "NoiCap": "applicantIdIssuer",
    "NoiCuTru": "applicantAddress",
}


_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=None)
def _moj_catalog(name: str) -> dict[str, str]:
    """Danh mục mã → tên của eForm Bộ Tư pháp (dữ liệu VNeID trên cổng lưu dân tộc/giới tính bằng MÃ)."""
    rows = json.loads((_DATA_DIR / name).read_text(encoding="utf-8"))
    return {str(row["Ma"]).strip(): re.sub(r"\s+", " ", str(row["Ten"])).strip() for row in rows}


def _catalog_label(value, catalog: str) -> str:
    """Giá trị là MÃ danh mục thì đổi ra tên; không phải mã thì giữ nguyên chữ."""
    text = str(value or "").strip()
    return _moj_catalog(catalog).get(text, text) if text.isdigit() else text


def _gender_label(value) -> str:
    folded = _fold(value)
    if folded in ("nam", "male", "m", "1"):
        return "Nam"
    if folded in ("nu", "female", "f", "0", "2"):
        return "Nữ"
    return ""


def account_context(options: dict | None) -> dict:
    """Thông tin tài khoản đăng nhập cổng từ options.formContext, đã chuẩn hoá; rỗng nếu không có."""
    ctx = (options or {}).get("formContext") or {}
    if not isinstance(ctx, dict):
        return {}
    out = {}
    for key, ctx_key in _ACCOUNT_KEYS.items():
        value = ctx.get(ctx_key)
        if key == "NoiCuTru":
            if isinstance(value, dict):
                # Dữ liệu VNeID trên cổng lưu tỉnh/xã bằng MÃ danh mục hành chính.
                tinh, xa = names_by_code(value.get("tinh"), value.get("xa"))
                value = {**value, "tinh": tinh or value.get("tinh"), "xa": xa or value.get("xa")}
            area = _area(value) if isinstance(value, dict) else None
            if area:
                out[key] = area
            continue
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if not text:
            continue
        if key == "SoDinhDanh":
            text = _digits(text)
        elif key in ("NgaySinh", "NgayCap"):
            text = normalize_date(text)
            if not _date_key(text):
                continue
        elif key == "GioiTinh":
            text = _gender_label(_catalog_label(text, "moj_eform_gioi_tinh.json"))
        elif key == "DanToc":
            text = _catalog_label(text, "moj_eform_dan_toc.json")
        elif key == "NoiCap":
            text = normalize_issuer(text)
        if text:
            out[key] = text
    return out


def _is_account_person(account: dict, name, id_number, birthday) -> bool:
    """Khối nhân thân (tên, số, ngày sinh đã điền) có phải CHÍNH chủ tài khoản không.

    Số trùng hẳn là đủ (tên lệch là do OCR). Số lệch vì OCR (rơi/thừa chữ số, sai đúng một chữ số)
    phải kèm tên gần giống. Số trên tờ khai viết tay có khi lệch 2–3 chữ số: khi đó cần tên trùng
    (bỏ dấu) VÀ cùng ngày sinh. Khối không có số thì cần tên gần giống VÀ cùng ngày sinh — chỉ giống
    tên thì không đủ vì tên Việt trùng nhau rất nhiều.
    """
    account_id, block_id = account.get("SoDinhDanh"), _digits(id_number)
    account_dob, block_dob = _date_key(account.get("NgaySinh")), _date_key(birthday)
    same_dob = bool(account_dob and block_dob and account_dob == block_dob)
    similarity = _name_similarity(account.get("HoTen"), name)
    if account_id and block_id:
        if account_id == block_id:
            return True
        near_id = _id_match(account_id, block_id) is True or _is_one_digit_misread(account_id, block_id)
        if near_id and similarity >= _SAME_NAME_RATIO:
            return True
        return same_dob and _name_match(account.get("HoTen"), name) is True
    return same_dob and similarity >= _SAME_NAME_RATIO


# Ô của từng mục trên cổng → khoá tài khoản.
_ACCOUNT_SECTIONS = {
    "I": {"HoTen": "HoVaTenC", "SoDinhDanh": "SoDinhDanhC", "NgaySinh": "NgaySinhC",
          "NgayCap": "NgayCapDDC", "NoiCap": "NoiCapDDC", "prefix": "nyc",
          "id_twin": "SoGiayToTuyThanC", "id_type": "LoaiGiayToDinhDanhC"},
    "II": {"HoTen": "HoVaTenC1", "SoDinhDanh": "SoDinhDanhC1", "NgaySinh": "NgaySinhC1",
           "GioiTinh": "GioiTinhC1", "DanToc": "DanTocC1",
           "NgayCap": "NgayCapDDC1", "NoiCap": "NoiCapDDC1", "prefix": "nxn",
           "id_twin": "SoGiayToTuyThanC1", "id_type": "LoaiGiayToDinhDanhC1"},
}
_RELATION_FIELD = "quanhevoinguoiduocxacminh"


def _ui_field(name: str, value, default: bool = False) -> dict:
    if name == "DanTocC1":
        value = normalize_ethnic(value) or value
    field = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": value}
    if default:
        field["default"] = True
    if name in UI_ALIASES:
        field["aliases"] = UI_ALIASES[name]
    return field


def _apply_account(out: list[dict], options: dict | None) -> list[dict]:
    """Sau khi mapper đã chọn xong mục I/II: mục nào là CHÍNH chủ tài khoản thì điền lại theo tài khoản.

    Vai (ai là người yêu cầu, ai là người được cấp) vẫn do giấy tờ quyết định — tài khoản A mà hồ
    sơ là của B thì không đụng gì. Chỉ khi một mục đã điền trùng người tài khoản (xem
    `_is_account_person`) thì các ô tài khoản có giá trị mới ghi đè: dữ liệu VNeID là bản chuẩn
    CSDLQG, còn giấy tờ (nhất là tờ khai viết tay) hay bị OCR đọc sai. Mọi ô bị sửa ghi vào trace.
    """
    account = account_context(options)
    if not (account.get("HoTen") or account.get("SoDinhDanh")):
        return out
    index = {f["name"]: i for i, f in enumerate(out)}

    def current(name):
        i = index.get(name)
        return out[i]["value"] if i is not None else None

    def put(name, value, changes, section):
        if value in (None, "", {}):
            return
        field = _ui_field(name, value)
        i = index.get(name)
        if i is None:
            out.append(field)
            index[name] = len(out) - 1
            changes.append({"muc": section, "field": name, "cu": None, "moi": value})
        else:
            if out[i]["value"] != field["value"]:
                changes.append({"muc": section, "field": name, "cu": out[i]["value"], "moi": field["value"]})
            out[i] = field

    changes: list[dict] = []
    matched = []
    for section, names in _ACCOUNT_SECTIONS.items():
        if not current(names["HoTen"]) and not current(names["SoDinhDanh"]):
            continue
        if not _is_account_person(account, current(names["HoTen"]), current(names["SoDinhDanh"]),
                                  current(names["NgaySinh"])):
            continue
        matched.append(section)
        for key in ("HoTen", "SoDinhDanh", "NgaySinh", "GioiTinh", "DanToc", "NgayCap", "NoiCap"):
            if key in names and account.get(key):
                value = upper_person_name(account[key]) if key == "HoTen" else account[key]
                put(names[key], value, changes, section)
        if account.get("SoDinhDanh"):
            put(names["id_twin"], account["SoDinhDanh"], changes, section)
            put(names["id_type"], _id_doc_type_for(account["SoDinhDanh"], current(names["NoiCap"])),
                changes, section)
        if account.get("NoiCuTru"):
            prefix = names["prefix"]
            put(f"{prefix}NoiCuTru", "1", changes, section)
            put(f"{prefix}NoiCuTru_TrongNuoc", account["NoiCuTru"], changes, section)

    # Hai mục cùng là chủ tài khoản → cùng một người: "Bản thân" (số CCCD hai khối tờ khai lệch do
    # OCR từng làm mapper tick "Khác").
    if matched == ["I", "II"] and current(_RELATION_FIELD) != "1":
        i = index.get(_RELATION_FIELD)
        changes.append({"muc": "I", "field": _RELATION_FIELD, "cu": current(_RELATION_FIELD), "moi": "1"})
        if i is not None:
            out[i] = _ui_field(_RELATION_FIELD, "1")
        else:
            # Cổng dựng lại mục I khi đổi option quan hệ → radio phải đứng TRƯỚC khối nhân thân.
            first = min(index.get(n, len(out)) for n in _ACCOUNT_SECTIONS["I"].values() if n in index)
            out.insert(first, _ui_field(_RELATION_FIELD, "1"))
        out[:] = [f for f in out if f["name"] != "quanhekhac"]
    if changes:
        mon.output("account_override", changes)
    return out


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    """Derive deterministic UI fields for TTHN.

    Bốn trường hợp:

    A. BẢN THÂN (không có giấy ủy quyền, CCCD upload = người đăng nhập):
       - Mục I (người yêu cầu) = CCCD upload.
       - Mục II (người được xác nhận) = CCCD upload (cùng người).
       - Quan hệ = "1" (Bản thân).

    B. ỦY QUYỀN (có PoA_SubjectName từ giấy ủy quyền):
       - Người ủy quyền (Section I giấy ủy quyền) = người CẦN giấy → Mục II form.
       - Mục I: tờ khai ghi người yêu cầu thì theo tờ khai; không ghi thì Mục I = người được ủy
         quyền (người ĐI NỘP = CCCD upload), quan hệ = "2" (Khác: Người được ủy quyền).
         Riêng tài khoản phường Hiệp Hòa (cờ grantorAsRequester): Mục I CŨNG là người ủy quyền,
         quan hệ = "1" (Bản thân).

    C. THÂN NHÂN NỘP HỘ, KHÔNG giấy ủy quyền (tờ khai ghi RIÊNG khối "người yêu cầu" ở đầu tờ khai
       khác người ở Section II — vd con đứng khai hộ cha mẹ):
       - Mục I = khối "người yêu cầu" đầu tờ khai (ToKhaiYeuCau_*), ƯU TIÊN CAO NHẤT — không lấy
         nhầm sang thông tin người được cấp (ToKhai_*) như trước.
       - Mục II = người được cấp (ToKhai_*/NguoiDuocCap_*) như bình thường.
       - Quan hệ: "1" nếu số định danh/tên người yêu cầu trùng người được cấp, ngược lại "2"
         (Khác) kèm chữ quan hệ điền vào ô kẻ chấm cạnh option.

    D. CCCD-MISMATCH / KHÔNG có nguồn nào cho Mục I (không có khối người yêu cầu riêng, không có
       CCCD upload nào khớp):
       - Mục I: không đè (để cổng giữ thông tin người đăng nhập từ VNeID), chỉ set default loại cư trú.
       - Mục II = CCCD upload/tờ khai (người cần giấy).
       - Quan hệ: so mục I với mục II như case C ("1" khi cùng người, "2" khi khác người);
         không đủ dữ kiện cả hai phép so thì để trống (user tự chọn).
    """
    values = _by_name(fields)
    _route_cards(values)
    _normalize_issuers(values)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        if name == "DanTocC1":
            # MỌI nhánh (bản thân / ủy quyền / fallback tờ khai) phải đi qua bảng chuẩn hóa. Gửi
            # nguyên văn "K'Ho" thì dropdown của cổng không có option nào trùng, extension quay
            # sang khớp lỏng và bốc nhầm option ngắn ("Họ") vì dấu nháy là ranh giới từ.
            value = normalize_ethnic(value) or value
        field = {"name": name, "comp": comp, "value": value}
        if default:
            field["default"] = True  # extension tô VIỀN VÀNG (giá trị mặc định, không từ giấy tờ)
        if name in UI_ALIASES:
            field["aliases"] = UI_ALIASES[name]
        out.append(field)
        seen.add(name)

    def add_relation_other(declared, fallback: str = _RELATION_OTHER_FALLBACK) -> None:
        """Ô kẻ chấm cạnh option "Khác": chữ trên tờ khai, thiếu thì chữ trung tính (viền vàng).

        Ô này chỉ được cổng render SAU khi tick "Khác" nên luôn phát ngay sau radio quan hệ.
        """
        text = _relation_other_text(declared)
        add("quanhekhac", text or fallback, default=not text)

    has_card = _has_card(values, "NguoiDuocCap_") or _has_card(values, "NguoiYeuCau_")
    # Thẻ của NGƯỜI ĐI NỘP khác người được cấp (người được ủy quyền, người thân khai hộ).
    has_requester_card = _has_card(values, "NguoiYeuCau_")
    # Đây là TỜ KHAI, không phải ảnh CCCD → nhân thân có thể LLM chỉ đặt ở ToKhai_*.
    # Vẫn coi là có người để không rụng cả khối khi thiếu thẻ (xem cổng bên dưới).
    has_tokhai = bool(values.get("ToKhai_SoDinhDanh") or values.get("ToKhai_HoTen"))
    # Khối "người yêu cầu" ghi RIÊNG ở đầu tờ khai — CÓ THỂ khác người được cấp ở Section II
    # (thân nhân đứng nộp hộ mà không kèm giấy ủy quyền chính thức).
    # Khối "người yêu cầu" chỉ đáng tin khi nó THẬT SỰ đến từ tờ khai. TỜ KHAI luôn ghi giấy tờ tùy
    # thân của người yêu cầu ngay dưới tên ("CC/CCCD số ... cấp ngày ... tại ..."), nên một cái TÊN
    # TRƠ TRỌI — không số định danh, không ngày/nơi cấp, không cả dòng quan hệ — gần như luôn là tên
    # bắt nhầm ở tài liệu khác: cán bộ ký giấy XNTTHN cũ, người làm chứng, người ký thay.
    #
    # Không chặn thì mục I ra ĐÚNG MỘT CÁI TÊN: nhân thân của thẻ trong hồ sơ đã bị guard bên dưới
    # giữ lại (thẻ là của người khác), phần còn lại vẫn là dữ liệu VNeID của người đăng nhập → một
    # mục I lai ba nguồn. Chốt này KHÔNG dựa vào ToKhaiYeuCau_QuanHe vì agent hay bỏ hẳn field đó.
    declared_requester_evidence = any(
        values.get(name) for name in (
            "ToKhaiYeuCau_SoDinhDanh",
            "ToKhaiYeuCau_NgayCapGiayTo",
            "ToKhaiYeuCau_NoiCapGiayTo",
        )
    ) or bool(
        values.get("ToKhaiYeuCau_QuanHe")
        and not _is_officer_relation(values.get("ToKhaiYeuCau_QuanHe"))
    )
    # Dòng "Xét đề nghị của ông/bà ..." trên giấy XNTTHN ĐÃ CẤP là cán bộ tư pháp hộ tịch, không phải
    # người yêu cầu → bỏ hẳn khối này, để mục I lùi về CCCD trong hồ sơ.
    # Ghi "Bản thân" mà khối người yêu cầu không có số và mang tên khác hẳn người được cấp: khối
    # này bị ghép từ giấy khác (vd tên cán bộ ký giấy XNTTHN cũ khi hồ sơ không có tờ khai).
    declared_self_but_other = bool(
        _classify_relation(values.get("ToKhaiYeuCau_QuanHe")) == "1"
        and not values.get("ToKhaiYeuCau_SoDinhDanh")
        and _name_similarity(
            values.get("ToKhaiYeuCau_HoTen"),
            values.get("ToKhai_HoTen") or values.get("NguoiDuocCap_HoTen") or values.get("PoA_SubjectName"),
        ) < _OTHER_NAME_RATIO
    )
    has_declared_requester = bool(
        (values.get("ToKhaiYeuCau_HoTen") or values.get("ToKhaiYeuCau_SoDinhDanh"))
        and not _is_officer_relation(values.get("ToKhaiYeuCau_QuanHe"))
        and declared_requester_evidence
        and not declared_self_but_other
    )

    # --- Nơi cấp giấy tờ của người được cấp: thẻ → tờ khai → suy theo ngày cấp ---
    issuer = (
        values.get("NguoiDuocCap_NoiCap")
        or values.get("ToKhai_NoiCapGiayTo")
        or default_issuer(values.get("NguoiDuocCap_NgayCap") or values.get("ToKhai_NgayCapGiayTo"))
    )
    # Nơi cấp thẻ của người đi nộp — không mượn tờ khai vì tờ khai mục II là người khác.
    requester_issuer = values.get("NguoiYeuCau_NoiCap") or default_issuer(values.get("NguoiYeuCau_NgayCap"))
    nationality = values.get("NguoiDuocCap_QuocTich") or "Việt Nam"
    # Tờ khai phản ánh nơi cư trú hiện tại; giấy in chỉ là nguồn dự phòng.
    residence = _area(values.get("ToKhai_NoiCuTru") or values.get("NguoiDuocCap_NoiCuTru"))

    is_self = _is_self_request(options, values.get("NguoiDuocCap_HoTen"), values.get("NguoiDuocCap_SoDinhDanh"))

    # Phát hiện trường hợp ủy quyền: có PoA_SubjectName từ giấy ủy quyền
    poa_subject_name = values.get("PoA_SubjectName")
    has_poa = bool(poa_subject_name)
    declared_self = values.get("ToKhai_LaBanThan") is True or _fold(
        values.get("ToKhai_LaBanThan")
    ) in {"true", "1", "co"}

    # =========================================================
    # MỤC I & II cá nhân: chỉ điền khi có CCCD hoặc giấy ủy quyền
    # Không có CCCD + không có PoA → bỏ qua Mục I/II, vẫn điền tình trạng hôn nhân bên dưới
    # =========================================================
    # MỤC I & II: chỉ điền khi có CCCD hoặc giấy ủy quyền
    # Không có → bỏ qua thông tin cá nhân, vẫn điền tình trạng hôn nhân bên dưới
    # =========================================================
    if has_card or has_poa or has_tokhai or has_declared_requester:

        # --- MỤC I: Người yêu cầu ---
        # Ô "Quan hệ với người được xác minh" LUÔN được add() TRƯỚC khối nhân thân (HoVaTenC...):
        # cổng dựng lại Mục I mỗi khi đổi option quan hệ, tick SAU sẽ xóa mất dữ liệu vừa điền.
        if has_poa:
            # NGUOI YEU CAU = nguoi GHI TREN TO KHAI, khong phai nguoi cam ho so di nop.
            #
            # Giay uy quyen kieu "nop ho + ky thay" KHONG doi vai nguoi yeu cau: to khai van ghi
            # ten nguoi uy quyen o dong "Ho, chu dem, ten nguoi yeu cau" va quan he "Ban than".
            # Ban cu luon lay chu the CCCD upload lam muc I va luon tick "Khac", nen moi ho so co
            # uy quyen deu ra SAI NGUOI o muc I kem o tich sai -- ma nhin van hop le.
            tk_req_name = values.get("ToKhaiYeuCau_HoTen")
            req_is_subject = bool(
                tk_req_name and poa_subject_name
                and _fold(tk_req_name) == _fold(poa_subject_name)
            )
            if tk_req_name:
                relation_code_poa = _classify_relation(values.get("ToKhaiYeuCau_QuanHe")) or (
                    "1" if req_is_subject else "2"
                )
                add("quanhevoinguoiduocxacminh", relation_code_poa)
                if relation_code_poa == "2":
                    add_relation_other(values.get("ToKhaiYeuCau_QuanHe"), _RELATION_OTHER_POA)
                # Nguoi yeu cau CHINH LA nguoi duoc cap -> dung chung mot bo giay to voi muc II,
                # khong muon so ho chieu ghi tren to khai roi ghep voi loai giay to the can cuoc.
                if req_is_subject:
                    req_id = values.get("PoA_SubjectIdNumber") or values.get("ToKhaiYeuCau_SoDinhDanh")
                    req_ngay_cap = values.get("PoA_SubjectIdDate")
                    req_noi_cap = values.get("PoA_SubjectIssuer")
                else:
                    req_id = values.get("ToKhaiYeuCau_SoDinhDanh")
                    req_ngay_cap = values.get("ToKhaiYeuCau_NgayCapGiayTo")
                    req_noi_cap = values.get("ToKhaiYeuCau_NoiCapGiayTo")
                add("HoVaTenC", upper_person_name(
                    _card_name_when_same_person(values, req_id, tk_req_name) or tk_req_name))
                add("NgaySinhC",
                    _card_value_when_same_person(values, req_id, "NgaySinh")
                    or values.get("ToKhaiYeuCau_NgaySinh"))
                req_id = _card_id_when_id_matches(values, req_id)
                add("SoDinhDanhC", req_id)
                if req_id:
                    add("LoaiGiayToDinhDanhC",
                        _id_doc_type_for(req_id, req_noi_cap))
                add("SoGiayToTuyThanC", req_id)
                add("NgayCapDDC", req_ngay_cap)
                add("NoiCapDDC", req_noi_cap)
                add("nycLoaiCuTru", "Thường trú")
                residence_req = _area(values.get("ToKhaiYeuCau_NoiCuTru"))
            elif not grantor_as_requester(options):
                # To khai khong ghi nguoi yeu cau -> nguoi di nop dung ten minh, giu hanh vi cu.
                add("quanhevoinguoiduocxacminh", "2")
                add_relation_other(values.get("ToKhaiYeuCau_QuanHe"), _RELATION_OTHER_POA)
                add("HoVaTenC", upper_person_name(values.get("NguoiYeuCau_HoTen")))
                add("NgaySinhC", values.get("NguoiYeuCau_NgaySinh"))
                add("SoDinhDanhC", values.get("NguoiYeuCau_SoDinhDanh"))
                add("LoaiGiayToDinhDanhC",
                    _id_doc_type_for(values.get("NguoiYeuCau_SoDinhDanh"), requester_issuer))
                add("SoGiayToTuyThanC", values.get("NguoiYeuCau_SoDinhDanh"))
                add("NgayCapDDC", values.get("NguoiYeuCau_NgayCap"))
                if has_requester_card:
                    add("NoiCapDDC", requester_issuer)
                add("nycLoaiCuTru", "Thường trú")
                residence_req = _area(values.get("NguoiYeuCau_NoiCuTru"))
            else:
                # Chỉ tài khoản phường Hiệp Hòa (Bắc Ninh): tờ khai không ghi người yêu cầu (hồ sơ
                # chỉ có giấy ủy quyền + thẻ) thì người yêu cầu vẫn là NGƯỜI ỦY QUYỀN, người được
                # ủy quyền chỉ đi nộp thay. Mục I điền cùng người, cùng nguồn với mục II bên dưới,
                # quan hệ "Bản thân".
                add("quanhevoinguoiduocxacminh", "1")
                card = _poa_subject_card(values)
                tk_is_subject = _tk_is_poa_subject(values)
                req_id = card.get("SoDinhDanh") or values.get("PoA_SubjectIdNumber")
                req_noi_cap = (card.get("NoiCap") or values.get("PoA_SubjectIssuer")
                               or default_issuer(values.get("PoA_SubjectIdDate")))
                add("HoVaTenC", upper_person_name(
                    card.get("HoTen")
                    or _card_name_when_same_person(
                        values, values.get("PoA_SubjectIdNumber"), poa_subject_name)
                    or poa_subject_name))
                add("NgaySinhC", card.get("NgaySinh")
                    or (values.get("ToKhai_NgaySinh") if tk_is_subject else None)
                    or values.get("PoA_SubjectDoB"))
                add("SoDinhDanhC", req_id)
                if req_id:
                    add("LoaiGiayToDinhDanhC", _id_doc_type_for(req_id, req_noi_cap))
                add("SoGiayToTuyThanC", req_id)
                add("NgayCapDDC", card.get("NgayCap") or values.get("PoA_SubjectIdDate"))
                add("NoiCapDDC", req_noi_cap)
                add("nycLoaiCuTru", "Thường trú")
                residence_req = prefer_printed_street(
                    _area(values.get("ToKhai_NoiCuTru")) or _area(values.get("PoA_SubjectAddress")),
                    card.get("NoiCuTru"),
                )
            _add_residence(add, "nyc", residence_req)
        else:
            # KHÔNG ỦY QUYỀN: Mục I ưu tiên khối "người yêu cầu" ghi RIÊNG ở đầu tờ khai
            # (ToKhaiYeuCau_*) — người này có thể KHÁC người được cấp (Section II/ToKhai_*), vd
            # thân nhân đứng khai hộ. Không có khối đó thì mới lùi về CCCD upload. Không có nguồn
            # nào cả thì KHÔNG đè field — để cổng giữ nguyên dữ liệu VNeID của người đăng nhập.
            req_ten = values.get("ToKhaiYeuCau_HoTen")
            req_sdd = values.get("ToKhaiYeuCau_SoDinhDanh")
            if has_declared_requester:
                # Thẻ trong hồ sơ thường là của NGƯỜI ĐƯỢC CẤP, không phải người đứng khai. Mượn bừa
                # thì mục I ra tên một người ghép với số định danh của người khác — sai kiểu đó trông
                # vẫn hợp lệ nên không ai soát ra. Chỉ mượn khi thẻ khớp chính người yêu cầu.
                # Có thẻ riêng của người đi nộp thì xét thẻ đó; không thì xét thẻ người được cấp
                # (hồ sơ tự khai: người yêu cầu cũng là chủ thẻ đó).
                card_prefix = "NguoiYeuCau_" if has_requester_card else "NguoiDuocCap_"
                by_id = _id_match(req_sdd, values.get(f"{card_prefix}SoDinhDanh"))
                by_name = _name_match(req_ten, values.get(f"{card_prefix}HoTen"))
                if by_id is not None:
                    card_is_requester = by_id
                elif by_name is not None:
                    card_is_requester = by_name
                else:
                    card_is_requester = True   # không đủ dữ kiện để bác bỏ
                card = ({k[len(card_prefix):]: v for k, v in values.items() if k.startswith(card_prefix)}
                        if card_is_requester else {})
                card_issuer = requester_issuer if has_requester_card else issuer
                card_residence = _area(values.get("NguoiYeuCau_NoiCuTru")) if has_requester_card else residence
                # Cùng lý do như mục II: khối "người yêu cầu" cũng là chữ VIẾT TAY, nên khi số
                # định danh của họ trùng số trên thẻ trong hồ sơ thì lấy tên IN trên thẻ.
                cccd_ten = (_card_name_when_same_person(values, req_sdd, req_ten)
                            or req_ten or card.get("HoTen"))
                # Ngày sinh người yêu cầu: tờ khai CÓ ghi ngay dưới tên (ToKhaiYeuCau_NgaySinh).
                # Thiếu field đó thì Section II vẫn dùng được KHI hai khối là cùng một người (hồ sơ
                # tự khai, hoặc nhờ người khác nộp hộ nhưng người yêu cầu vẫn là chính chủ) — lúc
                # này thẻ trong hồ sơ là của người ĐI NỘP nên không được mượn ngày sinh của nó.
                if _same_person(
                    req_ten, req_sdd,
                    values.get("ToKhai_HoTen"), values.get("ToKhai_SoDinhDanh"),
                ):
                    tokhai_ns = values.get("ToKhai_NgaySinh")
                else:
                    tokhai_ns = None
                cccd_ns = (
                    _card_value_when_same_person(values, req_sdd, "NgaySinh")
                    or values.get("ToKhaiYeuCau_NgaySinh")
                    or tokhai_ns
                    or card.get("NgaySinh")
                )
                cccd_sdd = _card_id_when_id_matches(values, req_sdd) or card.get("SoDinhDanh")
                ngay_cap = values.get("ToKhaiYeuCau_NgayCapGiayTo") or card.get("NgayCap")
                noi_cap = values.get("ToKhaiYeuCau_NoiCapGiayTo") or (card_issuer if card_is_requester else None)
                residence_i = _area(values.get("ToKhaiYeuCau_NoiCuTru")) or (
                    card_residence if card_is_requester else None)
            elif has_card:
                # Không có tờ khai ghi người yêu cầu: thẻ người đi nộp (nếu có) là mục I, còn không
                # thì chủ thẻ duy nhất vừa là người yêu cầu vừa là người được cấp.
                card_prefix = "NguoiYeuCau_" if has_requester_card else "NguoiDuocCap_"
                cccd_ten = values.get(f"{card_prefix}HoTen")
                cccd_ns = values.get(f"{card_prefix}NgaySinh")
                cccd_sdd = values.get(f"{card_prefix}SoDinhDanh")
                ngay_cap = values.get(f"{card_prefix}NgayCap")
                noi_cap = requester_issuer if has_requester_card else issuer
                residence_i = _area(values.get("NguoiYeuCau_NoiCuTru")) if has_requester_card else residence
            else:
                cccd_ten = cccd_ns = cccd_sdd = ngay_cap = noi_cap = residence_i = None

            if cccd_ten or cccd_sdd:
                # Quan hệ chốt bằng chính hai người sắp được điền: mục I (cccd_*) so với mục II
                # (ToKhai_*/NguoiDuocCap_* — đúng biểu thức dùng ở khối mục II bên dưới). Trùng số định
                # danh hoặc trùng tên → "Bản thân"; khác người → "Khác" + chữ quan hệ ở ô kẻ chấm.
                # Chữ quan hệ trên tờ khai chỉ được tin khi khối "người yêu cầu" là thật.
                # Nhân thân mục I có thể đã MƯỢN thẻ trong hồ sơ (card_is_requester) — mượn xong
                # thì số định danh mục I trùng mục II một cách máy móc. So quan hệ phải dùng đúng
                # dữ kiện tờ khai tự khai ra, nếu không mọi hồ sơ nộp hộ đều thành "Bản thân".
                relation_code = _relation_code(
                    req_ten if has_declared_requester else cccd_ten,
                    req_sdd if has_declared_requester else cccd_sdd,
                    values.get("ToKhai_HoTen") or values.get("NguoiDuocCap_HoTen"),
                    values.get("ToKhai_SoDinhDanh") or values.get("NguoiDuocCap_SoDinhDanh"),
                    values.get("ToKhaiYeuCau_QuanHe") if has_declared_requester else None,
                    fallback_self=bool(is_self or declared_self),
                )
                if relation_code:
                    add("quanhevoinguoiduocxacminh", relation_code)
                # Chọn "Khác" thì cổng mở thêm ô nhập free-text ngay cạnh: điền đúng chữ quan hệ
                # trên tờ khai ("là con đẻ" → "Con đẻ"). Ô này chỉ tồn tại sau khi tick "Khác" nên
                # phải phát NGAY SAU radio quan hệ.
                if relation_code == "2":
                    add_relation_other(values.get("ToKhaiYeuCau_QuanHe") if has_declared_requester else None)

                add("HoVaTenC", upper_person_name(cccd_ten))
                add("NgaySinhC", cccd_ns)
                add("SoDinhDanhC", cccd_sdd)
                add("LoaiGiayToDinhDanhC", _id_doc_type_for(cccd_sdd, noi_cap or issuer))
                add("SoGiayToTuyThanC", cccd_sdd)
                add("NgayCapDDC", ngay_cap)
                add("NoiCapDDC", noi_cap)
                add("nycLoaiCuTru", "Thường trú")
                _add_residence(add, "nyc", residence_i)

        # --- MỤC II: Người được xác nhận ---
        if has_poa:
            # ỦY QUYỀN: Mục II = người ủy quyền (người CẦN giấy) từ giấy ủy quyền
            poa_issuer = values.get("PoA_SubjectIssuer") or default_issuer(values.get("PoA_SubjectIdDate"))
            # Giay uy quyen chi ghi VAN TAT (ten, nam sinh, so CCCD). To khai lai mo ta DAY DU
            # chinh nguoi uy quyen -> cung mot nguoi thi lay them ngay sinh du ngay/thang, gioi
            # tinh, dan toc tu do. Bo qua la muc II trong 3 o ma can bo phai go tay.
            #
            # KHONG muon khoi GIAY TO cua to khai: ho so ra nuoc ngoai co to khai ghi HO CHIEU
            # (so + ngay cap) trong khi giay uy quyen ghi so CCCD -> ghep ngay cap ho chieu vao
            # so the can cuoc la sai giay to ma nhin van hop le.
            tk_is_poa_subject = _tk_is_poa_subject(values)
            card = _poa_subject_card(values)

            def _tk(name):
                return values.get(name) if tk_is_poa_subject else None

            def add_with_declaration_fallback(ui_name, primary, declared_name) -> None:
                """Nguồn chắc chắn (thẻ / giấy ủy quyền) trước; thiếu thì lấy TỜ KHAI.

                Tờ khai mục II vốn chính là người cần giấy, nên "không khớp" gần như luôn là OCR đọc sai
                chữ viết tay. Vẫn điền để cán bộ khỏi gõ tay, nhưng chưa xác nhận được cùng người thì
                đánh dấu default → extension tô viền vàng để soát lại.
                """
                if primary:
                    add(ui_name, primary)
                    return
                declared = values.get(declared_name)
                add(ui_name, declared, default=not tk_is_poa_subject)

            # Họ tên / số / ngày cấp / nơi cấp / giới tính: THẺ CĂN CƯỚC của người ủy quyền (bản IN,
            # đúng dữ liệu CSDLQG đối chiếu) → giấy ủy quyền → tờ khai.
            add("HoVaTenC1", upper_person_name(
                card.get("HoTen")
                or _card_name_when_same_person(
                    values, values.get("PoA_SubjectIdNumber"), poa_subject_name)
                or poa_subject_name))
            # Giấy ủy quyền thường chỉ ghi NĂM sinh; tờ khai (cùng người) có đủ ngày/tháng.
            add_with_declaration_fallback(
                "NgaySinhC1",
                card.get("NgaySinh") or _tk("ToKhai_NgaySinh") or values.get("PoA_SubjectDoB"),
                "ToKhai_NgaySinh",
            )
            add_with_declaration_fallback(
                "GioiTinhC1", card.get("GioiTinh") or values.get("PoA_SubjectGender"), "ToKhai_GioiTinh")
            add_with_declaration_fallback(
                "DanTocC1",
                _tk("ToKhai_DanToc") or values.get("PoA_SubjectDanToc") or card.get("DanToc")
                or values.get("GiayToKhac_DanToc"),
                "ToKhai_DanToc")
            add("QuocTichC1", "Việt Nam")
            subject_id = card.get("SoDinhDanh") or values.get("PoA_SubjectIdNumber")
            subject_issuer = card.get("NoiCap") or poa_issuer
            add("SoDinhDanhC1", subject_id)
            add("LoaiGiayToDinhDanhC1", _id_doc_type_for(subject_id, subject_issuer))
            add("SoGiayToTuyThanC1", subject_id)
            add("NgayCapDDC1", card.get("NgayCap") or values.get("PoA_SubjectIdDate"))
            add("NoiCapDDC1", subject_issuer)
            add("nxnLoaiCuTru", "Thường trú")
            # Nơi cư trú: TỜ KHAI (đúng mẫu đang điền) thắng "chỗ ở hiện tại" trên giấy ủy quyền — giấy
            # ủy quyền hay ghi nơi tạm trú lúc ký (vd người ở TP HCM ủy quyền về Đà Lạt), không phải nơi
            # cư trú khai cho giấy XNTTHN, và thường khác tỉnh nên tỉnh/xã không khớp option. Chưa chắc
            # cùng người thì vẫn lấy tờ khai nhưng viền vàng.
            declared_residence = _area(values.get("ToKhai_NoiCuTru"))
            poa_residence = declared_residence or _area(values.get("PoA_SubjectAddress"))
            poa_residence = prefer_printed_street(poa_residence, card.get("NoiCuTru"))
            _add_residence(
                add, "nxn", poa_residence,
                default=bool(declared_residence) and not tk_is_poa_subject,
            )
        else:
            # BẢN THÂN hoặc CCCD-MISMATCH: Mục II = người trên tờ khai (ưu tiên) hoặc giấy in của họ
            # Ưu tiên: ToKhai_* → NguoiDuocCap_* (từng field riêng lẻ)
            # Tên: thẻ căn cước THẮNG tờ khai khi số định danh hai bên trùng nhau (xem
            # _card_name_when_same_person) — cùng người thì bản IN đáng tin hơn bản viết tay.
            # Không trùng số thì giữ nguyên thứ tự cũ: tờ khai → giấy in.
            add("HoVaTenC1", upper_person_name(
                _card_name_when_same_person(
                    values, values.get("ToKhai_SoDinhDanh"), values.get("ToKhai_HoTen"))
                or values.get("ToKhai_HoTen") or values.get("NguoiDuocCap_HoTen")))
            # Ngày sinh + giới tính: cùng quy tắc với họ tên — thẻ căn cước trùng số với tờ khai thì lấy
            # bản IN trên thẻ; không trùng số thì giữ thứ tự tờ khai → giấy in.
            tk_sdd = values.get("ToKhai_SoDinhDanh")
            subject_card = _card_prefix_for(values, tk_sdd)
            add("NgaySinhC1",
                _card_value_when_same_person(values, tk_sdd, "NgaySinh")
                or values.get("ToKhai_NgaySinh") or values.get("NguoiDuocCap_NgaySinh"))
            add("GioiTinhC1",
                _card_value_when_same_person(values, tk_sdd, "GioiTinh")
                or values.get("ToKhai_GioiTinh") or values.get("NguoiDuocCap_GioiTinh"))
            # Thẻ căn cước mẫu mới không in dân tộc — giấy tờ khác của chính người được cấp (giấy
            # XNTTHN cũ, xác nhận cư trú, giấy kết hôn) thường là nguồn DUY NHẤT khi không có tờ khai.
            add("DanTocC1", values.get("ToKhai_DanToc") or values.get("NguoiDuocCap_DanToc")
                or values.get("GiayToKhac_DanToc"))
            add("QuocTichC1", values.get("ToKhai_QuocTich") or nationality)
            # Giấy tờ: ưu tiên tờ khai, fallback giấy in
            so_dinh_danh = (
                _card_id_when_id_matches(values, values.get("ToKhai_SoDinhDanh"))
                or values.get("NguoiDuocCap_SoDinhDanh")
            )
            ngay_cap = values.get("ToKhai_NgayCapGiayTo") or values.get("NguoiDuocCap_NgayCap")
            noi_cap = values.get("ToKhai_NoiCapGiayTo") or issuer
            add("SoDinhDanhC1", so_dinh_danh)
            add("LoaiGiayToDinhDanhC1", _id_doc_type_for(so_dinh_danh, noi_cap))
            add("SoGiayToTuyThanC1", so_dinh_danh)
            add("NgayCapDDC1", ngay_cap)
            add("NoiCapDDC1", noi_cap)
            add("nxnLoaiCuTru", "Thường trú")
            # Thẻ căn cước trong hồ sơ là của CHÍNH người được cấp (trùng số) → sửa tên đường đọc sai
            # từ chữ viết tay theo bản in trên thẻ.
            if subject_card:
                residence = prefer_printed_street(residence, _area(values.get(f"{subject_card}NoiCuTru")))
            _add_residence(add, "nxn", residence)

    # =========================================================
    # TÌNH TRẠNG HÔN NHÂN: ưu tiên TỜ KHAI → fallback GIẤY TỜ CHỨNG MINH
    # =========================================================
    death_number = values.get("DeathCert_Number")
    death_date = values.get("DeathCert_Date")
    death_agency = values.get("DeathCert_Agency")
    divorce_number = values.get("DivorceDecision_Number")
    divorce_date = values.get("DivorceDecision_Date")
    divorce_agency = values.get("DivorceDecision_Agency")
    def add_marriage_raw_inputs(number, date, agency) -> None:
        """Ô con của vùng động (=2 và =5) được render sau khi chọn option → phát thêm theo DOM name.

        Cả hai vùng dùng CHUNG bộ ô "Số / Ngày cấp / Cơ quan cấp giấy chứng nhận kết hôn" nên dùng
        lại y nguyên; chỉ vùng =5 có thêm hai mốc thời gian, extension điền theo vị trí.
        """
        add("soGiayTo", number)
        date_match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(date or "").strip())
        if date_match:
            day, month, year = date_match.groups()
            day = day.zfill(2)
            month = month.zfill(2)
            add("ngayCapGiayTo-day", day)
            add("ngayCapGiayTo-month", month)
            add("ngayCapGiayTo-year", year)
            add("ngayCapGiayTo-name-date-input", f"{year}-{month}-{day}")
        add("coQuanCapGiayTo", agency)

    def decision_detail(number, date, agency) -> dict:
        """Ô con của vùng =3 (bản án ly hôn) và =4 (giấy chứng tử), bỏ phần đọc không ra.

        OCR quyết định ly hôn rất hay mất ĐÚNG dòng địa danh + ngày ban hành (dấu treo đè lên,
        trang scan lệch) trong khi số quyết định và tên tòa vẫn rõ. Đòi đủ cả ba thì cả tình
        trạng hôn nhân lẫn số bản án đều rụng, cán bộ phải gõ tay toàn bộ — trong khi giấy tờ
        đã chứng minh thừa đủ là người này ĐÃ LY HÔN. Điền phần đọc được, ô thiếu để trống cho
        cán bộ bổ sung.
        """
        return _drop_empty({
            "soBanAnQuyetDinhLyHon": number,
            "ngayCapBanAnQuyetDinhLyHon": date,
            "coQuanCapBanAnQuyetDinhLyHon": agency,
        })

    marriage_spouse = values.get("Marriage_SpouseName")
    marriage_number = values.get("Marriage_Number")
    marriage_date = values.get("Marriage_Date")
    marriage_agency = values.get("Marriage_Agency")
    declared_code = _status_code(values.get("TinhTrangHonNhanC1"))
    period_from = values.get("Period_TuNgay")
    period_to = values.get("Period_DenNgay")
    has_marriage = any((marriage_spouse, marriage_number, marriage_date, marriage_agency))
    # Đủ căn cứ kết luận ly hôn/góa khi đọc được BẤT KỲ mảnh nào của bản án/giấy tử: chỉ tài liệu
    # ly hôn/khai tử thật mới sinh ra các field này (xem prompt), nên một mảnh cũng đã là bằng chứng.
    has_divorce = any((divorce_number, divorce_date, divorce_agency))
    has_death = any((death_number, death_date, death_agency))

    # Hôn nhân HIỆN TẠI đăng ký SAU mốc ly hôn/khai tử của cuộc hôn nhân trước → người này đã kết
    # hôn LẠI. Chỉ kết luận khi cả hai mốc đều đọc được đúng dd/mm/yyyy; thiếu mốc nào thì để False
    # và giữ nguyên thứ tự ưu tiên cũ.
    _prior_end_keys = [key for key in (_date_key(divorce_date), _date_key(death_date)) if key]
    _marriage_key = _date_key(marriage_date)
    remarried_after_prior = bool(
        has_marriage and _marriage_key and _prior_end_keys and _marriage_key > max(_prior_end_keys)
    )

    # ---------------------------------------------------------
    # BƯỚC 1 — CHỐT MÃ OPTION. Tách hẳn khỏi bước phát field: bản cũ vừa xét điều kiện vừa phát
    # trong cùng một chuỗi `if/elif`, nên một nhánh khớp điều kiện ngoài mà không khớp nhánh con
    # nào bên trong là "ăn" mất lượt — không phát gì và cũng chặn luôn fallback. Ở đây mọi nhánh
    # đều PHẢI cho ra một mã (hoặc None), không nhánh nào kết thúc mà chưa quyết định.
    # ---------------------------------------------------------
    if period_from and period_to and has_marriage:
        # Tờ khai xin xác nhận CHƯA ĐKKH TRONG MỘT KHOẢNG THỜI GIAN ĐÃ QUA mà HIỆN TẠI đã có
        # vợ/chồng (vd bổ sung hồ sơ mua bán đất diễn ra trước khi cưới). Cổng có option RIÊNG cho
        # ca này (=5); chọn nhầm "Hiện tại đang có vợ/chồng" (=2) là mất sạch khoảng thời gian —
        # đúng cái người dân cần xác nhận — và form cũng không hiện hai ô mốc thời gian để điền.
        status = _PERIOD_MARRIED
    elif remarried_after_prior and not declared_code:
        # Hồ sơ có bản án ly hôn / giấy khai tử của vợ chồng CŨ nhưng giấy kết hôn hiện tại lại
        # đăng ký SAU mốc đó → đã kết hôn lại. Hai option =3/=4 đều kết thúc bằng "hiện tại chưa
        # đăng ký kết hôn với ai" nên chọn chúng là khai SAI sự thật. Chỉ áp dụng khi tờ khai
        # KHÔNG tự khai trạng thái (có khai thì theo tờ khai).
        status = _MARRIED
    elif declared_code:
        status = declared_code                  # tờ khai tự khai → tin tờ khai
    elif has_death:
        status = _WIDOWED                       # fallback: suy từ giấy chứng tử
    elif has_divorce:
        status = _DIVORCED                      # fallback: suy từ bản án/quyết định ly hôn
    elif marriage_number and marriage_date:
        status = _MARRIED                       # fallback: suy từ giấy chứng nhận kết hôn
    else:
        status = None

    # ---------------------------------------------------------
    # BƯỚC 2 — PHÁT FIELD theo mã đã chốt. add() tự bỏ qua dict rỗng/None nên không cần guard
    # "có đủ dữ liệu chưa": thiếu giấy tờ thì chỉ mất vùng chi tiết, ô tình trạng hôn nhân vẫn
    # được chọn — đúng thứ cán bộ cần nhất và không tự suy ra được.
    # ---------------------------------------------------------
    add("TinhTrangHonNhanC1", _TINH_TRANG_HON_NHAN.get(status, ""))
    if status == _PERIOD_MARRIED:
        add("nxnLoaiTinhTrangHonNhan=5", _drop_empty({
            "voChongHoTen": marriage_spouse,
            "thoiDiemBatDau": period_from,
            "thoiDiemKetThuc": period_to,
        }))
        add_marriage_raw_inputs(marriage_number, marriage_date, marriage_agency)
    elif status == _MARRIED:
        add("nxnLoaiTinhTrangHonNhan=2", _drop_empty({
            "voChongHoTen": marriage_spouse,
            "soGiayTo": marriage_number,
            "ngayCapGiayTo": marriage_date,
            "coQuanCapGiayTo": marriage_agency,
        }))
        add_marriage_raw_inputs(marriage_number, marriage_date, marriage_agency)
    elif status == _DIVORCED:
        add("nxnLoaiTinhTrangHonNhan=3", decision_detail(divorce_number, divorce_date, divorce_agency))
    elif status == _WIDOWED:
        add("nxnLoaiTinhTrangHonNhan=4", decision_detail(death_number, death_date, death_agency))

    # =========================================================
    # MỤC ĐÍCH & TRẢ KẾT QUẢ
    # =========================================================
    add("mucdich", _DEFAULT_PURPOSE)
    # Mục đích cụ thể từ tờ khai/giấy XNTTHN cũ → ô "Nhập mục đích" free-text.
    add("nhapmucdichkhac", values.get("Purpose"))
    add("TraKQ", "1")
    # Ô (17) "Số lượng bản sao" là bắt buộc trên cổng nhưng tờ khai giấy không có mục này → mặc
    # định 1 bản, đánh dấu default để extension tô viền vàng cho cán bộ sửa nếu người dân xin nhiều.
    add("SoLuong", "1", default=True)

    return _apply_account(out, options)

