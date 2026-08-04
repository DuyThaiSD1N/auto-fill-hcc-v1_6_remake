"""Map role-based compact facts to the legacy đăng ký lại khai sinh UI fields."""

import re
import unicodedata

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.ethnic_normalize import normalize_ethnic
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.legacy_fields.dang_ky_lai import ALLOWED as UI_COMP_BY_NAME
from app.pipelines.khai_sinh_dang_ky_lai.process import reason as _reason_mod

_COMP_BY_NAME = {
    **UI_COMP_BY_NAME,
    "LoaiDangKy": "x-radio",
    "nksLoaiKhaiSinh": "x-select-default",
    "DanTocC": "x-select",
    "CapBanSao": "x-radio",
    "SoLuong": "raw",
}

_STRUCTURAL_DEFAULTS = [
    {"name": "LoaiDangKy", "comp": "x-radio", "value": "2"},
    {"name": "nksLoaiKhaiSinh", "comp": "x-select-default", "value": "Đã xác định được cả cha lẫn mẹ"},
]


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _is_deceased_marker(area) -> bool:
    """Kiem tra neu LLM danh dau cha/me da mat bang {"diaChi": "Da chet"} hoac tuong tu."""
    if not isinstance(area, dict):
        return False
    tinh = str(area.get("tinh") or "").strip()
    xa = str(area.get("xa") or "").strip()
    dia = str(area.get("diaChi") or "").strip()
    # Chi co diaChi = "Da chet" / bien the, khong co tinh/xa that su
    if tinh or xa:
        return False
    folded = _fold(dia)
    return bool(folded) and any(
        kw in folded for kw in ("da chet", "dachet", "d.d. chat", "l.d.d. chat", "chet", "da mat")
    )


def _is_deceased_in_context(tag: str, context: str) -> bool:
    """Kiem tra reason context co chot cha (tag='cha') hoac me (tag='me') la da chet khong.

    Dung khi LLM khong tra *_ResidenceDomestic nhung reason da xac dinh Trang thai: da chet
    tu tai lieu khai tu / giay chung tu trong ho so.
    """
    if not context:
        return False
    section = _reason_mod._section(context, tag)
    if not section:
        return False
    status = _fold(_reason_mod._labeled_value(section, "Trạng thái"))
    return "da chet" in status or "chet" in status


def _normalize_domestic_area(value):
    """Chuan hoa viet tat don vi hanh chinh, sau do remap xa/phuong theo sap nhap."""
    if not isinstance(value, dict):
        return value

    normalized = dict(value)

    province = re.sub(r"\s+", " ", str(normalized.get("tinh") or "")).strip()
    province_key = re.sub(r"[^a-z0-9]+", "", _fold(province))
    if province_key in {"hochiminh", "tphochiminh", "thanhphohochiminh", "tphcm", "hcm"}:
        normalized["tinh"] = "Thành phố Hồ Chí Minh"
    elif re.match(r"^TP\.?\s*", province, flags=re.IGNORECASE):
        normalized["tinh"] = re.sub(
            r"^TP\.?\s*", "Thành phố ", province, count=1, flags=re.IGNORECASE
        ).strip()

    commune = re.sub(r"\s+", " ", str(normalized.get("xa") or "")).strip()
    commune_prefixes = (
        (r"^P(?:\.\s*|\s+)", "Phường "),
        (r"^X(?:\.\s*|\s+)", "Xã "),
        (r"^TT(?:\.\s*|\s+)", "Thị trấn "),
    )
    for pattern, replacement in commune_prefixes:
        if re.match(pattern, commune, flags=re.IGNORECASE):
            normalized["xa"] = re.sub(
                pattern, replacement, commune, count=1, flags=re.IGNORECASE
            ).strip()
            break
    else:
        for prefix, replacement in (
            ("phường", "Phường "),
            ("xã", "Xã "),
            ("thị trấn", "Thị trấn "),
        ):
            if re.match(rf"^{prefix}\s+", commune, flags=re.IGNORECASE):
                normalized["xa"] = re.sub(
                    rf"^{prefix}\s+", replacement, commune, count=1, flags=re.IGNORECASE
                ).strip()
                break

    # remap_area mặc định TẮT fallback (chỉ đổi xã khi khớp trực tiếp; xã sai → giữ nguyên, không bịa).
    return remap_area(normalized) or normalized


