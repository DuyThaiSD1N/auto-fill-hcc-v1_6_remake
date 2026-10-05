"""Dịch dữ kiện đã trích sang ô SurveyJS của biểu mẫu đăng ký khai sinh (Cổng DVC quốc gia mới)."""

import re
import unicodedata
from datetime import date

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type, normalize_issuer
from app.pipelines._shared.formatting import upper_person_name
from app.pipelines._shared.hospital_lookup import lookup_hospital

from .reason import LOAI_KHAI_SINH_OPTIONS, labeled_value, requester_context, section
from .schema import UI_COMP_BY_NAME

_MOTHER, _FATHER, _OTHER = "Mẹ", "Cha", "Khác"
_SELF_TEXT = "Bản thân"
_DANG_KY_DUNG_HAN = "Đăng ký đúng hạn"
_DANG_KY_QUA_HAN = "Đăng ký quá hạn"
_DANG_KY_CO_HO_SO = "Đăng ký cho người đã có hồ sơ, giấy tờ cá nhân"
# Luật Hộ tịch: cha mẹ đăng ký khai sinh cho con trong 60 ngày kể từ ngày sinh.
_HAN_DANG_KY_NGAY = 60
_HCM_PROVINCE_KEYS = {"hochiminh", "tphochiminh", "thanhphohochiminh", "tphcm", "hcm"}


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _parse_date(value) -> date | None:
    match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", str(value or "").strip())
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _full_date(value) -> str:
    """Ô ngày của cổng cần đủ ngày-tháng-năm; giấy chỉ ghi năm thì để trống, không ghép "01/01"."""
    return str(value).strip() if _parse_date(value) else ""


def _id_doc_type_with_number(number, hint, issuer: str = "") -> str:
    # Căn cước/CCCD luôn 12 chữ số → số 9 chữ số chỉ có thể là CMND cũ (trừ khi giấy ghi rõ hộ chiếu).
    if len(_digits(number)) == 9 and "chieu" not in _fold(hint):
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


def _birth_place(value):
    area = _area(value)
    # Sinh tại cơ sở y tế mà giấy không ghi xã → tra danh mục bệnh viện để bù xã/tỉnh.
    if area and not area.get("xa") and area.get("diaChi"):
        hospital = lookup_hospital(area["diaChi"])
        if hospital:
            area = {**area, "xa": hospital["xa"], "tinh": area.get("tinh") or hospital["tinh"]}
    return area


def _same_person(account_name: str, account_id: str, name, ids: list) -> tuple[bool, bool]:
    """(cùng người, chỉ khớp họ tên). Có số hai phía thì số quyết định."""
    numbers = {_digits(v) for v in ids if _digits(v)}
    if account_id and numbers:
        return account_id in numbers, False
    if account_name and name and _fold(account_name) == _fold(name):
        return True, True
    return False, False


def _relation(values: dict, context: str, options: dict | None) -> tuple[str, str, bool, str]:
    """(Khác/Cha/Mẹ, quan hệ khác, suy đoán, cảnh báo)."""
    account_name, account_id = requester_context(options)
    child = section(context, "con")
    roles = {
        _MOTHER: (values.get("Me_HoTen"), [values.get("Me_SoDinhDanh"), values.get("Me_SoGiayTo")]),
        _FATHER: (values.get("Cha_HoTen"), [values.get("Cha_SoDinhDanh"), values.get("Cha_SoGiayTo")]),
    }
    if account_name or account_id:
        for role, (name, ids) in roles.items():
            same, by_name = _same_person(account_name, account_id, name, ids)
            if same:
                return role, "", by_name, ""
        same, by_name = _same_person(
            account_name, account_id, values.get("Con_HoTen") or labeled_value(child, "Họ tên"),
            [labeled_value(child, "Số định danh")])
        if same:
            return _OTHER, _SELF_TEXT, by_name, ""
        # Người khác nộp: quan hệ cụ thể chỉ lấy từ tờ khai khi người yêu cầu trên tờ khai chính là tài khoản.
        requester_same, _ = _same_person(account_name, account_id, values.get("NguoiYeuCau_HoTen"),
                                         [values.get("NguoiYeuCau_SoDinhDanh")])
        detail = values.get("NguoiYeuCau_QuanHe") if requester_same else ""
        detail = detail or labeled_value(section(context, "quan_he"), "Quan hệ cụ thể")
        if not detail:
            return _OTHER, "", False, "Người nộp không phải cha/mẹ — cán bộ ghi rõ ô 'Quan hệ khác'."
        return _OTHER, detail, False, ""
    reasoned = _fold(labeled_value(section(context, "quan_he"), "Kết luận"))
    if reasoned in ("me", "cha"):
        return (_MOTHER if reasoned == "me" else _FATHER), "", True, ""
    if reasoned == "ban than":
        return _OTHER, _SELF_TEXT, True, ""
    return "", "", False, "Chưa xác định được quan hệ người nộp với người được khai sinh — cán bộ chọn ô Quan hệ."


def _loai_khai_sinh(values: dict, context: str) -> str:
    reasoned = labeled_value(section(context, "loai_khai_sinh"), "Kết luận")
    for option in LOAI_KHAI_SINH_OPTIONS:
        if _fold(option) == _fold(reasoned):
            return option
    # Phân vai không trả → suy theo việc giấy tờ có tên cha/mẹ hay không.
    has_mother, has_father = bool(values.get("Me_HoTen")), bool(values.get("Cha_HoTen"))
    if has_mother and has_father:
        return LOAI_KHAI_SINH_OPTIONS[0]
    if has_mother:
        return LOAI_KHAI_SINH_OPTIONS[2]
    if has_father:
        return LOAI_KHAI_SINH_OPTIONS[1]
    return ""


