"""Map facts nguồn sang Form.io của cổng DVC Ninh Bình (Đăng ký biến động QSDĐ, đơn Mẫu số 18)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date

from .schema import UI_COMP_BY_NAME


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


# Chủ hồ sơ là TỔ CHỨC → điền thêm ô "Cơ quan/Tổ chức" (data[organization]). Nhận diện theo tên.
_ORG_MARKERS = (
    "cong ty", "doanh nghiep", "tong cong ty", "hop tac xa", "htx",
    "chi nhanh", "xi nghiep", "tap doan", "nha may",
)


def _is_org_name(name: Any) -> bool:
    return any(marker in _fold(name) for marker in _ORG_MARKERS)


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
    match = re.fullmatch(r"\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})\s*", text)
    return normalize_date(match.group(0).replace("-", "/")) if match else None


def _area(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("chiTiet") or "",
    }
    return remap_area(area) if any(area.values()) else None


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    bare = re.sub(r"^(tỉnh|thành phố|tp\.?)\s+", "", text, flags=re.IGNORECASE).strip()
    return province_label(bare)


def _full_address(area: dict | None) -> str | None:
    if not area:
        return None
    parts = [_text(area.get(key)) for key in ("diaChi", "xa", "tinh")]
    return ", ".join(part for part in parts if part) or None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    del options
    values = _by_name(fields)
    out: list[dict] = []
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
    applicant_name = _text(values.get("NguoiNop_HoTen")) or owner_name
    authorized = bool(owner_name and applicant_name and _fold(owner_name) != _fold(applicant_name))

    # Không có ủy quyền: dùng toàn bộ fact chủ hồ sơ cho người nộp, không chỉ sao chép họ tên.
    source_prefix = "NguoiNop" if authorized else "ChuHoSo"
    applicant_area = _area(values.get(f"{source_prefix}_NoiCuTru"))
    applicant_id = _identity(values.get(f"{source_prefix}_SoDinhDanh"))

    add("data[ownerFullname]", owner_name)
    # Chủ hồ sơ là TỔ CHỨC (Công ty/HTX…): điền thêm ô "Cơ quan/Tổ chức" = tên tổ chức (điền cả
    # ownerFullname lẫn organization) để form không bỏ trống tên cơ quan.
    if _is_org_name(owner_name):
        add("data[organization]", owner_name)
    add("data[isOwnerDossier]", not authorized)
    add("data[fullname]", applicant_name)
    add("data[birthday]", _date(values.get(f"{source_prefix}_NgaySinh")))
    add("data[gender]", _text(values.get(f"{source_prefix}_GioiTinh")))
    add("data[identityNumber]", applicant_id)
    add("data[identityDate]", _date(values.get(f"{source_prefix}_NgayCap")))
    issuer = _text(values.get(f"{source_prefix}_NoiCap"))
    add("data[identityAgency]", normalize_issuer(issuer) if issuer else None)
    add("data[phoneNumber]", _phone(values.get(f"{source_prefix}_DienThoai")))
    add("data[email]", _text(values.get(f"{source_prefix}_Email")))
    add("data[chonDoiTuong]", "Cá nhân", default=True)
    add("data[nation]", applicant_area.get("quocGia") if applicant_area else "Việt Nam", default=True)
    if applicant_area:
        add("data[province]", _province_label(applicant_area.get("tinh")))
        add("data[district]", _text(applicant_area.get("xa")))
        add("data[address]", _text(applicant_area.get("diaChi")))
    add("data[noidungyeucaugiaiquyet]", _text(values.get("Don_NoiDungDeNghi")))
    # Ô Ghi chú: bảng thành phần hồ sơ (13 dòng) KHÔNG có dòng riêng cho CCCD/tờ khai thuế/giấy tờ hộ
    # tịch → các giấy tờ này được đính chung tại dòng Đơn đăng ký biến động (Mẫu số 18). Nêu rõ để cán
    # bộ biết chỗ tìm.
    add(
        "data[note]",
        "Căn cước công dân/CMND, tờ khai thuế và giấy tờ hộ tịch (nếu có) của các bên được đính kèm "
        "chung tại dòng Đơn đăng ký biến động đất đai (Mẫu số 18) vì mẫu không có dòng riêng cho các "
        "giấy tờ này.",
        default=True,
    )

    # Khối nhận kết quả theo đúng người trực tiếp nộp/được ủy quyền.
    add("data[hoTen]", applicant_name)
    add("data[soCCCD]", applicant_id)
    add("data[diaChi]", _full_address(applicant_area))

    return out, []
