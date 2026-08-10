"""Map compact OCR facts for civil-status extract copy to legacy x-* UI fields."""

import re
import unicodedata

from app.pipelines.trich_luc.process.schema import UI_ALIASES, UI_COMP_BY_NAME

_BIRTH_LOAI_YEU_CAU = "Giấy khai sinh bản sao/Trích lục ghi vào Sổ hộ tịch việc khai sinh (bản sao)"
_MARRIAGE_LOAI_YEU_CAU = "Trích lục kết hôn (bản sao)/ Trích lục ghi chú kết hôn (bản sao)"
_DEATH_LOAI_YEU_CAU = "Trích lục khai tử (bản sao)"
from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type, normalize_issuer
from app.pipelines._shared.area_remap import remap_area

_EVENT_TO_OPTION = {
    "birth": _BIRTH_LOAI_YEU_CAU,
    "marriage": _MARRIAGE_LOAI_YEU_CAU,
    "death": _DEATH_LOAI_YEU_CAU,
}

_EVENT_TO_DOCUMENT_NAME = {
    "birth": "Giấy khai sinh",
    "marriage": "Giấy chứng nhận kết hôn",
    "death": "Trích lục khai tử",
}

_HCM_PROVINCE_KEYS = {
    "hochiminh",
    "tphochiminh",
    "thanhphohochiminh",
    "tphcm",
    "hcm",
}

# Danh sách dân tộc biểu mẫu cho phép chọn trực tiếp. Giá trị ngoài danh sách phải chọn "Khác"
# rồi điền nguyên văn vào NDK_DanTocKhac; không để extension thử khớp một option không tồn tại.
_FORM_ETHNICITIES = {
    "ba na",
    "bo y",
    "brau",
    "bru-van kieu",
    "cham",
    "cho ro",
    "chu ru",
    "chut",
    "co",
    "co ho",
    "co lao",
    "co tu",
    "cong",
    "dao",
    "e de",
    "gia rai",
    "giay",
    "gie trieng",
    "ha nhi",
    "hoa",
    "hre",
    "khang",
    "khmer",
    "kho mu",
    "kinh",
    "la chi",
    "la ha",
    "la hu",
    "lao",
    "lo lo",
    "lu",
    "ma",
    "mang",
    "mnong",
    "mong",
    "mong (hmong)",
    "muong",
    "ngai",
    "nung",
    "o du",
    "pa then",
    "phu la",
    "pu peo",
    "ra glai",
    "ro mam",
    "san chay",
    "san diu",
    "si la",
    "ta oi",
    "tay",
    "thai",
    "tho",
    "xo dang",
    "xtieng",
}


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _copy_quantity(value) -> str:
    digits = _digits(value)
    return str(int(digits)) if digits and int(digits) > 0 else ""


def _civil_status_document_name(values: dict, event_type: str) -> str:
    """Tờ khai là nguồn yêu cầu, không phải tên giấy hộ tịch cần cấp bản sao."""
    name = str(values.get("HoTich_TenGiayTo") or "").strip()
    if not name or "to khai" in _fold(name) or "ban cam doan" in _fold(name):
        return _EVENT_TO_DOCUMENT_NAME.get(event_type, "")
    return name


def _requester_trusted(values: dict, options: dict | None) -> bool:
    """Nyc_* có đúng là giấy tờ của người yêu cầu không?

    - Có mỏ neo formContext (VNeID): tin khi Nyc_* khớp tên/số định danh người đăng nhập.
    - Không mỏ neo (fallback): KHÔNG tin nếu Nyc_* trùng CHỦ THỂ hộ tịch (đó là CCCD của người được
      đăng ký, không phải người yêu cầu — vd CCCD con); ngược lại tin.
    """
    ctx = (options or {}).get("formContext") or {}
    applicant_id = _digits(ctx.get("applicantIdentityNumber"))
    applicant_name = _fold(ctx.get("applicantFullname"))
    requester_id = _digits(values.get("Nyc_SoDinhDanh"))
    requester_name = _fold(values.get("Nyc_HoTen"))

    if applicant_id or applicant_name:
        if applicant_id and requester_id:
            return applicant_id == requester_id
        if applicant_name and requester_name:
            return applicant_name == requester_name
        return False

    # Không mỏ neo → vẫn chặn nếu model gán nhầm chính thẻ chủ thể vào Nyc_*.
    subj_id = _digits(values.get("HoTich_SoDinhDanh"))
    subj_name = _fold(values.get("HoTich_HoTenNguoiDuocDangKy"))
    if requester_id and subj_id and requester_id == subj_id:
        return False
    if requester_name and subj_name and requester_name == subj_name:
        return False
    return True