_DECEASED_AREA = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": "Đã chết"}


def _resolve_residence(values: dict, prefix: str, context: str = ""):
    """Lay dia chi cu tru cua cha/me:
    - Neu ResidenceDomestic la dia chi that -> dung truc tiep.
    - Neu ResidenceDomestic danh dau 'Da chet' HOAC reason context xac dinh da chet:
        -> BẮT BUỘC tra _DECEASED_AREA {"diaChi":"Đã chết"} de UI dien "Da chet".
        (KHÔNG dùng HometownFromDeathCert trong trường hợp này — đó là địa chỉ cũ
        trên giấy khai tử, không phải nơi cư trú hiện tại).
    - Neu ResidenceDomestic khong co NHƯNG co HometownFromDeathCert -> dung dia chi do.
    - Khong co ca hai -> tra None.
    """
    # prefix la "Father" hoac "Mother"; tag trong reason la "cha" hoac "me"
    reason_tag = "cha" if prefix == "Father" else "me"

    residence = values.get(f"{prefix}_ResidenceDomestic")
    is_deceased = (residence and _is_deceased_marker(residence)) or _is_deceased_in_context(reason_tag, context)

    if residence and not is_deceased:
        return _normalize_domestic_area(residence)

    # Cha/me da chet -> BẮT BUỘC tra "Đã chết", KHÔNG dùng HometownFromDeathCert
    if is_deceased:
        return _DECEASED_AREA

    # Khong co ResidenceDomestic nhung co HometownFromDeathCert (dia chi tu trich luc khai tu)
    # -> dung lam fallback khi KHÔNG xác định được là đã chết
    hometown_death = values.get(f"{prefix}_HometownFromDeathCert")
    if hometown_death and isinstance(hometown_death, dict):
        tinh = str(hometown_death.get("tinh") or "").strip()
        xa = str(hometown_death.get("xa") or "").strip()
        dia = str(hometown_death.get("diaChi") or "").strip()
        if tinh or xa or dia:
            return _normalize_domestic_area(hometown_death)

    return None


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _id_doc_type(number) -> str:
    """CMND cu ~9 so -> 'Chung minh nhan dan'; CCCD/Can cuoc 12 so -> 'Can cuoc cong dan'."""
    return "Chứng minh nhân dân" if len(_digits(number)) == 9 else "Căn cước công dân"


def _copy_value(value) -> str:
    folded = _fold(str(value or ""))
    if folded in {"yes", "true", "1", "co"}:
        return "Có"
    if folded in {"no", "false", "0", "khong"}:
        return "Không"
    return ""


def _copy_quantity(value) -> str:
    digits = _digits(value)
    return str(int(digits)) if digits and int(digits) > 0 else ""


def _is_birth_reregistration_declaration(title) -> bool:
    """Chi to khai dang ky lai khai sinh moi duoc phep dieu khien cac o cap ban sao."""
    folded = _fold(str(title or ""))
    return (
        "to khai" in folded
        and "dang ky lai" in folded
        and "khai sinh" in folded
        and "trich luc" not in folded
    )


def _issuer_or_default(values: dict, prefix: str) -> str:
    issuer = normalize_issuer(values.get(f"{prefix}_IdIssuePlace"))
    if issuer:
        return issuer
    number = values.get(f"{prefix}_IdNumber")
    # CMND (9 so): noi cap la "Cong an tinh ..." GHI TREN GIAY — KHONG mac dinh.
    if len(_digits(number)) == 9:
        return ""
    if number or values.get(f"{prefix}_IdIssueDate"):
        return default_issuer(values.get(f"{prefix}_IdIssueDate"))
    return ""


