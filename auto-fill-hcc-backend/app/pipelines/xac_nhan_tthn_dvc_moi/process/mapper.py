"""Dịch dữ kiện đã trích sang câu hỏi SurveyJS của tờ khai cấp Giấy XNTTHN (Cổng DVC quốc gia mới).

Giá trị nào không khớp được danh mục / định dạng của cổng thì BỎ TRỐNG cho cán bộ, không gửi giá trị cổng sẽ báo
lỗi validate.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import is_current_area, remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type, normalize_issuer
from app.pipelines._shared.ethnic_normalize import co_ho_local_group, normalize_ethnic
from app.pipelines._shared.formatting import upper_person_name
from app.pipelines._shared.nationality import normalize_nationality
from app.pipelines._shared.tai_khoan import account_context, date_key, matches_account

from .reason import labeled_value, section
from .schema import GIOI_TINH, LOAI_CU_TRU, LOAI_GIAY_TO, MUC_DICH, NOI_CU_TRU, QUAN_HE, TINH_TRANG, UI_COMP_BY_NAME

_DATE_RE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b")
_HCM_PROVINCE_KEYS = {"hochiminh", "tphochiminh", "thanhphohochiminh", "tphcm", "hcm"}
_ADDRESS_PART_RE = re.compile(r"[,;\n]|\s[-–]\s")

# Mã option tình trạng hôn nhân của cổng mới (khác eForm cũ: 1 = chưa đăng ký, 2 = đang có vợ/chồng).
_NEVER_MARRIED, _MARRIED, _DIVORCED, _WIDOWED, _PERIOD_MARRIED, _OTHER = "1", "2", "3", "4", "5", "6"
_STATUS_BY_KEY = {
    "chua_ket_hon": _NEVER_MARRIED, "co_vo_chong": _MARRIED, "ly_hon": _DIVORCED, "goa": _WIDOWED,
    "khoang_thoi_gian": _PERIOD_MARRIED, "khac": _OTHER,
}
# "hiện tại" là chữ chốt: nhãn ly hôn/góa cũng có cụm "đã có vợ/chồng" nhưng nói về QUÁ KHỨ.
_NOW_MARRIED_MARKERS = (
    "hien tai dang co", "hien tai co vo", "hien tai co chong", "hien tai da ket hon",
    "hien nay dang co", "hien nay co vo", "hien nay co chong", "hien nay da ket hon",
    "dang co vo", "dang co chong",
)
_WIDOW_MARKERS = ("da chet", "da qua doi", "da mat", "goa")
_NEVER_MARRIED_MARKERS = ("chua dang ky ket hon", "chua ket hon", "chua co vo", "chua co chong", "doc than")
_SELF_RELATIONS = {"ban than", "tu khai", "chinh minh"}
_PURPOSE_BY_KEY = {"ket_hon_co_quan_dai_dien": "1", "ket_hon_nuoc_ngoai": "2", "khac": "3"}


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _compact(value) -> str:
    return re.sub(r"[^a-z0-9]", "", _fold(value))


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _snap(table: dict, label) -> tuple[str, str] | None:
    """(code, nhãn danh mục) khớp đúng nhãn; không khớp chắc thì None."""
    key = _compact(label)
    if not key:
        return None
    return next(((code, text) for code, text in table.items() if _compact(text) == key), None)


def _full_date(value) -> str:
    match = _DATE_RE.search(str(value or ""))
    if not match:
        return ""
    day, month, year = match.groups()
    return f"{int(day):02d}/{int(month):02d}/{year}"


def _iso(ddmmyyyy: str) -> str:
    day, month, year = ddmmyyyy.split("/")
    return f"{year}-{month}-{day}"


def _id_doc_type_with_number(number, hint, issuer: str = "") -> str:
    # Căn cước/CCCD luôn 12 chữ số → số 9 chữ số chỉ có thể là CMND cũ (trừ khi giấy ghi rõ hộ chiếu).
    if len(_digits(number)) == 9 and "chieu" not in _fold(hint):
        return "Chứng minh nhân dân"
    return id_doc_type(hint or "Căn cước", issuer)


def _selectable(area: dict) -> bool:
    ward = str(area.get("xa") or "")
    return bool(ward) and is_current_area(str(area.get("tinh") or ""), ward)


def _ward_after_read_name(area: dict, remapped: dict, ocr_text: str) -> dict | None:
    """LLM lấy thôn/khu làm xã: thẻ CCCD in nơi thường trú hai dòng ("...: Khu A" / "Xã B, Huyện C, Tỉnh D") nên
    dòng đầu bị đọc thành xã. Tìm tên đã đọc trên giấy, cụm ĐẦU TIÊN ngay sau nó remap ra xã hiện hành cùng tỉnh
    là xã thật; tên đã đọc lùi về địa chỉ chi tiết."""
    name = _fold(area.get("xa"))
    if not name or not ocr_text:
        return None
    word = re.compile(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])")
    lines = ocr_text.splitlines()
    for i, line in enumerate(lines):
        if not word.search(_fold(line)):
            continue
        parts = [p.strip() for p in _ADDRESS_PART_RE.split("\n".join(lines[i:i + 2]))]
        start = next((j for j, part in enumerate(parts) if word.search(_fold(part))), None)
        if start is None:
            continue
        for part in parts[start + 1:start + 4]:
            if not part:
                continue
            found = remap_area({**area, "xa": part, "diaChi": ""})
            if not isinstance(found, dict) or not _selectable(found):
                continue
            if remapped.get("tinh") and _fold(found.get("tinh")) != _fold(remapped.get("tinh")):
                continue
            detail = str(area.get("diaChi") or "").strip()
            return {**found, "diaChi": f"{detail}, {area['xa']}" if detail else area["xa"]}
    return None


def _area(value, ocr_text: str = ""):
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
    if _fold(area["quocGia"]) not in ("viet nam", "vn"):
        return area
    huyen = str(value.get("huyen") or "").strip()
    remapped = remap_area({**area, "huyen": huyen} if huyen else dict(area))
    if not isinstance(remapped, dict):
        return area
    if area["xa"] and not _selectable(remapped):
        recovered = _ward_after_read_name(area, remapped, ocr_text)
        if recovered:
            return recovered
    # Xã cũ đã sáp nhập sang đơn vị mới khác tên → giữ tên cũ cuối địa chỉ chi tiết để lần ra địa bàn.
    old_name = re.sub(r"^(xã|phường|thị trấn)\s+", "", area["xa"], flags=re.IGNORECASE).strip()
    new_ward = str(remapped.get("xa") or "")
    detail = str(remapped.get("diaChi") or "").strip()
    if old_name and new_ward and _fold(old_name) not in _fold(new_ward) and _fold(old_name) not in _fold(detail):
        remapped = {**remapped, "diaChi": f"{detail}, {area['xa']}" if detail else area["xa"]}
    # Xã không chọn được trên cổng (kể cả thôn/xóm remap đã đẩy về địa chỉ chi tiết): extension để trống mà không báo.
    # Bỏ trống xã, giữ tên đã đọc ở cuối địa chỉ chi tiết, đánh dấu để tô viền vàng.
    ward = str(remapped.get("xa") or "")
    if area["xa"] and not _selectable(remapped):
        detail = str(remapped.get("diaChi") or "").strip()
        if ward and _fold(ward) not in _fold(detail):
            detail = f"{detail}, {ward}" if detail else ward
        remapped = {**remapped, "xa": "", "diaChi": detail, "_xaChuaChon": True}
    return remapped


def _submitter_phone(value, context: str) -> str:
    """Số điện thoại người nộp đọc từ giấy: chỉ khi người nộp có trong hồ sơ và số đúng dạng di động/cố định VN."""
    if _fold(labeled_value(section(context, "nguoi_nop"), "Có trong hồ sơ")) != "co":
        return ""
    digits = _digits(value)
    if digits.startswith("84") and len(digits) in (11, 12):
        digits = "0" + digits[2:]
    return digits if re.fullmatch(r"0\d{9,10}", digits) else ""


def _relation(values: dict, context: str, options: dict | None) -> tuple[str, str, bool, str]:
    """(mã quan hệ, chữ quan hệ khác, suy đoán, cảnh báo). Kết luận của bước phân vai → đối chiếu tài khoản."""
    reasoned = labeled_value(section(context, "quan_he"), "Kết luận")
    account = account_context(options)
    subject = (values.get("NguoiDuocCap_HoTen"), values.get("NguoiDuocCap_SoDinhDanh"), values.get("NguoiDuocCap_NgaySinh"))
    # None = không đủ dữ kiện đối chiếu (cổng không truyền tài khoản / không đọc được người được cấp).
    is_account = matches_account(account, *subject) if (
        (account.get("HoTen") or account.get("SoDinhDanh")) and (subject[0] or subject[1])) else None
    other_warning = "Người nộp khác người được cấp — cán bộ ghi mối quan hệ khác."
    if reasoned and _fold(reasoned) not in _SELF_RELATIONS:
        return "2", reasoned, False, ""
    if reasoned and is_account is not False:
        return "1", "", False, ""
    # Tài khoản đăng nhập rõ ràng là người khác: "Tự khai" trên tờ khai là của người yêu cầu, không phải người nộp.
    if is_account is False:
        return "2", "", True, other_warning
    if is_account:
        return "1", "", True, ""
    return "", "", False, "Chưa xác định được quan hệ của người nộp với người được cấp — cán bộ chọn ô Quan hệ."


def _status_code(value) -> str | None:
    """Mã chữ LLM trả → mã option; LLM lỡ trả chữ thì nhận theo từ khoá. Thứ tự từ khoá không đảo: nhãn ly hôn/góa
    cũng kết thúc bằng "chưa đăng ký kết hôn", còn "đã ly hôn RỒI CƯỚI LẠI" phải ra đang có vợ/chồng."""
    folded = _fold(value)
    if not folded:
        return None
    code = _STATUS_BY_KEY.get(folded.strip(" \"'."))
    if code:
        return code
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
    return None


def _marital_status(values: dict) -> str | None:
    """Chốt mã option tình trạng hôn nhân từ mã tờ khai + giấy tờ ly hôn / khai tử / kết hôn."""
    divorce = [values.get(f"BanAn_{k}") or values.get(f"DivorceDecision_{k}") for k in ("Number", "Date", "Agency")]
    death = [values.get(f"DeathCert_{k}") for k in ("Number", "Date", "Agency")]
    marriage = [values.get(f"Marriage_{k}") for k in ("SpouseName", "Number", "Date", "Agency")]
    declared = _status_code(values.get("TinhTrangHonNhan"))
    has_divorce, has_death, has_marriage = any(divorce), any(death), any(marriage)
    prior_end = [key for key in (date_key(_full_date(divorce[1])), date_key(_full_date(death[1]))) if key]
    married_key = date_key(_full_date(marriage[2]))
    # Giấy kết hôn hiện tại đăng ký SAU mốc ly hôn/khai tử của cuộc hôn nhân trước → đã kết hôn lại.
    remarried = bool(has_marriage and married_key and prior_end and married_key > max(prior_end))

    if values.get("Period_TuNgay") and values.get("Period_DenNgay") and has_marriage:
        # Xin xác nhận chưa ĐKKH trong khoảng đã qua mà nay đã có vợ/chồng: option riêng, chọn "đang có vợ/chồng" là
        # mất khoảng thời gian người dân cần xác nhận.
        return _PERIOD_MARRIED
    if remarried and not declared:
        return _MARRIED
    if declared == _PERIOD_MARRIED and not has_marriage:
        # Option "khoảng thời gian" chỉ dành cho người NAY đã có vợ/chồng (cổng bắt nhập vợ/chồng + giấy kết hôn):
        # không có dấu vết hôn nhân hiện tại thì khoảng thời gian xin xác nhận là của người vẫn chưa kết hôn.
        declared = _DIVORCED if has_divorce else _WIDOWED if has_death else _NEVER_MARRIED
    if declared == _NEVER_MARRIED and (has_death or has_divorce):
        # "Chưa đăng ký kết hôn" là đuôi chung của ly hôn/góa: có giấy tờ thì mã cụ thể hơn mới đúng.
        return _WIDOWED if has_death else _DIVORCED
    if declared:
        return declared
    if has_death:
        return _WIDOWED
    if has_divorce:
        return _DIVORCED
    # Hồ sơ không có tờ khai (chỉ CCCD + phiếu tra CSDL dân cư) vẫn đọc được tên vợ/chồng hiện tại.
    if marriage[0] or (marriage[1] and marriage[2]):
        return _MARRIED
    return None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = {f.get("name"): f.get("value") for f in fields or [] if isinstance(f, dict)}
    options = options or {}
    context = str(options.get("_reasoning_context") or "")
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value, *, code: str | None = None, default: bool = False) -> dict | None:
        if name in seen or value in (None, "", {}, []):
            return None
        field = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": value}
        if code:
            field["code"] = code
        if default:
            field["default"] = True  # extension tô viền vàng: giá trị không đọc từ giấy tờ
        out.append(field)
        seen.add(name)
        return field

    def add_choice(name: str, table: dict, code: str, *, default: bool = False) -> None:
        if code in table:
            add(name, table[code], code=code, default=default)

    def add_date(name: str, raw) -> dict | None:
        text = _full_date(raw)
        return add(name, text, code=_iso(text)) if text else None

    def add_text(name: str, raw) -> None:
        add(name, " ".join(str(raw or "").split()))

    add("citizenPhone", _submitter_phone(values.get("NguoiNop_SoDienThoai"), context))
    # Người nộp là chủ tài khoản định danh trong nước; chọn sẵn để cổng hiện địa chỉ thường trú đã đổ từ tài khoản.
    add_choice("citizenNycNoicutru", NOI_CU_TRU, "1", default=True)
    # Quan hệ chốt trước: chọn "Khác" thì cổng mới hiện ô ghi quan hệ.
    relation, other, guessed, warning = _relation(values, context, options)
    if warning:
        warnings.append(warning)
    add_choice("citizenQuanhevoinguoiduoccapGiayxacnhantinhtranghonnhan", QUAN_HE, relation, default=guessed)
    add("citizenField13", other)

    # Ba ô tra cứu CSDL dân cư đi đầu (cờ lookup): cổng tra được thì tự đổ + khóa giới tính, dân tộc, giấy tờ.
    personal_id = _digits(values.get("NguoiDuocCap_SoDinhDanh"))
    lookup = [
        add("citizenNDKHochudemtenngdccap", upper_person_name(values.get("NguoiDuocCap_HoTen"))),
        add_date("citizenNDKNgaythangnamsinh", values.get("NguoiDuocCap_NgaySinh")),
        add("citizenNDKSoDinhDanh", personal_id if len(personal_id) == 12 else ""),  # cổng chỉ nhận 12 số
    ]
    for item in lookup:
        if item:
            item["lookup"] = True
    if not values.get("NguoiDuocCap_HoTen"):
        warnings.append("Không đọc được người được cấp Giấy XNTTHN — cán bộ nhập khối người được cấp.")

    # Cổng tra được CSDL dân cư thì tự đổ các ô dưới (extension không ghi đè); tra không ra thì điền theo giấy tờ.
    gender = _snap(GIOI_TINH, values.get("NguoiDuocCap_GioiTinh"))
    if gender:
        add_choice("citizenNDKGioitinh", GIOI_TINH, gender[0])
    # Danh mục cổng không có "Khác": nhóm địa phương Cill/K'Ho/Lạch quy về Cơ Ho.
    ethnic = values.get("NguoiDuocCap_DanToc") or values.get("GiayToKhac_DanToc")
    add("citizenNDKDantoc", normalize_ethnic(co_ho_local_group(ethnic)) or None)
    number = _digits(values.get("NguoiDuocCap_SoGiayTo")) or (
        personal_id if values.get("NguoiDuocCap_NgayCap") else "")
    nationality = values.get("NguoiDuocCap_QuocTich")
    if nationality or number:
        # Có thẻ căn cước/CMND mà giấy không ghi quốc tịch → công dân Việt Nam, tô vàng.
        nationality = normalize_nationality(nationality, "Việt Nam", exact_only=True)
        add("citizenField20", nationality, code="VN" if _fold(nationality) == "viet nam" else None,
            default=not values.get("NguoiDuocCap_QuocTich"))
    if number:
        issue_date = _full_date(values.get("NguoiDuocCap_NgayCap"))
        # Mặc định cơ quan cấp theo ngày chỉ đúng với thẻ căn cước 12 số.
        issuer = normalize_issuer(values.get("NguoiDuocCap_NoiCap")) or (
            default_issuer(issue_date) if len(number) == 12 and issue_date else "")
        id_type = _snap(LOAI_GIAY_TO, _id_doc_type_with_number(number, values.get("NguoiDuocCap_LoaiGiayTo"), issuer))
        if id_type:
            add_choice("citizenNDKLoaigiayto", LOAI_GIAY_TO, id_type[0])
        add("citizenNDKSogiaytotuythan", number)
        add_date("citizenNDKNgaycap", issue_date)
        add("citizenNDKNocap", issuer)

    # Loại cư trú + radio quyết định cụm ô địa chỉ nào hiện ra nên đi trước. Loại cư trú không in trên giấy tờ nào →
    # mặc định Thường trú, tô vàng.
    residence = _area(values.get("NguoiDuocCap_NoiCuTru"), str(options.get("_ocr_text") or ""))
    if residence:
        add_choice("citizenNDKLoaicutru", LOAI_CU_TRU, "1", default=True)
        if _fold(residence.get("quocGia")) in ("viet nam", "vn"):
            add_choice("citizenNDKnoicutru", NOI_CU_TRU, "1")
            add("citizenNDKTinh_ThTru", residence.get("tinh"))
            add("citizenNDKXa_ThTru", residence.get("xa"))
            add("citizenNDKDiaChi_ThTru", residence.get("diaChi"), default=bool(residence.get("_xaChuaChon")))
            if residence.get("_xaChuaChon"):
                warnings.append("Chưa chọn được phường/xã nơi cư trú của người được cấp theo danh mục hiện hành — "
                                "cán bộ chọn lại ô Phường/Xã.")
        else:
            add_choice("citizenNDKnoicutru", NOI_CU_TRU, "2")
            add("citizenNDKQG_Khac", residence.get("quocGia"))
            add("citizenNDKDiachi_Khac", residence.get("diaChi"))

    # Tình trạng hôn nhân: chọn option trước, vùng chi tiết chỉ hiện sau khi chọn.
    status = _marital_status(values)
    if status:
        add_choice("citizenTinhtranghonnhan", TINH_TRANG, status)
    if status == _MARRIED:
        add("citizenHovatencuavochongnguoicoyeucauxacnhantinhtranghonnhan",
            upper_person_name(values.get("Marriage_SpouseName")))
        add_text("citizenField40", values.get("Marriage_Number"))
        add_date("citizenField41", values.get("Marriage_Date"))
        add_text("citizenField42", values.get("Marriage_Agency"))
    elif status == _DIVORCED:
        # Văn bản bản án thật (BanAn_*) thắng dòng người dân tự chép lên tờ khai (DivorceDecision_*) — tờ khai hay
        # chép nhầm năm/cơ quan; ô văn bản không đọc được thì tờ khai bù.
        add_text("citizenSoBananQuyetdinhlyhon", values.get("BanAn_Number") or values.get("DivorceDecision_Number"))
        add_date("citizenField46", values.get("BanAn_Date") or values.get("DivorceDecision_Date"))
        add_text("citizenField47", values.get("BanAn_Agency") or values.get("DivorceDecision_Agency"))
    elif status == _WIDOWED:
        add_text("citizenSogiaychungtuTrichluckhaituBanan", values.get("DeathCert_Number"))
        add_date("citizenField50", values.get("DeathCert_Date"))
        add_text("citizenField51", values.get("DeathCert_Agency"))
    elif status == _PERIOD_MARRIED:
        add("citizenField531", upper_person_name(values.get("Marriage_SpouseName")))
        add_text("citizenField53", values.get("Marriage_Agency"))
        add_text("citizenField54", values.get("Marriage_Number"))
        add_date("citizenField55", values.get("Marriage_Date"))
        add_date("citizenField56", values.get("Period_TuNgay"))
        add_date("citizenField57", values.get("Period_DenNgay"))
    elif status == _OTHER:
        add_text("citizenField59", values.get("TinhTrangHonNhan_NoiDung"))

    # Mục đích đã được bước phân vai khôi phục câu chữ; không chắc thì vẫn điền nhưng tô vàng cho cán bộ soát.
    purpose_block = section(context, "muc_dich")
    purpose_text = labeled_value(purpose_block, "Nội dung")
    purpose = _PURPOSE_BY_KEY.get(_fold(labeled_value(purpose_block, "Loại")).replace(" ", "_"))
    # Không xác định được loại → mặc định "Sử dụng vào mục đích khác" (trường hợp phổ biến nhất), tô vàng.
    add_choice("citizenField60", MUC_DICH, purpose or "3", default=not purpose)
    purpose = purpose or "3"
    if purpose == "3":
        add("citizenField69", purpose_text, default=_fold(labeled_value(purpose_block, "Độ chắc")) == "thap")
    elif purpose in ("1", "2"):
        add("citizenHochudemtendaiienncngoai", upper_person_name(values.get("KetHonVoi_HoTen")))
        add_date("citizenDaidienngaysinh", values.get("KetHonVoi_NgaySinh"))
        if values.get("KetHonVoi_QuocTich"):
            add("citizenDaidienquoctich", normalize_nationality(values["KetHonVoi_QuocTich"], "", exact_only=True))
        id_type = _snap(LOAI_GIAY_TO, values.get("KetHonVoi_LoaiGiayTo"))
        if id_type:
            add_choice("citizenDaidiengiaytotuythan", LOAI_GIAY_TO, id_type[0])
        add_text("citizenDaidiensogiayto", values.get("KetHonVoi_SoGiayTo"))
        add_date("citizenDaidienngaycap", values.get("KetHonVoi_NgayCap"))
        add_text("citizenDaidiencoquancap", values.get("KetHonVoi_CoQuanCap"))
        add_text("citizenDaidiendiachi", values.get("KetHonVoi_DiaChi"))
        add_text("citizenNoidudinhdangkykethon", values.get("KetHonVoi_NoiDuDinh"))
        if values.get("KetHonVoi_QuocGia"):
            add("citizenDaidienquocgia", normalize_nationality(values["KetHonVoi_QuocGia"], "", exact_only=True))

    # Ô bắt buộc, cổng ghi "điền 0 nếu không cần": không đọc được yêu cầu bản sao thì điền 0, tô vàng.
    quantity = _digits(values.get("SoLuongBanSao"))
    if quantity:
        add("citizenField70", str(int(quantity)))
    else:
        add("citizenField70", "0", default=True)
    return out, warnings
