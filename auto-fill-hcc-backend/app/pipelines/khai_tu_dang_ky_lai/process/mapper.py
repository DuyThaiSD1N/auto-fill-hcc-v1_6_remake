"""Map compact re-registration death facts to legacy x-* UI fields."""

import re

from app.pipelines._shared.formatting import normalize_date, parse_death_time, upper_person_name
from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines._shared.area_remap import remap_area
from app.pipelines.khai_tu_dang_ky_lai.process.schema import UI_COMP_BY_NAME


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _area(value):
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or "",
        "xa": re.sub(
            r"^(xã|phường|thị trấn|tt\.?)\s+",
            "",
            str(value.get("xa") or value.get("xã") or "").strip(),
            flags=re.IGNORECASE,
        ).strip(),
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "",
    }
    if not out["tinh"] and not out["xa"] and not out["diaChi"]:
        return None
    return remap_area(out)


def _date_or_year(value) -> str:
    text = str(value or "").strip()
    m = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b", text)
    if m:
        d, mo, y = m.groups()
        return f"{int(d):02d}/{int(mo):02d}/{y}"
    y = re.search(r"\b(\d{4})\b", text)
    return y.group(1) if y else ""


def _copy_value(value) -> str:
    folded = str(value or "").strip().lower()
    if folded in {"yes", "true", "1", "co", "có"}:
        return "Có"
    if folded in {"no", "false", "0", "khong", "không"}:
        return "Không"
    return str(value or "").strip()


def _id_doc_type(number) -> str:
    return "Chứng minh nhân dân" if len(_digits(number)) == 9 else "Căn cước công dân"


def _issue_place(issue_place, issue_date) -> str:
    if issue_place:
        return issue_place
    normalized_date = normalize_date(issue_date)
    if normalized_date:
        return default_issuer(normalized_date)
    return ""


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    """Derive deterministic UI fields from compact source facts."""
    _ = options or {}
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
            field["default"] = True
        out.append(field)
        seen.add(name)

    # Structural default: only option rendered in this eForm is "Đăng ký lại".
    add("loaiDangKy", "2")

    # I. Người yêu cầu.
    requester_id = values.get("Requester_IdNumber")
    add("HoVaTenC", upper_person_name(values.get("Requester_FullName")))
    add("SoDinhDanhC", requester_id)
    add("SoGiayToDinhDanhC", requester_id)
    if requester_id:
        add("LoaiGiayToDinhDanhC", _id_doc_type(requester_id))
    add("NgayCapDDC", normalize_date(values.get("Requester_IdIssueDate")))
    add("NoiCapDDC", _issue_place(values.get("Requester_IdIssuePlace"), values.get("Requester_IdIssueDate")))
    add("nycLoaiCuTru", "Thường trú")
    requester_area = _area(values.get("Requester_ResidenceDomestic"))
    if requester_area:
        add("nycNoiCuTru", "1")
        add("nycNoiCuTru_TrongNuoc", requester_area)
    add("QuanHe", values.get("Requester_Relationship"))

    # II. Thông tin đăng ký khai tử trước đây.
    add("coQuanDKTruocDay_filter", values.get("PreviousDeathRegistration_AgencyProvince"))
    add("coQuanDKTruocDay", values.get("PreviousDeathRegistration_AgencyCommune"))
    add("soDKTruocDay", values.get("PreviousDeathRegistration_Number"))
    add("quyenSoDKTruocDay", values.get("PreviousDeathRegistration_BookNumber"))
    add("ngayDKTruocDay", normalize_date(values.get("PreviousDeathRegistration_Date")))

    # III. Người được đăng ký lại khai tử.
    deceased_id = values.get("Deceased_IdNumber")
    add("HoTen", upper_person_name(values.get("Deceased_FullName")))
    add("NgaySinh", _date_or_year(values.get("Deceased_BirthDate")))
    add("GioiTinh", values.get("Deceased_Gender"))
    add("nktDanToc", values.get("Deceased_Ethnicity"))
    add("nktQuocTich", values.get("Deceased_Nationality") or "Việt Nam")
    add("SoDinhDanh", deceased_id)
    add("SoGiayToDinhDanh", deceased_id)
    if deceased_id:
        add("LoaiGiayToDinhDanh", _id_doc_type(deceased_id))
    add("NgayCapDD", normalize_date(values.get("Deceased_IdIssueDate")))
    add("NoiCapDD", _issue_place(values.get("Deceased_IdIssuePlace"), values.get("Deceased_IdIssueDate")))
    add("nktLoaiCuTru", "Thường trú")
    deceased_area = _area(values.get("Deceased_ResidenceDomestic"))
    if deceased_area:
        add("nktNoiCuTru", "1")
        add("nktNoiCuTru_TrongNuoc", deceased_area)

    add("NgayMat", normalize_date(values.get("Deceased_DeathDate")))
    death_time = parse_death_time(values.get("Deceased_DeathTime"))
    add("GioMat", death_time.get("hour"))
    add("PhutMat", death_time.get("minute"))
    death_place = _area(values.get("Deceased_DeathPlaceDomestic")) or _area({
        "quocGia": "Việt Nam",
        "diaChi": values.get("DeathNotice_IssueAgency"),
    })
    if death_place:
        add("nktNoiChet", "1")
        add("nktNoiChet_TrongNuoc", death_place)
    add("NguyenNhanMat", values.get("Deceased_DeathCause"))

    if values.get("DeathNotice_Number") or values.get("DeathNotice_IssueDate") or values.get("DeathNotice_IssueAgency"):
        add("gbtLoai", values.get("DeathNotice_Type") or "Giấy báo tử")
        add("gbtSo", values.get("DeathNotice_Number"))
        add("gbtNgay", normalize_date(values.get("DeathNotice_IssueDate")))
        add("gbtCoQuanCap", values.get("DeathNotice_IssueAgency"))

    copy = _copy_value(values.get("CopyRequest_WantsCopy"))
    if copy:
        add("CapBanSao", copy)
        if copy == "Có":
            add("SoLuong", values.get("CopyRequest_Quantity") or "1")

    return out
