"""Dựng hai trang tạm ngừng và người nộp từ facts đã trích xuất."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines.dang_ky_kinh_doanh.process import mapper as creation_mapper
from app.pipelines._shared.formatting import normalize_date


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


def _business_number(value: Any) -> str:
    """Giữ nguyên dấu - trong mã số hộ kinh doanh/MST vì cần thiết cho việc tìm kiếm."""
    text = _text(value)
    return re.sub(r"[^\d\-]", "", text)


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


def _person_fields(person: Any, prefix: str = "NguoiNop") -> list[dict]:
    if not isinstance(person, dict):
        return []
    mapping = {
        "hoTen": f"{prefix}_HoTen",
        "gioiTinh": f"{prefix}_GioiTinh",
        "ngaySinh": f"{prefix}_NgaySinh",
        "soDinhDanh": f"{prefix}_SoDinhDanh",
        "diaChi": f"{prefix}_DiaChi",
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
    # Giấy ủy quyền là căn cứ chính cho người nộp thay → lên đầu, thẻ căn cước chỉ bù field còn trống.
    candidates = creation_mapper.delegate_first(candidates, values)
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

    # ==================================================================================
    # TRANG "TẠM NGỪNG HOẠT ĐỘNG" (DW_SUSPENSIONEdit.aspx) — field DOM đã xác nhận qua bảng đặc tả
    # HTML thật (sheet "Ta_m_ngu_ng_kinh_doanh"). Checkbox "Áp dụng cho đơn vị trực thuộc" luôn
    # checked+disabled sẵn trên cổng (không cho đổi) nên KHÔNG cần điền.
    # ==================================================================================
    suspension_fields: list[dict] = []
    tu_ngay = normalize_date(values.get("TamNgung_TuNgay"))
    den_ngay = normalize_date(values.get("TamNgung_DenNgay"))
    ly_do = _text(values.get("TamNgung_LyDo"))
    if tu_ngay:
        suspension_fields.append({
            "name": "ctl00$C$UC_DW_SUSPENSIONEdtCtl$SUSPENSION_START_DATEFld",
            "comp": "dom-date",
            "value": tu_ngay,
        })
    if den_ngay:
        suspension_fields.append({
            "name": "ctl00$C$UC_DW_SUSPENSIONEdtCtl$SUSPENSION_END_DATEFld",
            "comp": "dom-date",
            "value": den_ngay,
        })
    if ly_do:
        suspension_fields.append({
            "name": "ctl00$C$UC_DW_SUSPENSIONEdtCtl$SUSPENSION_REASONFld",
            "comp": "dom-input",
            "value": ly_do,
        })

    # Trang người nộp dùng NGUYÊN logic của đăng ký hộ kinh doanh: đưa đủ nhân thân người nộp + chủ hộ
    # + danh sách CCCD sang creation_mapper.enrich để nó tự chốt radio vai trò, nhân thân, địa chỉ,
    # __applicantAddress và __identityCandidates. Extension vẫn chốt lại theo tài khoản THẬT sau khi
    # bấm "Sao chép thông tin đăng ký tài khoản" (chỉ cần số định danh HOẶC họ tên khớp chủ hộ là tick
    # "Người có thẩm quyền ký Giấy đề nghị đăng ký Hộ kinh doanh").
    candidates = _identity_candidates(values, applicant)
    applicant_compact = _person_fields(applicant) + _person_fields(owner, "ChuHo")
    # Người nộp thay có thể CHỈ có tên trong Giấy ủy quyền → chuyển tiếp nguyên nhóm field ủy quyền
    # để creation_mapper dựng nhân thân đó vào __identityCandidates.
    applicant_compact.extend(creation_mapper.authorization_fields(values))
    if isinstance(values.get("Cccd_DanhSach"), list) and values["Cccd_DanhSach"]:
        applicant_compact.append(_compact_field("Cccd_DanhSach", values["Cccd_DanhSach"]))
    # Hồ sơ có từ 2 nhân thân trở lên (kể cả chủ hộ + người ký Thông báo) ⇒ nhiều khả năng có người
    # nộp thay; enrich chỉ đếm được Cccd_DanhSach nên truyền sẵn cờ theo danh sách đầy đủ.
    if values.get("HasMultipleCCCD") or len(candidates) >= 2:
        applicant_compact.append(_compact_field("HasMultipleCCCD", True))
    applicant_fields = creation_mapper.enrich(applicant_compact, page="nguoi-nop-ho-so")

    # Thêm thông tin ủy quyền KÈM địa chỉ người được ủy quyền (giống logic cấp lại/thay đổi/chấm dứt)
    authorized_person_info = creation_mapper.authorized_person(values)
    authorization_info = {
        "coGiayUyQuyen": bool(values.get("UyQuyen_CoGiayUyQuyen")),
        "nguoiUyQuyen": {
            "hoTen": values.get("UyQuyen_NguoiUyQuyen_HoTen") or "",
            "soDinhDanh": values.get("UyQuyen_NguoiUyQuyen_SoDinhDanh") or "",
        },
    }
    if any(authorization_info["nguoiUyQuyen"].values()):
        authorization_data = dict(authorization_info)
        if authorized_person_info and authorized_person_info.get("diaChi"):
            authorization_data["nguoiDuocUyQuyen"] = {
                "hoTen": authorized_person_info.get("hoTen") or "",
                "soDinhDanh": authorized_person_info.get("soDinhDanh") or "",
                "diaChi": authorized_person_info.get("diaChi"),  # Đã normalize qua _addr()
            }
        applicant_fields.append(_compact_field("__authorization", authorization_data))

    pages = {
        "tam-ngung-hoat-dong": suspension_fields,
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
        business_number = _business_number(ma_so)
        registration_number = _registration_code(ma_dang_ky) if _has_letters(ma_dang_ky) else _digits(ma_dang_ky)

    search_options = [
        ("businessNumber", business_number),
        ("registrationNumber", registration_number),
        ("internalNumber", _digits(values.get("HoKinhDoanh_MaNoiBo"))),
        ("identityNumber", _digits(owner.get("soDinhDanh"))),
    ]
    method, value = next(((method, value) for method, value in search_options if value), ("", ""))
    flow = {
        "workflow": "suspension",
        "wizardType": "change",
        "amendmentType": "SUSPEN",
        "search": {
            "method": method,
            "value": value,
            "expectedName": _text(values.get("HienTai_Ten")),
            "expectedBusinessNumber": _business_number(values.get("HoKinhDoanh_MaSo")),
        },
        "nameChange": False,
        "pageOrder": ["tam-ngung-hoat-dong", "nguoi-nop-ho-so"],
        # Luồng tạm ngừng KHÔNG có trang chủ hộ để extension đối chiếu → gửi kèm nhân thân chủ hộ.
        # Extension so với tài khoản đang đăng nhập: khớp số định danh HOẶC họ tên ⇒ chủ hộ tự nộp.
        # Hồ sơ không kê khai riêng chủ hộ thì lấy người ký Thông báo tạm ngừng (mặc định là chủ hộ).
        "owner": {
            "hoTen": _text((owner or applicant).get("hoTen")),
            "soDinhDanh": _digits((owner or applicant).get("soDinhDanh")),
        },
        "identityCandidates": candidates,
    }
    return pages, flow
