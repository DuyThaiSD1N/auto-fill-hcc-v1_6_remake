"""Map compact TTHN facts to legacy x-* UI fields."""

import re
import unicodedata

from app.pipelines.xac_nhan_tthn.process.schema import UI_ALIASES, UI_COMP_BY_NAME

from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type
from app.pipelines._shared.area_remap import remap_area

_DEFAULT_PURPOSE = "Sử dụng vào mục đích khác"
_DIVORCED_STATUS = "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng đã ly hôn; hiện tại chưa đăng ký kết hôn với ai"
_WIDOWED_STATUS = "Đã đăng ký kết hôn hoặc đã có vợ/chồng nhưng vợ/chồng đã chết; hiện tại chưa đăng ký kết hôn với ai"
_MARRIED_STATUS = "Hiện tại đang có vợ/chồng"
_NEVER_MARRIED_STATUS = "Hiện tại chưa đăng ký kết hôn với ai"


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _normalize_commune_label(value) -> str:
    """Mở rộng viết tắt đơn vị hành chính để khớp option trên cổng."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    for pattern, prefix in (
        (r"^p(?:\.\s*|\s+)(.+)$", "Phường"),
        (r"^x(?:\.\s*|\s+)(.+)$", "Xã"),
    ):
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if match:
            return f"{prefix} {match.group(1).strip()}"
    return text


def _is_self_request(options: dict | None, cccd_name, cccd_id) -> bool:
    """Người yêu cầu có TRÙNG người trên CCCD upload không?

    So với tên + CCCD mà cổng đã điền sẵn cho NGƯỜI YÊU CẦU (formContext, lấy từ VNeID).
    Ưu tiên số căn cước; thiếu thì so tên (bỏ dấu). Thiếu cả hai → mặc định coi là bản thân
    (giữ hành vi cũ, an toàn cho ca tự làm phổ biến).
    """
    ctx = (options or {}).get("formContext") or {}
    applicant_id = _digits(ctx.get("applicantIdentityNumber"))
    upload_id = _digits(cccd_id)
    if applicant_id and upload_id:
        return applicant_id == upload_id
    applicant_name = _fold(ctx.get("applicantFullname"))
    upload_name = _fold(cccd_name)
    if applicant_name and upload_name:
        return applicant_name == upload_name
    return True


def _area(value):
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or "",
        "xa": _normalize_commune_label(
            value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or ""
        ),
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    remapped = remap_area(out)
    if isinstance(remapped, dict):
        remapped = {**remapped, "xa": _normalize_commune_label(remapped.get("xa"))}
    return remapped


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    """Derive deterministic UI fields for TTHN.

    Ba trường hợp:

    A. BẢN THÂN (không có giấy ủy quyền, CCCD upload = người đăng nhập):
       - Mục I (người yêu cầu) = CCCD upload.
       - Mục II (người được xác nhận) = CCCD upload (cùng người).
       - Quan hệ = "1" (Bản thân).

    B. ỦY QUYỀN (có PoA_SubjectName từ giấy ủy quyền):
       - Người ủy quyền (Section I giấy ủy quyền) = người CẦN giấy → Mục II form.
       - Người được ủy quyền (Section II giấy ủy quyền) = người ĐI NỘP = CCCD upload → Mục I form.
       - Quan hệ = "2" (Khác).

    C. CCCD-MISMATCH (CCCD upload KHÁC người đăng nhập, KHÔNG có giấy ủy quyền):
       - Mục I: không đè (để cổng giữ thông tin người đăng nhập), chỉ set default loại cư trú.
       - Mục II = CCCD upload (người cần giấy).
       - Quan hệ: để trống (user tự chọn).
    """
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
        if name in UI_ALIASES:
            field["aliases"] = UI_ALIASES[name]
        out.append(field)
        seen.add(name)

    has_cccd = bool(values.get("Cccd_SoDinhDanh") or values.get("Cccd_HoTen"))

    # --- Thông tin từ CCCD của người đi nộp (hoặc bản thân) ---
    issuer = values.get("Cccd_NoiCap") or default_issuer(values.get("Cccd_NgayCap"))
    nationality = values.get("Cccd_QuocTich") or "Việt Nam"
    # Tờ khai phản ánh nơi cư trú hiện tại; CCCD chỉ là nguồn dự phòng.
    residence = _area(values.get("ToKhai_NoiCuTru") or values.get("Cccd_NoiCuTru"))

    is_self = _is_self_request(options, values.get("Cccd_HoTen"), values.get("Cccd_SoDinhDanh"))

    # Phát hiện trường hợp ủy quyền: có PoA_SubjectName từ giấy ủy quyền
    poa_subject_name = values.get("PoA_SubjectName")
    has_poa = bool(poa_subject_name)
    declared_self = values.get("ToKhai_LaBanThan") is True or _fold(
        values.get("ToKhai_LaBanThan")
    ) in {"true", "1", "co"}

    # =========================================================
    # MỤC I & II cá nhân: chỉ điền khi có CCCD hoặc giấy ủy quyền
    # Không có CCCD + không có PoA → bỏ qua Mục I/II, vẫn điền tình trạng hôn nhân bên dưới
    # =========================================================
    # MỤC I & II: chỉ điền khi có CCCD hoặc giấy ủy quyền
    # Không có → bỏ qua thông tin cá nhân, vẫn điền tình trạng hôn nhân bên dưới
    # =========================================================
    if has_cccd or has_poa:

        # --- MỤC I: Người yêu cầu ---
        if has_poa:
            # ỦY QUYỀN: Mục I = người được ủy quyền = CCCD upload (đi nộp hộ)
            add("HoVaTenC", values.get("Cccd_HoTen"))
            add("NgaySinhC", values.get("Cccd_NgaySinh"))
            add("SoDinhDanhC", values.get("Cccd_SoDinhDanh"))
            add("LoaiGiayToDinhDanhC", id_doc_type("Thẻ căn cước công dân", issuer))
            add("SoGiayToTuyThanC", values.get("Cccd_SoDinhDanh"))
            add("NgayCapDDC", values.get("Cccd_NgayCap"))
            add("NoiCapDDC", issuer)
            add("nycLoaiCuTru", "Thường trú")
            if residence:
                add("nycNoiCuTru", "1")
                add("nycNoiCuTru_TrongNuoc", residence)
            else:
                add("nycNoiCuTru", "1", default=True)
                add("nycNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)
            add("quanhevoinguoiduocxacminh", "2")
        else:
            # BẢN THÂN hoặc CCCD-MISMATCH: điền đè từ CCCD upload
            add("HoVaTenC", values.get("Cccd_HoTen"))
            add("NgaySinhC", values.get("Cccd_NgaySinh"))
            add("SoDinhDanhC", values.get("Cccd_SoDinhDanh"))
            add("LoaiGiayToDinhDanhC", id_doc_type("Thẻ căn cước công dân", issuer))
            add("SoGiayToTuyThanC", values.get("Cccd_SoDinhDanh"))
            add("NgayCapDDC", values.get("Cccd_NgayCap"))
            add("NoiCapDDC", issuer)
            add("nycLoaiCuTru", "Thường trú")
            if residence:
                add("nycNoiCuTru", "1")
                add("nycNoiCuTru_TrongNuoc", residence)
            else:
                add("nycNoiCuTru", "1", default=True)
                add("nycNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)
            if is_self or declared_self:
                add("quanhevoinguoiduocxacminh", "1")

        # --- MỤC II: Người được xác nhận ---
        if has_poa:
            # ỦY QUYỀN: Mục II = người ủy quyền (người CẦN giấy) từ giấy ủy quyền
            poa_issuer = values.get("PoA_SubjectIssuer") or default_issuer(values.get("PoA_SubjectIdDate"))
            poa_residence = _area(values.get("PoA_SubjectAddress"))
            add("HoVaTenC1", poa_subject_name)
            add("NgaySinhC1", values.get("PoA_SubjectDoB"))
            add("GioiTinhC1", values.get("PoA_SubjectGender"))
            add("QuocTichC1", "Việt Nam")
            add("SoDinhDanhC1", values.get("PoA_SubjectIdNumber"))
            add("LoaiGiayToDinhDanhC1", id_doc_type("Thẻ căn cước công dân", poa_issuer))
            add("SoGiayToTuyThanC1", values.get("PoA_SubjectIdNumber"))
            add("NgayCapDDC1", values.get("PoA_SubjectIdDate"))
            add("NoiCapDDC1", poa_issuer)
            add("nxnLoaiCuTru", "Thường trú")
            if poa_residence:
                add("nxnNoiCuTru", "1")
                add("nxnNoiCuTru_TrongNuoc", poa_residence)
            else:
                add("nxnNoiCuTru", "1", default=True)
                add("nxnNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)
        else:
            # BẢN THÂN hoặc CCCD-MISMATCH: Mục II = người trên tờ khai (ưu tiên) hoặc CCCD upload
            # Ưu tiên: ToKhai_* → Cccd_* (từng field riêng lẻ)
            add("HoVaTenC1", values.get("ToKhai_HoTen") or values.get("Cccd_HoTen"))
            add("NgaySinhC1", values.get("ToKhai_NgaySinh") or values.get("Cccd_NgaySinh"))
            add("GioiTinhC1", values.get("ToKhai_GioiTinh") or values.get("Cccd_GioiTinh"))
            add("DanTocC1", values.get("ToKhai_DanToc") or values.get("Cccd_DanToc"))
            add("QuocTichC1", values.get("ToKhai_QuocTich") or nationality)
            # Giấy tờ: ưu tiên tờ khai, fallback CCCD
            so_dinh_danh = values.get("ToKhai_SoDinhDanh") or values.get("Cccd_SoDinhDanh")
            ngay_cap = values.get("ToKhai_NgayCapGiayTo") or values.get("Cccd_NgayCap")
            noi_cap = values.get("ToKhai_NoiCapGiayTo") or issuer
            add("SoDinhDanhC1", so_dinh_danh)
            add("LoaiGiayToDinhDanhC1", id_doc_type("Thẻ căn cước công dân", noi_cap))
            add("SoGiayToTuyThanC1", so_dinh_danh)
            add("NgayCapDDC1", ngay_cap)
            add("NoiCapDDC1", noi_cap)
            add("nxnLoaiCuTru", "Thường trú")
            if residence:
                add("nxnNoiCuTru", "1")
                add("nxnNoiCuTru_TrongNuoc", residence)
            else:
                add("nxnNoiCuTru", "1", default=True)
                add("nxnNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

    # =========================================================
    # TÌNH TRẠNG HÔN NHÂN: ưu tiên TỜ KHAI → fallback GIẤY TỜ CHỨNG MINH
    # =========================================================
    death_number = values.get("DeathCert_Number")
    death_date = values.get("DeathCert_Date")
    death_agency = values.get("DeathCert_Agency")
    divorce_number = values.get("DivorceDecision_Number")
    divorce_date = values.get("DivorceDecision_Date")
    divorce_agency = values.get("DivorceDecision_Agency")
    marriage_spouse = values.get("Marriage_SpouseName")
    marriage_number = values.get("Marriage_Number")
    marriage_date = values.get("Marriage_Date")
    marriage_agency = values.get("Marriage_Agency")
    declared_status = _fold(values.get("TinhTrangHonNhanC1"))

    # Ưu tiên 1: TỜ KHAI khai báo rõ ràng tình trạng hôn nhân
    if declared_status and declared_status != "":
        if declared_status == _fold(_WIDOWED_STATUS):
            # GÓA: từ tờ khai, bổ sung giấy tử nếu có
            add("TinhTrangHonNhanC1", _WIDOWED_STATUS)
            if death_number and death_date and death_agency:
                add("nxnLoaiTinhTrangHonNhan=4", {
                    "soBanAnQuyetDinhLyHon": death_number,
                    "ngayCapBanAnQuyetDinhLyHon": death_date,
                    "coQuanCapBanAnQuyetDinhLyHon": death_agency,
                })
        elif declared_status == _fold(_DIVORCED_STATUS):
            # ĐÃ LY HÔN: từ tờ khai, bổ sung giấy ly hôn nếu có
            add("TinhTrangHonNhanC1", _DIVORCED_STATUS)
            if divorce_number and divorce_date and divorce_agency:
                add("nxnLoaiTinhTrangHonNhan=3", {
                    "soBanAnQuyetDinhLyHon": divorce_number,
                    "ngayCapBanAnQuyetDinhLyHon": divorce_date,
                    "coQuanCapBanAnQuyetDinhLyHon": divorce_agency,
                })
        elif declared_status == _fold(_MARRIED_STATUS):
            # HIỆN ĐANG CÓ VỢ/CHỒNG: từ tờ khai, bổ sung giấy kết hôn nếu có
            add("TinhTrangHonNhanC1", _MARRIED_STATUS)
            marriage_detail = {
                "voChongHoTen": marriage_spouse,
                "soGiayTo": marriage_number,
                "ngayCapGiayTo": marriage_date,
                "coQuanCapGiayTo": marriage_agency,
            }
            marriage_detail = {key: value for key, value in marriage_detail.items() if value not in (None, "")}
            if marriage_detail:
                add("nxnLoaiTinhTrangHonNhan=2", marriage_detail)
                # Vùng =2 được render động. Phát thêm đúng DOM name sau field vùng để extension điền raw.
                add("soGiayTo", marriage_number)
                date_match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(marriage_date or "").strip())
                if date_match:
                    day, month, year = date_match.groups()
                    day = day.zfill(2)
                    month = month.zfill(2)
                    add("ngayCapGiayTo-day", day)
                    add("ngayCapGiayTo-month", month)
                    add("ngayCapGiayTo-year", year)
                    add("ngayCapGiayTo-name-date-input", f"{year}-{month}-{day}")
                add("coQuanCapGiayTo", marriage_agency)
        elif declared_status == _fold(_NEVER_MARRIED_STATUS):
            # CHƯA KẾT HÔN: từ tờ khai
            add("TinhTrangHonNhanC1", _NEVER_MARRIED_STATUS)
    
    # Ưu tiên 2: FALLBACK sang GIẤY TỜ CHỨNG MINH khi tờ khai không có
    elif death_number and death_date and death_agency:
        # GÓA: vợ/chồng đã chết (từ giấy tử)
        add("TinhTrangHonNhanC1", _WIDOWED_STATUS)
        add("nxnLoaiTinhTrangHonNhan=4", {
            "soBanAnQuyetDinhLyHon": death_number,
            "ngayCapBanAnQuyetDinhLyHon": death_date,
            "coQuanCapBanAnQuyetDinhLyHon": death_agency,
        })
    elif divorce_number and divorce_date and divorce_agency:
        # ĐÃ LY HÔN (từ giấy ly hôn)
        add("TinhTrangHonNhanC1", _DIVORCED_STATUS)
        add("nxnLoaiTinhTrangHonNhan=3", {
            "soBanAnQuyetDinhLyHon": divorce_number,
            "ngayCapBanAnQuyetDinhLyHon": divorce_date,
            "coQuanCapBanAnQuyetDinhLyHon": divorce_agency,
        })
    elif marriage_number and marriage_date:
        # HIỆN ĐANG CÓ VỢ/CHỒNG (từ giấy kết hôn)
        add("TinhTrangHonNhanC1", _MARRIED_STATUS)
        marriage_detail = {
            "voChongHoTen": marriage_spouse,
            "soGiayTo": marriage_number,
            "ngayCapGiayTo": marriage_date,
            "coQuanCapGiayTo": marriage_agency,
        }
        marriage_detail = {key: value for key, value in marriage_detail.items() if value not in (None, "")}
        add("nxnLoaiTinhTrangHonNhan=2", marriage_detail)
        # Vùng =2 được render động.
        add("soGiayTo", marriage_number)
        date_match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(marriage_date or "").strip())
        if date_match:
            day, month, year = date_match.groups()
            day = day.zfill(2)
            month = month.zfill(2)
            add("ngayCapGiayTo-day", day)
            add("ngayCapGiayTo-month", month)
            add("ngayCapGiayTo-year", year)
            add("ngayCapGiayTo-name-date-input", f"{year}-{month}-{day}")
        add("coQuanCapGiayTo", marriage_agency)

    # =========================================================
    # MỤC ĐÍCH & TRẢ KẾT QUẢ
    # =========================================================
    add("mucdich", _DEFAULT_PURPOSE)
    # Mục đích cụ thể từ tờ khai/giấy XNTTHN cũ → ô "Nhập mục đích" free-text.
    add("nhapmucdichkhac", values.get("Purpose"))
    add("TraKQ", "1")

    return out

