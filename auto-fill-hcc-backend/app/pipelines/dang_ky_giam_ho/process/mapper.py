"""Map compact guardian-registration facts to iframe x-* UI fields."""

import re
import unicodedata

from app.pipelines._shared.formatting import normalize_date
from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type, normalize_issuer
from app.pipelines.dang_ky_giam_ho.process.schema import UI_COMP_BY_NAME
from app.pipelines._shared.area_remap import remap_area


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _strip_admin_prefix(value):
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(xã|phường|thị trấn|tt\.?|tỉnh|thành phố|tp\.?)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _parse_area_text(value: str) -> dict | None:
    parts = [p.strip(" .") for p in re.split(r"[,;\n-]+", value or "") if p.strip(" .")]
    if not parts:
        return None
    out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
    district_prefix = re.compile(r"^(huyện|quận|thành phố|tp\.?|thị xã)\s+", re.IGNORECASE)
    if len(parts) >= 4 and district_prefix.match(parts[-2]):
        out["tinh"] = parts[-1]
        out["xa"] = parts[-3]
        out["diaChi"] = ", ".join(parts[:-3]).strip()
    elif len(parts) >= 3:
        out["tinh"] = parts[-1]
        out["xa"] = parts[-2]
        out["diaChi"] = ", ".join(parts[:-2]).strip()
    elif len(parts) == 2:
        out["tinh"] = parts[-1]
        out["diaChi"] = parts[0]
    else:
        out["diaChi"] = parts[0]
    return out if any(out.values()) else None


def _area(value):
    if isinstance(value, str):
        return _parse_area_text(value)
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or "",
        "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    return remap_area(out)


def _province_label(value) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    folded = _fold(text)
    if folded.startswith(("tinh ", "thanh pho ", "tp ")):
        return text
    if folded in {
        "ha noi",
        "hai phong",
        "da nang",
        "ho chi minh",
        "tp ho chi minh",
        "can tho",
        "hue",
    }:
        return f"Thành phố {_strip_admin_prefix(text)}"
    return f"Tỉnh {_strip_admin_prefix(text)}"


def _commune_label(value) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    if _fold(text).startswith(("xa ", "phuong ", "thi tran ", "tt ")):
        return text
    return text


def _detail(value) -> str:
    return " ".join(str(value or "").split()).strip()


def _upper_name(value) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text.upper() if text else ""


def _issuer(issue_place, issue_date) -> str:
    place = normalize_issuer(issue_place)
    if place:
        return place
    date = normalize_date(issue_date)
    return default_issuer(date) if date else ""


def _doc_type(issue_place, issue_date) -> str:
    issuer = _issuer(issue_place, issue_date)
    return id_doc_type("", issuer) if issuer else ""


def _copy_value(value) -> str:
    folded = _fold(value)
    if folded in {"yes", "true", "1", "co", "có"}:
        return "Có"
    if folded in {"no", "false", "0", "khong", "không"}:
        return "Không"
    return " ".join(str(value or "").split()).strip()


