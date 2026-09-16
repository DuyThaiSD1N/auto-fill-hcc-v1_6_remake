"""Map compact marriage facts to legacy x-* UI fields."""

import re
import unicodedata

from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type
from app.pipelines._shared.area_remap import is_current_area, remap_area
from app.pipelines._shared.ethnic_normalize import ethnicity_for_form
from app.pipelines._shared.formatting import prefer_printed_street, upper_person_name
from app.pipelines._shared.foreign_id import (
    normalize_nationality,
    normalize_id_type,
    normalize_foreign_tinh,
    is_foreign,
)
from app.pipelines.ket_hon.process.schema import UI_ALIASES, UI_COMP_BY_NAME


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


_HCM_PROVINCE_KEYS = {
    "hochiminh",
    "tphochiminh",
    "thanhphohochiminh",
    "tphcm",
    "thanhphohcm",
    "hcm",
}


def _normalize_domestic_province(value) -> str:
    """Chuẩn hóa alias cấp tỉnh cục bộ cho đăng ký kết hôn."""
    raw = re.sub(r"\s+", " ", str(value or "")).strip()
    key = re.sub(r"[^a-z0-9]+", "", _fold(raw))
    if key in _HCM_PROVINCE_KEYS:
        return "Thành phố Hồ Chí Minh"
    return raw


# Chuẩn hóa dân tộc về ĐÚNG nhãn option trong dropdown x-select của form.
# Phân biệt 2 option khác nhau: "Mông" (ghi "Mông") và "Mông (Hmông)" (ghi "H'Mông"/"H Mông"/"Hmông").
# Key = fold(bỏ dấu) đã loại bỏ ' và khoảng trắng.
_DAN_TOC_CANON = {
    "mong": "Mông",            # ghi "Mông" → option "Mông"
    "hmong": "Mông (Hmông)",   # ghi "H'Mông"/"H Mông"/"Hmông" → option "Mông (Hmông)"
}

# Không có mục "Kết hôn lần thứ mấy" trên giấy nhưng tình trạng hôn nhân đã cho biết người này
# TỪNG đăng ký kết hôn (đã ly hôn / vợ-chồng đã chết) → lần đăng ký này ít nhất là lần 2.
_SO_LAN_KET_HON_THEO_TINH_TRANG = {
    "2": "1",  # chưa đăng ký kết hôn với ai
    "3": "2",  # đã ly hôn
    "4": "2",  # vợ/chồng đã chết
}

_TINH_TRANG_HON_NHAN = {
    "1": "Hiện tại đang có vợ/chồng",
    "2": "Hiện tại chưa đăng ký kết hôn với ai",
    "3": "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng đã ly hôn; hiện tại chưa đăng ký kết hôn với ai",
    "4": "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng vợ/chồng đã chết; hiện tại chưa đăng ký kết hôn với ai",
    "5": "Từ ngày… tháng… năm… đến ngày… tháng… năm … chưa đăng ký kết hôn với ai; hiện tại đang có vợ/chồng",
    "6": "Khác",
}


# Radio "Loại đăng ký" của cổng khớp theo hậu tố id (loaiDangKy-1) hoặc theo nhãn hiển thị.
_LOAI_DANG_KY_LAN_DAU = "1"


def _loai_dang_ky(value) -> str:
    """Loại đăng ký ĐỌC TỪ TỜ KHAI → giá trị radio; rỗng nếu tờ khai không ghi."""
    text = str(value or "").strip()
    if not text:
        return ""
    # "Đăng ký lần đầu" dùng mã id để chắc chắn khớp; nhãn khác giữ nguyên cho
    # extension khớp theo text (vd "Đăng ký lại").
    return _LOAI_DANG_KY_LAN_DAU if "lan dau" in _fold(text) else text


def _normalize_dan_toc(value):
    raw = str(value or "").strip()
    if not raw:
        return raw
    key = _fold(raw).replace("'", "").replace("’", "").replace(" ", "")
    return _DAN_TOC_CANON.get(key, raw)


