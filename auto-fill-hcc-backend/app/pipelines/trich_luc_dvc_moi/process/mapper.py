"""Dịch dữ kiện đã trích sang ô SurveyJS của biểu mẫu cấp bản sao trích lục (Cổng DVC quốc gia mới)."""

import re
import unicodedata
from datetime import date

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.cccd import id_birth_year, id_gender
from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type, normalize_issuer
from app.pipelines._shared.ethnic_normalize import co_ho_local_group
from app.pipelines._shared.formatting import upper_person_name

from .reason import QUAN_HE_OPTIONS, labeled_value, requester_context, section
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


def _id_doc_type_with_number(number, hint, issuer: str = "") -> str:
    # Căn cước/CCCD luôn 12 chữ số → số 9 chữ số chỉ có thể là CMND cũ.
    if len(_digits(number)) == 9:
        return "Chứng minh nhân dân"
    return id_doc_type(hint or "Căn cước", issuer)


def _area(value):
    if not isinstance(value, dict):
        return None
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


def _relation(values: dict, context: str, options: dict | None, event: str) -> tuple[str, str, str]:
    """(nhãn quan hệ, quan hệ khác, cảnh báo). Số định danh hai phía quyết định "Bản thân"."""
    account_name, account_id = requester_context(options)
    subject = section(context, "nguoi_duoc_cap")
    subject_id = _digits(values.get("NguoiDuocCap_SoDinhDanh")) or _digits(labeled_value(subject, "Số định danh"))
    subject_name = values.get("NguoiDuocCap_HoTen") or labeled_value(subject, "Họ tên")
    deceased = event == "death" or _fold(labeled_value(subject, "Trạng thái")) == "da chet"

    block = section(context, "quan_he")
    relation = _quan_he_option(labeled_value(block, "Kết luận"))
    other = labeled_value(block, "Quan hệ khác")
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

    if account_id and subject_id and account_id == subject_id and not deceased:
        return _SELF, "", ""
    if relation == _SELF:
        same_name = bool(account_name) and _fold(account_name) == _fold(subject_name)
        if deceased or (account_id and subject_id) or not same_name:
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
        area = _area(values.get("NguoiDuocCap_NoiCuTru"))
        if area:
            add("citizenNDK_LoaiCuTru", "Thường trú", default=True)
            # Radio "Trong nước" phải chọn trước: bốn ô địa chỉ chỉ hiện sau khi chọn.
            add("citizenNDK_Noicutru", "1")
            add("citizenField21", area.get("quocGia") or "Việt Nam")
            add("citizenNDK_TinhThanh", area.get("tinh"))
            add("citizenNDK_PhuongXa", area.get("xa"))
            add("citizenField38", area.get("diaChi"))

    add("citizenLoaiViecYeuCau", _EVENT_TO_OPTION.get(event))
    add("citizenHoSo_CoQuanDangKy", values.get("GiayTo_CoQuanDangKy"))
    add("citizenTenGiayToHoTich", values.get("GiayTo_TenGiayTo") or _EVENT_TO_DOCUMENT_NAME.get(event))
    add("citizencauhoi3", values.get("GiayTo_So"))
    add("citizencauhoi4", values.get("GiayTo_QuyenSo"))
    add("citizencauhoi5", values.get("GiayTo_NgayDangKy"))
    quantity = _digits(values.get("SoLuongBanSao"))
    add("citizenSoLuongBanSao", str(int(quantity)) if quantity and int(quantity) > 0 else "")
    return out, warnings