def _birth_certificate_from_info(value) -> dict:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return {}
    out: dict[str, str] = {}

    number = re.search(r"(?:giấy\s+khai\s+sinh\s+)?số\s*[:\-]?\s*([A-Z0-9./-]+)", text, re.IGNORECASE)
    if number:
        out["number"] = number.group(1).strip()

    issue_date = re.search(
        r"(?:ngày\s+(?:đăng\s+ký|cấp)|cấp\s+ngày)\s*[:\-]?\s*"
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        text,
        re.IGNORECASE,
    )
    if issue_date:
        out["issue_date"] = issue_date.group(1)

    issue_place = re.search(
        r"(?:do|nơi\s+đăng\s+ký\s+khai\s+sinh\s*:?)\s*"
        r"(.+?)(?=(?:\s+cấp\s+ngày|\s*;\s*ngày|\s+ngày\s+đăng\s+ký|$))",
        text,
        re.IGNORECASE,
    )
    if issue_place:
        out["issue_place"] = issue_place.group(1).strip(" ;,.")
    return out


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    """Derive deterministic UI fields from compact source facts."""
    _ = options or {}
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    def add_area(prefix: str, area_value) -> None:
        area = _area(area_value)
        if not area:
            return
        if prefix == "Requester":
            add("TT_SoNhaToDanPhoC", _detail(area.get("diaChi")))
            add("TT_TinhThanhC", _province_label(area.get("tinh")))
            add("TT_PhuongXaC", _commune_label(area.get("xa")))
            return
        if prefix == "Guardian":
            add("cutru1", "Thường trú")
            add("noicutruA", _detail(area.get("diaChi")))
            add("tinhA", _province_label(area.get("tinh")))
            add("xaA", _commune_label(area.get("xa")))
            return
        if prefix == "Ward":
            add("cutru2", "Thường trú")
            add("noicutruB", _detail(area.get("diaChi")))
            add("TinhB", _province_label(area.get("tinh")))
            add("XaB", _commune_label(area.get("xa")))

    requester_issue_date = normalize_date(values.get("Requester_IdIssueDate"))
    requester_issuer = _issuer(values.get("Requester_IdIssuePlace"), requester_issue_date)
    requester_id = values.get("Requester_IdNumber")
    add("HoVaTenC", _upper_name(values.get("Requester_FullName")))
    add("SoDinhDanhC", requester_id)
    if requester_id:
        add("LoaiGiayToDinhDanhC", _doc_type(values.get("Requester_IdIssuePlace"), requester_issue_date))
    add("NgayCapDDC", requester_issue_date)
    add("NoiCapDDC", requester_issuer)
    add_area("Requester", values.get("Requester_ResidenceDomestic"))

    guardian_issue_date = normalize_date(values.get("Guardian_IdIssueDate"))
    guardian_issuer = _issuer(values.get("Guardian_IdIssuePlace"), guardian_issue_date)
    has_guardian = bool(values.get("Guardian_FullName") or values.get("Guardian_IdNumber"))
    add("hotenA", _upper_name(values.get("Guardian_FullName")))
    add("ngaysinhA", normalize_date(values.get("Guardian_BirthDate")))
    add("gioitinhA", values.get("Guardian_Gender"))
    add("dantocA", values.get("Guardian_Ethnicity"))
    if has_guardian:
        add("quoctichA", values.get("Guardian_Nationality") or "Việt Nam")
    add("sodinhdanhA", values.get("Guardian_IdNumber"))
    if values.get("Guardian_IdNumber"):
        add("loaigiaytoA", _doc_type(values.get("Guardian_IdIssuePlace"), guardian_issue_date))
        add("sodinhdanhA1", values.get("Guardian_IdNumber"))
    add("ngaycapA", guardian_issue_date)
    add("noicapA", guardian_issuer)
    add_area("Guardian", values.get("Guardian_ResidenceDomestic"))

    ward_issue_date = normalize_date(values.get("Ward_IdIssueDate"))
    ward_issuer = _issuer(values.get("Ward_IdIssuePlace"), ward_issue_date)
    has_ward = bool(values.get("Ward_FullName") or values.get("Ward_IdNumber"))
    add("hotenB", _upper_name(values.get("Ward_FullName")))
    add("ngaysinhB", normalize_date(values.get("Ward_BirthDate")))
    add("gioitinhB", values.get("Ward_Gender"))
    add("dantocB", values.get("Ward_Ethnicity"))
    if has_ward:
        add("quoctichB", values.get("Ward_Nationality") or "Việt Nam")
    add("sodinhdanhB", values.get("Ward_IdNumber"))
    birth_cert = {
        "number": values.get("Ward_BirthCertificateNumber"),
        "issue_date": normalize_date(values.get("Ward_BirthCertificateIssueDate")),
        "issue_place": values.get("Ward_BirthCertificateIssuePlace"),
    }
    info_birth_cert = _birth_certificate_from_info(values.get("Ward_BirthCertificateInfo"))
    birth_cert = {key: value or info_birth_cert.get(key) for key, value in birth_cert.items()}
    if values.get("Ward_IdNumber") and (ward_issue_date or ward_issuer):
        add("loaigiaytoB", _doc_type(values.get("Ward_IdIssuePlace"), ward_issue_date))
        add("sodinhdanhB1", values.get("Ward_IdNumber"))
        add("ngaycapB", ward_issue_date)
        add("noicapB", ward_issuer)
    elif birth_cert.get("number") or birth_cert.get("issue_date") or birth_cert.get("issue_place"):
        add("loaigiaytoB", "Giấy tờ khác bao gồm các giấy tờ có dán")
        add("sodinhdanhB1", birth_cert.get("number") or values.get("Ward_IdNumber"))
        add("ngaycapB", normalize_date(birth_cert.get("issue_date")))
        add("noicapB", birth_cert.get("issue_place"))
    add_area("Ward", values.get("Ward_ResidenceDomestic"))

    add("lydo", values.get("Registration_Reason"))
    copy = _copy_value(values.get("CopyRequest_WantsCopy"))
    if copy:
        add("CapBanSao", copy)
        if copy == "Có":
            add("soluong", values.get("CopyRequest_Quantity") or "1")

    return out