def _divorce_party_matches(person_name, parties) -> bool:
    """Người này có thật sự là đương sự của văn bản ly hôn LLM gán cho họ không?

    Hồ sơ kết hôn hay có HAI quyết định ly hôn (mỗi bên một văn bản) nằm cùng một file;
    LLM từng lấy văn bản của bên này điền cho cả hai bên. LLM phải trả kèm danh sách đương sự
    đọc trên chính văn bản đó (*_BanAnLyHon_DuongSu) để đối chiếu tất định ở đây.
    Thiếu dữ liệu đối chiếu → giữ nguyên kết quả LLM (không tự ý bỏ).
    """
    person = re.sub(r"[^a-z0-9]+", " ", _fold(person_name)).strip()
    listed = re.sub(r"[^a-z0-9]+", " ", _fold(parties)).strip()
    if not person or not listed:
        return True
    return f" {person} " in f" {listed} "


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _declaration_contradicts_card(card_id, declared_id) -> bool:
    """Số trên tờ khai KHÁC hẳn số trên thẻ của cùng cột nam/nữ.

    Cùng cột nên gần như luôn là OCR đọc sai chữ viết tay; chỉ coi là "khớp" khi trùng hẳn, lệch
    đúng một chữ số, hoặc tờ khai rơi 1–2 chữ số. Còn lại → giá trị tờ khai bù vào vẫn điền nhưng
    tô viền vàng để soát (không chắc thẻ và tờ khai là cùng người).
    """
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


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


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


