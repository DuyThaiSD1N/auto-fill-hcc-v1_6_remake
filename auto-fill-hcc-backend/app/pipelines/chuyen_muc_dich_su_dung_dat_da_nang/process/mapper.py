"""Map compact source facts → Form.io data[...] fields cho "Đăng ký biến động chuyển mục đích SDĐ không
phải xin phép" (cổng Đà Nẵng). CÙNG contact block với #75 — chỉ khác _PROC_TITLE.

HAI vai trong 1 panel:
- CHỦ HỒ SƠ (chủ đất đề nghị chuyển mục đích) → data[ownerFullname] (+ data[organization] khi tổ chức).
- NGƯỜI NỘP           → data[fullname]/birthday/gender/identityNumber/.../province/district/address,
  data[chonDoiTuong] (loại người nộp), data[taxCode] (khi người nộp là tổ chức).
- data[isOwnerDossier]: True khi chủ hồ sơ = người nộp (tự nộp) → cổng tự đổ; False khi ỦY QUYỀN (điền cả 2).
- data[noidungyeucaugiaiquyet] = "{tên chủ hồ sơ} ĐỀ NGHỊ GIẢI QUYẾT {tên thủ tục}".
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.chuyen_muc_dich_su_dung_dat_da_nang.process.schema import UI_COMP_BY_NAME

# Văn bản "Nội dung yêu cầu giải quyết" ghép: "{tên chủ hồ sơ} ĐỀ NGHỊ GIẢI QUYẾT {tên thủ tục}".
_PROC_TITLE = (
    "Đăng ký biến động chuyển mục đích sử dụng đất không phải xin phép cơ quan nhà nước có thẩm quyền"
)


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
        return _parse_area_text(value)
    if not isinstance(value, dict):
        return None
    out = {
        "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("phuong") or value.get("phường") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    return out if any(out.values()) else None


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or None


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
    return normalize_date(text)


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


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None]] = set()

    def add(name: str, value) -> None:
        if name in {s[0] for s in seen} or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add((name, None))

    def add_area(province_name, district_name, address_name, area) -> None:
        if not area:
            return
        xa = _commune_label(area.get("xa"))
        dia_chi = _text(area.get("diaChi"))
        # Chống địa chỉ ĐOÁN: nếu chỉ có tỉnh mà thiếu CẢ phường/xã LẪN số nhà/chi tiết → nhiều khả năng
        # LLM suy từ thửa đất/trụ sở tổ chức (không phải nơi thường trú thật của người nộp). Thường trú
        # trên CCCD luôn có đủ xã + số nhà → bỏ cả cụm để không điền lệch mỗi ô Tỉnh.
        if not xa and not dia_chi:
            return
        add(province_name, _province_label(area.get("tinh")))
        add(district_name, xa)
        add(address_name, dia_chi)

    # --- CHỦ HỒ SƠ (subject) ---
    owner_name = _text(values.get("ChuHoSo_HoTen"))
    owner_is_tc = _is_to_chuc(values.get("ChuHoSo_LoaiChuThe"), owner_name)

    # --- NGƯỜI NỘP ---
    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_is_tc = _is_to_chuc(values.get("NguoiNop_LoaiDoiTuong"), nop_name)
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    nop_mst = _identity(values.get("NguoiNop_MaSoThue"))
    nop_area = _area(values.get("NguoiNop_DiaChi"))

    if not owner_name:
        warnings.append("Thiếu tên chủ hồ sơ (bên nhận chuyển nhượng/chủ đăng ký).")

    # ỦY QUYỀN nếu người nộp KHÁC chủ hồ sơ; TỰ NỘP nếu trùng (hoặc thiếu người nộp).
    is_uy_quyen = bool(nop_name and owner_name and _fold(nop_name) != _fold(owner_name))

    # --- Chủ hồ sơ (luôn điền) ---
    add("data[ownerFullname]", owner_name)
    if owner_is_tc:
        add("data[organization]", owner_name)
    if owner_name:
        add("data[noidungyeucaugiaiquyet]", f"{owner_name} ĐỀ NGHỊ GIẢI QUYẾT {_PROC_TITLE}")

    if is_uy_quyen:
        # === ỦY QUYỀN: chủ hồ sơ ≠ người nộp → BỎ TÍCH, điền cả 2 vai. ===
        add("data[isOwnerDossier]", False)
        add("data[fullname]", nop_name)
        add("data[birthday]", _date(values.get("NguoiNop_NgaySinh")))
        add("data[gender]", _text(values.get("NguoiNop_GioiTinh")))
        add("data[identityNumber]", nop_id)
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap")))
        add_area("data[province]", "data[district]", "data[address]", nop_area)
        add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")))
        add("data[email]", _text(values.get("NguoiNop_Email")))
        add("data[chonDoiTuong]", "Tổ chức" if nop_is_tc else "Cá nhân")
        if nop_is_tc:
            add("data[taxCode]", nop_mst)
    else:
        # === TỰ NỘP: người nộp = chủ hồ sơ → TICH, điền phần người nộp bằng chính chủ hồ sơ. ===
        add("data[isOwnerDossier]", True)
        add("data[fullname]", nop_name or owner_name)
        add("data[birthday]", _date(values.get("NguoiNop_NgaySinh")))
        add("data[gender]", _text(values.get("NguoiNop_GioiTinh")))
        add("data[identityNumber]", nop_id)
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap")))
        add_area("data[province]", "data[district]", "data[address]", nop_area)
        add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")))
        add("data[email]", _text(values.get("NguoiNop_Email")))
        add("data[chonDoiTuong]", "Tổ chức" if (nop_is_tc or owner_is_tc) else "Cá nhân")
        if nop_is_tc or owner_is_tc:
            add("data[taxCode]", nop_mst)

    return out, warnings
