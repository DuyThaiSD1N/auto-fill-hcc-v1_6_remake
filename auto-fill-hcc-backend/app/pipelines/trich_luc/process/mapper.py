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
    """CCCD (Cccd_*) có ĐÚNG là của người yêu cầu không?

    - Có mỏ neo formContext (VNeID): tin ⇔ Cccd_* khớp tên/số định danh người đăng nhập.
    - Không mỏ neo (fallback): KHÔNG tin nếu Cccd_* trùng CHỦ THỂ hộ tịch (đó là CCCD của người được
      đăng ký, không phải người yêu cầu — vd CCCD con); ngược lại tin.
    """
    ctx = (options or {}).get("formContext") or {}
    applicant_id = _digits(ctx.get("applicantIdentityNumber"))
    applicant_name = _fold(ctx.get("applicantFullname"))
    cccd_id = _digits(values.get("Cccd_SoDinhDanh"))
    cccd_name = _fold(values.get("Cccd_HoTen"))

    if applicant_id or applicant_name:
        if applicant_id and cccd_id:
            return applicant_id == cccd_id
        if applicant_name and cccd_name:
            return applicant_name == cccd_name
        return False

    # Không mỏ neo → chặn trường hợp CCCD chính là chủ thể hộ tịch (người được đăng ký).
    subj_id = _digits(values.get("HoTich_SoDinhDanh"))
    subj_name = _fold(values.get("HoTich_HoTenNguoiDuocDangKy"))
    if cccd_id and subj_id and cccd_id == subj_id:
        return False
    if cccd_name and subj_name and cccd_name == subj_name:
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
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or "",
        "xa": _strip_admin_prefix(value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường")),
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    return remap_area(out)


def _cccd_is_subject(values: dict) -> bool:
    """CCCD upload có đúng là NGƯỜI ĐƯỢC ĐĂNG KÝ (chủ thể hộ tịch) không? (khớp tên/số định danh)."""
    cccd_id = _digits(values.get("Cccd_SoDinhDanh"))
    cccd_name = _fold(values.get("Cccd_HoTen"))
    subj_id = _digits(values.get("HoTich_SoDinhDanh"))
    subj_name = _fold(values.get("HoTich_HoTenNguoiDuocDangKy"))
    if cccd_id and subj_id:
        return cccd_id == subj_id
    if cccd_name and subj_name:
        return cccd_name == subj_name
    return False


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

    has_cccd = bool(values.get("Cccd_SoDinhDanh") or values.get("Cccd_HoTen"))
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

    def _fill_requester_from_cccd() -> None:
        cccd_issuer = normalize_issuer(values.get("Cccd_NoiCap")) or default_issuer(values.get("Cccd_NgayCap"))
        add("HoVaTenC", values.get("Cccd_HoTen"))
        add("SoDinhDanhC", values.get("Cccd_SoDinhDanh"))
        # Loại giấy tờ theo nơi cấp: Bộ Công an → "Thẻ Căn cước"; Cục Cảnh sát → "Thẻ căn cước công dân".
        add("LoaiGiayToDinhDanhC", id_doc_type("Căn cước", cccd_issuer))
        add("NYC_SoGiayToTuyThan", values.get("Cccd_SoDinhDanh"))
        add("NgayCapDDC", values.get("Cccd_NgayCap"))
        add("NoiCapDDC", cccd_issuer)
        add("NYC_LoaiCuTru", "Thường trú")
        area = _area(values.get("Cccd_NoiCuTru"))
        if area:
            add("NYC_NoiCuTru", "1")
            add("NYC_NoiCuTru_TrongNuoc", area)

    def _fill_ndk_from_cccd() -> None:
        cccd_issuer = normalize_issuer(values.get("Cccd_NoiCap")) or default_issuer(values.get("Cccd_NgayCap"))
        add("NDK_HoVaTen", values.get("Cccd_HoTen"))
        add("NDK_NgaySinh", values.get("Cccd_NgaySinh"))
        add("NDK_GioiTinh", values.get("Cccd_GioiTinh"))
        add("NDK_QuocTich", "Việt Nam")
        add("NDK_SoDinhDanh", values.get("Cccd_SoDinhDanh"))
        if values.get("Cccd_SoDinhDanh"):
            add("NDK_LoaiGiayToTuyThan", id_doc_type("Căn cước", cccd_issuer))
        add("NDK_SoGiayToTuyThan", values.get("Cccd_SoDinhDanh"))
        add("NDK_NgayCap", values.get("Cccd_NgayCap"))
        add("NDK_NoiCap", cccd_issuer)
        add("NDK_LoaiCuTru", "Thường trú")
        area = _area(values.get("Cccd_NoiCuTru"))
        if area:
            add("NDK_NoiCuTru", "1")
            add("NDK_NoiCuTru_TrongNuoc", area)

    if has_hotich:
        # Có giấy hộ tịch: CCCD → NGƯỜI YÊU CẦU (nếu tin chắc); NGƯỜI ĐƯỢC ĐĂNG KÝ lấy từ giấy hộ tịch.
        if has_cccd and _requester_trusted(values, options):
            _fill_requester_from_cccd()

        event_type = _event_type(values)

        has_person_info = any(
            values.get(name)
            for name in (
                "HoTich_HoTenNguoiDuocDangKy",
                "HoTich_NgaySinh",
                "HoTich_GioiTinh",
                "HoTich_DanToc",
                "HoTich_SoDinhDanh",
                "HoTich_SoGiayToTuyThan",
                "HoTich_NoiCuTru",
            )
        )
        if has_person_info:
            # CCCD upload có đúng là NGƯỜI ĐƯỢC ĐĂNG KÝ không? Giấy khai sinh/hộ tịch thường KHÔNG có
            # số định danh/ngày-nơi cấp/nơi cư trú của chủ thể → lấy bổ sung từ CCCD của chính người đó.
            subject_cccd = has_cccd and _cccd_is_subject(values)

            def _cc(name):
                return values.get(name) if subject_cccd else None

            add("NDK_HoVaTen", _registered_person_name(values, event_type))
            add("NDK_NgaySinh", values.get("HoTich_NgaySinh") or _cc("Cccd_NgaySinh"))
            add("NDK_GioiTinh", values.get("HoTich_GioiTinh") or _cc("Cccd_GioiTinh") or ("Nam" if event_type == "marriage" else None))
            add("NDK_DanToc", _ethnicity(values.get("HoTich_DanToc")))
            add("NDK_QuocTich", values.get("HoTich_QuocTich") or "Việt Nam")
            # GIẤY TỜ TÙY THÂN (loại/số/ngày/nơi cấp): HoTich_*GiayToTuyThan CHỈ đáng tin cho KẾT HÔN
            # (giấy tờ chồng/vợ). Với KHAI SINH, dòng "Giấy tờ tùy thân" trên giấy là của NGƯỜI ĐI KHAI SINH,
            # KHÔNG phải chủ thể (con) → BỎ; chủ thể (con) chỉ có SỐ ĐỊNH DANH, giấy tờ tùy thân chỉ lấy từ
            # CCCD của CHÍNH chủ thể (khi upload đúng người).
            is_birth = event_type == "birth"
            ht_loai = None if is_birth else values.get("HoTich_LoaiGiayToTuyThan")
            ht_so = None if is_birth else values.get("HoTich_SoGiayToTuyThan")
            ht_ngay = None if is_birth else values.get("HoTich_NgayCapGiayToTuyThan")
            ht_noi = None if is_birth else values.get("HoTich_NoiCapGiayToTuyThan")

            # Giấy tờ tùy thân RIÊNG của chính người được đăng ký (thẻ căn cước/CCCD của họ) —
            # ưu tiên CAO NHẤT khi có, đúng cho cả khai sinh (con đã có thẻ căn cước riêng).
            ct_loai = values.get("ChuThe_LoaiGiayToTuyThan")
            ct_so = values.get("ChuThe_SoGiayToTuyThan")
            ct_ngay = values.get("ChuThe_NgayCapGiayToTuyThan")
            ct_noi = values.get("ChuThe_NoiCapGiayToTuyThan")

            # GUARD tất định: ChuThe_* PHẢI là thẻ của CHÍNH chủ thể. LLM hay bắt nhầm thẻ người
            # yêu cầu (mẹ) rồi nhét vào cả Cccd_* lẫn ChuThe_* → điền sai của người khác. Chỉ nhận
            # khi số ChuThe khớp số định danh chủ thể; nếu trùng thẻ người yêu cầu hoặc lệch → BỎ.
            _ct_d = _digits(ct_so)
            _subj_d = _digits(values.get("HoTich_SoDinhDanh"))
            _req_d = _digits(values.get("Cccd_SoDinhDanh"))
            _ct_valid = bool(_ct_d) and (
                _ct_d == _subj_d if _subj_d else _ct_d != _req_d
            )
            if not _ct_valid:
                ct_loai = ct_so = ct_ngay = ct_noi = None

            add("NDK_SoDinhDanh", values.get("HoTich_SoDinhDanh") or ct_so or ht_so or _cc("Cccd_SoDinhDanh"))
            add("NDK_SoGiayToTuyThan", ct_so or ht_so or (values.get("HoTich_SoDinhDanh") if not is_birth else None) or _cc("Cccd_SoDinhDanh"))
            add("NDK_NgayCap", ct_ngay or ht_ngay or _cc("Cccd_NgayCap"))
            # Nơi cấp (issuer) tính TRƯỚC để suy loại giấy tờ theo đúng nơi cấp.
            ndk_noicap = None
            if ct_noi or ct_ngay:  # có thẻ riêng của chủ thể → suy nơi cấp từ thẻ đó
                ndk_noicap = normalize_issuer(ct_noi) or default_issuer(ct_ngay)
            if not ndk_noicap:
                ndk_noicap = ht_noi
            if not ndk_noicap and subject_cccd:
                ndk_noicap = normalize_issuer(values.get("Cccd_NoiCap")) or default_issuer(values.get("Cccd_NgayCap"))
            add("NDK_NoiCap", ndk_noicap)
            # Loại giấy tờ theo nơi cấp: Bộ Công an → "Thẻ Căn cước"; Cục Cảnh sát → "Thẻ căn cước công dân".
            id_hint = ct_loai or ht_loai
            if not id_hint and (ct_so or (values.get("HoTich_SoGiayToTuyThan") if not is_birth else None) or _cc("Cccd_SoDinhDanh")):
                id_hint = "Căn cước"  # có số nhưng LLM ko trả loại → để nơi cấp quyết
            add("NDK_LoaiGiayToTuyThan", id_doc_type(id_hint, ndk_noicap or "") if id_hint else None)
            add("NDK_LoaiCuTru", "Thường trú")
            ndk_area = _area(values.get("HoTich_NoiCuTru")) or (_area(values.get("Cccd_NoiCuTru")) if subject_cccd else None)
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
    elif has_cccd:
        # CHỈ có CCCD (không có giấy hộ tịch): người trên CCCD = NGƯỜI ĐƯỢC ĐĂNG KÝ (mục II) → điền hết.
        _fill_ndk_from_cccd()
        # Nếu CCCD khớp người đăng nhập (VNeID) thì người đó cũng là NGƯỜI YÊU CẦU → điền thêm mục I.
        ctx = (options or {}).get("formContext") or {}
        has_anchor = bool(_digits(ctx.get("applicantIdentityNumber")) or _fold(ctx.get("applicantFullname")))
        if has_anchor and _requester_trusted(values, options):
            _fill_requester_from_cccd()

    # Không điền (hoặc không tin) thông tin người yêu cầu → mặc định 3 trường cư trú, bôi vàng.
    # `seen` đảm bảo KHÔNG đè lên giá trị thật đã fill ở trên.
    add("NYC_LoaiCuTru", "Thường trú", default=True)
    add("NYC_NoiCuTru", "1", default=True)
    add("NYC_NoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

    # Form chỉ có ô số lượng, không có radio Có/Không cấp bản sao.
    copy_quantity = _copy_quantity(values.get("CopyRequest_Quantity"))
    if copy_quantity:
        add("SoLuong", copy_quantity)

    return out