def _previous_registration_number(values: dict) -> str:
    number = str(values.get("PreviousRegistration_Number") or "").strip()
    if not number:
        return ""
    has_registration_context = bool(values.get("PreviousRegistration_Date"))
    if number.isdigit() and 1 <= int(number) <= 30 and not has_registration_context:
        return ""
    return number


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    """Derive deterministic UI fields while preserving the extension response shape."""
    values = _by_name(fields)
    context: str = (options or {}).get("_reasoning_context") or ""
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = _COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if default:
            field["default"] = True
        out.append(field)
        seen.add(name)

    for default in _STRUCTURAL_DEFAULTS:
        add(default["name"], default["value"])

    # I. Nguoi yeu cau.
    # Uu tien: (1) Requester_* tu to khai/don ghi ro; (2) Lay tu Father_*/Mother_* neu
    # reason xac dinh nguoi yeu cau la cha hoac me; (3) Default VNeID.
    has_requester = bool(values.get("Requester_FullName") or values.get("Requester_IdNumber"))

    # Xac dinh nguoi yeu cau la cha hay me tu reason context
    _nyc_section = _reason_mod._section(context, "nguoi_yeu_cau") if context else ""
    _nyc_dong_thoi = _fold(_reason_mod._labeled_value(_nyc_section, "Vai trò đồng thời")) if _nyc_section else ""
    _nyc_is_father = "cha" in _nyc_dong_thoi
    _nyc_is_mother = "me" in _nyc_dong_thoi or "mẹ" in _nyc_dong_thoi

    if has_requester:
        # Truong hop 1: co field Requester_* rieng tu to khai/CCCD nguoi yeu cau
        add("HoVaTenC", values.get("Requester_FullName"))
        req_id = values.get("Requester_IdNumber")
        add("SoDinhDanhC", req_id)
        add("SoGiayToDinhDanhC", req_id)
        if req_id:
            add("LoaiGiayToDinhDanhC", _id_doc_type(req_id))
        add("NgayCapDDC", values.get("Requester_IdIssueDate"))
        add("NoiCapDDC", _issuer_or_default(values, "Requester"))
        req_area = values.get("Requester_ResidenceDomestic")
        if req_area:
            add("nycLoaiCuTru", "Thường trú")
            add("nycNoiCuTru", "1")
            add("nycNoiCuTru_TrongNuoc", _normalize_domestic_area(req_area))
        else:
            add("nycLoaiCuTru", "Thường trú", default=True)
            add("nycNoiCuTru", "1", default=True)
            add("nycNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

    elif _nyc_is_father and any(name.startswith("Father_") for name in values):
        # Truong hop 2a: nguoi yeu cau la CHA -> lay tu Father_*
        father_id = values.get("Father_IdNumber")
        add("HoVaTenC", values.get("Father_FullName"))
        add("SoDinhDanhC", father_id)
        add("SoGiayToDinhDanhC", father_id)
        if father_id:
            add("LoaiGiayToDinhDanhC", _id_doc_type(father_id))
        add("NgayCapDDC", values.get("Father_IdIssueDate"))
        add("NoiCapDDC", _issuer_or_default(values, "Father"))
        add("nycLoaiCuTru", "Thường trú")
        father_area = _resolve_residence(values, "Father", context)
        if father_area:
            add("nycNoiCuTru", "1")
            add("nycNoiCuTru_TrongNuoc", father_area)
        else:
            add("nycNoiCuTru", "1", default=True)
            add("nycNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

    elif _nyc_is_mother and any(name.startswith("Mother_") for name in values):
        # Truong hop 2b: nguoi yeu cau la ME -> lay tu Mother_*
        mother_id = values.get("Mother_IdNumber")
        add("HoVaTenC", values.get("Mother_FullName"))
        add("SoDinhDanhC", mother_id)
        add("SoGiayToDinhDanhC", mother_id)
        if mother_id:
            add("LoaiGiayToDinhDanhC", _id_doc_type(mother_id))
        add("NgayCapDDC", values.get("Mother_IdIssueDate"))
        add("NoiCapDDC", _issuer_or_default(values, "Mother"))
        add("nycLoaiCuTru", "Thường trú")
        mother_area = _resolve_residence(values, "Mother", context)
        if mother_area:
            add("nycNoiCuTru", "1")
            add("nycNoiCuTru_TrongNuoc", mother_area)
        else:
            add("nycNoiCuTru", "1", default=True)
            add("nycNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

    else:
        # Truong hop 3: khong xac dinh duoc -> de default VNeID
        add("nycLoaiCuTru", "Thường trú", default=True)
        add("nycNoiCuTru", "1", default=True)
        add("nycNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

    add(
        "DanTocC",
        normalize_ethnic(
            values.get("Father_Ethnicity")
            or values.get("Subject_Ethnicity")
            or values.get("Mother_Ethnicity")
        ),
    )

    # II. Nguoi duoc dang ky lai khai sinh.
    has_subject = any(name.startswith("Subject_") for name in values)
    if has_subject:
        add("HoTenKS", values.get("Subject_FullName"))
        add("NgaySinhChon", values.get("Subject_BirthDate"))
        add("GioiTinhKS", values.get("Subject_Gender"))
        add("DanTocKS", normalize_ethnic(values.get("Subject_Ethnicity")))
        add("QuocTichKS", values.get("Subject_Nationality") or "Việt Nam")
        if values.get("Subject_BirthPlaceDomestic"):
            add("nksNoiSinh", "1")
            add("nksNoiSinh_TrongNuoc", _normalize_domestic_area(values.get("Subject_BirthPlaceDomestic")))
        if values.get("Subject_HometownDomestic"):
            add("nksQueQuan", "1")
            add("nksQueQuan_TrongNuoc", _normalize_domestic_area(values.get("Subject_HometownDomestic")))

    # III. Me.
    has_mother = any(name.startswith("Mother_") for name in values)
    if has_mother:
        add("HoTenMeKS", values.get("Mother_FullName"))
        add("SoDinhDanhMe", values.get("Mother_IdNumber"))
        add("SoGiayToDinhDanhMe", values.get("Mother_IdNumber"))
        if values.get("Mother_IdNumber"):
            add("LoaiGiayToDinhDanhMe", _id_doc_type(values.get("Mother_IdNumber")))
        add("NgayCapDDMe", values.get("Mother_IdIssueDate"))
        add("NoiCapDDMe", _issuer_or_default(values, "Mother"))
        add("NamSinhMeKS", values.get("Mother_BirthDateOrYear"))
        add("DanTocMeKS", normalize_ethnic(values.get("Mother_Ethnicity")))
        add("QuocTichMeKS", values.get("Mother_Nationality") or "Việt Nam")
        add("MeLoaiCuTru", "Thường trú")
        me_addr = _resolve_residence(values, "Mother", context)
        if me_addr:
            add("MeNoiCuTru", "1")
            add("MeNoiCuTru_TrongNuoc", me_addr)

    # IV. Cha.
    has_father = any(name.startswith("Father_") for name in values)
    if has_father:
        add("HoTenChaKS", values.get("Father_FullName"))
        add("SoDinhDanhCha", values.get("Father_IdNumber"))
        add("SoGiayToDinhDanhCha", values.get("Father_IdNumber"))
        if values.get("Father_IdNumber"):
            add("LoaiGiayToDinhDanhCha", _id_doc_type(values.get("Father_IdNumber")))
        add("NgayCapDDCha", values.get("Father_IdIssueDate"))
        add("NoiCapDDCha", _issuer_or_default(values, "Father"))
        add("NamSinhChaKS", values.get("Father_BirthDateOrYear"))
        add("DanTocChaKS", normalize_ethnic(values.get("Father_Ethnicity")))
        add("QuocTichChaKS", values.get("Father_Nationality") or "Việt Nam")
        add("ChaLoaiCuTru", "Thường trú")
        cha_addr = _resolve_residence(values, "Father", context)
        if cha_addr:
            add("ChaNoiCuTru", "1")
            add("ChaNoiCuTru_TrongNuoc", cha_addr)

    # Thong tin dang ky truoc day.
    add("coQuanDKTruocDay_filter", values.get("PreviousRegistration_AgencyProvince"))
    add("soDKTruocDay", _previous_registration_number(values))
    add("quyenSoDKTruocDay", values.get("PreviousRegistration_BookNumber"))
    add("ngayDKTruocDay", values.get("PreviousRegistration_Date"))

    # Chi dien yeu cau ban sao khi to khai co khai bao that.
    if _is_birth_reregistration_declaration(values.get("CopyRequest_SourceDocumentTitle")):
        copy = _copy_value(values.get("CopyRequest_WantsCopy"))
        if copy:
            add("CapBanSao", copy)
            if copy == "Có":
                add("SoLuong", _copy_quantity(values.get("CopyRequest_Quantity")))

    return out
