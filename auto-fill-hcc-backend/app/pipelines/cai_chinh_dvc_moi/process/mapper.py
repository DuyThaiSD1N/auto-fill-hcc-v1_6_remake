"""Dịch dữ kiện đã trích sang ô SurveyJS của biểu mẫu thay đổi, cải chính hộ tịch (Cổng DVC quốc gia mới)."""

import re
import unicodedata

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type, normalize_issuer
from app.pipelines._shared.ethnic_normalize import co_ho_local_group
from app.pipelines._shared.formatting import upper_person_name

from .reason import labeled_value, requester_context, section
from .schema import UI_COMP_BY_NAME

_SELF = "Bản thân"
_OTHER = "Khác"
# Option nguyên văn của cổng. Tra theo cụm lõi đã fold; cụm dài đứng trước ("giám sát giám hộ" trước
# "giám hộ") để không khớp nhầm cụm ngắn hơn.
_VIEC_OPTIONS = {
    "cai chinh": "Cải chính thông tin hộ tịch",
    "thay doi": "Thay đổi thông tin hộ tịch",
    "bo sung": "Bổ sung thông tin hộ tịch",
    "xac dinh lai dan toc": "Xác định lại dân tộc",
}
_GIAY_TO_OPTIONS = {
    "khai sinh": "Giấy khai sinh",
    "khai tu": "Trích lục khai tử",
    "ket hon": "Giấy chứng nhận kết hôn",
    "giam sat giam ho": "Trích lục đăng ký đăng ký giám sát việc giám hộ",
    "giam ho": "Trích lục đăng ký giám hộ",
    "nhan cha me con": "Trích lục đăng ký nhận cha, mẹ, con",
}
_HCM_PROVINCE_KEYS = {"hochiminh", "tphochiminh", "thanhphohochiminh", "tphcm", "hcm"}


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _option(value, table: dict) -> str:
    key = re.sub(r"[^a-z ]+", " ", _fold(value))
    key = re.sub(r"\s+", " ", key)
    for core, option in table.items():
        if core in key:
            return option
    return ""


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


