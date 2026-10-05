"""Dịch dữ kiện đã trích sang câu hỏi SurveyJS của tờ khai khai tử (Cổng DVC quốc gia mới).

Giá trị nào không khớp được danh mục / định dạng của cổng thì BỎ TRỐNG cho cán bộ, không gửi giá trị cổng sẽ báo
lỗi validate.
"""

import re
import unicodedata
from datetime import date

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type, normalize_issuer
from app.pipelines._shared.ethnic_normalize import normalize_ethnic
from app.pipelines._shared.formatting import upper_person_name

from .reason import labeled_value, requester_context, section
from .schema import (
    DAN_TOC,
    GIOI_TINH,
    LOAI_CU_TRU,
    LOAI_DANG_KY,
    LOAI_GIAY_TO,
    NDK_ADDRESS_FIELDS,
    NOI_CU_TRU,
    QUOC_TICH,
    UI_COMP_BY_NAME,
)

_DATE_RE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b")
# Luật Hộ tịch Đ.33: đăng ký khai tử trong 15 ngày kể từ ngày có người chết.
_DUNG_HAN_NGAY = 15
_HCM_PROVINCE_KEYS = {"hochiminh", "tphochiminh", "thanhphohochiminh", "tphcm", "hcm"}
# Tên gọi khác của dân tộc → mã danh mục cổng (khóa đã bỏ dấu, bỏ khoảng trắng/gạch nối).
_DAN_TOC_ALIAS = {
    "khmer": "05", "mong": "08", "hmong": "08", "meo": "08", "ede": "12", "jrai": "10",
    "bahnar": "13", "xodang": "14", "koho": "16", "kho": "16", "stieng": "22", "katu": "26",
    "kmu": "29", "khmu": "29", "taoi": "31", "bru": "23", "vankieu": "23",
}


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _compact(value) -> str:
    """Bỏ dấu, lowercase, bỏ mọi ký tự không phải chữ/số: "Khơ-me" ≡ "khome", "H'Mông" ≡ "hmong"."""
    return re.sub(r"[^a-z0-9]", "", _fold(value))


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _snap(table: dict, label, aliases: dict | None = None) -> tuple[str, str] | None:
    """(code, nhãn danh mục) khớp đúng nhãn; không khớp chắc thì None."""
    key = _compact(label)
    if not key:
        return None
    for code, text in table.items():
        if _compact(text) == key:
            return code, text
    code = (aliases or {}).get(key)
    return (code, table[code]) if code else None


def _ngay(value) -> str:
    """Theo regex của cổng: dd/mm/yyyy | mm/yyyy | yyyy, có số 0 đứng trước."""
    text = str(value or "").strip()
    full = _DATE_RE.search(text)
    if full:
        day, month, year = full.groups()
        return f"{int(day):02d}/{int(month):02d}/{year}"
    month_year = re.search(r"(?<!\d)(\d{1,2})[/\-.](\d{4})(?!\d)", text)
    if month_year:
        return f"{int(month_year.group(1)):02d}/{month_year.group(2)}"
    year = re.search(r"(?<!\d)(1[89]\d{2}|20\d{2})(?!\d)", text)
    return year.group(1) if year else ""


def _full_date(value) -> str:
    text = _ngay(value)
    return text if re.fullmatch(r"\d{2}/\d{2}/\d{4}", text) else ""


def _iso(ddmmyyyy: str) -> str:
    day, month, year = ddmmyyyy.split("/")
    return f"{year}-{month}-{day}"


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
    if _fold(area["quocGia"]) not in ("viet nam", "vn"):
        return area
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


def _same_person(account_name: str, account_id: str, name, number) -> tuple[bool, bool]:
    """(cùng người, chỉ khớp họ tên). Có số hai phía thì số quyết định."""
    digits = _digits(number)
    if account_id and digits:
        return account_id == digits, False
    if account_name and name and _fold(account_name) == _fold(name):
        return True, True
    return False, False


