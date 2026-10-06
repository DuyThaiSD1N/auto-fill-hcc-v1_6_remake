"""Map compact source facts → Form.io data[...] fields cho "Đăng ký, cấp GCN cho người nhận chuyển nhượng trong dự
án bất động sản" (cổng Đà Nẵng, 1.012787). Theo "Mapping_DKCapGCN_nhan_chuyen_nhuong_DuAnBDS_DaNang.xlsx".

HAI vai trong 1 panel:
- CHỦ HỒ SƠ (bên nhận chuyển nhượng) → data[ownerFullname] (+ data[organization]/data[taxCode] khi tổ chức).
- NHÂN THÂN người nộp → data[fullname]/birthday/gender/identityNumber/identityDate/identityAgency,
  data[chonDoiTuong].
- LIÊN HỆ của hồ sơ (ưu tiên chủ hồ sơ): data[phoneNumber], data[email], data[province]/district/address.
- data[isOwnerDossier]: True khi tự nộp; False khi ỦY QUYỀN hoặc chủ hồ sơ tổ chức không có người nộp.
- data[noidungyeucaugiaiquyet]: KHÔNG điền — cổng điền sẵn, mapping yêu cầu giữ nguyên.

Chặn nhầm vai: chủ hồ sơ / người nộp trùng tên CHỦ ĐẦU TƯ (bên bán) → bỏ, cảnh báo (Đơn Mẫu 18 hay có thêm
một bản do chủ đầu tư ký, mục 1 là công ty).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines.dang_ky_cap_gcn_nhan_chuyen_nhuong_du_an_bat_dong_san.process.schema import UI_COMP_BY_NAME


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


def _parse_area_text(value: Any) -> dict | None:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip(" .")
    if not text:
        return None
    parts = [p.strip(" .") for p in re.split(r"\s*(?:,|;|\s+-\s+)\s*", text) if p.strip(" .")]
    if not parts:
        return None
    out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
    if parts and _fold(parts[-1]) in {"viet nam", "vn"}:
        parts = parts[:-1]
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
    elif parts:
        out["diaChi"] = parts[0]
    return out if any(v for k, v in out.items() if k != "quocGia") else None


def _area(value: Any) -> dict | None:
    if isinstance(value, str):
        return _parse_area_text(value)
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("phuong") or value.get("phường") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    return out if any(v for k, v in out.items() if k != "quocGia") else None


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or None


def _gender_from_identity(identity: str | None) -> str | None:
    """Chữ số thứ 4 của số định danh 12 số mã hóa thế kỷ + giới tính: chẵn → Nam, lẻ → Nữ."""
    if not identity or len(identity) != 12:
        return None
    return "Nam" if int(identity[3]) % 2 == 0 else "Nữ"


def _gender(value: Any) -> str | None:
    folded = _fold(value)
    if folded in {"nam", "male", "ong"}:
        return "Nam"
    if folded in {"nu", "female", "ba"}:
        return "Nữ"
    return None


def _phone(value: Any) -> str | None:
    """SĐT liền chữ số. Giữ số quốc tế dạng 00… (hồ sơ mẫu dùng số nước ngoài, mapping: nhập liền);
    "+84…" → "0…"; bỏ số máy lẻ trong ngoặc ("18006636 (1)")."""
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"\([^)]*\)", " ", text).strip()
    digits = re.sub(r"\D+", "", text.upper().replace("O", "0"))
    if text.startswith("+"):
        if digits.startswith("84") and len(digits) in (11, 12):
            return "0" + digits[2:]
        return "00" + digits if 8 <= len(digits) <= 15 else None
    if digits.startswith("00") and 10 <= len(digits) <= 17:
        return digits
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    if 10 <= len(digits) <= 11 and digits.startswith("0"):
        return digits
    return None


def _email(value: Any) -> str | None:
    m = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", str(value or ""))
    return m.group(0) if m else None


def _date(value: Any) -> str | None:
    """dd/mm/yyyy hợp lệ, ngược lại None. Chặn ô tờ khai ghi đảo (ô "ngày cấp" chứa số CCCD) và năm trơn."""
    text = _text(value)
    if not text:
        return None
    m = (re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b", text)
         or re.search(r"ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", text, flags=re.IGNORECASE))
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text)
        if not m:
            return None
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
        return None
    return f"{day:02d}/{month:02d}/{year}"


def _issuer(value: Any) -> str | None:
    text = _text(value)
    return normalize_issuer(text) if text else None


_ORG_MARKERS = ("cong ty", "doanh nghiep", "hop tac xa", "htx", "cty", "co phan", "tnhh", "co quan",
                "xi nghiep", "tap doan", "chi nhanh", "ngan hang")


def _is_to_chuc(loai: Any, name: Any) -> bool:
    f_loai = _fold(loai)
    if "to chuc" in f_loai:
        return True
    if "ca nhan" in f_loai:
        return False
    return any(m in _fold(name) for m in _ORG_MARKERS)


def _party_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _fold(value))


def _same_party(name: Any, investor: Any) -> bool:
    a, b = _party_key(name), _party_key(investor)
    if not a or not b:
        return False
    return a == b or (min(len(a), len(b)) >= 12 and (a in b or b in a))


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

    investor = _text(values.get("ChuDauTu_Ten"))

    # --- CHỦ HỒ SƠ (bên nhận chuyển nhượng) ---
    owner_name = _text(values.get("ChuHoSo_HoTen"))
    if owner_name and _same_party(owner_name, investor):
        warnings.append(
            f"Chủ hồ sơ đọc ra trùng chủ đầu tư dự án ({investor}) — có thể lấy nhầm Đơn Mẫu 18 bản do chủ đầu "
            "tư ký. Đã bỏ trống chủ hồ sơ; nhập bên NHẬN chuyển nhượng (bên mua)."
        )
        owner_name = None
    owner_is_tc = bool(owner_name) and _is_to_chuc(values.get("ChuHoSo_LoaiChuThe"), owner_name)
    owner_id = _identity(values.get("ChuHoSo_SoDinhDanh")) if owner_name else None
    owner_area = _area(values.get("ChuHoSo_DiaChi")) if owner_name else None
    owner_phone = _phone(values.get("ChuHoSo_DienThoai")) if owner_name else None
    owner_email = _email(values.get("ChuHoSo_Email")) if owner_name else None

    # --- NGƯỜI NỘP ---
    nop_name = _text(values.get("NguoiNop_HoTen"))
    if nop_name and _same_party(nop_name, investor):
        nop_name = None
    nop_is_tc = _is_to_chuc(values.get("NguoiNop_LoaiDoiTuong"), nop_name)
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh")) if nop_name else None
    nop_mst = _identity(values.get("NguoiNop_MaSoThue")) if nop_name else None
    nop_area = _area(values.get("NguoiNop_DiaChi")) if nop_name else None
    nop_phone = _phone(values.get("NguoiNop_DienThoai")) if nop_name else None
    nop_email = _email(values.get("NguoiNop_Email")) if nop_name else None

    if not owner_name:
        warnings.append("Thiếu tên chủ hồ sơ (bên nhận chuyển nhượng).")

    # ỦY QUYỀN: người nộp là CÁ NHÂN KHÁC chủ hồ sơ và CÓ số định danh (từ giấy ủy quyền/CCCD).
    person_is_uy_quyen = bool(nop_name and owner_name and _fold(nop_name) != _fold(owner_name) and nop_id)

    add("data[ownerFullname]", owner_name)
    if owner_is_tc:
        add("data[organization]", owner_name)

    def _fill_nhan_than(identity: str | None) -> None:
        birthday = _date(values.get("NguoiNop_NgaySinh"))
        add("data[birthday]", birthday)
        add("data[gender]", _gender(values.get("NguoiNop_GioiTinh")) or _gender_from_identity(identity))
        add("data[identityNumber]", identity)
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap")))
        if not birthday:
            warnings.append(
                "Hồ sơ không có ngày sinh đầy đủ của người nộp (thường do không kèm CCCD/CT07). Ô 'Ngày sinh' "
                "đang mang sẵn ngày sinh của tài khoản đăng nhập — sửa theo CCCD trước khi nộp."
            )

    if owner_is_tc and not person_is_uy_quyen:
        # Chủ hồ sơ TỔ CHỨC không có người được ủy quyền kèm CCCD → để trống nhân thân người nộp.
        add("data[isOwnerDossier]", False)
        if nop_name or nop_id:
            warnings.append("Chủ hồ sơ là tổ chức, không có giấy ủy quyền kèm CCCD → để trống nhân thân người "
                            "nộp (tránh ghép chéo danh tính).")
    elif person_is_uy_quyen:
        add("data[isOwnerDossier]", False)
        add("data[fullname]", nop_name)
        add("data[chonDoiTuong]", "Tổ chức" if nop_is_tc else "Cá nhân")
        _fill_nhan_than(nop_id)
    elif owner_name:
        # TỰ NỘP: người nộp = chủ hồ sơ cá nhân. Số định danh ưu tiên phần người nộp, thiếu thì của chủ hồ sơ.
        add("data[isOwnerDossier]", True)
        add("data[fullname]", owner_name)
        add("data[chonDoiTuong]", "Cá nhân")
        _fill_nhan_than(nop_id or owner_id)

    # --- Liên hệ của HỒ SƠ: ưu tiên CHỦ HỒ SƠ, thiếu thì người nộp ---
    add("data[phoneNumber]", owner_phone or nop_phone)
    add("data[email]", owner_email or nop_email)
    area = owner_area or nop_area
    if area:
        add("data[province]", _province_label(area.get("tinh")))
        add("data[district]", _text(area.get("xa")))
        add("data[address]", _text(area.get("diaChi")))
    elif owner_name:
        warnings.append("Thiếu địa chỉ thường trú chủ hồ sơ — ô Tỉnh/TP đang mặc định 'Thành phố Đà Nẵng', cần "
                        "chọn lại trước khi nộp.")
    if owner_is_tc:
        add("data[taxCode]", owner_id)
    elif person_is_uy_quyen and nop_is_tc:
        add("data[taxCode]", nop_mst)

    return out, warnings
