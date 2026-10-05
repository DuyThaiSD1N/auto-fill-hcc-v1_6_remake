"""Map compact facts sang Form.io của thủ tục xóa đăng ký tàu cá.

Phần I người nộp chỉ được trả khi một CCCD upload khớp cả tên và số định danh trong ``formContext``.
Điều này tránh lấy CCCD của chủ hồ sơ đổ nhầm vào người nộp khi nhân viên thực hiện nộp thay.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
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
    # Cổng dùng danh mục địa giới sau sáp nhập: CCCD/hợp đồng cũ còn ghi phường cũ (Hòa Hiệp Bắc, An Hải
    # Tây...) phải đổi sang phường hiện hành (Phường Hải Vân, Phường An Hải) thì dropdown mới khớp option.
    return remap_area(out) or out


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


def _form_address(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    # Tờ khai hay ghi kèm "(SĐT: ...)" sau địa chỉ người đề nghị; ô địa chỉ không nhận số điện thoại.
    text = re.sub(r"\(?\s*(?:SĐT|ĐT|Điện thoại|Tel)\s*[:.]?\s*[\d .]+\)?", "", text, flags=re.IGNORECASE)
    return _text(text)



_WARD_PREFIX = re.compile(r"^(xã|phường|thị trấn|đặc khu|p\.|x\.)\s*", re.IGNORECASE)
_DISTRICT_PREFIX = re.compile(r"^(huyện|quận|thị xã|q\.|h\.)\s*", re.IGNORECASE)
_WARD_LABEL = {"p.": "Phường", "x.": "Xã"}


def _form_area(value: Any, card_area: dict | None) -> dict | None:
    """Tách địa chỉ người đề nghị ghi trên Tờ khai thành {tinh,xa,diaChi}."""
    text = _form_address(value)
    if not text:
        return None
    # Tờ khai viết "phường A, thành phố B" hoặc kiểu GCN "P. A-Q. C-TP B".
    parts = [part.strip(" .") for part in re.split(r"\s*[,;]\s*|\s*-\s*", text) if part.strip(" .")]
    ward_index = next((i for i, part in enumerate(parts) if _WARD_PREFIX.match(part)), None)
    if ward_index is None:
        return _area(text)
    prefix = _WARD_PREFIX.match(parts[ward_index]).group(1)
    ward = f"{_WARD_LABEL.get(prefix.lower(), prefix.capitalize())} {parts[ward_index][len(prefix):].strip()}"
    tail = [part for part in parts[ward_index + 1:] if not _DISTRICT_PREFIX.match(part)]
    province = _strip_admin_prefix(tail[-1]) if tail else (card_area or {}).get("tinh", "")
    detail = ", ".join(parts[:ward_index])
    # Tờ khai thường chỉ ghi phường/tỉnh: mượn số nhà/tổ của CCCD khi cùng phường, khác phường thì bỏ
    # để không ghép tổ của phường cũ vào phường mới.
    if not detail and card_area and _fold(_strip_admin_prefix(card_area.get("xa"))) == _fold(
            _strip_admin_prefix(ward)):
        detail = card_area.get("diaChi") or ""
    return _area({"quocGia": "Việt Nam", "tinh": province, "xa": ward, "diaChi": detail})

_CCCD_PARTS = ("NgaySinh", "GioiTinh", "SoDinhDanh", "NgayCap", "NoiCap", "ThuongTru")


def _fill_applicant_from_cccd(values: dict, names: tuple[str | None, ...], options: dict | None) -> None:
    """LLM lúc lặp CCCD chủ hồ sơ vào NguoiDeNghi_*, lúc chỉ để ở Cccd*: bù từ Cccd* để kết quả ổn định."""
    if _identity(values.get("NguoiDeNghi_SoDinhDanh")):
        return
    context = (options or {}).get("formContext") or {}
    context_identity = _identity(context.get("applicantIdentityNumber") or context.get("identityNumber"))
    wanted = {_fold(name) for name in names if name}
    cards = [prefix for prefix in ("Cccd1", "Cccd2") if _identity(values.get(f"{prefix}_SoDinhDanh"))]
    chosen = [prefix for prefix in cards if _fold(_text(values.get(f"{prefix}_HoTen"))) in wanted]
    if not chosen and len(cards) == 1 and _identity(values.get(f"{cards[0]}_SoDinhDanh")) != context_identity:
        # Một thẻ duy nhất, không phải của người nộp: là CCCD chủ hồ sơ dù OCR đọc lệch họ tên.
        chosen = cards
    if len(chosen) != 1:
        return
    for part in _CCCD_PARTS:
        if values.get(f"NguoiDeNghi_{part}") in (None, "", {}, []):
            value = values.get(f"{chosen[0]}_{part}")
            if value not in (None, "", {}, []):
                values[f"NguoiDeNghi_{part}"] = value


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

    card_name = _text(values.get("NguoiDeNghi_HoTen"))
    form_name = _text(values.get("ToKhai_NguoiDeNghi_HoTen"))
    _fill_applicant_from_cccd(values, (card_name, form_name), options)
    applicant_name = card_name
    # CCCD (nhất là bản OCR) và Tờ khai lệch họ tên thì theo Tờ khai: người dân tự khai, cán bộ đối chiếu.
    if form_name and (not card_name or _fold(form_name) != _fold(card_name)):
        if card_name:
            warnings.append(
                f"Họ tên người đề nghị trên Tờ khai ({form_name}) khác CCCD ({card_name}); điền theo Tờ khai."
            )
        applicant_name = form_name
    applicant_identity = _identity(values.get("NguoiDeNghi_SoDinhDanh"))
    residence = _area(values.get("NguoiDeNghi_ThuongTru"))
    # Địa chỉ ghi trên Tờ khai đi thẳng vào ô của Tờ khai. Không có thì ưu tiên địa chỉ đã tách/chuẩn hóa
    # để dùng phường hiện hành; chuỗi đầy đủ từ LLM có thể còn quận, phường cũ trên CCCD/hợp đồng.
    full_applicant_address = (
        _form_address(values.get("ToKhai_NguoiDeNghi_DiaChi"))
        or _full_address(residence)
        or _text(values.get("NguoiDeNghi_DiaChiDayDu"))
    )
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
    if requester_is_owner:
        # Tài khoản đăng nhập chính là chủ hồ sơ: địa chỉ Phần I (cổng tự chép sang chủ hồ sơ) theo Tờ khai.
        requester_residence = (
            _form_area(values.get("ToKhai_NguoiDeNghi_DiaChi"), requester_residence) or requester_residence
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
    # Ô này thuộc Tờ khai: dòng "Cơ quan đăng ký" người dân đã ghi thắng cơ quan cấp GCN cũ.
    add(f"{_FORM}[CoQuanDangKy]",
        _text(values.get("ToKhai_CoQuanDangKy")) or _text(values.get("Tau_CoQuanDangKy")))
    add(f"{_FORM}[lyDoXoaDangKy]", _text(values.get("ToKhai_LyDoXoa")))
    add(f"{_FORM}[diaDanh]", _province_label(values.get("ToKhai_DiaDanh")))
    add(f"{_FORM}[ngayKhai]", _date(values.get("ToKhai_NgayKhai")))
    signer = _text(values.get("ToKhai_NguoiKy"))
    if signer and applicant_name and _fold(signer) == _fold(applicant_name):
        signer = applicant_name
    add(f"{_FORM}[chuCS]", signer or applicant_name)

    return out, warnings
