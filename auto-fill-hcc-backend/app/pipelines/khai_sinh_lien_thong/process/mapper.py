"""Map compact OCR-derived birth registration facts to Angular UI fields."""

import re
import unicodedata
from datetime import date, timedelta

from app.pipelines._shared.area_remap import city_province_area, remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.ethnic_normalize import OTHER_ETHNICITY_NAMES, normalize_ethnic
from app.pipelines._shared.foreign_id import is_foreign
from app.pipelines._shared.hospital_lookup import hospital_area, lookup_hospital
from app.pipelines.khai_sinh_lien_thong.process.schema import QUOC_TICH_QUOC_GIA, STATIC_DEFAULTS, UI_COMP_BY_NAME


# Cấu hình theo tài khoản: 4 phường Đà Lạt (Xuân Hương, Lâm Viên, Cam Ly, Lang Biang — Lâm Đồng) mục
# "Thông tin cấp thẻ BHYT" luôn chọn giám hộ trên thẻ = mẹ và nơi KCB ban đầu = Bệnh viện Sản - Nhi tỉnh Lâm
# Đồng. Phường Hải Châu (Đà Nẵng) và Phường Nha Trang (Khánh Hòa) chỉ chọn giám hộ trên thẻ = mẹ, nơi
# KCB để cán bộ tự chọn.
# Mapper không biết tài khoản nên router (Auto Fill) và pipeline_runner (Handfree) gọi
# with_account_process_options để server tự đặt cờ; cờ luôn bị ghi đè theo tài khoản, client không
# tự bật được cho xã khác.
PROCEDURE_KEY = "khai-sinh-dang-ky"
DA_LAT_BHYT_OPTION = "daLatBhytDefaults"
HAI_CHAU_BHYT_OPTION = "haiChauBhytDefaults"
NHA_TRANG_BHYT_OPTION = "nhaTrangBhytDefaults"
_DA_LAT_WARDS = {"xuan huong", "lam vien", "cam ly", "lang biang"}
_WARD_PREFIXES = ("xa ", "phuong ", "thi tran ")
# ng-select Nơi KCB: extension gõ chuỗi này vào ô tìm rồi chọn option CHỨA nó.
DA_LAT_NOI_KCB = "Bệnh viện Sản - Nhi tỉnh Lâm Đồng"


def _account_area(user: dict | None) -> tuple[str, str]:
    """(tỉnh, xã) của tài khoản đã bỏ dấu, bỏ tiền tố Xã/Phường/Thị trấn."""
    if not user:
        return "", ""
    tinh = re.sub(r"[^a-z0-9]+", " ", _fold(user.get("tinh"))).strip()
    xa = re.sub(r"[^a-z0-9]+", " ", _fold(user.get("xa"))).strip()
    for prefix in _WARD_PREFIXES:
        if xa.startswith(prefix):
            xa = xa[len(prefix):].strip()
            break
    return tinh, xa


def is_da_lat_bhyt_ward(user: dict | None) -> bool:
    """True khi tài khoản thuộc phường Xuân Hương/Lâm Viên/Cam Ly/Lang Biang - Đà Lạt, tỉnh Lâm Đồng."""
    tinh, xa = _account_area(user)
    if xa.endswith(" da lat"):
        xa = xa[: -len(" da lat")].strip()
    return "lam dong" in tinh and xa in _DA_LAT_WARDS


def is_hai_chau_bhyt_ward(user: dict | None) -> bool:
    """True khi tài khoản thuộc Phường Hải Châu, thành phố Đà Nẵng."""
    tinh, xa = _account_area(user)
    return "da nang" in tinh and xa == "hai chau"


