"""Map compact parent-child recognition facts to iframe x-* UI fields."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import default_issuer, id_doc_type, normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.nhan_cha_me_con.process.schema import UI_COMP_BY_NAME

_OTHER_DOC = "Giấy tờ khác bao gồm các giấy tờ có dán"
_REG_FOREIGN = "Ghi vào sổ việc nhận cha, mẹ, con đã được đăng ký tại cơ quan có thẩm quyền của nước ngoài"


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\n", " ")).strip(" ;,.")


def _upper_name(value: Any) -> str:
    text = _clean(value)
    return text.upper() if text else ""


def _strip_admin_prefix(value: Any) -> str:
    text = _clean(value)
    return re.sub(
        r"^(xã|phường|thị trấn|tt\.?|tỉnh|thành phố|tp\.?)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    folded = _fold(text)
    if folded.startswith(("tinh ", "thanh pho ", "tp ")):
        return text
    if folded in {"ha noi", "hai phong", "da nang", "ho chi minh", "tp ho chi minh", "can tho", "hue"}:
        return f"Thành phố {_strip_admin_prefix(text)}"
    return f"Tỉnh {_strip_admin_prefix(text)}"


def _commune_label(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    if _fold(text).startswith(("xa ", "phuong ", "thi tran ", "tt ")):
        return text
    return text


def _parse_area_text(value: str) -> dict | None:
    parts = [p.strip(" .") for p in re.split(r"[,;\n-]+", value or "") if p.strip(" .")]
    if not parts:
        return None
    out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
    district_prefix = re.compile(r"^(huyện|quận|thành phố|tp\.?|thị xã)\s+", re.IGNORECASE)
    commune_prefix = re.compile(r"^(xã|phường|thị trấn|tt\.?)\s+", re.IGNORECASE)
    detail_prefix = re.compile(r"^(số|sn|đường|phố|ngõ|tổ|tdp|thôn|bản|khu|xóm|ấp)\b", re.IGNORECASE)
    if len(parts) >= 4 and (district_prefix.match(parts[-2]) or (not commune_prefix.match(parts[-2]) and not detail_prefix.match(parts[-3]))):
        # OCR often drops "huyện/thành phố": "Thôn Tây Sơn, Mường So, Phong Thổ, Lai Châu".
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


def _area(value: Any) -> dict | None:
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
    return out if any(out.values()) else None


def _issuer(issue_place: Any, issue_date: Any) -> str:
    place = normalize_issuer(issue_place)
    if place:
        return place
    date = normalize_date(issue_date)
    return default_issuer(date) if date else ""


def _doc_type(issue_place: Any, issue_date: Any, hint: Any = "") -> str:
    issuer = _issuer(issue_place, issue_date)
    return id_doc_type(hint, issuer) if issuer or hint else ""


def _relationship(value: Any, parent_gender: Any = "") -> str:
    folded = _fold(value)
    if "bo" in folded or "cha" in folded:
        return "Cha"
    if "me" in folded:
        return "Mẹ"
    if "con" in folded:
        return "Con"
    gender = _fold(parent_gender)
    if gender == "nam":
        return "Cha"
    if gender == "nu":
        return "Mẹ"
    return _clean(value)


def _registration_type(value: Any) -> str:
    folded = _fold(value)
    if "nuoc ngoai" in folded or "ghi vao so" in folded:
        return _REG_FOREIGN
    return "Đăng ký mới"


def _confirmation_type(explicit: Any, relationship: Any, parent_gender: Any) -> str:
    text = _clean(explicit)
    if text in {"Cha nhận con", "Mẹ nhận con", "Con nhận cha", "Con nhận mẹ"}:
        return text
    folded = _fold(text)
    if "cha nhan con" in folded or "bo nhan con" in folded:
        return "Cha nhận con"
    if "me nhan con" in folded:
        return "Mẹ nhận con"
    if "con nhan cha" in folded or "con nhan bo" in folded:
        return "Con nhận cha"
    if "con nhan me" in folded:
        return "Con nhận mẹ"

    rel = _relationship(relationship, "")
    if rel == "Cha":
        return "Cha nhận con"
    if rel == "Mẹ":
        return "Mẹ nhận con"
    if rel == "Con":
        return "Con nhận mẹ" if _fold(parent_gender) == "nu" else "Con nhận cha"
    if _fold(parent_gender) == "nam":
        return "Cha nhận con"
    if _fold(parent_gender) == "nu":
        return "Mẹ nhận con"
    return ""


def _copy_value(value: Any) -> str:
    folded = _fold(value)
    if folded in {"yes", "true", "1", "co", "có"}:
        return "Có"
    if folded in {"no", "false", "0", "khong", "không"}:
        return "Không"
    return _clean(value)


def _same_identity(name_a: Any, id_a: Any, name_b: Any, id_b: Any) -> bool:
    """Hai bộ (họ tên, số định danh) có cùng chỉ về một người không. Số định danh là căn cứ
    chắc nhất; hai bên đều có số mà khác nhau thì KHÔNG so tên (trùng tên là chuyện thường)."""
    digits_a = re.sub(r"\D", "", str(id_a or ""))
    digits_b = re.sub(r"\D", "", str(id_b or ""))
    if digits_a and digits_b:
        return digits_a == digits_b
    folded_a = _fold(name_a)
    folded_b = _fold(name_b)
    return bool(folded_a) and folded_a == folded_b


def _birth_document_from_info(value: Any) -> dict:
    text = _clean(value)
    if not text:
        return {}
    out: dict[str, str] = {}
    if re.search(r"giấy\s+chứng\s+sinh|mã\s+số\s+gcs|\bgcs\b", text, re.IGNORECASE):
        out["type"] = "Giấy chứng sinh"
    elif re.search(r"giấy\s+khai\s+sinh", text, re.IGNORECASE):
        out["type"] = "Giấy khai sinh"

    number = re.search(
        r"(?:mã\s+số\s+gcs|số\s+gcs|giấy\s+(?:khai\s+sinh|chứng\s+sinh)\s+số|số)\s*[:\-]?\s*([A-Z0-9./-]+)",
        text,
        re.IGNORECASE,
    )
    if number:
        out["number"] = number.group(1).strip()

    issue_date = re.search(
        r"(?:ngày\s+(?:đăng\s+ký|cấp)|cấp\s+ngày)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        text,
        re.IGNORECASE,
    )
    if issue_date:
        out["issue_date"] = issue_date.group(1)

    issue_place = re.search(
        r"(?:do|nơi\s+(?:đăng\s+ký|cấp)\s*:?)\s*(.+?)(?=(?:\s+cấp\s+ngày|\s*;\s*ngày|\s+ngày\s+(?:đăng\s+ký|cấp)|$))",
        text,
        re.IGNORECASE,
    )
    if issue_place:
        out["issue_place"] = issue_place.group(1).strip(" ;,.")
    return out


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    """Derive deterministic iframe UI fields from compact source facts."""
    _ = options or {}
    values = dict(_by_name(fields))
    out: list[dict] = []
    seen: set[str] = set()
    has_source_values = bool(values)

    # Tờ khai có cấu trúc "Đề nghị công nhận [A] ... Là <Cha/Mẹ/Con> của [B]"; nhãn "Là ... của"
    # (không phải vị trí xuất hiện) mới quyết định A/B là Parent_* hay Child_*, nên LLM đôi khi đọc
    # nhầm hướng — gán cả Parent_* lẫn Child_* cùng trỏ về NGƯỜI CON (trùng tên/số định danh), bỏ
    # trống hẳn identity thật của cha/mẹ. Khi người yêu cầu tự khai quan hệ là Cha/Mẹ (hoặc Con) mà
    # khối tương ứng (Parent_*/Child_*) trống hoặc trùng hệt người còn lại, coi như người yêu cầu
    # CHÍNH LÀ người đó — lấy nguyên nhân thân từ Requester_* (đã ưu tiên đọc từ tờ khai) thay vì để
    # trống hoặc giữ dữ liệu sai.
    relationship = _relationship(
        values.get("Requester_RelationshipToRecognized") or values.get("Relationship_Claim"),
        values.get("Parent_Gender"),
    )
    if relationship in {"Cha", "Mẹ"}:
        parent_matches_child = _same_identity(
            values.get("Parent_FullName"), values.get("Parent_IdNumber"),
            values.get("Child_FullName"), values.get("Child_IdNumber"),
        )
        if not values.get("Parent_FullName") or parent_matches_child:
            for suffix in ("FullName", "BirthDate", "IdNumber", "IdIssueDate", "IdIssuePlace", "ResidenceDomestic"):
                requester_value = values.get(f"Requester_{suffix}")
                if requester_value not in (None, "", {}, []):
                    values[f"Parent_{suffix}"] = requester_value
            values.setdefault("Parent_Gender", "Nam" if relationship == "Cha" else "Nữ")
            values.setdefault("Parent_Nationality", "Việt Nam")
    elif relationship == "Con":
        child_matches_parent = _same_identity(
            values.get("Child_FullName"), values.get("Child_IdNumber"),
            values.get("Parent_FullName"), values.get("Parent_IdNumber"),
        )
        if not values.get("Child_FullName") or child_matches_parent:
            for suffix in ("FullName", "BirthDate", "IdNumber", "IdIssueDate", "IdIssuePlace", "ResidenceDomestic"):
                requester_value = values.get(f"Requester_{suffix}")
                if requester_value not in (None, "", {}, []):
                    values[f"Child_{suffix}"] = requester_value

    def add(name: str, value: Any) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    def add_domestic_area(prefix: str, area_value: Any) -> None:
        area = _area(area_value)
        if not area:
            return
        normalized = {
            "quocGia": area.get("quocGia") or "Việt Nam",
            "tinh": _province_label(area.get("tinh")),
            "xa": _commune_label(area.get("xa")),
            "diaChi": _clean(area.get("diaChi")),
        }
        if prefix == "Requester":
            add("DiaChiC", normalized["diaChi"])
            add("TT_TinhThanhC", normalized["tinh"])
            add("TT_PhuongXaC", normalized["xa"])
            return
        if prefix == "Parent":
            add("loaicutruA", "Thường trú")
            add("noicutruA", "Trong nước")
            add("noicutruA_TrongNuoc", normalized)
            return
        if prefix == "Child":
            add("loaicutruB", "Thường trú")
            add("noicutruB", "Trong nước")
            add("noicutruB_TrongNuoc", normalized)

    requester_issue_date = normalize_date(values.get("Requester_IdIssueDate"))
    requester_issuer = _issuer(values.get("Requester_IdIssuePlace"), requester_issue_date)
    requester_id = values.get("Requester_IdNumber")
    add("HoVaTenC", _upper_name(values.get("Requester_FullName")))
    add("SoDinhDanhC", requester_id)
    if requester_id:
        add("LoaiGiayToDinhDanhC", _doc_type(values.get("Requester_IdIssuePlace"), requester_issue_date))
        add("SoGiayToDinhDanhC", requester_id)
    add("NgayCapDDC", requester_issue_date)
    add("NoiCapDDC", requester_issuer)
    add_domestic_area("Requester", values.get("Requester_ResidenceDomestic"))
    add("nycSoDienThoai", values.get("Requester_PhoneNumber"))
    add("nycEmail", values.get("Requester_Email"))

    add("Quanhe", relationship)
    if has_source_values:
        add("LoaiDangKy", _registration_type(values.get("Registration_Type")))
    add(
        "loaiXacNhan",
        _confirmation_type(
            values.get("Confirmation_Type"),
            values.get("Requester_RelationshipToRecognized") or values.get("Relationship_Claim"),
            values.get("Parent_Gender"),
        ),
    )

    parent_issue_date = normalize_date(values.get("Parent_IdIssueDate"))
    parent_issuer = _issuer(values.get("Parent_IdIssuePlace"), parent_issue_date)
    has_parent = bool(values.get("Parent_FullName") or values.get("Parent_IdNumber"))
    add("HotenA", _upper_name(values.get("Parent_FullName")))
    add("ngaysinhA", normalize_date(values.get("Parent_BirthDate")))
    add("gioitinhA", values.get("Parent_Gender"))
    add("dantocA", values.get("Parent_Ethnicity"))
    if has_parent:
        add("quoctichA", values.get("Parent_Nationality") or "Việt Nam")
    add("sodinhdanhA", values.get("Parent_IdNumber"))
    if values.get("Parent_IdNumber"):
        add("loaigiaytoA", _doc_type(values.get("Parent_IdIssuePlace"), parent_issue_date))
        add("sogiaytodinhdanhA", values.get("Parent_IdNumber"))
    add("ngaycapA", parent_issue_date)
    add("NoiCapA", parent_issuer)
    add_domestic_area("Parent", values.get("Parent_ResidenceDomestic"))

    child_issue_date = normalize_date(values.get("Child_IdIssueDate"))
    child_issuer = _issuer(values.get("Child_IdIssuePlace"), child_issue_date)
    has_child = bool(values.get("Child_FullName") or values.get("Child_IdNumber") or values.get("Child_BirthDate"))
    add("hotenB", _upper_name(values.get("Child_FullName")))
    add("ngaysinhB", normalize_date(values.get("Child_BirthDate")))
    add("gioitinhB", values.get("Child_Gender"))
    add("dantocB", values.get("Child_Ethnicity"))
    if has_child:
        add("quoctichB", values.get("Child_Nationality") or "Việt Nam")
    add("sodinhdanhB", values.get("Child_IdNumber"))

    birth_doc = {
        "type": values.get("Child_BirthDocumentType"),
        "number": values.get("Child_BirthDocumentNumber"),
        "issue_date": normalize_date(values.get("Child_BirthDocumentIssueDate")),
        "issue_place": values.get("Child_BirthDocumentIssuePlace"),
    }
    info_birth_doc = _birth_document_from_info(values.get("Child_BirthDocumentInfo"))
    birth_doc = {key: value or info_birth_doc.get(key) for key, value in birth_doc.items()}

    if values.get("Child_IdNumber") and (child_issue_date or child_issuer):
        add("loaigiaytoB", _doc_type(values.get("Child_IdIssuePlace"), child_issue_date))
        add("sogiaytodinhdanhB", values.get("Child_IdNumber"))
        add("ngaycapB", child_issue_date)
        add("noicapB", child_issuer)
    elif birth_doc.get("number") or birth_doc.get("issue_date") or birth_doc.get("issue_place"):
        add("loaigiaytoB", _OTHER_DOC)
        add("tengiaytoB", birth_doc.get("type") or "Giấy khai sinh/Giấy chứng sinh")
        add("sogiaytodinhdanhB", birth_doc.get("number"))
        add("ngaycapB", normalize_date(birth_doc.get("issue_date")))
        add("noicapB", birth_doc.get("issue_place"))
    add_domestic_area("Child", values.get("Child_ResidenceDomestic"))

    copy = _copy_value(values.get("CopyRequest_WantsCopy"))
    if copy:
        add("CapBanSao", copy)

    return out
