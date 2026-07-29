"""Map role-based compact facts to the legacy đăng ký lại khai sinh UI fields."""

import re
import unicodedata

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

from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _normalize_domestic_area(value):
    """Mở rộng viết tắt đơn vị hành chính trước khi trả địa chỉ cho extension."""
    if not isinstance(value, dict):
        return value

    normalized = dict(value)

    province = re.sub(r"\s+", " ", str(normalized.get("tinh") or "")).strip()
    province_key = re.sub(r"[^a-z0-9]+", "", _fold(province))
    if province_key in {
        "hochiminh",
        "tphochiminh",
        "thanhphohochiminh",
        "tphcm",
        "hcm",
    }:
        # Cổng dùng tên cấp tỉnh đầy đủ; các biến thể TP./TP HCM dễ không khớp option.
        normalized["tinh"] = "Thành phố Hồ Chí Minh"
    elif re.match(r"^TP\.?\s*", province, flags=re.IGNORECASE):
        normalized["tinh"] = re.sub(
            r"^TP\.?\s*",
            "Thành phố ",
            province,
            count=1,
            flags=re.IGNORECASE,
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
                pattern,
                replacement,
                commune,
                count=1,
                flags=re.IGNORECASE,
            ).strip()
            break
    else:
        # Giữ nguyên tên nhưng thống nhất cách viết tiền tố đã có sẵn.
        for prefix, replacement in (
            ("phường", "Phường "),
            ("xã", "Xã "),
            ("thị trấn", "Thị trấn "),
        ):
            pattern = rf"^{prefix}\s+"
            if re.match(pattern, commune, flags=re.IGNORECASE):
                normalized["xa"] = re.sub(
                    pattern,
                    replacement,
                    commune,
                    count=1,
                    flags=re.IGNORECASE,
                ).strip()
                break

    return normalized


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _id_doc_type(number) -> str:
    """CMND cũ ~9 chữ số → 'Chứng minh nhân dân'; CCCD/Căn cước 12 số → 'Căn cước công dân'."""
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
    """Chỉ tờ khai đăng ký lại khai sinh mới được phép điều khiển các ô cấp bản sao."""
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
    # CMND (9 số): nơi cấp là "Công an tỉnh ..." GHI TRÊN GIẤY — KHÔNG mặc định "Cục Cảnh sát..."/
    # "Bộ Công an" (chỉ đúng cho CCCD/Căn cước). Không đọc được thì để trống.
    if len(_digits(number)) == 9:
        return ""
    if number or values.get(f"{prefix}_IdIssueDate"):
        return default_issuer(values.get(f"{prefix}_IdIssueDate"))
    return ""


def _previous_registration_number(values: dict) -> str:
    number = str(values.get("PreviousRegistration_Number") or "").strip()
    if not number:
        return ""

    # Tránh fill nhầm số thứ tự mục trong tờ khai, ví dụ "(7) Ngày, tháng, năm sinh".
    # Số đăng ký thật từ GKS/tờ khai thường có ngày đăng ký đi cùng.
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
            field["default"] = True  # extension tô VIỀN VÀNG (giá trị mặc định, không từ giấy tờ)
        out.append(field)
        seen.add(name)

    for default in _STRUCTURAL_DEFAULTS:
        add(default["name"], default["value"])

    # I. Người yêu cầu: KHÔNG điền tên/số/giấy tờ (cổng đã điền sẵn từ VNeID). Chỉ trả 3 trường cư trú
    # mặc định, bôi vàng.
    add("nycLoaiCuTru", "Thường trú", default=True)
    add("nycNoiCuTru", "1", default=True)
    add("nycNoiCuTru_TrongNuoc", {"quocGia": "Việt Nam"}, default=True)

    # II. Người được đăng ký lại khai sinh.
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

    # III. Mẹ.
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
        if values.get("Mother_ResidenceDomestic"):
            add("MeNoiCuTru", "1")
            add("MeNoiCuTru_TrongNuoc", _normalize_domestic_area(values.get("Mother_ResidenceDomestic")))

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
        if values.get("Father_ResidenceDomestic"):
            add("ChaNoiCuTru", "1")
            add("ChaNoiCuTru_TrongNuoc", _normalize_domestic_area(values.get("Father_ResidenceDomestic")))

    # Thông tin đăng ký trước đây.
    add("coQuanDKTruocDay_filter", values.get("PreviousRegistration_AgencyProvince"))
    add("soDKTruocDay", _previous_registration_number(values))
    add("quyenSoDKTruocDay", values.get("PreviousRegistration_BookNumber"))
    add("ngayDKTruocDay", values.get("PreviousRegistration_Date"))

    # Chỉ điền yêu cầu bản sao khi tờ khai có khai báo thật; không sinh giá trị mặc định.
    if _is_birth_reregistration_declaration(values.get("CopyRequest_SourceDocumentTitle")):
        copy = _copy_value(values.get("CopyRequest_WantsCopy"))
        if copy:
            add("CapBanSao", copy)
            if copy == "Có":
                add("SoLuong", _copy_quantity(values.get("CopyRequest_Quantity")))

    return out
