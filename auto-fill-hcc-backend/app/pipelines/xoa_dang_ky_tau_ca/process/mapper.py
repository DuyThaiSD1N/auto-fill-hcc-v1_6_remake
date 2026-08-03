"""Map compact facts sang Form.io của thủ tục xóa đăng ký tàu cá.

Phần I người nộp chỉ được trả khi một CCCD upload khớp cả tên và số định danh trong ``formContext``.
Điều này tránh lấy CCCD của chủ hồ sơ đổ nhầm vào người nộp khi nhân viên thực hiện nộp thay.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.xoa_dang_ky_tau_ca.process.schema import UI_COMP_BY_NAME

_FORM = "data[toKhaiDangKyTamThoiTauCa_Mau08]"


def _by_name(fields: list[dict]) -> dict:
    return {field["name"]: field["value"] for field in fields if field.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        direct = value.get("fullText") or value.get("full") or value.get("text")
        if direct:
            return _text(direct)
        parts = [
            value.get("diaChi") or value.get("dia_chi") or value.get("chiTiet"),
            value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường"),
            value.get("huyen") or value.get("quanHuyen"),
            value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh"),
        ]
        return ", ".join(str(part).strip() for part in parts if str(part or "").strip()) or None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(tỉnh|thành phố|tp\.?|xã|phường|thị trấn|tt\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    if folded.startswith(("tinh ", "thanh pho ", "tp ")):
        if folded.startswith("tp "):
            return re.sub(r"^TP\.?\s+", "Thành phố ", text, flags=re.IGNORECASE)
        return text
    cities = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
    return f"{'Thành phố' if folded in cities else 'Tỉnh'} {_strip_admin_prefix(text)}"


def _parse_area_text(value: Any) -> dict | None:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip(" .")
    if not text:
        return None
    parts = [part.strip(" .") for part in re.split(r"\s*(?:,|;|\s+-\s+)\s*", text) if part.strip(" .")]
    if not parts:
        return None
    out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
    district_prefix = re.compile(r"^(huyện|quận|thành phố|tp\.?|thị xã)\s+", re.IGNORECASE)
    if len(parts) >= 4 and district_prefix.match(parts[-2]):
        out["tinh"], out["xa"], out["diaChi"] = parts[-1], parts[-3], ", ".join(parts[:-3])
    elif len(parts) >= 3:
        out["tinh"], out["xa"], out["diaChi"] = parts[-1], parts[-2], ", ".join(parts[:-2])
    elif len(parts) == 2:
        out["tinh"], out["diaChi"] = parts[-1], parts[0]
    else:
        out["diaChi"] = parts[0]
    return out


def _area(value: Any) -> dict | None:
    if isinstance(value, str):
        return _parse_area_text(value)
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    if not any(out.values()):
        return None
    # Mapping/HTML dùng danh mục địa giới mới của Đà Nẵng. Hồ sơ cũ còn ghi phường An Hải Tây (quận
    # Sơn Trà), nay phải chọn Phường An Hải để Choices.js khớp được option hiện hành.
    if "da nang" in _fold(out.get("tinh")) and _fold(out.get("xa")) == "an hai tay":
        out["xa"] = "Phường An Hải"
    return out


def _full_address(area: dict | None) -> str | None:
    if not area:
        return None
    parts = [_text(area.get("diaChi")), _text(area.get("xa")), _province_label(area.get("tinh"))]
    return ", ".join(part for part in parts if part) or None


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text)
    return normalize_date(match.group(0).replace("-", "/") if match else text)


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


def _ship_type(value: Any) -> str | None:
    text = _fold(value)
    if not text:
        return None
    if "cong vu" in text:
        return "Tàu công vụ thủy sản/Public service ship"
    return "Tàu cá/Vessel"


def _registration_number(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"\s*-\s*", "-", text)
    # Tiền tố đăng ký tàu Đà Nẵng được in "ĐNa"; OCR/LLM thường đồng nhất thành "ĐNA".
    return re.sub(r"^ĐNA(?=-|\s|\d)", "ĐNa", text, flags=re.IGNORECASE)


def _ship_owner_address(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    # OCR mẫu đọc nhầm địa danh "Nại Hiên Đông" thành "Nại Hiền Đông"; sửa hẹp theo GCN/hợp đồng.
    return re.sub(r"\bNại\s+Hiền\s+Đông\b", "Nại Hiên Đông", text, flags=re.IGNORECASE)


def _single_owner_default(name: Any, ratio: Any) -> str | None:
    explicit = _text(ratio)
    if explicit:
        match = re.search(r"\d+(?:[.,]\d+)?", explicit)
        return match.group(0).replace(",", ".") if match else explicit
    owner = _text(name)
    if owner and not re.search(r"\b(và|and)\b|[;/&]", owner, flags=re.IGNORECASE):
        return "100"
    return None


def _requester_from_context(values: dict, options: dict | None) -> tuple[dict | None, str | None]:
    context = (options or {}).get("formContext") or {}
    context_name = _text(context.get("applicantFullname") or context.get("fullname"))
    context_identity = _identity(context.get("applicantIdentityNumber") or context.get("identityNumber"))
    if not context_name or not context_identity:
        return None, "Không nhận đủ họ tên và CCCD người nộp từ biểu mẫu; giữ nguyên Phần I."

    candidates: list[dict] = []
    for prefix in ("Cccd1", "Cccd2"):
        name = _text(values.get(f"{prefix}_HoTen"))
        identity = _identity(values.get(f"{prefix}_SoDinhDanh"))
        if name and identity:
            candidates.append({
                "name": name,
                "identity": identity,
                "birthday": values.get(f"{prefix}_NgaySinh"),
                "gender": values.get(f"{prefix}_GioiTinh"),
                "issue_date": values.get(f"{prefix}_NgayCap"),
                "issuer": values.get(f"{prefix}_NoiCap"),
                "residence": values.get(f"{prefix}_ThuongTru"),
            })

    # Giữ tương thích khi LLM đọc được CCCD của người đề nghị nhưng chưa lặp lại vào nhóm Cccd*.
    owner_name = _text(values.get("NguoiDeNghi_HoTen"))
    owner_identity = _identity(values.get("NguoiDeNghi_SoDinhDanh"))
    if owner_name and owner_identity:
        candidates.append({
            "name": owner_name,
            "identity": owner_identity,
            "birthday": values.get("NguoiDeNghi_NgaySinh"),
            "gender": values.get("NguoiDeNghi_GioiTinh"),
            "issue_date": values.get("NguoiDeNghi_NgayCap"),
            "issuer": values.get("NguoiDeNghi_NoiCap"),
            "residence": values.get("NguoiDeNghi_ThuongTru"),
        })

    for candidate in candidates:
        if _fold(candidate["name"]) == _fold(context_name) and candidate["identity"] == context_identity:
            # Trả đúng giá trị tài khoản trên cổng sau khi đã xác minh bằng giấy tờ upload.
            candidate["name"] = context_name
            candidate["identity"] = context_identity
            return candidate, None

    return None, "Không có CCCD upload khớp cả họ tên và số định danh người nộp; giữ nguyên Phần I."


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value: Any) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    applicant_name = _text(values.get("NguoiDeNghi_HoTen"))
    applicant_identity = _identity(values.get("NguoiDeNghi_SoDinhDanh"))
    residence = _area(values.get("NguoiDeNghi_ThuongTru"))
    # Ưu tiên địa chỉ đã tách/chuẩn hóa để dùng phường hiện hành; chuỗi đầy đủ từ LLM có thể còn quận,
    # phường cũ trên CCCD/hợp đồng.
    full_applicant_address = _full_address(residence) or _text(values.get("NguoiDeNghi_DiaChiDayDu"))
    current_owner = _text(values.get("ChuTau_HoTen"))
    requester, requester_warning = _requester_from_context(values, options)
    requester_residence = _area(requester.get("residence")) if requester else None
    requester_is_owner = bool(
        requester
        and applicant_name
        and applicant_identity
        and _fold(requester.get("name")) == _fold(applicant_name)
        and requester.get("identity") == applicant_identity
    )

    if not applicant_name:
        warnings.append("Thiếu họ tên người đề nghị xóa đăng ký từ CCCD/Tờ khai/Hợp đồng mua bán.")
    if not current_owner:
        warnings.append("Thiếu tên chủ tàu đang đứng trên GCN đăng ký cũ.")
    if requester_warning:
        warnings.append(requester_warning)

    # Chỉ ghi Phần I sau khi giấy tờ upload khớp đủ hai mỏ neo của tài khoản cổng.
    add("data[fullname]", requester.get("name") if requester else None)
    add("data[birthday]", _date(requester.get("birthday")) if requester else None)
    add("data[gender]", _text(requester.get("gender")) if requester else None)
    add("data[identityNumber]", requester.get("identity") if requester else None)
    add("data[identityDate]", _date(requester.get("issue_date")) if requester else None)
    add("data[idIssuePlace]", _issuer(requester.get("issuer")) if requester else None)
    if requester_residence:
        add("data[province]", _province_label(requester_residence.get("tinh")))
        add("data[district]", _text(requester_residence.get("xa")))
        add("data[address]", _text(requester_residence.get("diaChi")))

    # Khi người nộp khớp cả tên và CCCD với chủ hồ sơ, để Form.io tự sao chép Phần I qua checkbox;
    # gửi thêm owner* có thể ghi đè dữ liệu vừa được cơ chế của cổng đồng bộ.
    add("data[isOwnerDossierCheck]", requester_is_owner)
    if not requester_is_owner:
        add("data[ownerFullname]", applicant_name)
        add("data[ownerBirthday]", _date(values.get("NguoiDeNghi_NgaySinh")))
        add("data[ownerGender]", _text(values.get("NguoiDeNghi_GioiTinh")))
        add("data[ownerIdentityNumber]", applicant_identity)
        add("data[ownerIdentityDate]", _date(values.get("NguoiDeNghi_NgayCap")))
        add("data[ownerIdIssuePlace]", _issuer(values.get("NguoiDeNghi_NoiCap")))
        if residence:
            add("data[ownerProvince]", _province_label(residence.get("tinh")))
            add("data[ownerDistrict]", _text(residence.get("xa")))
            add("data[ownerAddress]", _text(residence.get("diaChi")))
        add("data[ownerNation]", _text(values.get("NguoiDeNghi_QuocTich")) or ("Việt Nam" if applicant_name else None))

    add(f"{_FORM}[kinhGui]", _text(values.get("ToKhai_KinhGui")))
    add(f"{_FORM}[deNghi]", _ship_type(values.get("ToKhai_LoaiTau")))
    add(f"{_FORM}[ngayXoa]", _date(values.get("ToKhai_NgayXoa")))
    add(f"{_FORM}[Ten]", _text(values.get("Tau_Ten")))
    add(f"{_FORM}[HoHieuSoImo]", _text(values.get("Tau_HoHieuSoImo")))
    add(f"{_FORM}[fullname]", current_owner)
    add(f"{_FORM}[address]", _ship_owner_address(values.get("ChuTau_DiaChi")))
    add(f"{_FORM}[TiLeSoHuu]", _single_owner_default(current_owner, values.get("ChuTau_TiLeSoHuu")))
    add(f"{_FORM}[tenNguoiDNXoa]", applicant_name)
    add(f"{_FORM}[diaChiNguoiXoa]", full_applicant_address)
    add(f"{_FORM}[NoiDangKy]", _text(values.get("Tau_NoiDangKy")))
    add(f"{_FORM}[SoDangKy]", _registration_number(values.get("Tau_SoDangKy")))
    add(f"{_FORM}[ngayDK]", _date(values.get("Tau_NgayDangKy")))
    add(f"{_FORM}[CoQuanDangKy]", _text(values.get("Tau_CoQuanDangKy")))
    add(f"{_FORM}[lyDoXoaDangKy]", _text(values.get("ToKhai_LyDoXoa")))
    add(f"{_FORM}[diaDanh]", _province_label(values.get("ToKhai_DiaDanh")))
    add(f"{_FORM}[ngayKhai]", _date(values.get("ToKhai_NgayKhai")))
    signer = _text(values.get("ToKhai_NguoiKy"))
    if signer and applicant_name and _fold(signer) == _fold(applicant_name):
        signer = applicant_name
    add(f"{_FORM}[chuCS]", signer or applicant_name)

    return out, warnings