def _strip_admin_prefix(value):
    """Giữ tên theo contract cũ, riêng phường hiện hành cần tiền tố để khớp option."""
    text = str(value or "").strip()
    if _fold(text) in {"phuong xuan huong", "p. xuan huong", "p xuan huong"}:
        return "Phường Xuân Hương"
    return re.sub(r"^(xã|phường|thị trấn|tt\.?)\s+", "", text, flags=re.IGNORECASE).strip()


def _area(value):
    if not isinstance(value, dict):
        return None
    province = str(value.get("tinh") or value.get("tỉnh") or "").strip()
    province_key = re.sub(r"[^a-z0-9]+", "", _fold(province))
    if province_key in _HCM_PROVINCE_KEYS:
        province = "Thành phố Hồ Chí Minh"
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": province,
        "xa": _strip_admin_prefix(value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường")),
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    return remap_area(out)


def _chu_the_matches_hotich(values: dict) -> bool:
    """ChuThe_* có khớp chủ thể trên giấy/tờ khai hộ tịch hay không."""
    subject_card_id = _digits(values.get("ChuThe_SoDinhDanh"))
    subject_card_name = _fold(values.get("ChuThe_HoTen"))
    subj_id = _digits(values.get("HoTich_SoDinhDanh"))
    subj_name = _fold(values.get("HoTich_HoTenNguoiDuocDangKy"))
    requester_id = _digits(values.get("Nyc_SoDinhDanh"))

    if subject_card_id and requester_id and subject_card_id == requester_id:
        return False
    if subject_card_id and subj_id:
        return subject_card_id == subj_id
    if subject_card_name and subj_name:
        return subject_card_name == subj_name
    # Không có mỏ neo chủ thể trong giấy hộ tịch: vẫn giữ ChuThe_* đã được prompt phân vai
    # từ quy tắc hai CCCD (một thẻ khớp formContext, thẻ còn lại là chủ thể).
    return bool(subject_card_id or subject_card_name) and not (subj_id or subj_name)


def _event_type(values: dict) -> str:
    raw = str(values.get("HoTich_LoaiSuKien") or "").strip().lower()
    if raw in _EVENT_TO_OPTION:
        return raw
    title = str(values.get("HoTich_TenGiayTo") or "").lower()
    if "kết hôn" in title or "ket hon" in title:
        return "marriage"
    if "khai tử" in title or "khai tu" in title or "chứng tử" in title or "chung tu" in title:
        return "death"
    if "khai sinh" in title:
        return "birth"
    return ""


def _strip_role_label(text: str) -> str:
    return re.sub(
        r"^\s*(họ[, ]*chữ đệm[, ]*tên\s*)?(chồng|bên nam|nam|người chồng)\s*[:：-]?\s*",
        "",
        str(text or "").strip(),
        flags=re.IGNORECASE,
    ).strip()


def _ethnicity(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    simplified = (
        text.lower().replace("'", "").replace("’", "").replace("`", "")
        .replace("ỗ", "ô").replace("hmỗng", "hmông")
    )
    # CHỈ biến thể HMÔNG (có "H" đứng đầu) → "Mông (Hmông)". Dân tộc "Mông" thường GIỮ NGUYÊN "Mông".
    if "hmong" in simplified or "hmông" in simplified or "h mong" in simplified or "h mông" in simplified:
        return "Mông (Hmông)"
    if simplified in ("mong", "mông"):
        return "Mông"
    return text


def _ethnicity_for_form(value: str) -> tuple[str, str]:
    """Trả (giá trị dropdown, giá trị nhập tay khi dropdown là Khác)."""
    text = _ethnicity(value)
    if not text:
        return "", ""
    if _fold(text) in _FORM_ETHNICITIES:
        return text, ""
    return "Khác", text


def _registered_person_name(values: dict, event_type: str) -> str:
    raw = str(values.get("HoTich_HoTenNguoiDuocDangKy") or "").strip()
    if event_type != "marriage" or not raw:
        return raw

    parts = [p.strip() for p in re.split(r"[;\n|]+", raw) if p.strip()]
    for part in parts:
        if re.search(r"\b(chồng|bên nam|người chồng)\b", part, flags=re.IGNORECASE):
            return _strip_role_label(part)
    if len(parts) >= 2:
        return _strip_role_label(parts[-1])
    return _strip_role_label(raw)


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    """Derive deterministic UI fields from compact source facts."""
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
        if name in UI_ALIASES:
            field["aliases"] = UI_ALIASES[name]
        if default:
            field["default"] = True  # extension tô VIỀN VÀNG (giá trị mặc định, không từ giấy tờ)
        out.append(field)
        seen.add(name)

    has_requester = bool(values.get("Nyc_SoDinhDanh") or values.get("Nyc_HoTen"))
    has_subject_card = bool(values.get("ChuThe_SoDinhDanh") or values.get("ChuThe_HoTen"))
    ctx = (options or {}).get("formContext") or {}
    has_requester_anchor = bool(
        _digits(ctx.get("applicantIdentityNumber")) or _fold(ctx.get("applicantFullname"))
    )
    has_hotich = any(
        name in values
        for name in (
            "HoTich_LoaiSuKien",
            "HoTich_TenGiayTo",
            "HoTich_HoTenNguoiDuocDangKy",
            "HoTich_CoQuanDangKy",
            "HoTich_So",
            "HoTich_NgayDangKy",
        )
    )
    has_subject_support = any(
        values.get(name)
        for name in (
            "NguoiDuocCap_HoTen",
            "NguoiDuocCap_NgaySinh",
            "NguoiDuocCap_GioiTinh",
        )
    )

    def _fill_requester() -> None:
        requester_issuer = normalize_issuer(values.get("Nyc_NoiCap")) or default_issuer(values.get("Nyc_NgayCap"))
        add("HoVaTenC", values.get("Nyc_HoTen"))
        add("SoDinhDanhC", values.get("Nyc_SoDinhDanh"))
        # Loại giấy tờ theo nơi cấp: Bộ Công an → "Thẻ Căn cước"; Cục Cảnh sát → "Thẻ căn cước công dân".
        add("LoaiGiayToDinhDanhC", id_doc_type("Căn cước", requester_issuer))
        add("NYC_SoGiayToTuyThan", values.get("Nyc_SoDinhDanh"))
        add("NgayCapDDC", values.get("Nyc_NgayCap"))
        add("NoiCapDDC", requester_issuer)
        add("NYC_LoaiCuTru", "Thường trú")
        area = _area(values.get("Nyc_NoiCuTru"))
        if area:
            add("NYC_NoiCuTru", "1")
            add("NYC_NoiCuTru_TrongNuoc", area)

    def _fill_subject_from_card() -> None:
        subject_issuer = normalize_issuer(values.get("ChuThe_NoiCap")) or default_issuer(values.get("ChuThe_NgayCap"))
        add("NDK_HoVaTen", values.get("ChuThe_HoTen"))
        add("NDK_NgaySinh", values.get("ChuThe_NgaySinh"))
        add("NDK_GioiTinh", values.get("ChuThe_GioiTinh"))
        add("NDK_QuocTich", values.get("ChuThe_QuocTich") or "Việt Nam")
        add("NDK_SoDinhDanh", values.get("ChuThe_SoDinhDanh"))
        if values.get("ChuThe_SoDinhDanh"):
            add(
                "NDK_LoaiGiayToTuyThan",
                id_doc_type(values.get("ChuThe_LoaiGiayTo") or "Căn cước", subject_issuer),
            )
        add("NDK_SoGiayToTuyThan", values.get("ChuThe_SoDinhDanh"))
        add("NDK_NgayCap", values.get("ChuThe_NgayCap"))
        add("NDK_NoiCap", subject_issuer)
        add("NDK_LoaiCuTru", "Thường trú")
        area = _area(values.get("ChuThe_NoiCuTru"))
        if area:
            add("NDK_NoiCuTru", "1")
            add("NDK_NoiCuTru_TrongNuoc", area)

    def _fill_subject_from_requester() -> None:
        """Một CCCD khớp formContext và không có chủ thể khác → người yêu cầu tự xin cho mình."""
        requester_issuer = normalize_issuer(values.get("Nyc_NoiCap")) or default_issuer(values.get("Nyc_NgayCap"))
        add("NDK_HoVaTen", values.get("Nyc_HoTen"))
        add("NDK_NgaySinh", values.get("Nyc_NgaySinh"))
        add("NDK_GioiTinh", values.get("Nyc_GioiTinh"))
        add("NDK_QuocTich", "Việt Nam")
        add("NDK_SoDinhDanh", values.get("Nyc_SoDinhDanh"))
        if values.get("Nyc_SoDinhDanh"):
            add("NDK_LoaiGiayToTuyThan", id_doc_type("Căn cước", requester_issuer))
        add("NDK_SoGiayToTuyThan", values.get("Nyc_SoDinhDanh"))
        add("NDK_NgayCap", values.get("Nyc_NgayCap"))
        add("NDK_NoiCap", requester_issuer)
        add("NDK_LoaiCuTru", "Thường trú")
        area = _area(values.get("Nyc_NoiCuTru"))
        if area:
            add("NDK_NoiCuTru", "1")
            add("NDK_NoiCuTru_TrongNuoc", area)

    def _fill_ndk_from_support() -> None:
        """Tài liệu bổ trợ chỉ đủ chứng minh ba dữ kiện cơ bản của người ở mục II."""
        add("NDK_HoVaTen", values.get("NguoiDuocCap_HoTen"))
        add("NDK_NgaySinh", values.get("NguoiDuocCap_NgaySinh"))
        add("NDK_GioiTinh", values.get("NguoiDuocCap_GioiTinh"))
        add("NDK_QuocTich", "Việt Nam")

    if has_hotich:
        # Có giấy hộ tịch: Nyc_* chỉ điền người yêu cầu; chủ thể lấy từ HoTich_* và bổ sung bằng ChuThe_*.
        if has_requester and _requester_trusted(values, options):
            _fill_requester()

        event_type = _event_type(values)

        has_person_info = has_subject_support or any(
            values.get(name)
            for name in (
                "HoTich_HoTenNguoiDuocDangKy",
                "HoTich_NgaySinh",
                "HoTich_GioiTinh",
                "HoTich_DanToc",
                "HoTich_SoDinhDanh",
                "HoTich_SoGiayToTuyThan",
                "HoTich_NoiCuTru",
                "ChuThe_HoTen",
                "ChuThe_SoDinhDanh",
            )
        )
        if has_person_info:
            subject_card = has_subject_card and _chu_the_matches_hotich(values)

            def _ct(name):
                return values.get(name) if subject_card else None

            add(
                "NDK_HoVaTen",
                _registered_person_name(values, event_type)
                or values.get("NguoiDuocCap_HoTen")
                or _ct("ChuThe_HoTen"),
            )
            add(
                "NDK_NgaySinh",
                values.get("HoTich_NgaySinh")
                or values.get("NguoiDuocCap_NgaySinh")
                or _ct("ChuThe_NgaySinh"),
            )
            add(
                "NDK_GioiTinh",
                values.get("HoTich_GioiTinh")
                or values.get("NguoiDuocCap_GioiTinh")
                or _ct("ChuThe_GioiTinh")
                or ("Nam" if event_type == "marriage" else None),
            )
            ethnicity, other_ethnicity = _ethnicity_for_form(values.get("HoTich_DanToc"))
            add("NDK_DanToc", ethnicity)
            add("NDK_DanTocKhac", other_ethnicity)
            add("NDK_QuocTich", values.get("HoTich_QuocTich") or _ct("ChuThe_QuocTich") or "Việt Nam")
            # HoTich_*GiayToTuyThan của birth chỉ được prompt trả từ block người được cấp
            # trên TỜ KHAI cấp bản sao. Giấy khai sinh chỉ có số định danh của trẻ thì
            # không có các field này, nên mapper chỉ điền NDK_SoDinhDanh.
            is_birth = event_type == "birth"
            ht_loai = values.get("HoTich_LoaiGiayToTuyThan")
            ht_so = values.get("HoTich_SoGiayToTuyThan")
            ht_ngay = values.get("HoTich_NgayCapGiayToTuyThan")
            ht_noi = values.get("HoTich_NoiCapGiayToTuyThan")

            # Guard hẹp cho giấy khai sinh cũ: nếu giấy tờ tùy thân không trùng số định
            # danh của trẻ thì đó có thể là giấy tờ người đi khai sinh, không được dùng.
            if is_birth and ht_so and values.get("HoTich_SoDinhDanh"):
                if _digits(ht_so) != _digits(values.get("HoTich_SoDinhDanh")):
                    ht_loai = ht_so = ht_ngay = ht_noi = None

            # Giấy tờ tùy thân RIÊNG của chính người được đăng ký (thẻ căn cước/CCCD của họ) —
            # ưu tiên CAO NHẤT khi có, đúng cho cả khai sinh (con đã có thẻ căn cước riêng).
            ct_loai = _ct("ChuThe_LoaiGiayTo")
            ct_so = _ct("ChuThe_SoDinhDanh")
            ct_ngay = _ct("ChuThe_NgayCap")
            ct_noi = _ct("ChuThe_NoiCap")

            # Guard cuối: không chấp nhận cùng một số cho Nyc_* và ChuThe_*.
            _ct_d = _digits(ct_so)
            _subj_d = _digits(values.get("HoTich_SoDinhDanh"))
            _req_d = _digits(values.get("Nyc_SoDinhDanh"))
            _ct_valid = bool(_ct_d) and (
                _ct_d == _subj_d if _subj_d else _ct_d != _req_d
            )
            if not _ct_valid:
                ct_loai = ct_so = ct_ngay = ct_noi = None
            
            # FALLBACK: Khi không có ChuThe_* hợp lệ VÀ không có tờ khai giấy tờ,
            # kiểm tra Nyc_* (người yêu cầu) có TRÙNG chủ thể → fallback Nyc_* cho NDK_*
            if not ct_so and not ht_so:
                nyc_id = values.get("Nyc_SoDinhDanh")
                nyc_name = _fold(values.get("Nyc_HoTen"))
                subj_name = _fold(values.get("HoTich_HoTenNguoiDuocDangKy"))
                
                # Kiểm tra Nyc_* có khớp chủ thể không (so sánh tên vì không có số định danh trong giấy khai sinh)
                nyc_matches_subject = False
                if nyc_name and subj_name and nyc_name == subj_name:
                    nyc_matches_subject = True
                # Hoặc nếu có số định danh ở cả 2 bên
                if nyc_id and _subj_d and _digits(nyc_id) == _subj_d:
                    nyc_matches_subject = True
                
                # Nếu khớp → fallback Nyc_* cho giấy tờ của NDK
                if nyc_matches_subject and nyc_id:
                    ct_so = nyc_id
                    ct_loai = "Căn cước"  # Fallback từ CCCD người yêu cầu
                    ct_ngay = values.get("Nyc_NgayCap")
                    ct_noi = values.get("Nyc_NoiCap")

            add("NDK_SoDinhDanh", ct_so or ht_so or values.get("HoTich_SoDinhDanh"))
            add(
                "NDK_SoGiayToTuyThan",
                ct_so or ht_so or (values.get("HoTich_SoDinhDanh") if not is_birth else None),
            )
            add("NDK_NgayCap", ct_ngay or ht_ngay)
            # Nơi cấp (issuer) tính TRƯỚC để suy loại giấy tờ theo đúng nơi cấp.
            ndk_noicap = None
            if ct_noi or ct_ngay:  # có thẻ riêng của chủ thể → suy nơi cấp từ thẻ đó
                ndk_noicap = normalize_issuer(ct_noi) or default_issuer(ct_ngay)
            if not ndk_noicap:
                ndk_noicap = normalize_issuer(ht_noi)
            add("NDK_NoiCap", ndk_noicap)
            # Loại giấy tờ theo nơi cấp: Bộ Công an → "Thẻ Căn cước"; Cục Cảnh sát → "Thẻ căn cước công dân".
            id_hint = ct_loai or ht_loai
            if not id_hint and (ct_so or ht_so):
                id_hint = "Căn cước"  # có số nhưng LLM ko trả loại → để nơi cấp quyết
            add("NDK_LoaiGiayToTuyThan", id_doc_type(id_hint, ndk_noicap or "") if id_hint else None)
            add("NDK_LoaiCuTru", "Thường trú")
            ndk_area = _area(values.get("HoTich_NoiCuTru")) or _area(_ct("ChuThe_NoiCuTru"))
            # Fallback nơi cư trú từ Nyc_NoiCuTru khi không có từ giấy hộ tịch/ChuThe
            # Kiểm tra nếu ct_so được set từ Nyc (fallback case) hoặc không có nơi cư trú nào
            if not ndk_area:
                # Kiểm tra nếu đã có fallback từ Nyc_* (ct_so mà không phải từ ChuThe_*)
                if ct_so and not _ct("ChuThe_SoDinhDanh"):
                    ndk_area = _area(values.get("Nyc_NoiCuTru"))
            if ndk_area:
                add("NDK_NoiCuTru", "1")
                add("NDK_NoiCuTru_TrongNuoc", ndk_area)

        add("HoSo_LoaiYeuCau", _EVENT_TO_OPTION.get(event_type))
        add("HoSo_CoQuanDangKy", values.get("HoTich_CoQuanDangKy"))
        add("HoSo_TenGiayTo", _civil_status_document_name(values, event_type))
        add("HoSo_So", values.get("HoTich_So"))
        add("HoSo_QuyenSo", values.get("HoTich_QuyenSo"))
        add("HoSo_NgayCapSo", values.get("HoTich_NgayDangKy"))
        add("PhuongThucNhanKQ", "2")
    elif has_subject_support:
        # Nyc_* là người yêu cầu; giấy chứng sinh/CT01 xác định người mục II.
        if has_requester and _requester_trusted(values, options):
            _fill_requester()
        _fill_ndk_from_support()
    else:
        # Không có giấy hộ tịch: hai nhóm đã được phân vai độc lập trong prompt.
        requester_trusted = has_requester and _requester_trusted(values, options)
        if requester_trusted:
            _fill_requester()
        if has_subject_card:
            _fill_subject_from_card()
        elif requester_trusted and has_requester_anchor:
            # Chỉ có một CCCD và thẻ đó khớp người đăng nhập: tự làm cho chính mình.
            _fill_subject_from_requester()

    # KHÔNG điền default cho NYC_* - để VNeID tự động điền từ thông tin đăng nhập
    # Extension sẽ skip các field mà backend không trả về

    # Form chỉ có ô số lượng, không có radio Có/Không cấp bản sao.
    copy_quantity = _copy_quantity(values.get("CopyRequest_Quantity"))
    if copy_quantity:
        add("SoLuong", copy_quantity)

    return out
