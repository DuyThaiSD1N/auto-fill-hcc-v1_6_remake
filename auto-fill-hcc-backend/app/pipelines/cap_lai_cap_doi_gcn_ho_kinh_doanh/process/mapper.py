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


def _has_letters(value: Any) -> bool:
    return bool(re.search(r"[A-Za-z]", _text(value)))


def _registration_code(value: Any) -> str:
    """Mã đăng ký hộ kinh doanh kiểu cũ có lẫn CHỮ CÁI (vd "32A8010625": mã tỉnh + chữ + số).
    Giữ nguyên chữ + số, bỏ khoảng trắng/dấu chấm/gạch ngang, viết hoa cho khớp định dạng cổng."""
    return re.sub(r"[^0-9A-Za-z]", "", _text(value)).upper()


def _person_identity(value: Any) -> tuple[str, str]:
    if not isinstance(value, dict):
        return ("", "")
    return (_fold(value.get("hoTen")), _digits(value.get("soDinhDanh")))


def _normalize_person_address(value: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(value)
    if value.get("diaChi") not in (None, "", {}, []):
        normalized["diaChi"] = creation_mapper._addr(value["diaChi"])
    return normalized


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
    """Danh sách nhân thân từ CCCD và giấy ủy quyền, người được ủy quyền đứng ĐẦU.
    
    Dùng logic giống thủ tục đăng ký (delegate_first) để:
    - Người được ủy quyền từ giấy ủy quyền đứng đầu
    - Gộp với CCCD của chính họ (nếu có) để bù thiếu ngày sinh/giới tính/địa chỉ
    - CCCD ưu tiên field từ giấy ủy quyền, chỉ bù những field trống
    """
    candidates: list[dict[str, Any]] = []
    raw = values.get("Cccd_DanhSach")
    if isinstance(raw, list):
        candidates.extend(item for item in raw if isinstance(item, dict))
    for item in (applicant, values.get("ChuHo")):
        if isinstance(item, dict):
            candidates.append(item)
    
    # Dùng delegate_first() từ mapper đăng ký để xử lý người ủy quyền ĐÚNG
    candidates = creation_mapper.delegate_first(candidates, values)
    
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in candidates:
        key = _person_identity(item)
        if key == ("", "") or key in seen:
            continue
        seen.add(key)
        output.append(_normalize_person_address(item))
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
    applicant_compact = _person_fields(applicant)
    applicant_compact.extend(creation_mapper.authorization_fields(values))
    if isinstance(values.get("Cccd_DanhSach"), list) and values["Cccd_DanhSach"]:
        applicant_compact.append(_compact_field("Cccd_DanhSach", values["Cccd_DanhSach"]))
    authorization = {
        "coGiayUyQuyen": bool(values.get("UyQuyen_CoGiayUyQuyen")),
        "nguoiUyQuyen": {
            "hoTen": values.get("UyQuyen_NguoiUyQuyen_HoTen") or "",
            "soDinhDanh": values.get("UyQuyen_NguoiUyQuyen_SoDinhDanh") or "",
        },
    }
    identity_candidates = _identity_candidates(values, applicant)
    if (values.get("HasMultipleCCCD") or len(identity_candidates) >= 2
            or creation_mapper.authorized_person(values)):
        applicant_compact.append(_compact_field("HasMultipleCCCD", True))
    applicant_fields = creation_mapper.enrich(applicant_compact, page="nguoi-nop-ho-so")
    
    # Thêm thông tin ủy quyền KÈM địa chỉ người được ủy quyền để extension điền khi check radio
    authorized_person_info = creation_mapper.authorized_person(values)
    if any(authorization["nguoiUyQuyen"].values()):
        authorization_data = dict(authorization)
        # Thêm địa chỉ người được ủy quyền (đã gộp từ giấy ủy quyền + CCCD nếu có)
        if authorized_person_info and authorized_person_info.get("diaChi"):
            authorization_data["nguoiDuocUyQuyen"] = {
                "hoTen": authorized_person_info.get("hoTen") or "",
                "soDinhDanh": authorized_person_info.get("soDinhDanh") or "",
                "diaChi": authorized_person_info.get("diaChi"),  # Đã normalize qua _addr()
            }
        applicant_fields.append(_compact_field("__authorization", authorization_data))
    
    pages = {
        "thong-tin-de-nghi-cap-lai": request_fields,
        "nguoi-nop-ho-so": applicant_fields,
    }

    ma_so = values.get("HoKinhDoanh_MaSo")
    ma_dang_ky = values.get("HoKinhDoanh_MaDangKy")
    # "Mã số Hộ kinh doanh" (ô businessNumber, GDT_CODEFld) chỉ nhận mã THUẦN SỐ (dạng MST). Mã có
    # lẫn CHỮ CÁI (vd "32A8010625" — mã đăng ký hộ kinh doanh kiểu cũ: mã tỉnh + chữ + số) PHẢI vào
    # đúng ô "Mã số đăng ký hộ kinh doanh" (registrationNumber, IMP_BUSINESS_REG_NUMBERFbl) — điền
    # nhầm ô businessNumber sẽ tra cứu ra rỗng. OCR/LLM có thể gán mã này vào field HoKinhDoanh_MaSo
    # theo thói quen nên tự soi lại theo NỘI DUNG (có chữ cái hay không), không tin tuyệt đối tên field.
    if ma_so and _has_letters(ma_so):
        business_number = ""
        registration_number = _registration_code(ma_so)
    else:
        business_number = _digits(ma_so)
        registration_number = _registration_code(ma_dang_ky) if _has_letters(ma_dang_ky) else _digits(ma_dang_ky)

    search_options = [
        ("businessNumber", business_number),
        ("registrationNumber", registration_number),
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
        "owner": {
            "hoTen": _text((owner or applicant).get("hoTen")),
            "soDinhDanh": _digits((owner or applicant).get("soDinhDanh")),
        },
        "pageOrder": ["thong-tin-de-nghi-cap-lai", "nguoi-nop-ho-so"],
        "identityCandidates": identity_candidates,
    }
    return pages, flow