def _relation(values: dict, context: str, options: dict | None) -> tuple[str, bool, str]:
    """(quan hệ người nộp với người mất, suy đoán, cảnh báo)."""
    account_name, account_id = requester_context(options)
    declared = values.get("NguoiYeuCau_QuanHe")
    same, by_name = _same_person(account_name, account_id, values.get("NguoiYeuCau_HoTen"),
                                 values.get("NguoiYeuCau_SoDinhDanh"))
    if declared and (same or not (account_name or account_id)):
        return declared, by_name or not same, ""
    reasoned = labeled_value(section(context, "quan_he"), "Kết luận")
    if reasoned:
        return reasoned, True, ""
    return "", False, "Chưa xác định được quan hệ của người nộp với người mất — cán bộ ghi ô Quan hệ."


def _loai_dang_ky(values: dict, context: str, today: date | None = None) -> tuple[tuple[str, str], bool]:
    """((mã, nhãn), suy luận). Tờ khai → phân vai → 15 ngày kể từ ngày chết → mặc định đúng hạn."""
    declared = _snap(LOAI_DANG_KY, values.get("ToKhai_LoaiDangKy"))
    if declared:
        return declared, False
    reasoned = _snap(LOAI_DANG_KY, labeled_value(section(context, "loai_dang_ky"), "Kết luận"))
    if reasoned:
        return reasoned, True
    text = _full_date(values.get("NguoiMat_NgayMat"))
    if text:
        day, month, year = (int(part) for part in text.split("/"))
        try:
            elapsed = ((today or date.today()) - date(year, month, day)).days
            code = "1" if 0 <= elapsed <= _DUNG_HAN_NGAY else "4"
            return (code, LOAI_DANG_KY[code]), True
        except ValueError:
            pass
    return ("1", LOAI_DANG_KY["1"]), True


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

    def add_choice(name: str, snapped, *, default: bool = False) -> None:
        if snapped:
            add(name, snapped[1], code=snapped[0], default=default)

    def add_date(name: str, raw) -> None:
        text = _full_date(raw)
        if text:
            add(name, text, code=_iso(text))

    relation, guessed, warning = _relation(values, context, options)
    if warning:
        warnings.append(warning)
    add("citizenmoiquanhe", relation, default=guessed)

    # Ba ô tra cứu CSDL dân cư đi đầu (cờ lookup): cổng tra được thì tự đổ + khóa các ô bên dưới.
    personal_id = _digits(values.get("NguoiMat_SoDinhDanh"))
    lookup = [
        add("citizenNDK_HoVaTen", upper_person_name(values.get("NguoiMat_HoTen"))),
        add("citizenNDK_SoDinhDanh", personal_id if len(personal_id) == 12 else ""),  # cổng chỉ nhận 12 số
        add("citizenNDK_NgaySinh", _ngay(values.get("NguoiMat_NgaySinh"))),
    ]
    for item in lookup:
        if item:
            item["lookup"] = True
    if not values.get("NguoiMat_HoTen"):
        warnings.append("Không đọc được người được đăng ký khai tử — cán bộ nhập khối người mất.")

    add_choice("citizenGioitinh_NgdcKT", _snap(GIOI_TINH, values.get("NguoiMat_GioiTinh")))
    dan_toc = values.get("NguoiMat_DanToc")
    add_choice("citizenDantoc_NgdcKT",
               _snap(DAN_TOC, dan_toc, _DAN_TOC_ALIAS) or _snap(DAN_TOC, normalize_ethnic(dan_toc), _DAN_TOC_ALIAS))
    quoc_tich = values.get("NguoiMat_QuocTich")
    if quoc_tich:
        add("citizenQuoctich_NgdcKT", quoc_tich, code=(_snap(QUOC_TICH, quoc_tich) or (None,))[0])

    number = str(values.get("NguoiMat_SoGiayTo") or "").strip() or (
        personal_id if values.get("NguoiMat_NgayCap") else "")
    if number:
        issue_date = _full_date(values.get("NguoiMat_NgayCap"))
        # Mặc định cơ quan cấp theo ngày chỉ đúng với thẻ căn cước 12 số.
        issuer = normalize_issuer(values.get("NguoiMat_NoiCap")) or (
            default_issuer(issue_date) if len(_digits(number)) == 12 and issue_date else "")
        add_choice("citizenLoaiGiaytotuythan_NgdcKT",
                   _snap(LOAI_GIAY_TO, _id_doc_type_with_number(number, values.get("NguoiMat_LoaiGiayTo"), issuer)))
        add("citizenSogiaytotuythan_NgdcKT", number)
        add_date("citizenField19", issue_date)
        add("citizenNoicapgiaytotuythan_NgdcKT", issuer)

    add("citizenField56", _ngay(values.get("NguoiMat_NgayMat")))
    gio = re.match(r"^\s*(\d{1,2})\s*[:hg]\s*(\d{1,2})", str(values.get("NguoiMat_GioMat") or ""))
    if gio and int(gio.group(1)) < 24 and int(gio.group(2)) < 60:
        add("citizenGiomat", str(int(gio.group(1))))
        add("citizenPhutmat", str(int(gio.group(2))))
    loai_dang_ky, suy_luan = _loai_dang_ky(values, context)
    add_choice("citizenNDKLoaidangky", loai_dang_ky, default=suy_luan)

    # Nơi cư trú cuối cùng: loại cư trú + radio quyết định cụm ô địa chỉ nào hiện ra nên đi trước. Loại cư trú
    # không in trên giấy tờ nào → mặc định Thường trú, tô vàng.
    residence = _area(values.get("NguoiMat_NoiCuTru"))
    if residence:
        add_choice("citizenNDKLoaicutru", ("1", LOAI_CU_TRU["1"]), default=True)
        if _fold(residence.get("quocGia")) in ("viet nam", "vn"):
            add("citizenNDKnoicutru", NOI_CU_TRU["1"], code="1")
            tinh, xa, dia_chi = NDK_ADDRESS_FIELDS["1"]
            add(tinh, residence.get("tinh"))
            add(xa, residence.get("xa"))
            add(dia_chi, residence.get("diaChi"))
        else:
            add("citizenNDKnoicutru", NOI_CU_TRU["2"], code="2")
            add("citizenNDKQG_Khac", residence.get("quocGia"))
            add("citizenNDKDiaChi_Khac", residence.get("diaChi"))

    death_place = _area(values.get("NguoiMat_NoiChet"))
    if death_place:
        in_country = _fold(death_place.get("quocGia")) in ("viet nam", "vn")
        # Radio chọn trước: cụm ô địa chỉ nơi chết chỉ hiện sau khi chọn, extension dò ô theo nhãn sau radio.
        add("citizenNoichet", NOI_CU_TRU["1" if in_country else "2"], code="1" if in_country else "2")
        if in_country:
            area_field = add("citizenNoichet_TrongNuoc", death_place)
            if area_field:
                area_field["radio"] = "citizenNoichet"
    add("citizenNguyennhanchet_NgdcKT", values.get("NguoiMat_NguyenNhan"))

    if values.get("Gbt_Loai") or values.get("Gbt_So"):
        add("citizenLoaigiaybaotu", values.get("Gbt_Loai"))
        add("citizenSogiaybaotu_NgdcKT", " ".join(str(values.get("Gbt_So") or "").split()))
        add_date("citizenNgaythangnamcapgiaybaotu", values.get("Gbt_NgayCap"))
        add("citizenCoquancapgiaybaotucochuthichneukhongcothidetrong", values.get("Gbt_CoQuanCap"))

    # Ô bắt buộc, cổng ghi "điền 0 nếu không cần": không đọc được yêu cầu bản sao thì điền 0, tô vàng.
    quantity = _digits(values.get("SoLuongBanSao"))
    if quantity:
        add("citizenSoluongbansaonguoiyeucaudenghi", str(int(quantity)))
    else:
        add("citizenSoluongbansaonguoiyeucaudenghi", "0", default=True)
    return out, warnings
