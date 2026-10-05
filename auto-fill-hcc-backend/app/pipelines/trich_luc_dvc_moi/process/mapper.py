"""Dịch dữ kiện đã trích sang ô SurveyJS của biểu mẫu cấp bản sao trích lục (Cổng DVC quốc gia mới)."""

import re
import unicodedata
from datetime import date

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type, normalize_issuer
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


def _event_type(values: dict, context: str) -> str:
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

    if account_id and subject_id and account_id == subject_id and not deceased:
        return _SELF, "", ""
    if relation == _SELF:
        same_name = bool(account_name) and _fold(account_name) == _fold(subject_name)
        if deceased or (account_id and subject_id) or not same_name:
            return "", "", ("Phân vai kết luận \"Bản thân\" nhưng người nộp không khớp người được cấp — "
                            "cán bộ chọn ô Quan hệ.")
    if relation == _OTHER and not other:
        relation = ""
    if not relation:
        return "", "", "Chưa xác định được quan hệ của người nộp với người được cấp — cán bộ chọn ô Quan hệ."
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
    # Quan hệ phải chốt TRƯỚC: chọn "Bản thân" thì cổng tự đổ khối người được cấp từ người nộp,
    # chọn khác thì cổng dựng lại khối đó — điền nhân thân trước sẽ bị xóa.
    relation, other, warning = _relation(values, context, options, event)
    if warning:
        warnings.append(warning)
    add("citizenQuanhe", relation)
    add("citizenField8", other)

    if relation != _SELF:
        name = values.get("NguoiDuocCap_HoTen")
        if not name:
            warnings.append("Không đọc được người được cấp bản sao — cán bộ nhập khối người được cấp.")
        add("citizenNDK_HoVaTen", upper_person_name(name))
        personal_id = _digits(values.get("NguoiDuocCap_SoDinhDanh"))
        add("citizenNDK_SoDinhDanh", personal_id if len(personal_id) == 12 else "")
        birth = values.get("NguoiDuocCap_NgaySinh")
        add("citizenNDK_NgaySinh", birth)

        issue_date = values.get("NguoiDuocCap_NgayCap")
        card_number = _digits(values.get("NguoiDuocCap_SoGiayTo")) or (personal_id if issue_date else "")
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
        add("citizenField32", values.get("NguoiDuocCap_DanToc"))
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