def is_nha_trang_bhyt_ward(user: dict | None) -> bool:
    """True khi tài khoản thuộc ĐÚNG Phường Nha Trang, tỉnh Khánh Hòa (Bắc/Nam/Tây Nha Trang không tính)."""
    tinh, xa = _account_area(user)
    return "khanh hoa" in tinh and xa == "nha trang"


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Trả bản sao options với cờ mặc định BHYT (Đà Lạt, Hải Châu, Nha Trang) do server quyết theo tài khoản."""
    result = dict(options or {})
    result.pop(DA_LAT_BHYT_OPTION, None)
    result.pop(HAI_CHAU_BHYT_OPTION, None)
    result.pop(NHA_TRANG_BHYT_OPTION, None)
    if procedure == PROCEDURE_KEY and is_da_lat_bhyt_ward(user):
        result[DA_LAT_BHYT_OPTION] = True
    if procedure == PROCEDURE_KEY and is_hai_chau_bhyt_ward(user):
        result[HAI_CHAU_BHYT_OPTION] = True
    if procedure == PROCEDURE_KEY and is_nha_trang_bhyt_ward(user):
        result[NHA_TRANG_BHYT_OPTION] = True
    return result


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _fold(value) -> str:
    """Bỏ dấu + lowercase để so khớp bất chấp OCR hoa/thường/dấu (kể cả đ→d)."""
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.replace("Đ", "D").replace("đ", "d").lower().strip()


def _first_token(full_name) -> str:
    parts = [p for p in str(full_name or "").split() if p]
    return parts[0] if parts else ""


def _align_father_surname(father_name, child_name) -> str:
    """OCR CCCD hay đọc lệch dấu họ cha ("TỔNG" thay "TỐNG", MRZ cùng "TONG"). Họ cha chỉ khác họ con
    ở dấu → viết theo họ con trên giấy chứng sinh/tờ khai; chữ đệm và tên giữ nguyên."""
    parts = str(father_name or "").split()
    child_ho = _first_token(child_name)
    if parts and child_ho and parts[0] != child_ho and _fold(parts[0]) == _fold(child_ho):
        parts[0] = child_ho
    return " ".join(parts)


def _upper_name(value) -> str:
    """Tên chủ thể trên form hộ tịch phải viết IN HOA, đồng thời gom khoảng trắng OCR."""
    return " ".join(str(value or "").split()).upper()


def _ethnicity_for_form(value) -> tuple[str, str]:
    """Cil/Cill/Cao Lan không có option riêng: chọn Khác và giữ nguyên cách ghi vào ô nhập tay."""
    raw = str(value or "").strip()
    if not raw:
        return "", ""
    if _fold(raw) in OTHER_ETHNICITY_NAMES:
        return "Khác", raw
    return normalize_ethnic(raw), ""


# Bệnh viện Hoàn Mỹ Đà Lạt: chi tiết nơi sinh luôn ghi đủ "… - Đồi Long Thọ". OCR tờ khai viết tay hay
# đọc "Đồi" thành "Đài"/"Đổi" (hoặc bỏ mất phần đuôi) → ghi cố định cả cụm thay vì chép đuôi OCR.
_HOAN_MY_DA_LAT = "Bệnh viện Đa khoa Hoàn Mỹ Đà Lạt - Đồi Long Thọ"


def _blank_dots(value) -> str:
    """Bỏ dấu chấm điền chỗ trống của mẫu in ("49..." → "49"); chỉ có chấm → rỗng."""
    text = re.sub(r"[.…\s]+$", "", str(value or "")).strip()
    return text if re.search(r"\w", text) else ""


def _norm_birth_place(area):
    """Nơi sinh là cơ sở y tế tuyến tỉnh (vd "Bệnh viện đa khoa TỈNH") mà OCR ghi tắt, thiếu tên
    tỉnh → nối tên tỉnh vào chi tiết để ra "Bệnh viện đa khoa tỉnh <Tỉnh>"."""
    if not isinstance(area, dict):
        return area
    tinh = area.get("tinh") or area.get("tỉnh")
    dia = str(area.get("diaChi") or area.get("dia_chi") or area.get("diachi") or "").strip()
    xa = area.get("xa") or area.get("xã")
    low = _fold(dia)
    if "hoan my" in low and "da lat" in low:
        return {**area, "diaChi": _HOAN_MY_DA_LAT}
    if not (tinh and dia):
        return area
    out = dict(area)
    is_facility = any(k in low for k in ("benh vien", "trung tam y te", "tram y te", "phong kham", "nha ho sinh"))
    if is_facility and _fold(tinh) not in low and re.search(r"(tinh|thanh pho)$", low):
        dia = f"{dia} {tinh}"
        out["diaChi"] = dia
    # Bệnh viện đa khoa TỈNH LAI CHÂU đặt trụ sở tại phường/xã Tân Phong → điền xã khi OCR thiếu
    # (few-shot prompt hay bỏ sót). Chỉ áp cho bệnh viện tuyến tỉnh của Lai Châu.
    combined = _fold(f"{dia} {tinh}")
    if not xa and "benh vien da khoa tinh" in combined and "lai chau" in combined:
        out["xa"] = "Tân Phong"
    return out


# Tên cơ sở y tế IN HOA (dòng "Tại:" của giấy chứng sinh) → viết hoa theo quy tắc: hoa chữ đầu mỗi từ
# (tên riêng), rồi hạ các cụm chung về chữ thường.
_FACILITY_PHRASES = (
    ("Bệnh Viện", "Bệnh viện"),
    ("Trung Tâm Y Tế", "Trung tâm Y tế"),
    ("Trạm Y Tế", "Trạm Y tế"),
    ("Phòng Khám", "Phòng khám"),
    ("Nhà Hộ Sinh", "Nhà hộ sinh"),
    ("Đa Khoa", "đa khoa"),
    ("Quân Y", "Quân y"),
    ("Đại Học", "Đại học"),
    ("Y Học Cổ Truyền", "Y học cổ truyền"),
)
_FACILITY_ADMIN_WORDS = re.compile(r"(?<=\s)(Tỉnh|Thành Phố|Huyện|Quận|Thị Xã|Phường|Xã|Số|Cơ Sở)(?=\s|$)")


def _facility_word(word: str) -> str:
    if any(c.isdigit() for c in word) or re.fullmatch(r"[IVX]{2,}", word):
        return word
    return "-".join(p[:1].upper() + p[1:].lower() for p in word.split("-"))


def _facility_name_case(value) -> str:
    """'BỆNH VIỆN SẢN - NHI X SỐ 2 TỈNH X' → 'Bệnh viện Sản - Nhi X số 2'. Chỉ đổi khi chuỗi IN HOA hết;
    đuôi 'tỉnh/thành phố <T>' lặp lại tên đã có trong tên cơ sở thì bỏ."""
    text = " ".join(str(value or "").split())
    if not text:
        return text
    if not any(c.islower() for c in text):
        text = " ".join(_facility_word(w) for w in text.split(" "))
        for old, new in _FACILITY_PHRASES:
            text = re.sub(rf"\b{old}\b", new, text)
        text = _FACILITY_ADMIN_WORDS.sub(lambda m: m.group(1).lower(), text)
    match = re.match(r"^(.+?)[\s,\-]+(tỉnh|thành phố|tp\.?)\s+(.+)$", text, flags=re.IGNORECASE)
    if match and _fold(match.group(3)) in _fold(match.group(1)):
        text = match.group(1).strip()
    return text


def _province_key(value) -> str:
    """Tên tỉnh đã fold, bỏ tiền tố loại đơn vị ("tỉnh"/"thành phố"/"tp")."""
    return re.sub(r"^(tinh|thanh pho|tp\.?)\s+", "", _fold(value)).strip()


def _fix_tk_birth_province(tk, gcs):
    """Tờ khai ghi tỉnh nơi sinh mâu thuẫn với chính TÊN cơ sở y tế → lấy tỉnh của cơ sở.

    Dòng "Nơi sinh" trên tờ khai viết tay hay bị OCR đọc nhầm tên địa danh cuối dòng (vd
    "..., P. X, <thành phố của tỉnh A>" ra một thành phố của tỉnh B), trong khi tên bệnh viện
    tuyến tỉnh ngay đầu dòng vẫn ghi rõ tỉnh A. Chỉ sửa khi tên tỉnh của cơ sở (theo giấy chứng
    sinh hoặc bảng bệnh viện) CÓ trong diaChi và tỉnh tờ khai thì KHÔNG; xã + chi tiết giữ nguyên.
    """
    if not isinstance(tk, dict):
        return tk
    tk_tinh = tk.get("tinh") or tk.get("tỉnh")
    dia = str(tk.get("diaChi") or tk.get("dia_chi") or tk.get("diachi") or "")
    tk_key = _province_key(tk_tinh)
    folded_dia = _fold(dia)
    if not (tk_key and folded_dia) or tk_key in folded_dia:
        return tk
    candidates = []
    if isinstance(gcs, dict):
        candidates.append(gcs.get("tinh") or gcs.get("tỉnh"))
    hospital = lookup_hospital(dia)
    if hospital:
        candidates.append(hospital["tinh"])
    for tinh in candidates:
        key = _province_key(tinh)
        if key and key != tk_key and key in folded_dia:
            return {**tk, "tinh": tinh}
    return tk


def _is_birth_cert_serial(value) -> bool:
    """Số giấy chứng sinh (vd "01327.GCS.12096.25") — KHÔNG phải số giấy CN kết hôn."""
    text = str(value or "").upper()
    return "GCS" in text or "CHUNG SINH" in text or "CHỨNG SINH" in text


def _clean_phone(value) -> str:
    """Chuẩn hóa SĐT VN: sửa lỗi OCR, khôi phục số 0 đứng đầu cho di động."""
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    text = text.translate(str.maketrans({"O": "0", "o": "0", "S": "5", "s": "5", "I": "1", "l": "1"}))
    digits = re.sub(r"\D", "", text)
    if len(digits) < 8:
        return ""
    if digits.startswith("84") and len(digits) in (11, 12):
        digits = "0" + digits[2:]
    elif len(digits) == 9 and digits[0] in "35789":
        digits = "0" + digits
    # Chỉ điền khi là SĐT VN hợp lệ (10-11 số, bắt đầu bằng 0); tránh điền số rác do OCR mờ.
    return digits if len(digits) in (10, 11) and digits.startswith("0") else ""


def _positive_copy_quantity(value) -> str:
    """Chỉ nhận số lượng bản sao thật, dương; không có số thì để trống."""
    match = re.search(r"\d+", str(value or ""))
    if not match:
        return ""
    quantity = int(match.group())
    return str(quantity) if quantity > 0 else ""


def _upper_name(full_name: str | None) -> str:
    """Họ tên con/cha/mẹ trên biểu mẫu liên thông LUÔN viết HOA toàn bộ.

    Cổng không tự chuẩn hoá nên giấy tờ ghi kiểu gì extension điền y hệt kiểu đó; hồ sơ có ba ô
    tên viết ba kiểu khác nhau ("Nguyễn Văn A" / "NGUYỄN VĂN B") trông như dữ liệu lấy sai nguồn.
    str.upper() nhận biết Unicode nên giữ nguyên dấu tiếng Việt ("Nguyễn" -> "NGUYỄN").
    """
    return " ".join(str(full_name or "").split()).upper()


def _split_name(full_name: str | None) -> tuple[str, str, str]:
    parts = [p for p in str(full_name or "").split() if p]
    if not parts:
        return "", "", ""
    if len(parts) == 1:
        return "", "", parts[0]
    if len(parts) == 2:
        return parts[0], "", parts[1]
    return parts[0], " ".join(parts[1:-1]), parts[-1]


def _clean_child_name(value, mother_name) -> str:
    """Chặn placeholder và lỗi LLM copy tên mẹ khi giấy chứng sinh chưa đặt tên trẻ."""
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    if re.fullmatch(r"[/\\|._\-\s]+", text):
        return ""
    folded = re.sub(r"\s+", " ", _fold(text))
    if folded in {
        "chua dat ten",
        "chua co ten",
        "chua dat",
        "khong co ten",
    }:
        return ""
    mother_folded = re.sub(r"\s+", " ", _fold(mother_name))
    if mother_folded and folded == mother_folded:
        return ""
    return text


def _strip_admin_prefix(value):
    """xa CHỈ giữ TÊN đơn vị, bỏ tiền tố loại (Xã/Phường/Thị trấn/TT)."""
    text = str(value or "").strip()
    return re.sub(r"^(xã|phường|thị trấn|tt\.?)\s+", "", text, flags=re.IGNORECASE).strip()


# Đổi tên tỉnh/thành theo sắp xếp đơn vị hành chính 2025: giấy tờ cũ ghi tên CŨ → chuẩn hóa tên MỚI.
_TINH_RENAME = {
    "thua thien hue": "Huế",
}


def _norm_tinh(value):
    """Chuẩn hóa tên tỉnh về đơn vị hành chính hiện hành (vd 'Thừa Thiên Huế' → 'Huế')."""
    if not value:
        return value
    return _TINH_RENAME.get(_fold(value), value)


def _province_name_key(value) -> str:
    """Tên tỉnh/thành đã bỏ dấu, bỏ tiền tố Tỉnh/Thành phố/TP/T.P và dấu câu."""
    text = re.sub(r"[^a-z0-9]+", " ", _fold(value)).strip()
    return re.sub(r"^(tinh|thanh pho|tp|t p)\s+", "", text).strip()


def _area(value):
    if not isinstance(value, dict):
        return None
    xa = _strip_admin_prefix(value.get("xa") or value.get("xã"))
    dia = value.get("diaChi") or value.get("dia_chi") or value.get("diachi")
    # diaChi chỉ là phần CHI TIẾT (bản/tổ/thôn/số nhà). Nếu nó chính là tên xã/phường
    # (vd "Phường Tân Phong" trong khi xa="Tân Phong") → trùng lặp vô nghĩa, bỏ đi.
    if dia and _strip_admin_prefix(dia).strip().lower() == (xa or "").strip().lower():
        dia = None
    tinh = _norm_tinh(value.get("tinh") or value.get("tỉnh"))
    # Dòng chỉ ghi tỉnh/thành ("T.P Hải Phòng") bị chép nguyên vào diaChi → trùng tỉnh, bỏ.
    if dia and tinh and _province_name_key(dia) == _province_name_key(tinh):
        dia = None
    out = {"tinh": tinh, "xa": xa, "diaChi": dia}
    out = {k: v for k, v in out.items() if v not in (None, "", {}, [])}
    # Áp dụng remap địa chỉ để chuẩn hóa xã/phường theo sáp nhập đơn vị hành chính
    return city_province_area(remap_area(out)) if out else None


_ADMIN_SEGMENT = re.compile(r"^(xã|phường|thị trấn|thị xã|quận|huyện|thành phố|tp\.?|tỉnh)\s", re.IGNORECASE)


def _dktt_detail(value) -> str:
    """Phần chi tiết (số nhà/đường/thôn) TRƯỚC phường/xã của nơi đề nghị đăng ký thường trú trên CT01.

    LLM đôi khi để nguyên cả dòng trong diaChi → cắt từ đoạn (sau dấu phẩy) bắt đầu bằng cấp hành chính,
    và bỏ đuôi "phường <xa>" khi không có dấu phẩy ngăn."""
    if not isinstance(value, dict):
        return ""
    text = str(value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "").strip()
    text = re.sub(r"^(đăng ký thường trú\s*)?(tại|ở)\s*:?\s*", "", text, flags=re.IGNORECASE)
    parts = []
    for part in text.split(","):
        part = part.strip()
        if _ADMIN_SEGMENT.match(part):
            break
        parts.append(part)
    text = ", ".join(p for p in parts if p)
    xa = _strip_admin_prefix(value.get("xa") or value.get("xã"))
    if xa:
        text = re.sub(rf"\s*-?\s*(xã|phường|thị trấn)?\s*{re.escape(xa)}\s*$", "", text, flags=re.IGNORECASE)
    return text.strip(" ,-")


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _is_year_only(value) -> bool:
    return bool(re.fullmatch(r"\d{4}", str(value or "").strip()))


def _dmy(value) -> str:
    """'5/4/2021' → '05/04/2021'; không đúng dạng ngày đầy đủ → rỗng (ô Ngày cấp không nhận năm trần)."""
    m = re.fullmatch(r"\s*(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\s*", str(value or ""))
    return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}" if m else ""


def _gender(value) -> str:
    folded = _fold(value)
    if folded.startswith("nam") or folded == "male":
        return "Nam"
    if folded.startswith("nu") or folded == "female":
        return "Nữ"
    return ""


# Tờ CT01 (thay đổi thông tin cư trú) nộp kèm khai sinh liên thông: người ở mục 1 DƯỚI 6 TUỔI chính là
# người được khai sinh. Giấy chứng sinh hay ghi "chưa đặt tên" và không có tờ khai khai sinh → tên con
# chỉ còn ở CT01. Người lớn hơn (cha/mẹ tự kê khai cho mình) không được coi là con.
_CT01_CHILD_MAX_AGE = 6


def _ct01_child(values: dict, today: date | None = None) -> dict:
    """{HoTen, NgaySinh, GioiTinh} của người ở mục 1 CT01 khi người đó dưới 6 tuổi; không thì {}."""
    m = re.fullmatch(r"\s*(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\s*", str(values.get("Ct01_NgaySinh") or ""))
    if not m:
        return {}
    try:
        birth = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return {}
    today = today or date.today()
    # Lệch múi giờ server (UTC) có thể khiến trẻ sinh trong ngày trông như sinh "ngày mai" → nới 1 ngày.
    if birth > today + timedelta(days=1):
        return {}
    day = 28 if (birth.month, birth.day) == (2, 29) else birth.day
    if today >= date(birth.year + _CT01_CHILD_MAX_AGE, birth.month, day):
        return {}
    name = _clean_child_name(values.get("Ct01_HoTen"), values.get("ThongTinMe_HoTen"))
    # Tên trùng cha/chủ hộ = LLM chép nhầm người lớn vào mục 1 → bỏ tên, vẫn giữ ngày sinh/giới tính.
    if name and _fold(name) in {_fold(values.get("ThongTinBo_HoTen")), _fold(values.get("Ct01_ChuHoHoTen"))}:
        name = ""
    out = {"HoTen": name, "NgaySinh": birth.strftime("%d/%m/%Y"), "GioiTinh": _gender(values.get("Ct01_GioiTinh"))}
    return {k: v for k, v in out.items() if v}


def _nyc_person(vai_tro: str, ten, cccd, gioi_tinh, ngay_cap, noi_cap, noi_cu_tru) -> dict:
    """Một ứng viên người yêu cầu. Nơi cấp không đọc được thì suy theo ngày cấp — CHỈ cho số định danh
    12 số (CCCD/Căn cước); CMND 9 số do công an tỉnh cấp, không suy được."""
    so = _digits(cccd)
    ngay = _dmy(ngay_cap)
    noi = normalize_issuer(noi_cap) or (default_issuer(ngay) if ngay and len(so) == 12 else "")
    person = {
        "vaiTro": vai_tro,
        "ten": _upper_name(ten),
        "cccd": so,
        "gioiTinh": _gender(gioi_tinh),
        "ngayCap": ngay,
        "noiCap": noi,
        "noiCuTru": noi_cu_tru or None,
    }
    return {k: v for k, v in person.items() if v not in (None, "", {}, [])}


def _same_person(a: dict, b: dict) -> bool:
    """Trùng số định danh; một bên thiếu số thì so họ tên bỏ dấu. Hai số khác nhau là hai người."""
    if a.get("cccd") and b.get("cccd"):
        return a["cccd"] == b["cccd"]
    return bool(a.get("ten")) and " ".join(_fold(a["ten"]).split()) == " ".join(_fold(b.get("ten")).split())


# ── Đọc thẳng thẻ CCCD/Căn cước trong văn bản OCR ──
# LLM hay bỏ sót thẻ của người thứ ba (người đi nộp không phải cha/mẹ) vì nó chỉ chú ý giấy tờ cha/mẹ/con.
# Mặt trước thẻ in nhãn song ngữ cố định nên đọc bằng regex chắc hơn; chỉ dùng để BÙ ứng viên người yêu cầu.
_CARD_NO = re.compile(r"(?:Số\s*/\s*No\.?|Số định danh cá nhân\s*/\s*Personal identification number)[ \t]*:?[ \t]*(\d{12})\b",
                      re.IGNORECASE)
_CARD_NAME = re.compile(r"Họ và tên\s*/\s*Full name\s*:?[ \t]*(?:\n\s*)?([^\n]+)", re.IGNORECASE)
_CARD_SEX = re.compile(r"Giới tính\s*/\s*Sex\s*:?\s*(Nam|Nữ)", re.IGNORECASE)
_CARD_RESIDENCE = re.compile(
    r"(?:Nơi thường trú|Nơi cư trú)\s*/\s*Place of residence\s*:?\s*(.+?)\s*(?:\n\s*(?:Có giá trị|Date of expiry|Ngày, tháng, năm)|\n\s*\n|$)",
    re.IGNORECASE | re.DOTALL,
)
# Mặt sau: ngày cấp đứng TRƯỚC dòng MRZ "IDVNM<9 số giấy><1 số kiểm><12 số định danh>" của cùng thẻ.
_CARD_ISSUE = re.compile(
    r"(?:Date,\s*month,\s*year|Date of issue)\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})(.{0,1500}?)IDVNM\d{10}(\d{12})",
    re.IGNORECASE | re.DOTALL,
)
_WARD_PREFIX = re.compile(r"^(xã|phường|thị trấn|đặc khu)\s", re.IGNORECASE)


def _card_residence(text: str):
    """'TDP 13 Nhân Mỹ\\nMỹ Đình 1, Nam Từ Liêm, Hà Nội' → {tinh, xa, diaChi} đã quy đổi sáp nhập.

    Thẻ CCCD in dòng chi tiết riêng, dòng dưới là 'xã, huyện, tỉnh' (cũ) hoặc 'xã, tỉnh' (mới)."""
    lines = [" ".join(l.split()) for l in str(text or "").splitlines() if l.strip()]
    if not lines:
        return None
    detail, admin = (" ".join(lines[:-1]), lines[-1]) if len(lines) > 1 else ("", lines[0])
    parts = [p.strip() for p in admin.split(",") if p.strip()]
    if not parts:
        return None
    tinh, huyen, extra = parts[-1], "", []
    if len(parts) >= 3 and not _WARD_PREFIX.match(parts[-2]):
        xa, huyen, extra = parts[-3], parts[-2], parts[:-3]
    elif len(parts) >= 2:
        xa, extra = parts[-2], parts[:-2]
    else:
        xa = ""
    dia = ", ".join(p for p in [detail, *extra] if p)
    out = {k: v for k, v in {"tinh": _norm_tinh(tinh), "xa": _strip_admin_prefix(xa), "diaChi": dia}.items() if v}
    return city_province_area(remap_area(out, huyen_hint=huyen or None)) if out.get("tinh") else None


def _cards_from_ocr(ocr_text: str) -> list[dict]:
    """Mọi thẻ CCCD/Căn cước đọc được trong OCR: {cccd, ten, gioiTinh, ngayCap, noiCuTru}."""
    text = str(ocr_text or "")
    issue = {m.group(3): m.group(1) for m in _CARD_ISSUE.finditer(text)}
    starts = [m for m in _CARD_NO.finditer(text)]
    cards = []
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        chunk = text[m.end():min(end, m.end() + 1200)]
        name = _CARD_NAME.search(chunk)
        if not name:  # mặt trước thẻ luôn in họ tên; không có là số định danh nằm ở giấy khác
            continue
        sex = _CARD_SEX.search(chunk)
        residence = _CARD_RESIDENCE.search(chunk)
        cards.append({
            "cccd": m.group(1),
            "ten": name.group(1).strip(),
            "gioiTinh": sex.group(1) if sex else "",
            "ngayCap": issue.get(m.group(1), ""),
            "noiCuTru": _card_residence(residence.group(1)) if residence else None,
        })
    return cards


def _nyc_candidates(values: dict, cha_noi_cu_tru, me_noi_cu_tru, ocr_text: str = "") -> list[dict]:
    """Danh sách người có thể là người đang đăng nhập (cha, mẹ, người thứ ba trên CCCD), kèm các ô của
    khối "Thông tin người yêu cầu". Dòng người yêu cầu trên TỜ KHAI gộp vào người trùng, không trùng ai
    thì thành một ứng viên riêng."""
    people = []
    if values.get("ThongTinBo_SoDinhDanh") or values.get("ThongTinBo_HoTen"):
        people.append(_nyc_person(
            "cha", values.get("ThongTinBo_HoTen"), values.get("ThongTinBo_SoDinhDanh"), "Nam",
            values.get("ThongTinBo_NgayCapCccd"), values.get("ThongTinBo_NoiCapCccd"), cha_noi_cu_tru,
        ))
    if values.get("ThongTinMe_SoDinhDanh") or values.get("ThongTinMe_HoTen"):
        people.append(_nyc_person(
            "me", values.get("ThongTinMe_HoTen"), values.get("ThongTinMe_SoDinhDanh"), "Nữ",
            values.get("ThongTinMe_NgayCapCccd"), values.get("ThongTinMe_NoiCapCccd"), me_noi_cu_tru,
        ))
    if values.get("NguoiKhac_SoDinhDanh") or values.get("NguoiKhac_HoTen"):
        people.append(_nyc_person(
            "khac", values.get("NguoiKhac_HoTen"), values.get("NguoiKhac_SoDinhDanh"),
            values.get("NguoiKhac_GioiTinh"), values.get("NguoiKhac_NgayCapCccd"),
            values.get("NguoiKhac_NoiCapCccd"), _area(values.get("NguoiKhac_NoiCuTru")),
        ))
    # Thẻ đọc thẳng từ OCR: trùng số người đã có → chỉ bù ô LLM bỏ sót; số mới → người thứ ba.
    for card in _cards_from_ocr(ocr_text):
        found = _nyc_person("khac", card["ten"], card["cccd"], card["gioiTinh"], card["ngayCap"], "",
                            card["noiCuTru"])
        match = next((p for p in people if p.get("cccd") == found.get("cccd")), None)
        if match is None:
            people.append(found)
        else:
            for key in ("ngayCap", "noiCap", "noiCuTru"):
                if found.get(key) and not match.get(key):
                    match[key] = found[key]
    if values.get("Tk_NguoiYeuCau_HoTen") or values.get("Tk_NguoiYeuCau_SoGiayTo"):
        tk = _nyc_person(
            "toKhai", values.get("Tk_NguoiYeuCau_HoTen"), values.get("Tk_NguoiYeuCau_SoGiayTo"), "",
            values.get("Tk_NguoiYeuCau_NgayCap"), values.get("Tk_NguoiYeuCau_NoiCap"),
            _area(values.get("Tk_NguoiYeuCau_NoiCuTru")),
        )
        match = next((p for p in people if _same_person(p, tk)), None)
        if match is None:
            people.append(tk)
        else:
            # Ngày/nơi cấp in trên thẻ đáng tin hơn chữ viết tay → tờ khai chỉ bù ô thẻ không có.
            # Nơi cư trú thì lời khai trên tờ khai thắng (thẻ có thể còn ghi địa chỉ cũ). vaiTro giữ theo thẻ.
            for key, value in tk.items():
                if key == "noiCuTru" or not match.get(key):
                    match[key] = value
    fillable = ("gioiTinh", "ngayCap", "noiCap", "noiCuTru")
    out = []
    for person in people:
        if not (person.get("cccd") or person.get("ten")) or not any(person.get(k) for k in fillable):
            continue
        if person.get("noiCuTru"):
            # Cổng đòi cả Loại cư trú + Quốc gia trước khi chọn tỉnh/xã; giấy tờ không ghi → mặc định.
            person["loaiCuTru"] = "Thường trú"
            person["quocGia"] = "Việt Nam"
        out.append(person)
    return out


# ── Cha/mẹ là người nước ngoài ──
# Tên nước nhãn của cổng không suy ra được: tên tiếng Anh và tên quen gọi. Còn lại tra thẳng theo danh mục.
_QUOC_TICH_ALIASES = {
    "vietnamese": "Việt Nam",
    "my": "Hoa Kỳ (American)",
    "us": "Hoa Kỳ (American)",
    "usa": "Hoa Kỳ (American)",
    "america": "Hoa Kỳ (American)",
    "unitedstates": "Hoa Kỳ (American)",
    "unitedstatesofamerica": "Hoa Kỳ (American)",
    "uc": "Ô-xtrây-li-a (Australian)",
    "australia": "Ô-xtrây-li-a (Australian)",
    "uk": "Anh (British)",
    "britain": "Anh (British)",
    "greatbritain": "Anh (British)",
    "england": "Anh (British)",
    "unitedkingdom": "Anh (British)",
    "korea": "Hàn Quốc (South Korean)",
    "korean": "Hàn Quốc (South Korean)",
    "southkorea": "Hàn Quốc (South Korean)",
    "republicofkorea": "Hàn Quốc (South Korean)",
    "northkorea": "Triều Tiên (North Korean)",
    "japan": "Nhật Bản (Japanese)",
    "nhat": "Nhật Bản (Japanese)",
    "china": "Trung Quốc",
    "chinese": "Trung Quốc",
    "trunghoa": "Trung Quốc",
    "taiwan": "Trung Quốc (Đài Loan)",
    "macao": "Trung Quốc (Ma-cao) (Macau, Chinese)",
    "germany": "Đức (German)",
    "france": "Pháp (French)",
    "russia": "Nga (Russian)",
    "russianfederation": "Nga (Russian)",
    "italy": "I-ta-li-a (Italian)",
    "spain": "Tây Ban Nha (Spanish)",
    "netherlands": "Hà Lan (Dutch)",
    "holland": "Hà Lan (Dutch)",
    "belgium": "Bỉ (Belgian)",
    "switzerland": "Thụy Sĩ (Swiss)",
    "sweden": "Thụy Điển (Swedish)",
    "norway": "Na Uy (Norwegian)",
    "denmark": "Đan Mạch (Danis)",
    "finland": "Phần Lan (Finnish)",
    "poland": "Ba Lan (Polish)",
    "austria": "Áo (Austrian)",
    "ireland": "Ai len (Irish)",
    "czechrepublic": "Séc (Czech)",
    "czechia": "Séc (Czech)",
    "ukraine": "U-crai-na (Ukrainian)",
    "turkey": "Thổ Nhĩ Kỳ (Turkish)",
    "india": "Ấn Độ (Indian)",
    "laos": "Lào (Laotian)",
    "cambodia": "Căm-pu-chia (Cambodian)",
    "thailand": "Thái Lan (Thai)",
    "singapore": "Xinh-ga-po (Singaporean)",
    "malaysia": "Ma-lai-xi-a (Malaysian)",
    "indonesia": "In-đô-nê-xi-a (Indonesian)",
    "philippines": "Phi-líp-pin (Filipino)",
    "myanmar": "Mi-an-ma (Burmese)",
    "mexico": "Mê-hi-cô (Mexican)",
    "brazil": "Bra-xin (Brazilian)",
    "southafrica": "Nam Phi (South African)",
    # Nhãn của cổng lấy "Nigerian" cho Ni-giê, nhưng đó là người Ni-giê-ri-a.
    "nigeria": "Ni-giê-ri-a (Nigierian)",
    "nigerian": "Ni-giê-ri-a (Nigierian)",
}


def _nation_key(value) -> str:
    """'Cộng hòa Pháp'/'Pháp' → 'phap', 'Ca-na-đa'/'Canađa'/'Canada' → 'canada': chỉ còn chữ và số, bỏ danh xưng nhà nước."""
    folded = re.sub(r"^(cong hoa lien bang|cong hoa|lien bang|vuong quoc|hop chung quoc|nha nuoc)\s+", "", _fold(value))
    return re.sub(r"[^a-z0-9]", "", folded)


def _nation_index() -> dict[str, str]:
    """Mọi cách gọi một nước → nhãn ô Quốc tịch: tên, tên trong ngoặc, nhãn ô Quốc gia."""
    index = dict(_QUOC_TICH_ALIASES)
    for quoc_tich, quoc_gia in QUOC_TICH_QUOC_GIA.items():
        for part in (quoc_tich, quoc_gia, *re.split(r"[()/,]", quoc_tich)):
            key = _nation_key(part)
            if key:
                index.setdefault(key, quoc_tich)
    return index


_NATION_INDEX = _nation_index()


def _nation_label(value) -> str:
    """Tên nước/quốc tịch đọc trên giấy → nhãn ô Quốc tịch của cổng; không nhận ra → rỗng."""
    text = str(value or "")
    for part in (text, *re.split(r"[()/,]", text)):
        label = _NATION_INDEX.get(_nation_key(part))
        if label:
            return label
    return ""


def _foreign_nationality(value) -> str:
    """Nhãn quốc tịch của người nước ngoài; người Việt hoặc giấy không ghi → rỗng.

    Nước không có trong danh mục thì giữ chữ trên giấy: extension báo không chọn được, cán bộ chọn tay."""
    text = " ".join(str(value or "").split()).strip(" .,;")
    if not is_foreign(text):
        return ""
    label = _nation_label(text) or text
    return "" if label == "Việt Nam" else label


_VN_ADDRESS = re.compile(r"\b(tỉnh|thành phố|tp|phường|xã|thị trấn)\b", re.IGNORECASE)


def _abroad_address(value) -> str:
    """Dòng nơi cư trú nếu ở nước ngoài; người nước ngoài cư trú tại Việt Nam → rỗng.

    Giữ nguyên cả tên nước: ô Quốc gia bị cổng khoá nên ô Chi tiết là chỗ duy nhất còn ghi được nước cư trú."""
    text = " ".join(str(value or "").split()).strip(" .,;")
    nuoc = _nation_label(text.rsplit(",", 1)[-1])
    if nuoc == "Việt Nam" or (not nuoc and _VN_ADDRESS.search(text)):
        return ""
    return text


# Giấy kết hôn in hai cột nên OCR gộp hai bên vào một dòng: "Quốc tịch: Việt Nam Quốc tịch: Ca-na-đa". Tiêu đề IN HOA để
# không nhầm dòng "Thông tin về Giấy chứng nhận kết hôn" trên tờ khai.
_GCN_BLOCK = re.compile(r"GIẤY CHỨNG NHẬN KẾT HÔN(.*?)(?:Nơi đăng ký kết hôn|\n=====|\Z)", re.DOTALL)
_PASSPORT = re.compile(
    r"(?i:hộ chiếu)\s*(?i:số)?\s*:?\s*([A-Z0-9]{6,})[\s,;.]*(.*?)\s*(?i:(?:cấp\s+)?ngày(?:\s+cấp)?)\s*:?\s*"
    r"(\d{1,2}/\d{1,2}/\d{4})"
)


def _marriage_columns(block: str, label: str) -> list[str]:
    """Giá trị của một nhãn in ở cả hai cột, theo thứ tự trên giấy."""
    found = re.findall(rf"{label}\s*:\s*([^\n|]*?)\s*(?={label}\s*:|\||$)", block, flags=re.IGNORECASE | re.MULTILINE)
    return [value.strip(" .,;") for value in found]


def _marriage_sides(ocr_text: str) -> dict:
    """Đọc thẳng GIẤY KẾT HÔN trong OCR: {"Vo": {...}, "Chong": {...}} gồm QuocTich, GiayTo, NoiCuTru.

    LLM hay bỏ sót quốc tịch của bên nước ngoài dù OCR đọc rõ; mục này là nguồn bù. Thiếu một cột thì không biết
    giá trị thuộc bên nào → bỏ cả nhãn đó."""
    match = _GCN_BLOCK.search(str(ocr_text or ""))
    if not match:
        return {}
    block = match.group(1)
    vo = re.search(r"\bvợ\b|bên nữ", block, re.IGNORECASE)
    chong = re.search(r"\bchồng\b|bên nam", block, re.IGNORECASE)
    first, second = ("Chong", "Vo") if vo and chong and chong.start() < vo.start() else ("Vo", "Chong")
    sides: dict = {"Vo": {}, "Chong": {}}
    for key, label in (("QuocTich", "Quốc tịch"), ("GiayTo", "Giấy tờ tùy thân"), ("NoiCuTru", "Nơi cư trú")):
        columns = _marriage_columns(block, label)
        if len(columns) == 2:
            sides[first][key], sides[second][key] = columns
    return sides


def _fill_foreign_facts(values: dict, role: str, facts: dict) -> None:
    """Bù quốc tịch, hộ chiếu, nơi cư trú của người nước ngoài từ giấy kết hôn; ô LLM đã trả thì giữ."""
    quoc_tich = facts.get("QuocTich")
    if quoc_tich and not _foreign_nationality(values.get(f"{role}_QuocTich")):
        values[f"{role}_QuocTich"] = quoc_tich
    if not _foreign_nationality(values.get(f"{role}_QuocTich")):
        return
    passport = _PASSPORT.search(facts.get("GiayTo") or "")
    if passport:
        so, noi_cap, ngay_cap = passport.groups()
        values.setdefault(f"{role}_SoDinhDanh", so)
        values.setdefault(f"{role}_NgayCapHoChieu", ngay_cap)
        if noi_cap:
            values.setdefault(f"{role}_NoiCapHoChieu", noi_cap)
    if facts.get("NoiCuTru"):
        values.setdefault(f"{role}_NoiCuTruNuocNgoai", facts["NoiCuTru"])


def _fill_from_marriage_cert(values: dict, role: str, side: str, facts: dict | None = None) -> None:
    """Bù thông tin cha/mẹ từ bên tương ứng trên GIẤY KẾT HÔN khi đúng là một người.

    Đúng người = trùng số giấy tờ, hoặc trùng họ tên (bỏ dấu/hoa thường). Vai trò chưa có danh tính
    từ nguồn nào khác (vd hồ sơ không kèm CCCD cha, giấy chứng sinh không ghi cha) → nhận luôn bên
    tương ứng trên giấy kết hôn. Chỉ bù ô còn trống; riêng ngày sinh chỉ có năm (giấy chứng sinh hay
    ghi "1990") được thay bằng ngày đầy đủ cùng năm.

    facts: bên này đọc thẳng từ OCR (xem _marriage_sides), dùng bù thông tin người nước ngoài.
    """
    gcn = {key: values.get(f"GcnKetHon_{side}_{key}") for key in ("HoTen", "NgaySinh", "SoGiayTo", "DanToc")}
    gcn_id = _digits(gcn["SoGiayTo"])
    role_id = _digits(values.get(f"{role}_SoDinhDanh"))
    gcn_name = " ".join(_fold(gcn["HoTen"]).split())
    role_name = " ".join(_fold(values.get(f"{role}_HoTen")).split())
    role_empty = not role_id and not role_name
    if not (
        (gcn_id and gcn_id == role_id)
        or (gcn_name and gcn_name == role_name)
        or (role_empty and gcn_name)
    ):
        return
    if gcn["HoTen"] and not values.get(f"{role}_HoTen"):
        values[f"{role}_HoTen"] = _upper_name(gcn["HoTen"])
    birth = str(gcn["NgaySinh"] or "").strip()
    current = values.get(f"{role}_NgaySinh")
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", birth) and (
        not current or (_is_year_only(current) and str(current).strip() == birth[-4:])
    ):
        values[f"{role}_NgaySinh"] = birth
    # Chưa có số định danh từ nguồn khác → điền số giấy tờ trên giấy kết hôn. Số 12 số là số định danh;
    # còn lại (CMND 9 số, chứng minh quân đội dạng "33A021121427") giữ nguyên cả chữ cái.
    if gcn_id and not role_id:
        values[f"{role}_SoDinhDanh"] = (
            gcn_id if len(gcn_id) == 12 else re.sub(r"[^0-9A-Za-z]", "", str(gcn["SoGiayTo"])).upper()
        )
    if gcn["DanToc"] and not values.get(f"{role}_DanToc"):
        values[f"{role}_DanToc"] = gcn["DanToc"]
    _fill_foreign_facts(values, role, facts or {})


def enrich(fields: list[dict], options: dict | None = None, *, ocr_text: str = "") -> list[dict]:
    """Derive deterministic Angular form fields from compact source facts.

    ocr_text: văn bản OCR gộp mọi file — chỉ dùng để đọc thẳng thẻ CCCD bù ứng viên người yêu cầu."""
    options = options or {}
    values = _by_name(fields)
    for name_field in (
        "Gcs_HoTenCon",
        "Tk_HoTenCon",
        "ThongTinBo_HoTen",
        "ThongTinMe_HoTen",
        "CccdNam_HoTen",
        "CccdNu_HoTen",
        "Ct01_HoTen",
        "Ct01_ChuHoHoTen",
    ):
        if name_field in values:
            values[name_field] = _upper_name(values[name_field])
    # Người mục 1 CT01 dưới 6 tuổi = người được khai sinh. Tên con: tờ khai > CT01 > giấy chứng sinh
    # (tên trên giấy chứng sinh chỉ là "dự định đặt", CT01 kê khai cùng lúc khai sinh nên mới hơn).
    def pick_child_name() -> str:
        for raw in (values.get("Tk_HoTenCon"), _ct01_child(values).get("HoTen"), values.get("Gcs_HoTenCon")):
            name = _clean_child_name(raw, values.get("ThongTinMe_HoTen"))
            if name:
                return name
        return ""

    if values.get("ThongTinBo_HoTen"):
        values["ThongTinBo_HoTen"] = _align_father_surname(values["ThongTinBo_HoTen"], pick_child_name())
    marriage_sides = _marriage_sides(ocr_text)
    _fill_from_marriage_cert(values, "ThongTinMe", "Vo", marriage_sides.get("Vo"))
    _fill_from_marriage_cert(values, "ThongTinBo", "Chong", marriage_sides.get("Chong"))
    # Tính sau khi bù cha/mẹ từ giấy kết hôn: chặn tên con trùng tên mẹ/cha cần tên đã bù.
    ct01_child = _ct01_child(values)
    child_name = pick_child_name()
    # Nhãn quốc tịch của cha/mẹ người nước ngoài; rỗng = người Việt.
    me_quoc_tich = _foreign_nationality(values.get("ThongTinMe_QuocTich"))
    cha_quoc_tich = _foreign_nationality(values.get("ThongTinBo_QuocTich"))
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if default:
            item["default"] = True
        out.append(item)
        seen.add(name)

    def add_name(prefix: str, full_name: str | None) -> None:
        ho, chu_dem, ten = _split_name(_upper_name(full_name))
        add(f"{prefix}Ho" if prefix else "Ho", ho)
        add(f"{prefix}ChuDem" if prefix else "ChuDem", chu_dem)
        add(f"{prefix}Ten" if prefix else "Ten", ten)

    # Quốc tịch khác Việt Nam, cổng tự (changeChaMaQuocTich/changeMeMaQuocTich trong bundle của cổng):
    #  - đặt Dân tộc mã 55 rồi khoá, ghi Dân tộc khác = tên quốc tịch;
    #  - xoá trắng, bỏ bắt buộc và KHOÁ Loại cư trú + Quốc gia → gửi hai ô này chỉ ra "không điền được";
    #  - gỡ ô Số định danh, hiện ba ô bắt buộc <Khoi>HoChieuSo / HoChieuNgayCap / HoChieuNoiCap.
    def add_nationality(prefix: str, quoc_tich: str, dan_toc) -> None:
        """Quốc tịch đi TRƯỚC mọi ô của khối vì nó quyết định các ô còn lại. Dropdown dân tộc đi trước ô DantocKhac."""
        add(f"{prefix}MaQuocTich", quoc_tich or "Việt Nam")
        select, khac = ("Khác", quoc_tich) if quoc_tich else _ethnicity_for_form(dan_toc)
        add(f"{prefix}MaDanToc", select)
        add(f"{prefix}DantocKhac", khac)

    def add_identity(prefix: str, role: str, quoc_tich: str) -> None:
        if not quoc_tich:
            add(f"{prefix}SoGiayTo", values.get(f"{role}_SoDinhDanh"))
            return
        add(f"{prefix}HoChieuSo", values.get(f"{role}_SoDinhDanh"))
        add(f"{prefix}HoChieuNgayCap", _dmy(values.get(f"{role}_NgayCapHoChieu")))
        add(f"{prefix}HoChieuNoiCap", values.get(f"{role}_NoiCapHoChieu"))

    def add_residence(prefix: str, quoc_tich: str, noi_cu_tru, dia_chi_nuoc_ngoai: str) -> None:
        if not quoc_tich:
            add(f"{prefix}LoaiCuTru", "Thường trú")
            add(f"{prefix}MaQuocGia", "Việt Nam")
        add(f"{prefix}DiaChi", {"diaChi": dia_chi_nuoc_ngoai} if dia_chi_nuoc_ngoai else noi_cu_tru)

    has_child = bool(child_name) or bool(ct01_child) or any(
        name in values
        for name in (
            "Tk_NgaySinhCon",
            "Tk_GioiTinhCon",
            "Tk_DanTocCon",
            "Gcs_NgaySinhCon",
            "Gcs_GioiTinhCon",
            "Gcs_DanTocCon",
            "Gcs_NoiSinh",
        )
    )
    has_father = bool(values.get("ThongTinBo_SoDinhDanh") or values.get("ThongTinBo_HoTen"))
    has_mother = bool(values.get("ThongTinMe_SoDinhDanh") or values.get("ThongTinMe_HoTen"))
    # LLM hay bỏ ThongTinMe_NoiCuTru khi mẹ không có CCCD mà giấy kết hôn (cũ) ghi địa chỉ khác giấy chứng
    # sinh → lấy dòng thường trú mẹ trên giấy chứng sinh làm nguồn dự phòng.
    me_noi_cu_tru = (
        _area(values.get("Tk_NoiCuTruMe"))
        or _area(values.get("ThongTinMe_NoiCuTru"))
        or _area(values.get("Gcs_NoiThuongTruMe"))
    )
    cha_noi_cu_tru = _area(values.get("Tk_NoiCuTruCha")) or _area(values.get("ThongTinBo_NoiCuTru"))
    # Cư trú ở nước ngoài: địa chỉ không tách được tỉnh/xã Việt Nam, đi riêng qua add_residence.
    me_dia_chi_nn = _abroad_address(values.get("ThongTinMe_NoiCuTruNuocNgoai")) if me_quoc_tich else ""
    cha_dia_chi_nn = _abroad_address(values.get("ThongTinBo_NoiCuTruNuocNgoai")) if cha_quoc_tich else ""
    if me_dia_chi_nn:
        me_noi_cu_tru = None
    if cha_dia_chi_nn:
        cha_noi_cu_tru = None

    # Ngoại lệ Lâm Đồng dùng ở HAI nơi: dân tộc con (trong khối has_child) và quê quán con
    # (ngoài khối). Trước đây tính bên trong `if has_child:` nên hồ sơ KHÔNG có giấy chứng sinh
    # lẫn tờ khai — has_child = False — chạy tới phần quê quán là nổ UnboundLocalError
    # "cannot access local variable 'is_lam_dong'", công dân chỉ thấy "Xử lý giấy tờ chưa xong".
    ns_raw = _fix_tk_birth_province(values.get("Tk_NoiSinh"), values.get("Gcs_NoiSinh")) or values.get("Gcs_NoiSinh")
    ns_area = _area(_norm_birth_place(ns_raw)) if ns_raw else None
    birth_province = _fold(ns_area.get("tinh") or "") if ns_area else ""
    is_lam_dong = "lam dong" in birth_province

    if has_child:
        add_name("", child_name)
        # Thông tin con nói chung ưu tiên TỜ KHAI. RIÊNG NGÀY SINH ưu tiên GIẤY CHỨNG SINH:
        # đó là bản ghi y tế gốc của sự kiện sinh; con số ngày người khai gõ tay ở tờ khai hay
        # lệch/typo so với ngày sinh thực (vd tờ khai ghi số "28" nhưng chữ + chứng sinh là "20").
        add("NgaySinh", values.get("Gcs_NgaySinhCon") or values.get("Tk_NgaySinhCon") or ct01_child.get("NgaySinh"))
        add("GioiTinh", values.get("Tk_GioiTinhCon") or values.get("Gcs_GioiTinhCon") or ct01_child.get("GioiTinh"))
        
        # ns_area / is_lam_dong đã tính TRƯỚC khối này (xem chú thích ở trên).
        # Dân tộc con: ưu tiên tờ khai, rồi giấy chứng sinh; nếu không có thì SUY LUẬN theo cha/mẹ (bôi vàng):
        #  1) Tờ khai ghi rõ dân tộc con → dùng (chính xác nhất).
        #  2) Giấy chứng sinh ghi rõ dân tộc con → dùng.
        #  3) NGOẠI LỆ LÂM ĐỒNG: nếu con sinh ra ở Lâm Đồng → theo dân tộc MẸ.
        #  4) Cha và mẹ CÙNG dân tộc → con theo dân tộc đó.
        #  5) Con mang họ cha → theo dân tộc cha.
        #  6) Con mang họ mẹ → theo dân tộc mẹ.
        #  7) Chỉ có dân tộc cha (không biết dân tộc mẹ) → theo dân tộc cha.
        #  8) Chỉ có dân tộc mẹ (không biết dân tộc cha) → theo dân tộc mẹ.
        #  Cha/mẹ người nước ngoài không có dân tộc trong danh mục → con chỉ suy theo người còn lại.
        dan_toc_con = values.get("Tk_DanTocCon") or values.get("Gcs_DanTocCon")
        dan_toc_suy_luan = False
        if not dan_toc_con:
            dt_cha = "" if cha_quoc_tich else values.get("ThongTinBo_DanToc")
            dt_me = "" if me_quoc_tich else values.get("ThongTinMe_DanToc")
            ho_con = _fold(_first_token(child_name))
            ho_cha = _fold(_first_token(values.get("ThongTinBo_HoTen")))
            ho_me = _fold(_first_token(values.get("ThongTinMe_HoTen")))
            
            if is_lam_dong and dt_me:
                # NGOẠI LỆ LÂM ĐỒNG: theo dân tộc mẹ
                dan_toc_con = dt_me
                dan_toc_suy_luan = True
            elif dt_cha and dt_me and _fold(dt_cha) == _fold(dt_me):
                # Cùng dân tộc
                dan_toc_con = dt_cha
                dan_toc_suy_luan = True
            elif ho_con and ho_con == ho_cha and dt_cha:
                # Họ theo cha
                dan_toc_con = dt_cha
                dan_toc_suy_luan = True
            elif ho_con and ho_con == ho_me and dt_me:
                # Họ theo mẹ
                dan_toc_con = dt_me
                dan_toc_suy_luan = True
            elif dt_cha:
                # Chỉ biết dân tộc cha → mặc định theo cha
                dan_toc_con = dt_cha
                dan_toc_suy_luan = True
            elif dt_me:
                # Chỉ biết dân tộc mẹ
                dan_toc_con = dt_me
                dan_toc_suy_luan = True
        dan_toc_con_select, dan_toc_con_khac = _ethnicity_for_form(dan_toc_con)
        # Dropdown phải đi trước để Angular render ô DantocKhac rồi extension mới điền field kế tiếp.
        add("MaDanToc", dan_toc_con_select, default=dan_toc_suy_luan)
        add("DantocKhac", dan_toc_con_khac, default=dan_toc_suy_luan)
        add("MaQuocTich", "Việt Nam")
        add("NsMaQuocGia", "Việt Nam")
        # Nơi sinh là bệnh viện có trong bảng → xã theo bảng (đè cả xã OCR đọc sai), tỉnh bù khi trống.
        ns_area = hospital_area(ns_area)
        if ns_area and ns_area.get("diaChi"):
            ns_area = {**ns_area, "diaChi": _facility_name_case(ns_area["diaChi"])}
        add("NsDiaChi", ns_area)

    if has_mother:
        add_nationality("Me", me_quoc_tich, values.get("ThongTinMe_DanToc"))
        add_name("Me", values.get("ThongTinMe_HoTen"))
        add("MeNgaySinh", values.get("ThongTinMe_NgaySinh"))
        add_identity("Me", "ThongTinMe", me_quoc_tich)
        # Nơi cư trú mẹ: TỜ KHAI trước, rồi ThongTinMe_NoiCuTru (CCCD đứng đầu), cuối cùng giấy chứng sinh.
        add_residence("Me", me_quoc_tich, me_noi_cu_tru, me_dia_chi_nn)

    if has_father:
        add_nationality("Cha", cha_quoc_tich, values.get("ThongTinBo_DanToc"))
        add_name("Cha", values.get("ThongTinBo_HoTen"))
        # Form liên thông dùng 1 ô họ tên gộp (ChaHoTen); form cũ dùng 3 ô tách ở trên.
        add("ChaHoTen", _upper_name(values.get("ThongTinBo_HoTen")))
        add("ChaNgaySinh", values.get("ThongTinBo_NgaySinh"))
        add_identity("Cha", "ThongTinBo", cha_quoc_tich)
        # Nơi cư trú cha: TỜ KHAI trước, rồi mới tới nguồn khác (ThongTinBo_NoiCuTru — CCCD đứng đầu).
        add_residence("Cha", cha_quoc_tich, cha_noi_cu_tru, cha_dia_chi_nn)

    # Quê quán CON (QqDiaChi) — lấy theo thứ tự ưu tiên:
    #  1) TỜ KHAI có ghi quê quán con riêng → ưu tiên (chính xác nhất).
    #  2) Quê quán trên CCCD cha (ThongTinBo_QueQuan) — CCCD cũ có dòng "Quê quán".
    #  3) Nơi đăng ký khai sinh trên thẻ CĂN CƯỚC mới của cha (ThongTinBo_NoiDangKyKhaiSinh).
    #  4) Nơi cư trú của cha (ThongTinBo_NoiCuTru) — fallback cuối cùng theo tục lệ
    #     quê quán con = quê cha.
    #  NGOẠI LỆ LÂM ĐỒNG: nếu nơi sinh con (NsDiaChi) có tỉnh = "Lâm Đồng", lấy QUÊ QUÁN MẸ
    #     thay vì cha (theo quy định địa phương); tuyệt đối không dùng nơi cư trú mẹ thay thế.
    #  CHA NGƯỜI NƯỚC NGOÀI: cũng lấy QUÊ QUÁN MẸ — địa chỉ của cha không phải đơn vị hành chính Việt Nam.
    #  Không có nguồn nào → để trống (không bịa).
    tk_que_quan = _area(values.get("Tk_QueQuanCon"))

    if tk_que_quan:
        add("QqMaQuocGia", "Việt Nam")
        add("QqDiaChi", tk_que_quan)
    else:
        # is_lam_dong tính ở đầu hàm — NGOÀI khối has_child, vì nhánh này chạy cả khi hồ sơ
        # chưa có thông tin con.
        if (is_lam_dong or cha_quoc_tich) and has_mother:
            # Lâm Đồng lấy đúng QUÊ QUÁN MẸ. Không có field này thì để trống; nơi cư trú là một
            # khái niệm khác và không được dùng làm fallback cho quê quán của con.
            que_quan_me = _area(values.get("ThongTinMe_QueQuan"))
            if que_quan_me:
                add("QqMaQuocGia", "Việt Nam")
                add("QqDiaChi", que_quan_me)
        elif not cha_quoc_tich:
            # Trường hợp thông thường: lấy quê quán từ CHA
            que_quan_cha = (
                _area(values.get("ThongTinBo_QueQuan"))
                or _area(values.get("ThongTinBo_NoiDangKyKhaiSinh"))
                or _area(values.get("Tk_NoiCuTruCha"))
                or _area(values.get("ThongTinBo_NoiCuTru"))
            )
            if que_quan_cha:
                add("QqMaQuocGia", "Việt Nam")
                add("QqDiaChi", que_quan_cha)

    # Giấy chứng nhận kết hôn của cha mẹ (nếu có) → mục "Thông tin về Giấy CN kết hôn".
    # Chặn cứng: số giấy chứng sinh (chứa "GCS", vd "01327.GCS.12096.25") KHÔNG phải số kết hôn.
    # Giấy kết hôn thật thắng dòng người dân chép lên tờ khai; ô giấy thật không đọc được thì tờ khai bù.
    gcn = {key: _blank_dots(values.get(f"GcnKetHon_{key}")) or _blank_dots(values.get(f"Tk_GcnKetHon_{key}"))
           for key in ("So", "QuyenSo", "NgayCap", "NoiCap")}
    if gcn["So"] and _is_birth_cert_serial(gcn["So"]):
        gcn["So"] = ""
    if any(gcn.values()):
        add("GiayCNKHSo", gcn["So"])
        add("GiayCNKHQuyenSo", gcn["QuyenSo"])
        add("GiayCNKHNgayCap", gcn["NgayCap"])
        add("GiayCNKHNoiCap", gcn["NoiCap"])

    # Quan hệ người yêu cầu với người được khai sinh. Danh tính người yêu cầu (tên + CCCD) do
    # cổng tự đổ từ tài khoản đăng nhập vào ô readonly trên form → chỉ extension đọc được. Ta
    # gửi kèm danh tính cha/mẹ để extension so khớp: trùng CCCD/tên cha → "Cha", mẹ → "Mẹ",
    # khác cả hai → mặc định "Người giám hộ/đại diện hợp pháp".
    if has_father or has_mother:
        add("NycQuanHe", {
            "chaCccd": values.get("ThongTinBo_SoDinhDanh"),
            "chaTen": values.get("ThongTinBo_HoTen"),
            "meCccd": values.get("ThongTinMe_SoDinhDanh"),
            "meTen": values.get("ThongTinMe_HoTen"),
        })

    # Khối "Thông tin người yêu cầu" cổng đổ từ tài khoản đăng nhập, có người thiếu ngày/nơi cấp, nơi cư
    # trú. Gửi mọi người có trong giấy tờ (cha, mẹ, người thứ ba, người ký tờ khai); extension đọc CCCD/tên
    # readonly trên form để chọn ĐÚNG người, rồi chỉ điền ô còn trống — khối đã đủ thì không đụng.
    nyc_candidates = _nyc_candidates(values, cha_noi_cu_tru, me_noi_cu_tru, ocr_text)
    if nyc_candidates:
        add("NycBuThieu", {"nguoi": nyc_candidates})

    # Số điện thoại: SĐT ghi trên giấy tờ là của NGƯỜI KÝ TỜ KHAI. Khối "Thông tin người yêu cầu"
    # trên cổng lại là người ĐANG ĐĂNG NHẬP (readonly, chỉ extension đọc được) → gửi kèm tên người
    # yêu cầu trên tờ khai để extension so tên; trùng thì mới điền ô SĐT, khác thì bỏ qua vì đó là
    # số của người khác.
    phone = _clean_phone(values.get("LienHe_SoDienThoai"))
    nyc_ten = _upper_name(values.get("Tk_NguoiYeuCau_HoTen"))
    if phone and nyc_ten:
        add("NycSdt", {"sdt": phone, "ten": nyc_ten})

    # Đăng ký thường trú: nếu hồ sơ có TỜ KHAI CT01 (thay đổi thông tin cư trú) → chọn xác nhận
    # bằng VĂN BẢN GIẤY (LoaiXacNhanVNeID="1") thay cho VNeID, rồi điền "Thông tin chủ hộ" theo CT01.
    # Xác định chủ hộ là bố/mẹ theo SỐ ĐỊNH DANH (chắc chắn), fallback TÊN; khác cả hai → điền tay 3 ô.
    ct01_ten = values.get("Ct01_ChuHoHoTen")
    ct01_sdd = values.get("Ct01_ChuHoSoDinhDanh")
    if ct01_ten or ct01_sdd:
        add("LoaiXacNhanVNeID", "1")

        ct01_sdd_d = re.sub(r"\D", "", str(ct01_sdd or ""))
        cha_sdd_d = re.sub(r"\D", "", str(values.get("ThongTinBo_SoDinhDanh") or ""))
        me_sdd_d = re.sub(r"\D", "", str(values.get("ThongTinMe_SoDinhDanh") or ""))
        ct01_ten_f = _fold(ct01_ten)

        is_bo = (ct01_sdd_d and ct01_sdd_d == cha_sdd_d) or (
            not ct01_sdd_d and ct01_ten_f and has_father and ct01_ten_f == _fold(values.get("ThongTinBo_HoTen"))
        )
        is_me = (ct01_sdd_d and ct01_sdd_d == me_sdd_d) or (
            not ct01_sdd_d and ct01_ten_f and has_mother and ct01_ten_f == _fold(values.get("ThongTinMe_HoTen"))
        )

        # Một số phiên bản form không có ô tick "Bố/Mẹ là chủ hộ" → vẫn phải có tên + số định danh chủ hộ.
        # Phát 2 ô chữ TRƯỚC ô tick: form có ô tick thì tích sau cùng, cổng tự đổ lại theo khối cha/mẹ.
        if is_bo:
            add("DkttChuHo", ct01_ten or values.get("ThongTinBo_HoTen"))
            add("DkttChuhoSoGiayTo", ct01_sdd or values.get("ThongTinBo_SoDinhDanh"))
            add("DkttIsTtBo", True)
            add("DkttMaQuanHe", "Con đẻ")
            add("LoaiThanNhanXacNhan", "1")
            add("LoaiChuSoHuuChoO", "1")
            seen.add("DkttIsTtMe")
        elif is_me:
            add("DkttChuHo", ct01_ten or values.get("ThongTinMe_HoTen"))
            add("DkttChuhoSoGiayTo", ct01_sdd or values.get("ThongTinMe_SoDinhDanh"))
            add("DkttIsTtMe", True)
            add("DkttMaQuanHe", "Con đẻ")
            add("LoaiThanNhanXacNhan", "2")
            add("LoaiChuSoHuuChoO", "2")
            seen.add("DkttIsTtBo")
        else:  # chủ hộ là người khác → điền tay 3 ô; không đủ căn cứ chọn bố/mẹ ở hai radio xác nhận / chủ sở hữu
            seen.update({"DkttIsTtBo", "DkttIsTtMe", "LoaiThanNhanXacNhan", "LoaiChuSoHuuChoO"})
            add("DkttChuHo", ct01_ten)
            add("DkttChuhoSoGiayTo", ct01_sdd)
            add("DkttMaQuanHe", values.get("Ct01_QuanHeVoiChuHo"))
            seen.add("DkttMaQuanHe")  # quan hệ trống cũng KHÔNG để default "Con đẻ" (sai cho người khác)

    # "Nơi đề nghị đăng ký thường trú": Tỉnh/Phường cổng tự đổ (readonly) → chỉ điền ô Chi tiết theo
    # mục "Nội dung đề nghị" của CT01.
    dktt_detail = _dktt_detail(values.get("Ct01_NoiDeNghiDktt"))
    if dktt_detail:
        add("DkttDiaChi", {"diaChi": dktt_detail})

    # Bản sao: chỉ khi tờ khai có số lượng thật mới điền số lượng.
    # CapBanSao="1" để Angular hiện ô BanSaoSoLuong trước khi extension điền số.
    copy_quantity = _positive_copy_quantity(values.get("CopyRequest_Quantity"))
    if copy_quantity:
        add("CapBanSao", "1")
        add("BanSaoSoLuong", copy_quantity)

    # 4 phường Đà Lạt: giám hộ trên thẻ BHYT = mẹ, nơi KCB ban đầu = BV Sản - Nhi tỉnh Lâm Đồng (viền vàng).
    # Thêm TRƯỚC STATIC_DEFAULTS để đè mặc định "Thông tin cha".
    if options.get(DA_LAT_BHYT_OPTION):
        add("NguoiGiamHo", "Thông tin mẹ", default=True)
        add("CskcbbdMa", DA_LAT_NOI_KCB, default=True)
    # Phường Hải Châu - Đà Nẵng và Phường Nha Trang - Khánh Hòa: chỉ giám hộ trên thẻ BHYT = mẹ.
    if options.get(HAI_CHAU_BHYT_OPTION) or options.get(NHA_TRANG_BHYT_OPTION):
        add("NguoiGiamHo", "Thông tin mẹ", default=True)

    for default in STATIC_DEFAULTS:
        if default["name"] not in seen:
            out.append(dict(default))
            seen.add(default["name"])

    return out
