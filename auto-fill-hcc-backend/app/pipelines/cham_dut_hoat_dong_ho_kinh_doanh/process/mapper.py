"""Dựng hai trang chấm dứt và người nộp từ facts đã trích xuất."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines.dang_ky_kinh_doanh.process import mapper as creation_mapper


def _by_name(fields: list[dict]) -> dict[str, Any]:
    return {item["name"]: item.get("value") for item in fields if item.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def _fold(value: Any) -> str:
    text = _text(value).lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", "".join(
        ch for ch in text if unicodedata.category(ch) != "Mn"
    )).split())


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", _text(value))


def _person_identity(value: Any) -> tuple[str, str]:
    if not isinstance(value, dict):
        return ("", "")
    return (_fold(value.get("hoTen")), _digits(value.get("soDinhDanh")))


def _same_person(left: Any, right: Any) -> bool:
    l_name, l_id = _person_identity(left)
    r_name, r_id = _person_identity(right)
    return bool((l_id and r_id and l_id == r_id) or (l_name and r_name and l_name == r_name))


def _merge_person(primary: Any, fallback: Any) -> dict[str, Any]:
    first = dict(primary) if isinstance(primary, dict) else {}
    second = dict(fallback) if isinstance(fallback, dict) else {}
    if first and second and not _same_person(first, second):
        return first
    # Tờ thông báo thường chỉ ghi tên/CCCD người nộp, còn địa chỉ nằm ở phần chủ hộ.
    # Giữ dữ liệu fallback rồi chỉ ghi đè bằng giá trị thực để không làm mất địa chỉ.
    merged = second
    merged.update({key: value for key, value in first.items() if value not in (None, "", {}, [])})
    return merged


def _compact_field(name: str, value: Any) -> dict:
    return {"name": name, "comp": "raw", "value": value}


def _person_fields(person: Any) -> list[dict]:
    if not isinstance(person, dict):
        return []
    mapping = {
        "hoTen": "NguoiNop_HoTen",
        "gioiTinh": "NguoiNop_GioiTinh",
        "ngaySinh": "NguoiNop_NgaySinh",
        "soDinhDanh": "NguoiNop_SoDinhDanh",
        "diaChi": "NguoiNop_DiaChi",
    }
    return [_compact_field(target, person.get(source)) for source, target in mapping.items()
            if person.get(source) not in (None, "", {}, [])]


def _identity_candidates(values: dict[str, Any], applicant: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    raw = values.get("Cccd_DanhSach")
    if isinstance(raw, list):
        candidates.extend(item for item in raw if isinstance(item, dict))
    for item in (applicant, values.get("ChuHo")):
        if isinstance(item, dict):
            candidates.append(item)
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in candidates:
        key = _person_identity(item)
        if key == ("", "") or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def build(fields: list[dict]) -> tuple[dict[str, list[dict]], dict[str, Any]]:
    values = _by_name(fields)
    owner = values.get("ChuHo") if isinstance(values.get("ChuHo"), dict) else {}
    applicant = _merge_person(values.get("NguoiNop"), owner)

    reason = _text(values.get("ChamDut_LyDo"))
    dissolution_fields = [{
        "name": "ctl00$C$UC_DW_DISSOLUTIONCtl$DISSOLUTION_TYPE_IDFld",
        "comp": "dom-select",
        # HTML mẫu xác nhận option ổn định value=OTHER cho trường hợp không có loại chuyên biệt.
        "value": _text(values.get("ChamDut_LoaiHinh")) or "OTHER",
    }]
    if reason:
        dissolution_fields.append({
            "name": "ctl00$C$UC_DW_DISSOLUTIONCtl$REASON_DESCFld",
            "comp": "dom-input",
            "value": reason,
        })

    applicant_fields = creation_mapper.enrich(_person_fields(applicant), page="nguoi-nop-ho-so")
    pages = {
        "cham-dut-hoat-dong": dissolution_fields,
        "nguoi-nop-ho-so": applicant_fields,
    }

    search_options = [
        ("businessNumber", _digits(values.get("HoKinhDoanh_MaSo"))),
        ("registrationNumber", _digits(values.get("HoKinhDoanh_MaDangKy"))),
        ("internalNumber", _digits(values.get("HoKinhDoanh_MaNoiBo"))),
        ("identityNumber", _digits(owner.get("soDinhDanh"))),
    ]
    method, value = next(((method, value) for method, value in search_options if value), ("", ""))
    flow = {
        "workflow": "dissolution",
        "wizardType": "change",
        "amendmentType": "DISSOLU",
        "search": {
            "method": method,
            "value": value,
            "expectedName": _text(values.get("HienTai_Ten")),
            "expectedBusinessNumber": _digits(values.get("HoKinhDoanh_MaSo")),
        },
        "nameChange": False,
        "pageOrder": ["cham-dut-hoat-dong", "nguoi-nop-ho-so"],
        "identityCandidates": _identity_candidates(values, applicant),
    }
    return pages, flow