def _normalize_admin_unit(value):
    """Giữ loại đơn vị và mở rộng P/X/TT để khớp nhãn phường xã trên form."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    patterns = (
        (r"^P(?:\.\s*|\s+)", "Phường "),
        (r"^X(?:\.\s*|\s+)", "Xã "),
        (r"^TT(?:\.\s*|\s+)", "Thị trấn "),
        (r"^phường\s+", "Phường "),
        (r"^xã\s+", "Xã "),
        (r"^thị\s+trấn\s+", "Thị trấn "),
    )
    for pattern, replacement in patterns:
        if re.match(pattern, text, flags=re.IGNORECASE):
            return re.sub(pattern, replacement, text, count=1, flags=re.IGNORECASE).strip()
    return text


def _has_usable_ward(area) -> bool:
    """Địa chỉ này có ra được một xã/phường CHỌN ĐƯỢC trên cổng không (đã qua remap)."""
    if not isinstance(area, dict):
        return False
    xa = area.get("xa") or ""
    return bool(xa) and is_current_area(area.get("tinh") or "", xa)


def _pick_residence(declared, printed, nationality: str):
    """Nơi cư trú: TỜ KHAI trước, nhưng chỉ khi nó ra được một xã có thật.

    Tờ khai là chữ viết tay, hay ghi tắt hoặc thiếu cấp, và LLM có lúc điền bừa cho ô bỏ trống
    (chép luôn địa chỉ của bên kia). Khi đó ô xã không khớp option nào trên cổng — giữ tờ khai là
    vứt mất địa chỉ ĐÚNG đã in trên thẻ căn cước của chính người đó, đổi một địa chỉ sai lấy một
    ô trống. Địa chỉ nước ngoài không có trong danh mục xã nên giữ nguyên thứ tự ưu tiên cũ.
    """
    if is_foreign(nationality):
        return declared or printed
    if _has_usable_ward(declared):
        return declared
    if _has_usable_ward(printed):
        return printed
    return declared or printed


def _area(value, nationality: str = "Việt Nam"):
    if not isinstance(value, dict):
        return None
    # quocGia: dùng từ LLM nếu có, không thì suy từ nationality
    quoc_gia = value.get("quocGia") or value.get("quoc_gia") or ""
    if not quoc_gia or _fold(quoc_gia) == "viet nam":
        # Nếu LLM trả "Việt Nam" nhưng người này là nước ngoài → dùng nationality
        quoc_gia = nationality if is_foreign(nationality) else "Việt Nam"

    tinh_raw = value.get("tinh") or value.get("tỉnh") or ""

    # Normalize tên tỉnh nước ngoài nếu có trong bảng
    if is_foreign(quoc_gia) and tinh_raw:
        tinh_raw = normalize_foreign_tinh(quoc_gia, tinh_raw)
    elif tinh_raw:
        # Prompt phải trả tên cấp tỉnh đầy đủ; mapper vẫn chặn các alias HCM phổ biến.
        tinh_raw = _normalize_domestic_province(tinh_raw)

    out = {
        "quocGia": quoc_gia,
        "tinh":    tinh_raw,
        "xa":      _normalize_admin_unit(value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường")),
        "diaChi":  value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    # Chỉ remap địa chỉ Việt Nam (bảng remap_lam_dong không có địa danh nước ngoài)
    if not is_foreign(quoc_gia):
        # "huyen" là khóa GỢI Ý, không phải ô trên biểu mẫu — nhưng phải chuyển tiếp cho remap:
        # nó gỡ nhập nhằng tên xã trùng ở nhiều huyện, và là bằng chứng để phát hiện LLM đọc lệch
        # cấp (đặt tên thôn vào ô xã, đẩy tên xã thật sang "huyen"). Bỏ ở đây thì remap mù.
        return remap_area(out, huyen_hint=value.get("huyen") or value.get("quanHuyen") or "")
    return out


def enrich(fields: list[dict]) -> list[dict]:
    """Derive deterministic UI fields from compact source facts."""
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False, **extra) -> None:
        # default=True: giá trị suy diễn/mặc định (không đọc từ giấy tờ) — FE tô viền VÀNG
        # để người dân tự rà và sửa nếu không đúng hoàn cảnh của mình.
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value, **extra}
        if name in UI_ALIASES:
            item["aliases"] = UI_ALIASES[name]
        if default:
            item["default"] = True
        out.append(item)
        seen.add(name)

    def add_person(src: str, dst: str, declaration: str) -> None:
        declaration_area_name = f"{declaration}_NoiCuTru_TrongNuoc"
        has_person = bool(
            values.get(f"{src}_SoDinhDanh") or values.get(f"{src}_HoTen")
            or values.get(f"{declaration}_SoDinhDanh") or values.get(f"{declaration}_HoTen")
        )
        if not has_person:
            return
        # Nhân thân: THẺ CĂN CƯỚC (bản IN) trước — họ tên, số, ngày sinh, ngày cấp, nơi cấp; tờ khai
        # chỉ bù ô thẻ thiếu. Số tờ khai trái hẳn số thẻ → vẫn bù nhưng viền vàng để soát.
        unsure = _declaration_contradicts_card(
            values.get(f"{src}_SoDinhDanh"), values.get(f"{declaration}_SoDinhDanh"))

        def identity(name: str) -> tuple:
            card_value = values.get(f"{src}_{name}")
            if card_value:
                return card_value, False
            declared = values.get(f"{declaration}_{name}")
            return declared, bool(declared) and unsure

        ho_ten, ho_ten_default = identity("HoTen")
        so_dinh_danh, so_default = identity("SoDinhDanh")
        ngay_sinh, ngay_sinh_default = identity("NgaySinh")
        ngay_cap, ngay_cap_default = identity("NgayCap")
        noi_cap, noi_cap_default = identity("NoiCap")
        issuer = noi_cap or default_issuer(ngay_cap)

        # Suy nationality: ưu tiên field QuocTich, fallback từ quocGia trong địa chỉ
        # v2: thêm fallback quocGia để xử lý khi LLM bỏ sót QuocTich
        raw_quoc_tich = values.get(f"{src}_QuocTich")
        if not raw_quoc_tich:
            # LLM hay bỏ sót QuocTich nhưng đặt đúng quocGia trong địa chỉ
            addr_raw = values.get(f"{src}_NoiCuTru_TrongNuoc")
            if isinstance(addr_raw, dict):
                raw_quoc_tich = addr_raw.get("quocGia") or addr_raw.get("quoc_gia")
        nationality = normalize_nationality(raw_quoc_tich)
        # Nơi cư trú: TỜ KHAI trước (khai hiện tại), thẻ căn cước đỡ khi tờ khai không dùng được.
        to_khai_area_raw = values.get(declaration_area_name)
        cccd_area_raw = values.get(f"{src}_NoiCuTru_TrongNuoc")
        declared_area = _area(to_khai_area_raw, nationality) if isinstance(to_khai_area_raw, dict) and (
            to_khai_area_raw.get("tinh") or to_khai_area_raw.get("xa") or to_khai_area_raw.get("diaChi")
        ) else None
        printed_area = _area(cccd_area_raw, nationality)
        area = _pick_residence(declared_area, printed_area, nationality)
        # Tên đường viết tay trên tờ khai sửa theo địa chỉ IN trên thẻ của chính người đó.
        area = prefer_printed_street(area, _area(cccd_area_raw, nationality))

        add(f"HoTen{dst}", upper_person_name(ho_ten), default=ho_ten_default)
        add(f"SoDinhDanh_{dst}", so_dinh_danh, default=so_default)
        add(f"SoGiayToDinhDanh_{dst}", so_dinh_danh, default=so_default)

        # Loại giấy tờ: người nước ngoài dùng foreign_id_map, người VN dùng issuer
        if is_foreign(nationality):
            # Ưu tiên loại giấy tờ từ LLM → normalize, fallback "Hộ chiếu (CMND nước ngoài)"
            raw_id_type = values.get(f"{src}_LoaiGiayTo")
            id_type = normalize_id_type(raw_id_type) or "Hộ chiếu (CMND nước ngoài)"
        else:
            id_type = id_doc_type("Thẻ căn cước công dân", issuer)
        add(f"LoaiGiayToDinhDanh_{dst}", id_type)

        add(f"NgaySinh{dst}", ngay_sinh, default=ngay_sinh_default)
        add(f"NgayCapDD_{dst}", ngay_cap, default=ngay_cap_default)
        add(f"NoiCapDD_{dst}", issuer, default=noi_cap_default)
        # Không giấy nào ghi dân tộc → KHÔNG đoán, để trống; FE tự tô ĐỎ ô "-- Chọn --"
        # (markAllEmptyFieldsRed) để cán bộ/người dân biết phải tự chọn.
        # Dân tộc: CCCD chip không in dân tộc nên nguồn thật gần như luôn là cột tờ khai. Tên có trong
        # dropdown thì chọn thẳng (biến thể như "K'Ho" → "Cơ Ho"); tên ngoài danh sách (vd "Cill") thì
        # chọn "Khác" và ghi nguyên văn vào ô bên cạnh — ô đó chỉ render sau khi chọn nên phát ngay sau.
        dan_toc, dan_toc_khac = ethnicity_for_form(
            values.get(f"{src}_DanToc") or values.get(f"{declaration}_DanToc"))
        add(f"DanToc{dst}", _normalize_dan_toc(dan_toc))
        add(f"DanTocKhac{dst}", dan_toc_khac, otherOf=f"DanToc{dst}")
        add(f"QuocTich{dst}", nationality)
        add(f"LoaiCuTru_{dst}", "Thường trú")
        if area:
            if is_foreign(nationality):
                # Người nước ngoài: radio "2" (Khác) + field NuocNgoai
                add(f"NoiCuTru_{dst}", "2")
                full_addr = ", ".join(p for p in (area.get("diaChi"), area.get("xa"), area.get("tinh")) if p)
                add(f"NoiCuTru_{dst}_NuocNgoai", {"quocGia": area["quocGia"], "diaChi": full_addr})
            else:
                # Người Việt Nam: radio "1" (Trong nước) + field TrongNuoc
                add(f"NoiCuTru_{dst}", "1")
                add(f"NoiCuTru_{dst}_TrongNuoc", area)
        # Mỗi bên xử lý độc lập: nếu cả số lần và tình trạng đều không có
        # thì giữ mặc định nghiệp vụ của form (lần 1, chưa đăng ký).
        # Nếu một trong hai có bằng chứng thì chỉ điền field có bằng chứng,
        # không suy diễn field còn thiếu.
        so_lan = str(values.get(f"{src}_SoLanKetHon") or "").strip()
        status_code = str(values.get(f"{src}_TinhTrangHonNhan") or "").strip()
        if not so_lan and not status_code:
            add(f"SoLanKetHon_{dst}", "1", default=True)
            add(f"LoaiTinhTrangHonNhan_{dst}", _TINH_TRANG_HON_NHAN["2"], default=True)
        else:
            if so_lan:
                add(f"SoLanKetHon_{dst}", so_lan)
            elif status_code in _SO_LAN_KET_HON_THEO_TINH_TRANG:
                # Giấy tờ không ghi số lần nhưng tình trạng hôn nhân đã suy ra được;
                # gắn default để FE tô vàng cho người dùng rà lại (có thể là lần 3+).
                add(f"SoLanKetHon_{dst}",
                    _SO_LAN_KET_HON_THEO_TINH_TRANG[status_code], default=True)
            add(f"LoaiTinhTrangHonNhan_{dst}", _TINH_TRANG_HON_NHAN.get(status_code))
            # Kết hôn lần 1 = chưa từng đăng ký kết hôn lần nào → tình trạng hôn nhân
            # chỉ có thể là "Hiện tại chưa đăng ký kết hôn với ai" (suy ra được chắc
            # chắn từ số lần, nên không tô vàng).
            if so_lan == "1":
                add(f"LoaiTinhTrangHonNhan_{dst}", _TINH_TRANG_HON_NHAN["2"])
            elif status_code == "3":
                # Chỉ điền khi văn bản ly hôn thật sự ghi tên người này là đương sự — chặn
                # trường hợp LLM lấy quyết định của bên kia gán sang (số/ngày/cơ quan sai hết).
                if _divorce_party_matches(ho_ten,
                                          values.get(f"{src}_BanAnLyHon_DuongSu")):
                    decision = {
                        "soBanAnQuyetDinhLyHon": values.get(f"{src}_BanAnLyHon_So"),
                        "ngayCapBanAnQuyetDinhLyHon": values.get(f"{src}_BanAnLyHon_Ngay"),
                        "coQuanCapBanAnQuyetDinhLyHon": values.get(f"{src}_BanAnLyHon_CoQuan"),
                    }
                    decision = {k: v for k, v in decision.items() if v}
                    if decision:
                        add(f"TTHN_LyHon{dst}", decision)

    add_person("CccdNu", "BenNu", "ToKhaiNu")
    add_person("CccdNam", "BenNam", "ToKhaiNam")

    # Chỉ tác động radio khi tờ khai ghi rõ loại đăng ký. Không có dữ liệu thì bỏ hẳn;
    # cổng tự giữ trạng thái của nó, mapper không mặc định "Đăng ký lần đầu".
    loai_dang_ky = _loai_dang_ky(values.get("ToKhai_LoaiDangKy"))
    if loai_dang_ky:
        add("loaiDangKy", loai_dang_ky)

    # Số lượng dương vừa là bằng chứng chọn "Có", vừa được điền vào input raw SoLuong.
    # Không có số lượng thật thì không tự mặc định.
    copy_quantity = _positive_copy_quantity(values.get("CopyRequest_Quantity"))
    if copy_quantity:
        add("CapBanSao", "Có")
        add("SoLuong", copy_quantity)
    else:
        add("CapBanSao", _copy_value(values.get("CopyRequest_WantsCopy")))

    return out
