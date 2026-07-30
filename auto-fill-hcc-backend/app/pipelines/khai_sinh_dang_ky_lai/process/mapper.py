"""Map role-based compact facts to the legacy đăng ký lại khai sinh UI fields."""

import re
import unicodedata

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines._shared.legacy_fields.dang_ky_lai import ALLOWED as UI_COMP_BY_NAME

_COMP_BY_NAME = {
    **UI_COMP_BY_NAME,
    "LoaiDangKy": "x-radio",
    "nksLoaiKhaiSinh": "x-select-default",
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

    return remap_area(normalized) or normalized


def _resolve_residence(values: dict, prefix: str):
    """Lay dia chi cu tru cua cha/me:
    - Neu ResidenceDomestic la dia chi that -> dung truc tiep.
    - Neu ResidenceDomestic danh dau 'Da chet' -> thu lay HometownFromDeathCert (que quan tren
      trich luc khai tu) thay the, van qua remap.
    - Neu ca hai khong co -> tra None.
    """
    residence = values.get(f"{prefix}_ResidenceDomestic")
    if residence and not _is_deceased_marker(residence):
        return _normalize_domestic_area(residence)

    # Cha/me da mat: thu dung que quan tu trich luc khai tu
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

    # I. Nguoi yeu cau: khong dien ten/so/giay to (cong da dien san tu VNeID).
    add("nycLoaiCuTru", "Thường trú", default=True)
    add("nycNoiCuTru", "1", default=True)
    add("nycNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

    # II. Nguoi duoc dang ky lai khai sinh.
    has_subject = any(name.startswith("Subject_") for name in values)
    if has_subject:
        add("HoTenKS", values.get("Subject_FullName"))
        add("NgaySinhChon", values.get("Subject_BirthDate"))
        add("GioiTinhKS", values.get("Subject_Gender"))
        add("DanTocKS", values.get("Subject_Ethnicity"))
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
        add("DanTocMeKS", values.get("Mother_Ethnicity"))
        add("QuocTichMeKS", values.get("Mother_Nationality") or "Việt Nam")
        add("MeLoaiCuTru", "Thường trú")
        me_addr = _resolve_residence(values, "Mother")
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
        add("DanTocChaKS", values.get("Father_Ethnicity"))
        add("QuocTichChaKS", values.get("Father_Nationality") or "Việt Nam")
        add("ChaLoaiCuTru", "Thường trú")
        cha_addr = _resolve_residence(values, "Father")
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
