"""Map compact "thay đổi/cải chính hộ tịch" facts → field UI x-* trên form moj."""

import re
import unicodedata

from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines._shared.area_remap import remap_area
from app.pipelines.thay_doi_ho_tich.process.schema import UI_COMP_BY_NAME


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _normalize_person_name(value):
    """Giấy hộ tịch cũ hay chèn gạch nối giữa từng tiếng; eForm cần tên chuẩn."""
    text = str(value or "").strip()
    text = re.sub(r"\s*[-‐‑–—]+\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# Chuẩn hóa dân tộc về đúng nhãn option dropdown: "Mông" giữ "Mông"; "H'Mông"/"Hmông" → "Mông (Hmông)".
_DAN_TOC_CANON = {"mong": "Mông", "hmong": "Mông (Hmông)"}


def _normalize_dan_toc(value):
    raw = str(value or "").strip()
    if not raw:
        return raw
    key = _fold(raw).replace("'", "").replace("’", "").replace(" ", "")
    return _DAN_TOC_CANON.get(key, raw)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _strip_admin_prefix(value):
    """xa CHỈ giữ TÊN đơn vị, bỏ tiền tố loại (Xã/Phường/Thị trấn/TT)."""
    text = str(value or "").strip()
    return re.sub(r"^(xã|phường|thị trấn|tt\.?)\s+", "", text, flags=re.IGNORECASE).strip()


# Thành phố thuộc tỉnh hay bị nhầm là "tỉnh" → ánh xạ về tỉnh thật (OCR/tờ khai chỉ ghi tên TP).
_CITY_TO_PROVINCE = {
    "da lat": "Lâm Đồng",
    "bao loc": "Lâm Đồng",
}


def _norm_tinh(value):
    text = str(value or "").strip()
    return _CITY_TO_PROVINCE.get(_fold(text), text)


def _area(value):
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": _norm_tinh(value.get("tinh") or value.get("tỉnh")),
        "xa": _strip_admin_prefix(value.get("xa") or value.get("xã")),
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    return remap_area(out)


_LOAI_KEY = {
    "birth": "birth", "khai sinh": "birth",
    "marriage": "marriage", "ket hon": "marriage",
    "death": "death", "khai tu": "death",
}

_NGHIEP_VU = {
    "birth": "Hồ sơ khai sinh",
    "marriage": "Hồ sơ kết hôn",
    "death": "Hồ sơ khai tử",
}


def _event_type(values: dict) -> str:
    raw = _fold(values.get("LoaiSuKien"))
    if raw in _LOAI_KEY:
        return _LOAI_KEY[raw]
    name = _fold(values.get("TenGiayTo"))
    if "ket hon" in name:
        return "marriage"
    if "khai tu" in name or "chung tu" in name or "bao tu" in name:
        return "death"
    if "khai sinh" in name:
        return "birth"
    return ""


def _viec_dang_ky(values: dict) -> str | None:
    """Map cụm 'Đề nghị cơ quan đăng ký việc <X>' → 1 trong 4 option của select viecDangKy."""
    text = _fold(values.get("ViecDangKy"))
    if not text:
        return None
    if "dan toc" in text:
        return "Xác định lại dân tộc"
    if "cai chinh" in text:
        return "Cải chính"
    if "bo sung" in text:
        return "Bổ sung hộ tịch"
    if "thay doi" in text:
        return "Thay đổi"
    return None


def _identity_cards(values: dict) -> list[dict]:
    cards = values.get("DanhSachCccd")
    if not isinstance(cards, list):
        return []
    return [card for card in cards if isinstance(card, dict)]


def _card_matches_person(card: dict, values: dict, prefix: str) -> bool:
    """Khớp thẻ với chủ thể; số khác nhau là bằng chứng loại trừ mạnh."""
    card_id = _digits(card.get("SoDinhDanh"))
    person_id = _digits(values.get(f"{prefix}_SoDinhDanh"))
    if card_id and person_id:
        return card_id == person_id

    card_name = _fold(card.get("HoTen"))
    person_name = _fold(values.get(f"{prefix}_HoTen"))
    if not card_name or not person_name or card_name != person_name:
        return False

    card_dob = _digits(card.get("NgaySinh"))
    person_dob = _digits(values.get(f"{prefix}_NgaySinh"))
    return not card_dob or not person_dob or card_dob == person_dob


def _requester_card(values: dict, options: dict | None) -> dict | None:
    ctx = (options or {}).get("formContext") or {}
    requester_id = _digits(
        ctx.get("applicantIdentityNumber")
        or ctx.get("identityNumber")
    )
    requester_name = _fold(
        ctx.get("applicantFullname")
        or ctx.get("fullname")
    )
    cards = _identity_cards(values)

    if requester_id:
        matches = [
            card for card in cards
            if _digits(card.get("SoDinhDanh")) == requester_id
        ]
        if len(matches) == 1:
            return matches[0]
    if requester_name:
        matches = [
            card for card in cards
            if _fold(card.get("HoTen")) == requester_name
        ]
        if len(matches) == 1:
            return matches[0]
    return None


def _card_for_subject(values: dict, prefix: str) -> dict | None:
    matches = [
        card for card in _identity_cards(values)
        if _card_matches_person(card, values, prefix)
    ]
    return matches[0] if len(matches) == 1 else None


def _marriage_subject(values: dict, options: dict | None = None) -> str | None:
    """Chọn chồng/vợ bằng khớp CCCD, không dùng fallback "không chồng thì vợ"."""
    requester_card = _requester_card(values, options)
    if requester_card:
        direct_matches = [
            prefix
            for prefix in ("Chong", "Vo")
            if _card_matches_person(requester_card, values, prefix)
        ]
        if len(direct_matches) == 1:
            return direct_matches[0]

    card_matches = [
        prefix
        for prefix in ("Chong", "Vo")
        if _card_for_subject(values, prefix) is not None
    ]
    if len(card_matches) == 1:
        return card_matches[0]

    # Tương thích output cũ chưa có DanhSachCccd.
    cccd_id = _digits(values.get("Cccd_SoDinhDanh"))
    cccd_name = _fold(values.get("Cccd_HoTen"))

    def matches(prefix: str) -> bool:
        person_id = _digits(values.get(f"{prefix}_SoDinhDanh"))
        person_name = _fold(values.get(f"{prefix}_HoTen"))
        if cccd_id and person_id:
            return cccd_id == person_id
        return bool(cccd_name and person_name and cccd_name == person_name)

    direct_matches = [
        prefix
        for prefix in ("Chong", "Vo")
        if matches(prefix)
    ]
    if len(direct_matches) == 1:
        return direct_matches[0]

    # Người yêu cầu có thể là con/người đại diện, không thuộc hai bên kết hôn.
    # Khi chỉ một bên được agent bổ sung đủ dấu hiệu CCCD đính kèm, chọn đúng bên đó.
    def has_attached_identity(prefix: str) -> bool:
        person_id = _digits(values.get(f"{prefix}_SoDinhDanh"))
        has_valid_id = len(person_id) in (9, 12)
        has_card_detail = bool(
            values.get(f"{prefix}_NgayCapGiayTo")
            or values.get(f"{prefix}_NoiCapGiayTo")
        )
        return has_valid_id and has_card_detail

    enriched_matches = [
        prefix
        for prefix in ("Chong", "Vo")
        if has_attached_identity(prefix)
    ]
    return enriched_matches[0] if len(enriched_matches) == 1 else None


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    """Suy ra field UI tất định từ source facts compact."""
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

    # ----- Mục I: cổng tự điền danh tính. (3) Số giấy tờ tùy thân = số định danh cổng đã điền. -----
    ctx = (options or {}).get("formContext") or {}
    applicant_id = str(ctx.get("applicantIdentityNumber") or "").strip()
    if applicant_id:
        add("SoGiayToTuyThanC", applicant_id)
    # 3 default cư trú (viền vàng).
    add("nycLoaiCuTru", "Thường trú", default=True)
    add("nycNoiCuTru", "Trong Nước", default=True)
    add("nycNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

    # ----- Mục II: người có nội dung thay đổi — chọn chủ thể theo nguồn. -----
    # TỜ KHAI cải chính / khai sinh / khai tử: chủ thể là 1 người ở nhóm ChuThe_*.
    # Trích lục KẾT HÔN: chủ thể là chồng HOẶC vợ (theo CCCD người yêu cầu đối chiếu).
    event = _event_type(values)
    if values.get("ChuThe_HoTen") or values.get("ChuThe_SoDinhDanh"):
        src = "ChuThe"
    elif event == "marriage":
        src = _marriage_subject(values, options)
    else:
        src = None

    if src:
        subject_card = _card_for_subject(values, src)
        has_correction_declaration = bool(
            values.get("ViecDangKy")
            or values.get("NoiDungThayDoi")
            or values.get("LyDo")
        )

        def g(sub: str):
            # Tờ khai là lời khai cư trú hiện tại của người được cải chính, nên ưu tiên hơn CCCD.
            if (
                src == "ChuThe"
                and sub == "NoiCuTru"
                and has_correction_declaration
                and values.get("ChuThe_NoiCuTru") not in (None, "", {}, [])
            ):
                return values["ChuThe_NoiCuTru"]
            if subject_card:
                card_key = {
                    "HoTen": "HoTen",
                    "NgaySinh": "NgaySinh",
                    "GioiTinh": "GioiTinh",
                    "QuocTich": "QuocTich",
                    "SoDinhDanh": "SoDinhDanh",
                    "NgayCapGiayTo": "NgayCap",
                    "NoiCapGiayTo": "NoiCap",
                    "NoiCuTru": "NoiCuTru",
                }.get(sub)
                if card_key and subject_card.get(card_key) not in (None, "", {}, []):
                    return subject_card[card_key]
            return values.get(f"{src}_{sub}")

        add("ntdHoTen", _normalize_person_name(g("HoTen")))
        add("ntdNgaySinh", g("NgaySinh"))
        add("ntdGioiTinh", g("GioiTinh"))
        add("ntdDanToc", _normalize_dan_toc(g("DanToc")))
        add("ntdQuocTich", g("QuocTich") or "Việt Nam")

        # Chủ thể CHÍNH LÀ người trên CCCD đính kèm (tự khai) → dùng CCCD làm nguồn DỰ PHÒNG cho số
        # định danh + ngày/nơi cấp giấy tờ (LLM trích dòng giấy tờ trên tờ khai rất chập chờn).
        subject_is_cccd = bool(
            (_digits(g("SoDinhDanh")) and _digits(g("SoDinhDanh")) == _digits(values.get("Cccd_SoDinhDanh")))
            or (_fold(g("HoTen")) and _fold(g("HoTen")) == _fold(values.get("Cccd_HoTen")))
        )

        def cc(cccd_key):
            return values.get(cccd_key) if subject_is_cccd else None

        so_dinh_danh = g("SoDinhDanh") or cc("Cccd_SoDinhDanh")
        add("ntdSoDDCN", so_dinh_danh)

        ngay_cap = g("NgayCapGiayTo") or cc("Cccd_NgayCap")
        noi_cap = g("NoiCapGiayTo") or cc("Cccd_NoiCap")
        # Trẻ trong GIẤY KHAI SINH chỉ có số định danh, KHÔNG có CCCD → bỏ trống khối giấy tờ tùy thân.
        # NHƯNG người lớn có CCCD (ngày/nơi cấp) → vẫn điền, kể cả khi sự kiện hộ tịch gốc là khai sinh.
        has_id_card = bool(ngay_cap or noi_cap or g("SoGiayTo"))
        if so_dinh_danh and (event != "birth" or has_id_card):
            add("ntdLoaiGiayToTuyThan", "Căn cước công dân")
            add("ntdSoGiayToTuyThan", g("SoGiayTo") or so_dinh_danh)
            add("ntdNgayCapGiayToTuyThan", ngay_cap)
            add("ntdNoiCapGiayToTuyThan", noi_cap or default_issuer(ngay_cap))
        residence = _area(g("NoiCuTru"))
        if residence:
            add("ntdLoaiCuTru", "Thường trú")
            add("ntdNoiCuTru", "Trong Nước")
            add("ntdNoiCuTru_TrongNuoc", residence)

    # ----- Mục III: nội dung đề nghị. -----
    add("viecDangKy", _viec_dang_ky(values))
    add("nghiepVuDK", _NGHIEP_VU.get(event))
    add("soDangKyHSGoc", values.get("HoSo_So"))
    # Quyển số chỉ điền khi giấy tờ ghi rõ; không suy ra từ số đăng ký.
    if values.get("HoSo_QuyenSo"):
        add("quyenDangKyHSGoc", values.get("HoSo_QuyenSo"))
    add("ngayDangKyHSGoc", values.get("HoSo_NgayDangKy"))
    add("noiDangKyHSGoc", values.get("HoSo_NoiDangKy"))

    # Nội dung đề nghị cải chính + lý do (chỉ có trên tờ khai).
    add("noiDungDK", values.get("NoiDungThayDoi"))
    add("lyDoDK", values.get("LyDo"))

    # Không tự chọn cấp bản sao/số lượng; người dùng quyết định trên form.
    add("TraKQ", "Trực tiếp", default=True)

    return out
