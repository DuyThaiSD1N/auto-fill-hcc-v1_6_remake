"""Map compact facts của "Đăng ký lại kết hôn" sang field UI x-*."""

import re
import unicodedata

from app.locations.catalog import PROVINCES, WARDS_BY_SLUG
from app.pipelines._shared.compact_agent.issuer import (
    ISSUER_BO_CONG_AN,
    ISSUER_CUC,
    default_issuer,
    id_doc_type,
    issuer_by_issue_date,
    normalize_issuer,
)
from app.pipelines._shared.area_remap import (
    canonical_province,
    canonical_ward,
    city_province_area,
    is_current_area,
    remap_area,
)
from app.pipelines._shared.ethnic_normalize import ethnicity_for_form
from app.pipelines._shared.formatting import prefer_printed_street, upper_person_name
from app.pipelines._shared.tai_khoan import apply_account_marriage
from app.pipelines.ket_hon_lai.process.schema import UI_COMP_BY_NAME

_TINH_TRANG_HON_NHAN_DEFAULT = "Hiện tại đang có vợ/chồng"
_LOAI_DANG_KY_LAI = "Đăng ký lại"
_DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
# Dấu chấm giữ chỗ của mẫu tờ khai viết tay ("TDP....A....") không phải chữ của địa chỉ.
_FILLER_RE = re.compile(r"\.{2,}|…+")
# Lượt trích ghi "—" cho phần địa chỉ giấy bỏ trống (theo dòng "_tach").
_DASH_ONLY_RE = re.compile(r"^[\s—–\-.]*$")
# Dưới cấp xã không có thành phố: chi tiết mở đầu "TP <tên>" là OCR đọc rơi chữ "D" của "TDP".
_TP_DETAIL_RE = re.compile(r"^TP\.?\s+(?=\S)")


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _full_date(value) -> str:
    """Chỉ nhận ngày đủ dd/mm/yyyy: nguồn chỉ ghi năm / tháng-năm thì ô ngày để trống, không tự thêm ngày tháng."""
    text = str(value or "").strip()
    return text if _DATE_RE.match(text) else ""


def _edit_distance(a: str, b: str) -> int:
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        prev, row[0] = row[0], i
        for j, cb in enumerate(b, start=1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (ca != cb))
    return row[-1]


def _names_align(a, b) -> bool:
    """Cùng một tên, cho phép lệch MỘT ký tự ở MỘT tiếng (mức sai của OCR chữ viết tay)."""
    words_a, words_b = _fold(a).split(), _fold(b).split()
    if not words_a or not words_b:
        return False
    if words_a == words_b:
        return True
    if len(words_a) != len(words_b) or len(words_a) < 2:
        return False
    diff = [(x, y) for x, y in zip(words_a, words_b) if x != y]
    if len(diff) != 1:
        return False
    x, y = diff[0]
    if len(x) == len(y):
        return sum(p != q for p, q in zip(x, y)) == 1
    short, long = sorted((x, y), key=len)
    return len(long) - len(short) == 1 and any(long[:i] + long[i + 1:] == short for i in range(len(long)))


def _declaration_contradicts_card(card_id, declared_id) -> bool:
    """Số trên tờ khai KHÁC hẳn số trên thẻ của cùng bên: chỉ coi là khớp khi trùng hẳn, lệch đúng một chữ số, hoặc
    tờ khai rơi 1–2 chữ số (mức sai OCR chữ viết tay)."""
    card, declared = _digits(card_id), _digits(declared_id)
    if not card or not declared or card == declared:
        return False
    if len(card) == len(declared):
        return sum(a != b for a, b in zip(card, declared)) != 1
    short, long = sorted((card, declared), key=len)
    if not 0 < len(long) - len(short) <= 2:
        return True
    it = iter(long)
    return not all(ch in it for ch in short)


def _card_is_other_person(card_name, card_id, declared_name, declared_id, other_card_id="") -> bool:
    """TH1: thẻ lệch CẢ họ tên lẫn số định danh so với khối tờ khai → thẻ của người khác.

    Trùng số (TH2) hoặc chỉ lệch một trong hai (thường do OCR chữ viết tay) thì vẫn là cùng người. Không coi là người
    khác khi họ tên tờ khai đọc lẫn chữ số (OCR chữ viết tay hỏng), hoặc số trên tờ khai là số thẻ của bên kia (người
    khai chép nhầm dòng giấy tờ của vợ / chồng).
    """
    if not declared_name or not card_name or _names_align(card_name, declared_name):
        return False
    if re.search(r"\d", str(declared_name)):
        return False
    card_digits, declared_digits, other_digits = _digits(card_id), _digits(declared_id), _digits(other_card_id)
    if declared_digits and other_digits and not _declaration_contradicts_card(other_digits, declared_digits):
        return False
    return not (card_digits and declared_digits and not _declaration_contradicts_card(card_digits, declared_digits))


