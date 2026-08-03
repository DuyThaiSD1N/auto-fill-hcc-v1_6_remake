"""Dựng hai trang cấp lại/cấp đổi và người nộp từ facts đã trích xuất."""

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
    text = unicodedata.normalize("NFD", _text(value).lower().replace("đ", "d"))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", "".join(
        char for char in text if unicodedata.category(char) != "Mn"
    )).split())


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", _text(value))


def _person_identity(value: Any) -> tuple[str, str]:
    if not isinstance(value, dict):
        return ("", "")
    return (_fold(value.get("hoTen")), _digits(value.get("soDinhDanh")))


def _same_person(left: Any, right: Any) -> bool:
    left_name, left_id = _person_identity(left)
    right_name, right_id = _person_identity(right)
    return bool((left_id and right_id and left_id == right_id) or (left_name and right_name and left_name == right_name))


def _merge_person(primary: Any, fallback: Any) -> dict[str, Any]:
    first = dict(primary) if isinstance(primary, dict) else {}
    second = dict(fallback) if isinstance(fallback, dict) else {}
    if first and second and not _same_person(first, second):
        return first
    merged = second
    merged.update({key: value for key, value in first.items() if value not in (None, "", {}, [])})
    return merged


def _compact_field(name: str, value: Any) -> dict:
    return {"name": name, "comp": "raw", "value": value}


def _person_fields(person: Any) -> list[dict]:
    if not isinstance(person, dict):
        return []
    mapping = {
        "hoTen": "NguoiNop_HoTen", "gioiTinh": "NguoiNop_GioiTinh",
        "ngaySinh": "NguoiNop_NgaySinh", "soDinhDanh": "NguoiNop_SoDinhDanh",
        "ngayCap": "NguoiNop_NgayCap", "noiCap": "NguoiNop_NoiCap",
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
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in candidates:
        key = _person_identity(item)
        if key == ("", "") or key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def build(fields: list[dict]) -> tuple[dict[str, list[dict]], dict[str, Any]]:
    values = _by_name(fields)
    owner = values.get("ChuHo") if isinstance(values.get("ChuHo"), dict) else {}
    applicant = _merge_person(values.get("NguoiKy"), owner)
    request_kind = _text(values.get("DeNghi_Loai")).lower()
    if request_kind not in {"cap_lai", "cap_doi"}:
        request_kind = ""

    request_fields = [_compact_field("__reissueRequest", {
        "kind": request_kind,
        "reason": _text(values.get("DeNghi_LyDo")),
    })]
    pages = {
        "thong-tin-de-nghi-cap-lai": request_fields,
        "nguoi-nop-ho-so": creation_mapper.enrich(_person_fields(applicant), page="nguoi-nop-ho-so"),
    }

    search_options = [
        ("businessNumber", _digits(values.get("HoKinhDoanh_MaSo"))),
        ("registrationNumber", _digits(values.get("HoKinhDoanh_MaDangKy"))),
        ("internalNumber", _digits(values.get("HoKinhDoanh_MaNoiBo"))),
        ("identityNumber", _digits(owner.get("soDinhDanh") or applicant.get("soDinhDanh"))),
    ]
    method, value = next(((method, value) for method, value in search_options if value), ("", ""))
    flow = {
        "workflow": "reissue",
        "wizardType": "reissue",
        "registrationOption": "REI",
        "requestKind": request_kind,
        "search": {
            "method": method,
            "value": value,
            "expectedName": _text(values.get("HienTai_Ten")),
            "expectedBusinessNumber": _digits(values.get("HoKinhDoanh_MaSo")),
        },
        "pageOrder": ["thong-tin-de-nghi-cap-lai", "nguoi-nop-ho-so"],
        "identityCandidates": _identity_candidates(values, applicant),
    }
    return pages, flow
