"""Dịch dữ kiện đã trích sang ô SurveyJS của biểu mẫu cấp Phiếu lý lịch tư pháp (3.000333, Cổng DVC quốc gia mới).

Radio "Loại tờ khai" quyết định bộ ô: Cá nhân (tài khoản = người yêu cầu cấp phiếu — nhân thân, thường trú, cha, mẹ
cổng khoá theo CSDLQG, chỉ còn mở loại giấy tờ, ngày sinh, tên gọi khác, tạm trú, vợ/chồng, điện thoại, email) / Khai
hộ (tài khoản = người được ủy quyền hoặc cha mẹ — người khai nhập tay toàn bộ khối người yêu cầu). Chọn biến thể theo
mốc tài khoản (formContext); thiếu mốc thì theo mẫu tờ khai (mẫu ủy quyền → Khai hộ).
"""

from datetime import date

from app.pipelines._shared.area_remap import canonical_province, canonical_ward, city_province_area, remap_area
from app.pipelines._shared.compact_agent.issuer import (
    default_issuer,
    issuer_by_issue_date,
    normalize_issuer,
    short_issuer,
)
from app.pipelines._shared.ethnic_normalize import co_ho_local_group
from app.pipelines._shared.formatting import upper_person_name
from app.pipelines.khai_sinh_dvc_moi.process.mapper import (
    _card_back,
    _digits,
    _fold,
    _full_date,
    _id_doc_type_with_number,
    _parse_date,
)
from app.pipelines.khai_sinh_dvc_moi.process.reason import requester_context

from .schema import UI_COMP_BY_NAME

CA_NHAN, KHAI_HO = "Cá nhân", "Khai hộ"
_LOAI_TO_KHAI_CODE = {CA_NHAN: "1", KHAI_HO: "2"}
_VIET_NAM = "Việt Nam"
_TUOI_THANH_NIEN = 18

FEE_WARNING = "Chọn ô 'Đối tượng nộp phí' theo danh mục của cổng (không có giấy miễn/giảm → đối tượng nộp đủ phí)."
RELATION_WARNING = ("Tờ khai không ghi người khai là ai của người yêu cầu cấp phiếu (hoặc người khai không phải chủ "
                    "tài khoản) — chọn tay ô 'Mối quan hệ với người yêu cầu cấp Phiếu Lý lịch tư pháp'.")


def _text(value) -> str:
    return str(value or "").strip()


def _truthy(value) -> bool:
    return value is True or _fold(value) in ("true", "co", "1")


def _phone(value) -> str:
    digits = _digits(value)
    if digits.startswith("84") and len(digits) in (11, 12):
        digits = "0" + digits[2:]
    return digits if len(digits) in (10, 11) and digits.startswith("0") else ""


def _email(value) -> str:
    text = _text(value)
    return text if "@" in text and " " not in text else ""


def _gender(value) -> str:
    folded = _fold(value)
    if folded in ("nam", "male", "m"):
        return "Nam"
    if folded in ("nu", "female", "f"):
        return "Nữ"
    return ""


def _other_name(value) -> str:
    text = _text(value)
    return "" if _fold(text) in ("", "khong", "khong co", "-") else text


def _area(value) -> dict | None:
    """Địa chỉ trong nước → {quocGia, tinh, xa, diaChi} theo danh mục hiện hành (đã sáp nhập)."""
    if not isinstance(value, dict):
        return None
    area = {
        "quocGia": _text(value.get("quocGia")) or _VIET_NAM,
        "tinh": _text(value.get("tinh")),
        "xa": _text(value.get("xa")),
        "diaChi": _text(value.get("diaChi") or value.get("chiTietDuoiXa")),
    }
    if not (area["tinh"] or area["xa"] or area["diaChi"]):
        return None
    if _fold(area["quocGia"]) not in ("viet nam", "vietnam", "vn"):
        return area
    huyen = _text(value.get("huyen"))
    remapped = remap_area({**area, "huyen": huyen} if huyen else dict(area))
    remapped = city_province_area(remapped if isinstance(remapped, dict) else area)
    province = canonical_province(remapped.get("tinh")) or _text(remapped.get("tinh"))
    ward = canonical_ward(province, remapped.get("xa")) or _text(remapped.get("xa"))
    return {"quocGia": _VIET_NAM, "tinh": province, "xa": ward, "diaChi": _text(remapped.get("diaChi"))}


def _same_person(account_name: str, account_id: str, name, number) -> bool | None:
    """Cùng người với tài khoản không. Có số CÙNG LOẠI hai phía thì số quyết định; không đủ căn cứ → None."""
    digits = _digits(number)
    if account_id and digits and len(digits) == len(account_id):
        return digits == account_id
    if account_name and _text(name):
        return _fold(account_name) == _fold(name)
    return None