def _copy_value(value) -> str:
    folded = _fold(value)
    if folded in {"yes", "true", "1", "co"}:
        return "Có"
    if folded in {"no", "false", "0", "khong"}:
        return "Không"
    return ""


def _positive_copy_quantity(value) -> str:
    match = re.search(r"\d+", str(value or ""))
    if not match:
        return ""
    quantity = int(match.group())
    return str(quantity) if quantity > 0 else ""


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _strip_admin_prefix(value):
    """xa CHỈ giữ TÊN đơn vị, bỏ tiền tố loại (Xã/Phường/Thị trấn/TT)."""
    text = str(value or "").strip()
    return re.sub(r"^(xã|phường|thị trấn|tt\.?|p\.|x\.)\s*", "", text, flags=re.IGNORECASE).strip()


def _text(value) -> str:
    text = str(value or "").strip()
    return "" if _DASH_ONLY_RE.match(text) else text


def _ward_by_fold(province: str, xa: str) -> str:
    """Tên phường / xã HIỆN HÀNH của tỉnh trùng tên trên giấy khi bỏ dấu (OCR chữ viết tay hay mất / lệch dấu); chỉ nhận
    khi đúng một đơn vị của tỉnh trùng như vậy."""
    name = canonical_province(province)
    key = re.sub(r"^(phuong|xa|thi tran|dac khu)\s+", "", _fold(xa))
    if not name or not key:
        return ""
    slug = next((item["slug"] for item in PROVINCES if item["name"] == name), "")
    wards = [ward.split(" - ")[0].strip() for ward in WARDS_BY_SLUG.get(slug, {}).get("communes") or []]
    found = [ward for ward in wards if re.sub(r"^(phuong|xa|thi tran|dac khu)\s+", "", _fold(ward)) == key]
    return found[0] if len(found) == 1 else ""


def _clean_detail(value, tinh) -> str:
    text = " ".join(_FILLER_RE.sub(" ", _text(value)).split()).strip(" ,.;")
    rest = _TP_DETAIL_RE.sub("", text)
    if rest != text and not canonical_province(rest) and _fold(rest) != _fold(tinh):
        text = f"TDP {rest}"
    return text


def _tach_part(value: dict, label: str) -> str | None:
    """Một phần của dòng "_tach" ("chi tiết: ... | xã: ... | huyện (bỏ): ... | tỉnh: ..."); None khi không có."""
    match = re.search(rf"(?:^|\|)\s*{re.escape(label)}:([^|]*)", str(value.get("_tach") or ""))
    return match.group(1).strip(" —–-") if match else None


