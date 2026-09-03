"""Map compact source facts → Form.io data[...] fields cho "Đính chính GCN đã cấp lần đầu có sai sót"
(cổng Đà Nẵng). Field-key contact block Y HỆT #110; thêm Phần II thửa đất + nội dung đính chính.

HAI vai trong 1 panel:
- CHỦ HỒ SƠ (người đề nghị đính chính) → data[ownerFullname] (+ data[organization] khi tổ chức).
- NGƯỜI NỘP → data[fullname]/birthday/.../province/district/address, data[chonDoiTuong], data[taxCode].
- data[isOwnerDossier]: True khi chủ = người nộp (tự nộp — mặc định); False khi ỦY QUYỀN (điền cả 2).
- data[noidungyeucaugiaiquyet] = NỘI DUNG ĐÍNH CHÍNH (chép mục 2 Đơn Mẫu 18).
- Phần II: data[diaChiThuaDat]/SoToBanDo/SoThuaDat + province2/district2/nation2 (thửa đất trên GCN).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.dinh_chinh_gcn_da_cap_da_nang.process.schema import UI_COMP_BY_NAME


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
    # Chuẩn hóa phường/xã sau sáp nhập (vd "Nam Dương" → "Phường Hải Châu") để khớp SELECT trên form.
    # ⚠ remap_area build key bằng tỉnh CÓ prefix ("thanh pho da nang") ≠ bảng "da nang" → TP trực thuộc
    # TW không khớp; strip prefix tỉnh TRƯỚC khi remap, _province_label gắn lại "Thành phố" sau.
    if not out:
        return None
    if out.get("tinh"):
        out["tinh"] = _strip_admin_prefix(out["tinh"])
    return remap_area(out, allow_diachi_fallback=True)


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

    # --- CHỦ HỒ SƠ (người đề nghị đính chính) ---
    owner_name = _text(values.get("ChuHoSo_HoTen"))
    owner_is_tc = _is_to_chuc(values.get("ChuHoSo_LoaiChuThe"), owner_name)
    noi_dung_dinh_chinh = _text(values.get("NoiDungDinhChinh"))

    # --- NGƯỜI NỘP ---
    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_is_tc = _is_to_chuc(values.get("NguoiNop_LoaiDoiTuong"), nop_name)
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    nop_mst = _identity(values.get("NguoiNop_MaSoThue"))
    nop_area = _area(values.get("NguoiNop_DiaChi"))

    if not owner_name:
        warnings.append("Thiếu tên chủ hồ sơ (người đề nghị đính chính).")
    if not noi_dung_dinh_chinh:
        warnings.append("Thiếu nội dung đính chính (mục 2 Đơn Mẫu 18).")

    # ỦY QUYỀN nếu người nộp KHÁC chủ hồ sơ; TỰ NỘP nếu trùng (hoặc thiếu người nộp).
    is_uy_quyen = bool(nop_name and owner_name and _fold(nop_name) != _fold(owner_name))

    # --- Chủ hồ sơ (luôn điền) ---
    add("data[ownerFullname]", owner_name)
    if owner_is_tc:
        add("data[organization]", owner_name)
    # Nội dung yêu cầu = NỘI DUNG ĐÍNH CHÍNH (chép mục 2 Đơn Mẫu 18), KHÔNG ghép "ĐỀ NGHỊ GIẢI QUYẾT".
    add("data[noidungyeucaugiaiquyet]", noi_dung_dinh_chinh)

    # --- Phần II: thửa đất/công trình được đính chính (lấy ở GCN) ---
    thua_dat_area = _area(values.get("ThuaDat_DiaChi"))
    if thua_dat_area:
        add("data[nation2]", "Việt Nam")
        add("data[province2]", _province_label(thua_dat_area.get("tinh")))
        add("data[district2]", _commune_label(thua_dat_area.get("xa")))
        add("data[diaChiThuaDat]", _text(values.get("ThuaDat_DiaChi")))
    add("data[SoToBanDo]", _text(values.get("ThuaDat_SoTo")))
    add("data[SoThuaDat]", _text(values.get("ThuaDat_SoThua")))

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
        # === TỰ NỘP (mặc định): người nộp = chủ hồ sơ → TICH, điền nhân thân bằng chính chủ hồ sơ. ===
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
