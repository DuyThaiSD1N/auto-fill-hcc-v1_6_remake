"""Map compact source facts → Form.io data[...] fields cho "Đăng ký biến động QSDĐ..." (cổng Đà Nẵng).

HAI vai trong 1 panel (form CHỈ có 1 khối "Người nộp hồ sơ" + tên chủ hồ sơ ở trên):
- CHỦ HỒ SƠ (subject) → data[ownerFullname] (+ data[organization] khi tổ chức).
- NHÂN THÂN người nộp  → data[fullname]/birthday/gender/identityNumber/identityDate/identityAgency,
  data[chonDoiTuong] (loại người nộp).
- THÔNG TIN LIÊN HỆ CỦA HỒ SƠ (ưu tiên CHỦ HỒ SƠ): data[phoneNumber], data[province]/district/address,
  data[taxCode] = "Mã định danh tổ chức, doanh nghiệp" (MST/mã số DN của chủ hồ sơ khi là tổ chức).
- data[isOwnerDossier]: True khi chủ hồ sơ = người nộp (tự nộp); False khi ỦY QUYỀN hoặc tổ chức-để-trống.
- data[noidungyeucaugiaiquyet] = Nội dung biến động LẤY TỪ ĐƠN Mẫu 18 (mục 2) — KHÔNG mặc định.

Nhân thân người nộp — 3 nhánh:
1. ỦY QUYỀN (người nộp là cá nhân KHÁC chủ hồ sơ, có CCCD từ giấy ủy quyền) → điền cả 2 vai.
2. TỰ NỘP (chủ hồ sơ CÁ NHÂN = người nộp) → tick isOwnerDossier, điền nhân thân = chủ hồ sơ.
3. CHỦ HỒ SƠ TỔ CHỨC không có ủy quyền-kèm-CCCD → ĐỂ TRỐNG nhân thân người nộp (chỉ điền chủ hồ sơ +
   liên hệ); KHÔNG suy đoán người đại diện pháp luật/người ký đơn (chốt user 05/09/2026).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.dang_ky_bien_dong_dat_dai_da_nang.process.schema import UI_COMP_BY_NAME


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
        add(province_name, _province_label(area.get("tinh")))
        add(district_name, _commune_label(area.get("xa")))
        add(address_name, _text(area.get("diaChi")))

    # --- CHỦ HỒ SƠ (subject) — nguồn cho thông tin liên hệ của hồ sơ (SĐT/địa chỉ/mã số DN) ---
    owner_name = _text(values.get("ChuHoSo_HoTen"))
    owner_is_tc = _is_to_chuc(values.get("ChuHoSo_LoaiChuThe"), owner_name)
    owner_id = _identity(values.get("ChuHoSo_SoDinhDanh"))   # tổ chức=mã số DN/MST, cá nhân=CCCD.
    owner_area = _area(values.get("ChuHoSo_DiaChi"))
    owner_phone = _phone(values.get("ChuHoSo_DienThoai"))

    # --- NGƯỜI NỘP (nhân thân người trực tiếp nộp; có thể ủy quyền) ---
    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_is_tc = _is_to_chuc(values.get("NguoiNop_LoaiDoiTuong"), nop_name)
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    nop_mst = _identity(values.get("NguoiNop_MaSoThue"))
    nop_area = _area(values.get("NguoiNop_DiaChi"))
    nop_phone = _phone(values.get("NguoiNop_DienThoai"))

    # Nội dung yêu cầu giải quyết: LẤY TỪ ĐƠN (mục 2 "Nội dung biến động"), KHÔNG mặc định/ghép cứng.
    noi_dung = _text(values.get("NoiDungBienDong"))

    if not owner_name:
        warnings.append("Thiếu tên chủ hồ sơ (bên nhận chuyển nhượng/chủ đăng ký).")

    # ỦY QUYỀN nếu người nộp là 1 CÁ NHÂN KHÁC chủ hồ sơ và CÓ CCCD (từ giấy ủy quyền).
    is_uy_quyen = bool(nop_name and owner_name and _fold(nop_name) != _fold(owner_name))
    person_is_uy_quyen = is_uy_quyen and bool(nop_id)

    # --- Chủ hồ sơ (luôn điền) ---
    add("data[ownerFullname]", owner_name)
    if owner_is_tc:
        add("data[organization]", owner_name)
    if noi_dung:
        add("data[noidungyeucaugiaiquyet]", noi_dung)
    elif owner_name:
        warnings.append("Thiếu 'Nội dung biến động' trong Đơn Mẫu 18 — không điền Nội dung yêu cầu giải quyết.")

    def _fill_nguoi_nop() -> None:
        add("data[birthday]", _date(values.get("NguoiNop_NgaySinh")))
        add("data[gender]", _text(values.get("NguoiNop_GioiTinh")))
        add("data[identityNumber]", nop_id)
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap")))

    # --- Nhân thân người nộp — 3 nhánh ---
    if owner_is_tc and not person_is_uy_quyen:
        # === CHỦ HỒ SƠ TỔ CHỨC, KHÔNG có người được ủy quyền (kèm CCCD) → ĐỂ TRỐNG nhân thân người nộp.
        # Không suy đoán người đại diện pháp luật/người ký đơn; user tự nhập. Chỉ điền chủ hồ sơ + liên hệ. ===
        add("data[isOwnerDossier]", False)
        if nop_name or nop_id:
            warnings.append("Chủ hồ sơ là tổ chức, không có giấy ủy quyền kèm CCCD → để trống nhân thân người nộp (tránh ghép chéo danh tính).")
    elif person_is_uy_quyen:
        # === ỦY QUYỀN: chủ hồ sơ ≠ người nộp → BỎ TÍCH, điền cả 2 vai. ===
        add("data[isOwnerDossier]", False)
        add("data[fullname]", nop_name)
        add("data[chonDoiTuong]", "Tổ chức" if nop_is_tc else "Cá nhân")
        _fill_nguoi_nop()
    else:
        # === TỰ NỘP: người nộp = chủ hồ sơ (cá nhân) → TICH, điền nhân thân bằng chính chủ hồ sơ. ===
        add("data[isOwnerDossier]", True)
        add("data[fullname]", nop_name or owner_name)
        add("data[chonDoiTuong]", "Tổ chức" if (nop_is_tc or owner_is_tc) else "Cá nhân")
        _fill_nguoi_nop()

    # --- Thông tin liên hệ của HỒ SƠ: ưu tiên CHỦ HỒ SƠ (SĐT + địa chỉ), fallback người nộp ---
    add("data[phoneNumber]", owner_phone or nop_phone)
    add_area("data[province]", "data[district]", "data[address]", owner_area or nop_area)
    add("data[email]", _text(values.get("NguoiNop_Email")))
    # Mã định danh tổ chức, doanh nghiệp: MST/mã số DN của chủ hồ sơ (nếu tổ chức); nếu không thì của người nộp.
    if owner_is_tc:
        add("data[taxCode]", owner_id)
    elif nop_is_tc:
        add("data[taxCode]", nop_mst)

    return out, warnings
