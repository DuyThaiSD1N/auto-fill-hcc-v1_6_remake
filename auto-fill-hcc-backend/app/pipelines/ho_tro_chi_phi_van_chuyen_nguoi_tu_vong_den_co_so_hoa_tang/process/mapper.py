"""Map facts nguồn sang Form.io của cổng DVC Đà Nẵng (hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng).

HAI vai trên form (cùng contact block với cap_doi_gcn_da_nang):
- CHỦ HỒ SƠ -> data[ownerFullname] (+ data[organization] khi cơ quan, tổ chức đứng ra hỏa táng).
- NGƯỜI NỘP -> khối data[fullname]/birthday/gender/.../province/district/address + data[chonDoiTuong].
- data[isOwnerDossier]: True khi tự nộp (khối người nộp mang chính thông tin chủ hồ sơ); False khi ủy quyền.
- data[noidungyeucaugiaiquyet] = câu khung của cổng điền tên chủ hồ sơ.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.cccd import id_gender
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date

from .schema import UI_COMP_BY_NAME

PROC_TITLE = "Hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng"


def _by_name(fields: list[dict]) -> dict[str, Any]:
    return {item["name"]: item.get("value") for item in fields if item.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" ,;:")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _identity(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", _text(value) or "")
    return digits or None


def _phone(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", (_text(value) or "").upper().replace("O", "0"))
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = re.search(r"\b(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]\s*(\d{4})\b", text)
    return normalize_date(f"{match.group(1)}/{match.group(2)}/{match.group(3)}") if match else None


def _gender(value: Any, id_number: str | None) -> str | None:
    folded = _fold(value)
    if folded in {"nam", "male"}:
        return "Nam"
    if folded in {"nu", "female"}:
        return "Nữ"
    # Đơn không có ô giới tính người khai; số CCCD 12 chữ số mã hóa giới tính ở chữ số thứ 4.
    return id_gender(id_number) or None


def _area(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    tinh = re.sub(r"^(tỉnh|thành phố|tp\.?)\s+", "", _text(value.get("tinh")) or "", flags=re.IGNORECASE)
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": tinh,
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("chiTiet") or "",
    }
    if not (area["xa"] or area["diaChi"]):
        return None
    return remap_area(area, allow_diachi_fallback=True)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    del options
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value: Any, *, default: bool = False) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        item = {"name": name, "comp": comp, "value": value}
        if default:
            item["default"] = True
        out.append(item)
        seen.add(name)

    owner_name = _text(values.get("ChuHoSo_HoTen"))
    org_name = _text(values.get("ChuHoSo_TenToChuc"))
    submitter_name = _text(values.get("NguoiNop_HoTen"))
    authorized = bool(owner_name and submitter_name and _fold(owner_name) != _fold(submitter_name))

    if not owner_name and not org_name:
        warnings.append("Thiếu tên chủ hồ sơ (người đứng ra hỏa táng ở Mục II Đơn đề nghị).")

    def person_val(key: str):
        """Fact của người điền vào khối NGƯỜI NỘP. Tự nộp thì hai vai là một người nên bù chéo được."""
        if authorized:
            return values.get(f"NguoiNop_{key}")
        value = values.get(f"ChuHoSo_{key}")
        if value in (None, "", {}, []):
            value = values.get(f"NguoiNop_{key}")
        return value

    add("data[ownerFullname]", owner_name or org_name)
    add("data[isOwnerDossier]", not authorized)
    add("data[organization]", org_name)

    person_id = _identity(person_val("SoDinhDanh"))
    add("data[fullname]", submitter_name if authorized else (owner_name or submitter_name))
    add("data[birthday]", _date(person_val("NgaySinh")))
    add("data[gender]", _gender(person_val("GioiTinh"), person_id))
    add("data[identityNumber]", person_id)
    add("data[identityDate]", _date(person_val("NgayCap")))
    issuer = _text(person_val("NoiCap"))
    add("data[identityAgency]", normalize_issuer(issuer) if issuer else None)
    add("data[phoneNumber]", _phone(person_val("DienThoai")))
    add("data[email]", _text(person_val("Email")))
    # Cơ quan, tổ chức đứng ra hỏa táng và tự nộp -> đối tượng "Tổ chức"; còn lại "Cá nhân" (mặc định cổng).
    add("data[chonDoiTuong]", "Tổ chức" if (org_name and not authorized) else "Cá nhân", default=not org_name)

    area = _area(person_val("NoiCuTru"))
    add("data[nation]", (area or {}).get("quocGia") or "Việt Nam", default=True)
    if area:
        add("data[province]", province_label(area.get("tinh")))
        add("data[district]", _text(area.get("xa")))
        add("data[address]", _text(area.get("diaChi")))

    if owner_name or org_name:
        add(
            "data[noidungyeucaugiaiquyet]",
            f"ÔNG/BÀ: {owner_name or org_name} (chủ hồ sơ) ĐỀ NGHỊ GIẢI QUYẾT {PROC_TITLE}",
        )
    return out, warnings