def loai_to_khai(values: dict, options: dict | None) -> tuple[str, bool]:
    """(Cá nhân / Khai hộ, suy đoán). Tài khoản trùng người yêu cầu → Cá nhân; khác → Khai hộ; thiếu mốc tài khoản →
    theo mẫu tờ khai (ô vàng)."""
    account_name, account_id = requester_context(options)
    same = _same_person(account_name, account_id, values.get("NYC_HoTen"), values.get("NYC_SoGiayTo"))
    if same is not None:
        return (CA_NHAN if same else KHAI_HO), False
    return (KHAI_HO if _truthy(values.get("ToKhai_UyQuyen")) else CA_NHAN), True


def _age(birth: date | None) -> int | None:
    if not birth:
        return None
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def _id_document(values: dict, ocr_text: str) -> dict:
    """Loại / số / ngày cấp / nơi cấp giấy tờ của người yêu cầu. Mặt sau thẻ khớp MRZ thắng giá trị LLM ghép."""
    number = _text(values.get("NYC_SoGiayTo"))
    digits = _digits(number)
    if len(digits) in (9, 12):
        number = digits
    if not number:
        return {}
    card_date, card_issuer = _card_back(ocr_text, digits)
    issue_date = card_date or _full_date(values.get("NYC_NgayCap"))
    issuer = card_issuer or normalize_issuer(values.get("NYC_NoiCap")) or (
        default_issuer(issue_date) if len(digits) == 12 and issue_date else "")
    issuer = issuer_by_issue_date(issuer, issue_date)
    doc_type = _id_doc_type_with_number(number, values.get("NYC_LoaiGiayTo"), issuer)
    # Danh mục cổng ghi "Căn cước" cho thẻ theo Luật Căn cước 2023 (mapping); thiếu mục đó thì extension khớp gần nhất.
    if _fold(doc_type) == "the can cuoc":
        doc_type = "Căn cước"
    return {"type": doc_type, "number": number, "date": issue_date, "issuer": short_issuer(issuer)}


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = {f.get("name"): f.get("value") for f in fields or [] if isinstance(f, dict)}
    options = options or {}
    ocr_text = str(options.get("_ocr_text") or "")
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False, **extra) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        field = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": value, **extra}
        if default:
            field["default"] = True  # extension tô viền vàng: giá trị không đọc thẳng từ giấy tờ
        out.append(field)
        seen.add(name)

    def add_area(names: tuple[str, str, str], area: dict | None) -> None:
        if not area:
            return
        add(names[0], area.get("tinh"))
        # Xã nạp theo tỉnh: thiếu tỉnh thì chọn xã là chọn trên danh mục rỗng.
        if area.get("tinh"):
            add(names[1], area.get("xa"))
        add(names[2], area.get("diaChi"))

    variant, guessed = loai_to_khai(values, options)
    # Radio chốt TRƯỚC: cổng ẩn/hiện cả khối ô theo lựa chọn này.
    add("citizenLoaiToKhai", variant, default=guessed, code=_LOAI_TO_KHAI_CODE[variant])

    birth = _full_date(values.get("NYC_NgaySinh"))
    id_doc = _id_document(values, ocr_text)
    residence = _area(values.get("NYC_NoiThuongTru"))
    temporary = _area(values.get("NYC_NoiTamTru"))
    phone = _phone(values.get("NYC_SoDienThoai"))
    email = _email(values.get("NYC_Email"))
    spouse = upper_person_name(values.get("NYC_HoTenVoChong"))

    if variant == CA_NHAN:
        add("citizenField18", id_doc.get("type"))
        add("citizenTenGoiKhac_NYC", _other_name(values.get("NYC_TenGoiKhac")))
        add("citizenDateOfBirth", birth)
        add_area(("citizenCauhoi1", "citizenField33", "citizenDiaChiCuThe"), temporary)
        add("citizenHoVaTenVoChong_NYC", spouse)
        add("citizenPhone", phone)
        add("citizenEmail", email)
    else:
        account_name, account_id = requester_context(options)
        declarant_is_account = _same_person(account_name, account_id, values.get("NguoiKhai_HoTen"),
                                            values.get("NguoiKhai_SoGiayTo"))
        # Ô điện thoại + quan hệ của khối người được ủy quyền là của TÀI KHOẢN: chỉ lấy từ người khai trên tờ khai khi
        # người đó chính là tài khoản (hoặc không có mốc tài khoản để so).
        if declarant_is_account is not False:
            add("citizenSoDienThoai_NYC_UyQuyen", _phone(values.get("NguoiKhai_SoDienThoai")))
            add("citizenMoiQuanHe_NYC_NguoiUyQuyen", _text(values.get("NguoiKhai_QuanHe")))
        if "citizenMoiQuanHe_NYC_NguoiUyQuyen" not in seen:
            warnings.append(RELATION_WARNING)

        add("citizenLoaiGiayTo_NguoiUyQuyen", id_doc.get("type"))
        add("citizenSoGiayTo_NguoiUyQuyen", id_doc.get("number"))
        add("citizenNgayCap_NguoiUyQuyen", id_doc.get("date"))
        add("citizenNoiCap_NguoiUyQuyen", id_doc.get("issuer"))
        add("citizenHoVaTen_NguoiUyQuyen", upper_person_name(values.get("NYC_HoTen")))
        add("citizenField32", _other_name(values.get("NYC_TenGoiKhac")))
        add("citizenNgaySinh_NguoiUyQuyen", birth)
        add("citizenGioiTinh_NguoiUyQuyen", _gender(values.get("NYC_GioiTinh")))
        birth_place = _area(values.get("NYC_NoiSinh"))
        if birth_place:
            add("NoiSinhDangKy_QuocGia_NguoiUyQuyen", birth_place.get("quocGia"))
            if birth_place.get("quocGia") == _VIET_NAM and birth_place.get("tinh"):
                # Ô Tỉnh / Xã của panel động chỉ hiện sau khi chọn Quốc gia, tên ô chưa biết → extension dò theo nhãn
                # ("Tỉnh/ thành phố", "Xã/ Phường") ngay sau ô Quốc gia (setArea).
                add("NoiSinhDangKy_NguoiUyQuyen", {"quocGia": _VIET_NAM, "tinh": birth_place.get("tinh"),
                                                   "xa": birth_place.get("xa") or ""},
                    radio="NoiSinhDangKy_QuocGia_NguoiUyQuyen")
        nationality = _text(values.get("NYC_QuocTich"))
        vn_card = len(_digits(id_doc.get("number"))) == 12
        add("QuocTich_NguoiUyQuyen", nationality or (_VIET_NAM if vn_card else ""), default=not nationality)
        add("citizenDanToc_NguoiUyQuyen", co_ho_local_group(values.get("NYC_DanToc")))
        add_area(("citizenNoiThuongTru_MaTinh_NguoiUyQuyen", "citizenNoiThuongTru_MaXa_NguoiUyQuyen",
                  "citizenNoiThuongTru_DiaChiChiTiet_NguoiUyQuyen"), residence)
        add_area(("citizenNoiTamTru_MaTinh_NguoiUyQuyen", "citizenNoiTamTru_MaXa_NguoiUyQuyen",
                  "citizenNoiTamTru_DiaChiChiTiet_NguoiUyQuyen"), temporary)
        add("citizenHoTenCha_NguoiUyQuyen", upper_person_name(values.get("NYC_HoTenCha")))
        add("citizenHoVaTenMe_NguoiUyQuyen", upper_person_name(values.get("NYC_HoTenMe")))
        add("citizenHoVaTenVoChong_NguoiUyQuyen", spouse)
        add("citizenSoDienThoai_NguoiUyQuyen", phone)
        add("citizenEmail_NguoiUyQuyen", email)

    # Loại phiếu: tờ khai ghi rõ thì theo tờ khai; khai hộ cho người đã thành niên là ủy quyền → chỉ được Phiếu số 1.
    # Còn lại giữ lựa chọn cổng để sẵn (Loại phiếu số 1).
    so_phieu = _digits(values.get("LoaiPhieu"))
    age = _age(_parse_date(birth))
    if so_phieu in ("1", "2"):
        add("citizenLoaiPhieu", f"Loại phiếu số {so_phieu}")
    elif variant == KHAI_HO and age is not None and age >= _TUOI_THANH_NIEN:
        add("citizenLoaiPhieu", "Loại phiếu số 1", default=True)

    confirm = _fold(values.get("YeuCauCDNCV"))
    if confirm in ("co", "khong"):
        add("YeuCauCDNCV", "Có" if confirm == "co" else "Không")
    else:
        add("YeuCauCDNCV", "Không", default=True)

    warnings.append(FEE_WARNING)
    quantity = _digits(values.get("SoLuongPhieu"))
    if quantity and int(quantity) > 0:
        extra = max(0, int(quantity) - 2)
        warnings.append(f"Tờ khai xin {int(quantity)} phiếu: ở tab 'PHÍ, LỆ PHÍ' đặt số lượng 'từ bản thứ 3' = {extra} "
                        f"(cổng để sẵn 1).")
    return out, warnings