def _area(value):
    if not isinstance(value, dict):
        return None
    tinh_raw = _text(value.get("tinh") or value.get("tỉnh"))
    # Ô tinh là một tỉnh khác hẳn tỉnh chép ở dòng "_tach" của chính địa chỉ đó: theo phần chép nguyên văn từ giấy.
    copied = _tach_part(value, "tỉnh")
    if copied and canonical_province(copied) and canonical_province(tinh_raw) not in (None, canonical_province(copied)):
        tinh_raw = copied
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": tinh_raw,
        "xa": _strip_admin_prefix(_text(value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường"))),
        "diaChi": _clean_detail(value.get("diaChi") or value.get("dia_chi") or value.get("diachi"), tinh_raw),
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    remapped = remap_area(out)
    # Địa chỉ HAI CẤP (giấy không ghi huyện) mà tên xã trên giấy là xã HIỆN HÀNH của tỉnh đó: giữ tên trên giấy — bảng
    # sáp nhập còn mang một xã CŨ trùng tên của tỉnh cũ, đã nhập vào xã khác.
    district = _tach_part(value, "huyện (bỏ)")
    if isinstance(remapped, dict) and district is not None and (
            not district or _fold(district) in (_fold(value.get("tinh") or ""), _fold(tinh_raw))):
        current = canonical_ward(remapped.get("tinh"), out["xa"])
        if current:
            remapped = {**remapped, "xa": current}
    if isinstance(remapped, dict) and remapped.get("xa") and not is_current_area(str(remapped.get("tinh") or ""),
                                                                                str(remapped.get("xa") or "")):
        current = _ward_by_fold(str(remapped.get("tinh") or ""), out["xa"])
        if current:
            remapped = {**remapped, "xa": current}
    return city_province_area(remapped)


# Tỉnh đã giải thể trước 2025 (giấy chứng nhận kết hôn cũ còn ghi) → các tỉnh hiện hành chứa địa bàn của nó. Bảng sáp
# nhập không có các tên này nên tra xã theo cả nước và có thể ra một xã cùng tên ở tỉnh khác.
_OLD_PROVINCES = {
    "ha bac": ("Bắc Ninh",),
    "hoang lien son": ("Lào Cai",),
    "vinh phu": ("Phú Thọ",),
    "ha nam ninh": ("Ninh Bình",),
    "nam ha": ("Ninh Bình",),
    "quang nam da nang": ("Đà Nẵng",),
    "minh hai": ("Cà Mau",),
    "cuu long": ("Vĩnh Long",),
    "bac thai": ("Thái Nguyên",),
    "ha tuyen": ("Tuyên Quang",),
    "hai hung": ("Hải Phòng", "Hưng Yên"),
    "ha son binh": ("Hà Nội", "Phú Thọ"),
    "nghe tinh": ("Nghệ An", "Hà Tĩnh"),
    "binh tri thien": ("Quảng Trị", "Huế"),
    "nghia binh": ("Quảng Ngãi", "Gia Lai"),
    "phu khanh": ("Đắk Lắk", "Khánh Hòa"),
    "thuan hai": ("Khánh Hòa", "Lâm Đồng"),
    "song be": ("Hồ Chí Minh", "Đồng Nai"),
    "cao lang": ("Cao Bằng", "Lạng Sơn"),
    "gia lai kon tum": ("Gia Lai", "Quảng Ngãi"),
}
_DISTRICT_AGENCY_RE = re.compile(r"^(huyen|quan|thi xa|thanh pho|tp)\b")


def _province_key(value) -> str:
    key = re.sub(r"[^a-z0-9]+", " ", _fold(value)).strip()
    return re.sub(r"^(tinh|thanh pho|tp)\s+", "", key)


def _previous_registration_area(values: dict) -> dict | None:
    """Nơi đăng ký kết hôn trước đây → đơn vị hành chính HIỆN HÀNH (dropdown của cổng chỉ liệt kê đơn vị hiện hành).

    Giữ tiền tố loại đơn vị ("Xã/Phường/Thị trấn") vì option trên cổng có tiền tố. Chỉ điền ô đơn vị khi tra được một
    đơn vị hiện hành của đúng tỉnh: cơ quan cấp huyện, xã đã giải thể, xã của tỉnh cũ mà bảng tra ra tỉnh khác → chỉ
    điền tỉnh, để cán bộ tự chọn đơn vị còn hơn chọn nhầm.
    """
    tinh = str(values.get("KetHonCu_TinhDangKy") or "").strip()
    xa = re.sub(r"^\s*(ubnd|uy ban nhan dan|ủy ban nhân dân|uỷ ban nhân dân)\s+", "", str(values.get("KetHonCu_XaDangKy") or ""),
                flags=re.IGNORECASE).strip()
    if _DISTRICT_AGENCY_RE.match(_fold(xa)):
        xa = ""
    if not tinh and not xa:
        return None
    candidates = _OLD_PROVINCES.get(_province_key(tinh))
    area = city_province_area(remap_area({"quocGia": "Việt Nam", "tinh": tinh, "xa": xa, "diaChi": ""}))
    province = canonical_province(area.get("tinh") or "")
    if candidates and province not in candidates:
        area = {**area, "tinh": candidates[0] if len(candidates) == 1 else "", "xa": ""}
        province = canonical_province(area["tinh"] or "")
    if not province:
        area = {**area, "tinh": ""}
    if area.get("xa") and not (province and is_current_area(province, area["xa"])):
        area = {**area, "xa": ""}
    return area if area.get("tinh") or area.get("xa") else None


def _registration_number(value) -> str:
    """Số / quyển số đăng ký cũ phải có chữ số và không phải một ngày (lượt trích có khi chép cả cụm ngày đăng ký)."""
    text = str(value or "").strip()
    if not re.search(r"\d", text) or re.search(r"\b(ngay|thang|nam)\b", _fold(text)) or re.fullmatch(
            r"\d{1,2}[/.-]\d{1,2}[/.-]\d{4}", text):
        return ""
    # Số của bản sao / trích lục cấp lại ("…/TL.KH-BS") không phải số đăng ký kết hôn gốc.
    if re.search(r"-\s*bs\b|\btl\s*\.?\s*kh\b", _fold(text)):
        return ""
    return text


def _ui_field(name: str, value) -> dict | None:
    comp = UI_COMP_BY_NAME.get(name)
    return {"name": name, "comp": comp, "value": value} if comp else None


def _issuer(noi_cap, ngay_cap) -> str:
    """Tên cơ quan cấp đầy đủ. Cụm in sẵn của mẫu tờ khai liệt kê cả hai cơ quan ("Cục CSQLHC về TTXH/Bộ Công an") mà
    người khai không gạch bớt thì không cho biết cơ quan nào → theo ngày cấp. Không có cả nơi cấp lẫn ngày cấp thì để
    trống: ngày cấp quyết định loại thẻ."""
    text = _fold(noi_cap)
    if "bo cong an" in text and ("cuc" in text or "c06" in text):
        noi_cap = ""
    issuer = normalize_issuer(noi_cap)
    if not issuer:
        return default_issuer(ngay_cap) if ngay_cap else ""
    # Cơ quan cấp phải khớp ngày cấp: thẻ cấp từ 01/7/2024 do Bộ Công an cấp, thẻ cấp trước đó do Cục Cảnh sát cấp.
    issuer = issuer_by_issue_date(issuer, ngay_cap)
    if issuer == ISSUER_BO_CONG_AN and default_issuer(_full_date(ngay_cap)) == ISSUER_CUC and _full_date(ngay_cap):
        return ISSUER_CUC
    return issuer


def _ethnicity(*sources) -> str:
    """Dân tộc theo nguồn đầu tiên có trong dropdown: chữ OCR ngoài danh mục (đọc lệch) thì xét nguồn kế, hết nguồn thì
    để trống cho cán bộ chọn."""
    for source in sources:
        value, other = ethnicity_for_form(source)
        if value and not other:
            return value
    return ""


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    """Suy field UI tất định từ compact facts."""
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if default:
            field["default"] = True  # extension tô VIỀN VÀNG (giá trị mặc định, không từ giấy tờ)
        out.append(field)
        seen.add(name)

    def add_person(side: str, declaration: str, other: str) -> None:
        if not (
            values.get(f"{side}_SoDinhDanh") or values.get(f"{side}_HoTen")
            or values.get(f"{declaration}_SoDinhDanh") or values.get(f"{declaration}_HoTen")
        ):
            return
        # TH1 — thẻ lệch CẢ tên lẫn số so với khối vợ/chồng trên tờ khai: thẻ của NGƯỜI KHÁC. Điền theo tờ khai
        # (viền vàng), bỏ ngày/nơi cấp và nơi cư trú của thẻ. Còn lại: thẻ (bản IN) trước, tờ khai bù ô thẻ thiếu; số
        # tờ khai trái hẳn số thẻ thì phần bù viền vàng để soát.
        card_is_other = _card_is_other_person(
            values.get(f"{side}_HoTen"), values.get(f"{side}_SoDinhDanh"),
            values.get(f"{declaration}_HoTen"), values.get(f"{declaration}_SoDinhDanh"),
            values.get(f"{other}_SoDinhDanh"))
        unsure = _declaration_contradicts_card(values.get(f"{side}_SoDinhDanh"), values.get(f"{declaration}_SoDinhDanh"))

        def identity(name: str) -> tuple:
            declared = values.get(f"{declaration}_{name}")
            if card_is_other:
                return declared, bool(declared)
            card_value = values.get(f"{side}_{name}")
            if card_value:
                return card_value, False
            return declared, bool(declared) and unsure

        ho_ten, ho_ten_default = identity("HoTen")
        so_dinh_danh, so_default = identity("SoDinhDanh")
        ngay_sinh, ngay_sinh_default = identity("NgaySinh")
        ngay_cap, ngay_cap_default = identity("NgayCap")
        noi_cap, noi_cap_default = identity("NoiCap")
        issuer = _issuer(noi_cap, ngay_cap)
        # Nơi cư trú: người dân tự khai trên tờ khai / bản cam đoan trước (thẻ hay in nơi thường trú cũ trước sáp nhập),
        # thẻ bù khi không có; tên đường viết tay sửa theo địa chỉ IN trên thẻ của chính người đó.
        declared_raw = values.get(f"{declaration}_NoiCuTru_TrongNuoc")
        card_raw = None if card_is_other else values.get(f"{side}_NoiCuTru_TrongNuoc")
        card_area = _area(card_raw)
        if isinstance(declared_raw, dict) and declared_raw.get("xa") and not declared_raw.get("tinh") and card_area:
            # Tờ khai ghi thiếu cấp tỉnh: chỉ bù đúng phần thiếu từ thẻ của chính người đó.
            declared_raw = {**declared_raw, "tinh": card_area.get("tinh")}
        declared_area = _area(declared_raw)
        if declared_area and not declared_area.get("xa") and card_area and card_area.get("xa"):
            # Dòng tờ khai không ghi xã (chỉ có chi tiết / tỉnh): lấy trọn địa chỉ theo thẻ, không ghép nửa nọ nửa kia.
            declared_area = None
        area = prefer_printed_street(declared_area, card_area) if declared_area else card_area
        dan_toc = _ethnicity(values.get(f"{declaration}_DanToc"),
                             None if card_is_other else values.get(f"{side}_DanToc"))

        add(f"HoTen{side}", upper_person_name(ho_ten), ho_ten_default)
        add(f"SoDinhDanh_{side}", so_dinh_danh, so_default)
        add(f"SoGiayToDinhDanh_{side}", so_dinh_danh, so_default)
        add(f"LoaiGiayToDinhDanh_{side}", id_doc_type("Căn cước công dân", issuer))
        add(f"NgaySinh{side}", ngay_sinh, ngay_sinh_default)
        add(f"NgayCapDD_{side}", ngay_cap, ngay_cap_default)
        add(f"NoiCapDD_{side}", issuer, noi_cap_default)
        add(f"DanToc{side}", dan_toc)
        add(f"QuocTich{side}", values.get(f"{side}_QuocTich") or "Việt Nam")
        add(f"LoaiCuTru_{side}", "Thường trú")
        if area:
            add(f"NoiCuTru_{side}", "1")
            add(f"NoiCuTru_{side}_TrongNuoc", area)
        # Đăng ký lại = hai người đang là vợ chồng: tình trạng hôn nhân mặc định (viền vàng). Số lần kết hôn không có
        # trên tờ khai đăng ký lại → để trống cho cán bộ.
        add(f"LoaiTinhTrangHonNhan_{side}", _TINH_TRANG_HON_NHAN_DEFAULT, default=True)

    add_person("BenNu", "ToKhaiNu", "BenNam")
    add_person("BenNam", "ToKhaiNam", "BenNu")

    # Hồ sơ gốc (lần đăng ký kết hôn trước đây).
    add("loaiDangKy", _LOAI_DANG_KY_LAI, default=True)
    add("soDangKyTruocDay", _registration_number(values.get("KetHonCu_So")))
    # Quyển số không có công thức suy ra đáng tin cậy; chỉ điền khi tài liệu ghi rõ.
    add("quyenDangKyTruocDay", _registration_number(values.get("KetHonCu_QuyenSo")))
    add("ngayDangKyTruocDay", _full_date(values.get("KetHonCu_NgayDangKy")))
    # Cascading: chọn TỈNH (filter) trước để dropdown đơn vị load, rồi mới chọn đơn vị.
    noi_dang_ky_cu = _previous_registration_area(values)
    if noi_dang_ky_cu:
        add("noiDangKyTruocDay_filter", noi_dang_ky_cu.get("tinh"))
        add("noiDangKyTruocDay", noi_dang_ky_cu.get("xa"))

    # Đề nghị cấp bản sao: chỉ theo ô tích / số lượng ghi trên tờ khai. Số lượng dương vừa là bằng chứng chọn "Có"
    # vừa điền ô SoLuong; tờ khai để trống thì bỏ hẳn (cán bộ hỏi người dân), không tự mặc định.
    copy_quantity = _positive_copy_quantity(values.get("CopyRequest_Quantity"))
    if copy_quantity:
        add("CapBanSao", "Có")
        add("SoLuong", copy_quantity)
    else:
        add("CapBanSao", _copy_value(values.get("CopyRequest_WantsCopy")))

    return apply_account_marriage(out, options, _ui_field, _area,
                                  lambda issuer: id_doc_type("Căn cước công dân", issuer))