def _loai_dang_ky(values: dict, context: str) -> str:
    if _fold(labeled_value(section(context, "loai_khai_sinh"), "Đã có hồ sơ, giấy tờ cá nhân")) == "co":
        return _DANG_KY_CO_HO_SO
    born = _parse_date(values.get("Con_NgaySinh"))
    if not born:
        return ""
    return _DANG_KY_DUNG_HAN if (date.today() - born).days <= _HAN_DANG_KY_NGAY else _DANG_KY_QUA_HAN


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

    def add_area(radio: str, value) -> None:
        if not value:
            return
        # Radio "Trong nước" phải chọn trước: các ô địa chỉ chỉ hiện sau khi chọn.
        add(radio, "Trong nước")
        area_field = add(f"{radio}_TrongNuoc", value)
        if area_field:
            area_field["radio"] = radio

    # Quan hệ + loại khai sinh chốt TRƯỚC: cổng ẩn/hiện khối cha mẹ theo hai ô này.
    relation, relation_detail, guessed, warning = _relation(values, context, options)
    if warning:
        warnings.append(warning)
    add("citizenQuanhevoinguoiduockhaisinh", relation, default=guessed)
    if relation == _OTHER:
        add("citizenField62", relation_detail, default=guessed)
    add("citizenLoaiDangKy", _loai_dang_ky(values, context), default=True)
    add("citizenLoaikhaisinh_NgdcKS", _loai_khai_sinh(values, context))

    add("citizenHoVaTen_NgdcKS", upper_person_name(values.get("Con_HoTen")))
    add("citizenNgaythangnamsinh_NgdcKS", _full_date(values.get("Con_NgaySinh")))
    add("citizenGioitinh_NgdcKS", values.get("Con_GioiTinh"))
    quoc_tich = values.get("Con_QuocTich")
    add("citizenQuoctich_NgdcKS", quoc_tich or "Việt Nam", default=not quoc_tich)
    add("citizenDanToc_NgdcKS", values.get("Con_DanToc"))
    add_area("citizenNoisinhnks", _birth_place(values.get("Con_NoiSinh")))
    add_area("citizenQuequannks", _area(values.get("Con_QueQuan")))

    parents = (
        ("Me", "mẹ", {
            "name": "citizenNDK_HoVaTen", "id": "citizenNDK_SoDinhDanh", "birth": "citizenNDK_NgaySinh",
            "nation": "citizenQuoctich_me", "ethnic": "citizenDanToc_me", "doc": "citizenLoaiGiaytotuythan_me",
            "number": "citizenSoGiayToTuyThan_me", "issued": "citizenNgaythangnamcap__me",
            "issuer": "citizenCoquancap_me", "residence_type": "citizenMeLoaicutru", "residence": "citizenMeNoicutru",
        }),
        ("Cha", "cha", {
            "name": "citizenNDK_HoVaTenCha", "id": "citizenNDK_SoDinhDanhCha", "birth": "citizenNDK_NgaySinhCha",
            "nation": "citizenQuoctich_cha", "ethnic": "citizenDanToc_cha", "doc": "citizenField24",
            "number": "citizenSoGiayToTuyThan_cha", "issued": "citizenNgaythangnamcap__cha",
            "issuer": "citizenCoquancap_cha", "residence_type": "citizenChaLoaicutru",
            "residence": "citizenChaNoicutru",
        }),
    )
    for prefix, label, ui in parents:
        name = values.get(f"{prefix}_HoTen")
        if not name:
            continue
        add(ui["name"], upper_person_name(name))
        personal_id = _digits(values.get(f"{prefix}_SoDinhDanh"))
        add(ui["id"], personal_id if len(personal_id) == 12 else "")
        add(ui["birth"], _full_date(values.get(f"{prefix}_NgaySinh")))
        add(ui["nation"], values.get(f"{prefix}_QuocTich"))
        add(ui["ethnic"], values.get(f"{prefix}_DanToc"))
        hint = values.get(f"{prefix}_LoaiGiayTo")
        number = str(values.get(f"{prefix}_SoGiayTo") or "").strip() or personal_id
        if number:
            issue_date = _full_date(values.get(f"{prefix}_NgayCap"))
            # Mặc định cơ quan cấp theo ngày chỉ đúng với thẻ căn cước 12 số.
            issuer = normalize_issuer(values.get(f"{prefix}_NoiCap")) or (
                default_issuer(issue_date) if len(_digits(number)) == 12 and issue_date else "")
            add(ui["doc"], _id_doc_type_with_number(number, hint, issuer))
            add(ui["number"], number)
            add(ui["issued"], issue_date)
            add(ui["issuer"], issuer)
        if values.get(f"{prefix}_DaChet") is True or _fold(values.get(f"{prefix}_DaChet")) == "true":
            warnings.append(f"Theo giấy tờ, {label} đã chết — cán bộ chọn ô nơi cư trú của {label} theo hướng dẫn cổng.")
            continue
        residence = _area(values.get(f"{prefix}_NoiCuTru"))
        if residence:
            add(ui["residence_type"], "Thường trú", default=True)
            add_area(ui["residence"], residence)

    quantity = _digits(values.get("SoLuongBanSao"))
    add("citizenSoluongbansao", str(int(quantity)) if quantity else "")
    return out, warnings