def _relation(values: dict, context: str, options: dict | None) -> tuple[str, bool, str]:
    """(Bản thân / Khác, có phải suy đoán, cảnh báo). Số định danh hai phía quyết định trước, rồi họ tên."""
    account_name, account_id = requester_context(options)
    subject = section(context, "nguoi_thay_doi")
    subject_id = _digits(values.get("NguoiThayDoi_SoDinhDanh")) or _digits(labeled_value(subject, "Số định danh"))
    subject_name = values.get("NguoiThayDoi_HoTen") or labeled_value(subject, "Họ tên")
    deceased = _fold(labeled_value(subject, "Trạng thái")) == "da chet"

    if account_id and subject_id:
        return (_SELF if account_id == subject_id and not deceased else _OTHER), False, ""
    if account_name and subject_name:
        same = _fold(account_name) == _fold(subject_name) and not deceased
        # Chỉ khớp họ tên (thiếu số định danh) → tô vàng để cán bộ rà.
        return (_SELF if same else _OTHER), True, ""
    reasoned = _fold(labeled_value(section(context, "quan_he"), "Kết luận"))
    if reasoned == "khac" or (reasoned == "ban than" and not deceased):
        return (_OTHER if reasoned == "khac" else _SELF), True, ""
    return "", False, "Chưa xác định được người nộp có phải người có nội dung thay đổi — cán bộ chọn ô Quan hệ."


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = {f.get("name"): f.get("value") for f in fields or [] if isinstance(f, dict)}
    options = options or {}
    context = str(options.get("_reasoning_context") or "")
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False) -> dict | None:
        if name in seen or value in (None, "", {}, []):
            return None
        field = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": value}
        if default:
            field["default"] = True  # extension tô viền vàng: giá trị không đọc từ giấy tờ
        out.append(field)
        seen.add(name)
        return field

    # Khối người nộp cổng đổ theo tài khoản nhưng hay bỏ trống radio nơi cư trú → mặc định "Trong Nước",
    # chỉ ghi khi ô còn trống để không đè lựa chọn có sẵn.
    nyc_residence = add("citizenNycNoicutru", "Trong Nước", default=True)
    if nyc_residence:
        nyc_residence["onlyIfEmpty"] = True

    # Quan hệ phải chốt TRƯỚC: "Bản thân" thì cổng tự đổ khối người có nội dung thay đổi, chọn khác thì cổng
    # dựng lại khối đó — điền nhân thân trước sẽ bị xóa.
    relation, guessed, warning = _relation(values, context, options)
    if warning:
        warnings.append(warning)
    add("citizenQuanhevsngcaichinhhotich1", relation, default=guessed)

    if relation != _SELF:
        name = values.get("NguoiThayDoi_HoTen")
        if not name:
            warnings.append("Không đọc được người có nội dung thay đổi — cán bộ nhập khối này.")
        add("citizenNDKHoTen", upper_person_name(name))
        personal_id = _digits(values.get("NguoiThayDoi_SoDinhDanh"))
        add("citizenNDKSodinhdanh", personal_id if len(personal_id) == 12 else "")
        add("citizenNDKNgaysinh", values.get("NguoiThayDoi_NgaySinh"))

        issue_date = values.get("NguoiThayDoi_NgayCap")
        card_number = _digits(values.get("NguoiThayDoi_SoGiayTo")) or (personal_id if issue_date else "")
        if card_number:
            # Mặc định cơ quan cấp theo ngày chỉ đúng với thẻ căn cước 12 số; CMND do công an tỉnh cấp.
            issuer = normalize_issuer(values.get("NguoiThayDoi_NoiCap")) or (
                default_issuer(issue_date) if len(card_number) == 12 else "")
            add("citizenNDKLoaiGiaytotuythan",
                _id_doc_type_with_number(card_number, values.get("NguoiThayDoi_LoaiGiayTo"), issuer))
            add("citizenNDKSogiaytotuythan", card_number)
            add("citizenNDKNgaycapgiaytotuythan", issue_date)
            add("citizenNDKCoquancap", issuer)

        add("citizenNDKLoaicutru", "Thường trú", default=True)
        add("citizenNDKGioitinh", values.get("NguoiThayDoi_GioiTinh"))
        quoc_tich = values.get("NguoiThayDoi_QuocTich")
        add("citizenNDKQuocTich", quoc_tich or "Việt Nam", default=not quoc_tich)
        # Danh mục dân tộc của cổng không có "Khác": nhóm địa phương Cill/K'Ho/Lạch quy về Cơ Ho.
        add("citizenNDKDantoc", co_ho_local_group(values.get("NguoiThayDoi_DanToc")))
        area = _area(values.get("NguoiThayDoi_NoiCuTru"))
        if area:
            # Radio "Trong Nước" phải chọn trước: các ô địa chỉ chỉ hiện sau khi chọn.
            add("citizenNDKNoiCuTru", "Trong Nước")
            area_field = add("citizenNDKNoiCuTru_TrongNuoc", area)
            if area_field:
                area_field["radio"] = "citizenNDKNoiCuTru"

    viec = values.get("ViecDangKy") or labeled_value(section(context, "viec_dang_ky"), "Loại việc")
    add("citizenViecDangKy", _option(viec, _VIEC_OPTIONS))
    giay_to = values.get("HoSo_LoaiGiayTo") or labeled_value(
        section(context, "viec_dang_ky"), "Giấy tờ hộ tịch đã đăng ký")
    add("citizenLoainghiepvu", _option(giay_to, _GIAY_TO_OPTIONS))
    add("citizenTTSodangkyhosogoc", values.get("HoSo_So"))
    add("citizenTTQuyensodangkyhosogoc", values.get("HoSo_QuyenSo"))
    add("citizenTTngayDangKyHSGoc", values.get("HoSo_NgayDangKy"))
    add("citizenTTNoidangkyhosogoc", values.get("HoSo_NoiDangKy"))
    add("citizenTTNoidungdk", values.get("NoiDung"))
    add("citizenLydothaydoi", values.get("LyDo"))
    quantity = _digits(values.get("SoLuongBanSao"))
    add("citizenSoluongbansao", str(int(quantity)) if quantity else "")
    return out, warnings
