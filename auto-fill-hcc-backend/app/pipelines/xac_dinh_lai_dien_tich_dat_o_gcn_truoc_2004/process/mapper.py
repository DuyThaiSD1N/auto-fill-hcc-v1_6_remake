"""Map compact source facts → Form.io data[...] fields cho "Xác định lại diện tích đất ở (GCN cấp trước
01/7/2004)" — cổng Đà Nẵng. Khối "Thông tin chung" + panel thửa đất Y HỆT dang_ky_dat_dai_lan_dau_da_nang.

HAI vai trong 1 panel:
- CHỦ HỒ SƠ (người đứng Đơn) → data[ownerFullname] (+ data[organization] khi tổ chức).
- NGƯỜI NỘP → data[fullname]/birthday/gender/identityNumber/.../province/district/address, data[chonDoiTuong].
- data[isOwnerDossier]: True khi tự nộp (mặc định); False khi ỦY QUYỀN (điền cả 2 vai).
- data[noidungyeucaugiaiquyet] = mục 2 "Nội dung biến động" của Đơn.
- data[note] = văn bản của cơ quan đăng ký đất đai + danh sách giấy tờ trong tệp đính kèm chung (bước 2 không
  có ô ghi chú nên cán bộ tiếp nhận chỉ đọc được ở đây).
- Panel thửa đất: data[diaChiThuaDat]/[SoToBanDo]/[SoThuaDat]/[province2]/[district2]/[nation2].
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.xac_dinh_lai_dien_tich_dat_o_gcn_truoc_2004.process.schema import UI_COMP_BY_NAME

# Đơn bỏ trống mục 2 thì ô bắt buộc "Nội dung yêu cầu giải quyết" ghi đúng tên việc của thủ tục.
_DEFAULT_NOI_DUNG = "Xác định lại diện tích đất ở"


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        direct = value.get("fullText") or value.get("full") or value.get("text")
        if direct:
            return _text(direct)
        parts = [
            value.get("diaChi") or value.get("chiTiet"),
            value.get("xa") or value.get("phuong"),
            value.get("tinh") or value.get("tinhThanh"),
        ]
        return ", ".join(str(p).strip() for p in parts if str(p or "").strip()) or None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _multiline_text(value: Any) -> str | None:
    """Giữ NGUYÊN xuống dòng (cho textarea nội dung yêu cầu): chỉ gộp khoảng trắng thừa mỗi dòng, bỏ dòng rỗng."""
    if value in (None, "", {}, []):
        return None
    if isinstance(value, (list, tuple)):
        value = "\n".join(str(v) for v in value)
    lines = [" ".join(str(line).split()) for line in str(value).replace("\r", "").split("\n")]
    lines = [line.strip(" .") for line in lines if line.strip(" .")]
    return "\n".join(lines) or None


def _text_list(value: Any) -> list[str]:
    """Field mảng (NguoiCungSuDung, GiayToTrongHoSo): LLM có lúc trả chuỗi ngăn cách ';' hoặc xuống dòng."""
    if value in (None, "", {}, []):
        return []
    items = value if isinstance(value, (list, tuple)) else re.split(r"[;\n]+", str(value))
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _text(item)
        if not text:
            continue
        text = text.strip(" .")
        key = _fold(text)
        if key and key not in seen:
            seen.add(key)
            out.append(text)
    return out


def _parcel_number(value: Any) -> str | None:
    """Chỉ giữ số thửa/số tờ; bỏ chữ dẫn 'thửa đất số'/'tờ bản đồ số'. Nhiều thửa giữ dạng '101, 102'."""
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"(?i)(thửa\s*đất\s*số|thửa\s*số|số\s*thửa|tờ\s*bản\s*đồ\s*số|tờ\s*bản\s*đồ|số\s*tờ)", "", text)
    parts = [p.strip(" :;.,-") for p in re.split(r"\s*(?:,|;|\bvà\b)\s*", text)]
    parts = [p for p in parts if p]
    unique: list[str] = []
    for p in parts:
        if p not in unique:
            unique.append(p)
    return ", ".join(unique) or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(tỉnh|thành\s*phố|t\.?\s*p\.?|xã|phường|thị trấn|t\.?\s*t\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    bare = _strip_admin_prefix(text)
    folded = _fold(bare)
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {bare}"


def _commune_label(value: Any) -> str | None:
    return _text(value)


def _parse_area_text(value: Any) -> dict | None:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip(" .")
    if not text:
        return None
    parts = [p.strip(" .") for p in re.split(r"\s*(?:,|;|\s+-\s+)\s*", text) if p.strip(" .")]
    if not parts:
        return None
    out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
    district_prefix = re.compile(r"^(huyện|quận|thành phố|tp\.?|thị xã)\s+", re.IGNORECASE)
    if len(parts) >= 4 and district_prefix.match(parts[-2]):
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
        out = _parse_area_text(value)
    elif isinstance(value, dict):
        out = {
            "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
            "tinh": value.get("tinh") or value.get("tinhThanh") or "",
            "xa": value.get("xa") or value.get("phuong") or value.get("phường") or "",
            "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
        }
        out = out if any(out.values()) else None
    else:
        return None
    # Chuẩn hóa phường/xã sau sáp nhập để khớp SELECT trên form. ⚠ remap_area build key bằng tỉnh KHÔNG
    # prefix ("da nang" ≠ "thanh pho da nang") → strip prefix tỉnh TRƯỚC; _province_label gắn lại sau.
    if not out:
        return None
    if out.get("tinh"):
        out["tinh"] = _strip_admin_prefix(out["tinh"])
    return remap_area(out, allow_diachi_fallback=True)


def _area_full_text(area: dict) -> str | None:
    """Địa chỉ thửa đất đủ 3 cấp cho textarea data[diaChiThuaDat] (mapping: 'Tổ …, Phường …, Thành phố …')."""
    parts = [_text(area.get("diaChi")), _commune_label(area.get("xa")), _province_label(area.get("tinh"))]
    return ", ".join(p for p in parts if p) or None


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or None


def _gender_from_identity(identity: str | None) -> str | None:
    """Chữ số thứ 4 của số định danh 12 số mã hóa thế kỷ + giới tính: chẵn → Nam, lẻ → Nữ.

    Bộ hồ sơ mẫu không kèm CCCD, chỉ có số CCCD trên Đơn → đây là nguồn giới tính còn lại.
    """
    if not identity or len(identity) != 12:
        return None
    return "Nam" if int(identity[3]) % 2 == 0 else "Nữ"


def _phone(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text.upper().replace("O", "0").replace("S", "5"))
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    if 10 <= len(digits) <= 11 and digits.startswith("0"):
        return digits
    return None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text)
    if m:
        return normalize_date(m.group(0).replace("-", "/"))
    # CHỈ có NĂM → BỎ TRỐNG thay vì để ô flatpickr tự suy ra ngày sai.
    if re.fullmatch(r"\d{4}", text.strip()):
        return None
    return normalize_date(text)


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


def _gender(value: Any) -> str | None:
    folded = _fold(value)
    if folded in {"nam", "male", "ong"}:
        return "Nam"
    if folded in {"nu", "female", "ba"}:
        return "Nữ"
    return None


_ORG_MARKERS = ("cong ty", "doanh nghiep", "hop tac xa", "htx", "cty", "co phan", "tnhh", "co quan",
                "xi nghiep", "tap doan", "chi nhanh", "ngan hang")


def _is_to_chuc(loai: Any, name: Any) -> bool:
    f_loai = _fold(loai)
    if "to chuc" in f_loai:
        return True
    if "ca nhan" in f_loai:
        return False
    return any(m in _fold(name) for m in _ORG_MARKERS)


def _note(van_ban: str | None, giay_to: list[str]) -> str | None:
    parts: list[str] = []
    if van_ban:
        parts.append(f"Hồ sơ nộp theo {van_ban.rstrip('.')}.")
    if giay_to:
        parts.append("Tệp đính kèm gồm: " + "; ".join(giay_to) + ".")
    return " ".join(parts) or None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    def add_area(province_name, district_name, address_name, area) -> None:
        if not area:
            return
        xa = _commune_label(area.get("xa"))
        dia_chi = _text(area.get("diaChi"))
        # Chỉ có tỉnh, thiếu cả phường/xã lẫn chi tiết → nhiều khả năng LLM suy từ thửa đất; bỏ cả cụm.
        if not xa and not dia_chi:
            return
        add(province_name, _province_label(area.get("tinh")))
        add(district_name, xa)
        add(address_name, dia_chi)

    # --- CHỦ HỒ SƠ ---
    owner_name = _text(values.get("ChuHoSo_HoTen"))
    owner_is_tc = _is_to_chuc(values.get("ChuHoSo_LoaiChuThe"), owner_name)
    owner_area = _area(values.get("ChuHoSo_DiaChi"))

    # --- NGƯỜI NỘP ---
    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_is_tc = _is_to_chuc(values.get("NguoiNop_LoaiDoiTuong"), nop_name)
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    nop_mst = _identity(values.get("NguoiNop_MaSoThue"))
    nop_area = _area(values.get("NguoiNop_DiaChi"))
    nop_birthday = _date(values.get("NguoiNop_NgaySinh"))
    nop_gender = _gender(values.get("NguoiNop_GioiTinh")) or _gender_from_identity(nop_id)

    if not owner_name:
        warnings.append("Thiếu tên chủ hồ sơ (người đứng tên Đơn đăng ký biến động).")

    is_uy_quyen = bool(nop_name and owner_name and _fold(nop_name) != _fold(owner_name))

    # --- Chủ hồ sơ ---
    add("data[ownerFullname]", owner_name)
    if owner_is_tc:
        add("data[organization]", owner_name)
    add("data[noidungyeucaugiaiquyet]", _multiline_text(values.get("NoiDungYeuCau")) or _DEFAULT_NOI_DUNG)
    add("data[note]", _note(_text(values.get("VanBanCoQuan")), _text_list(values.get("GiayToTrongHoSo"))))

    # --- Panel thửa đất ---
    parcel_area = _area(values.get("ThuaDat_DiaChi"))
    if parcel_area:
        add("data[province2]", _province_label(parcel_area.get("tinh")))
        add("data[district2]", _commune_label(parcel_area.get("xa")))
        add("data[diaChiThuaDat]", _area_full_text(parcel_area))
        add("data[nation2]", parcel_area.get("quocGia") or "Việt Nam")
    add("data[SoToBanDo]", _parcel_number(values.get("ThuaDat_SoTo")))
    add("data[SoThuaDat]", _parcel_number(values.get("ThuaDat_SoThua")))

    # --- Người nộp ---
    add("data[isOwnerDossier]", not is_uy_quyen)
    add("data[fullname]", nop_name or owner_name)
    add("data[birthday]", nop_birthday)
    add("data[gender]", nop_gender)
    add("data[identityNumber]", nop_id)
    add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
    add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap")))
    # Tự nộp: ưu tiên địa chỉ ghi trên Đơn (chủ hồ sơ) hơn CCCD hay còn địa danh cũ.
    add_area("data[province]", "data[district]", "data[address]", nop_area if is_uy_quyen else (owner_area or nop_area))
    add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")))
    add("data[email]", _text(values.get("NguoiNop_Email")))
    is_tc = nop_is_tc if is_uy_quyen else (nop_is_tc or owner_is_tc)
    add("data[chonDoiTuong]", "Tổ chức" if is_tc else "Cá nhân")
    if is_tc:
        add("data[taxCode]", nop_mst)

    if not nop_birthday:
        warnings.append(
            "Hồ sơ không có ngày sinh đầy đủ của người nộp (thường do không kèm CCCD). Ô 'Ngày sinh' có thể "
            "đang mang sẵn ngày sinh của tài khoản đăng nhập — cán bộ sửa theo CCCD trước khi nộp."
        )
    co_users = [n for n in _text_list(values.get("NguoiCungSuDung")) if _fold(n) != _fold(owner_name)]
    if co_users:
        warnings.append(
            f"Thửa đất có thêm {len(co_users)} người cùng sử dụng ({', '.join(co_users)}) nhưng form chỉ có một "
            "chủ hồ sơ. Nếu họ ủy quyền cho người đứng đơn thì cần đính văn bản ủy quyền ở dòng 'Văn bản về "
            "việc đại diện'."
        )

    return out, warnings
