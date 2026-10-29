"""Map compact source facts → Form.io data[...] fields cho "Đăng ký biến động 1.013980" (cổng Đà Nẵng).

Phần I — 1 panel, HAI vai:
- CHỦ HỒ SƠ → data[ownerFullname]; data[chonDoiTuong] theo LOẠI CHỦ HỒ SƠ (mapping: chủ là doanh nghiệp thì
  "Tổ chức" dù người nộp là cá nhân được ủy quyền) + data[taxCode] (MST, ô chỉ hiện khi chọn "Tổ chức").
- NGƯỜI NỘP → data[fullname]/birthday/gender/identityNumber/identityDate/identityAgency và nhóm địa chỉ
  data[nation]/province/district/address = nơi cư trú CỦA NGƯỜI NỘP (mapping), tự nộp thì = chủ hồ sơ.
- data[isOwnerDossier]: True khi chủ hồ sơ cá nhân tự nộp; False khi ủy quyền hoặc chủ tổ chức chưa rõ người nộp.
- data[noidungyeucaugiaiquyet] = mục 2 Đơn; data[phoneNumber] = SĐT liên hệ của hồ sơ; data[note] = đơn cam kết.

Nhân thân người nộp — 3 nhánh như dang_ky_bien_dong_dat_dai_da_nang:
1. ỦY QUYỀN (cá nhân KHÁC chủ hồ sơ, có số CCCD) → điền cả 2 vai.
2. TỰ NỘP (chủ hồ sơ CÁ NHÂN) → tích isOwnerDossier, nhân thân = chủ hồ sơ.
3. CHỦ TỔ CHỨC không có ủy quyền-kèm-CCCD → để trống nhân thân người nộp, không đoán người đại diện pháp luật.

Phần II — thửa đất: data[diaChiThuaDat] ghép lại từ địa chỉ ĐÃ quy đổi (địa danh mới) + data[SoToBanDo]/
[SoThuaDat] + data[nation2]/[province2]/[district2].
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.locations.catalog import ward_name_matches
from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.dang_ky_bien_dong_thoa_thuan_thanh_vien_ho_gia_dinh_da_nang.process.schema import UI_COMP_BY_NAME


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
            value.get("chiTietDuoiXa") or value.get("diaChi") or value.get("chiTiet"),
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
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue", "bac ninh"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {bare}"


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


# "Tổ 11 Hòa Khê" — tên đứng SAU số tổ/thôn là PHƯỜNG/XÃ CŨ (địa chỉ cũ 4 cấp viết trống tiền tố).
_UNIT_THEN_WARD = re.compile(
    r"^(?P<unit>(?:tổ|tổ dân phố|thôn|khối|khu phố|xóm|ấp)\s*\d+[a-z]?)\s+(?P<ward>[^\d,;]{3,})$", re.IGNORECASE
)
_HAS_WARD_TYPE = re.compile(r"^(phường|xã|thị trấn|đặc khu)\s", re.IGNORECASE)


def _fix_old_four_level(out: dict) -> dict:
    """LLM hay đọc "Tổ 11 Hòa Khê, Thanh Khê, Đà Nẵng" thành xa="Thanh Khê" (QUẬN cũ, trùng tên phường mới)
    + chi tiết "Tổ 11 Hòa Khê" dù prompt đã dặn. Chi tiết dạng "<tổ/thôn> <số> <tên>" mà xa là tên trơn không
    tiền tố → tên sau số tổ mới là phường/xã; giữ địa chỉ gốc để dùng lại nếu phường cũ không quy đổi được."""
    match = _UNIT_THEN_WARD.match(" ".join(str(out.get("diaChi") or "").split()))
    xa = " ".join(str(out.get("xa") or "").split())
    if not match or not xa or _HAS_WARD_TYPE.match(xa):
        return out
    return {**out, "xa": match.group("ward").strip(), "diaChi": match.group("unit"), "diaChiGoc": match.group(0)}


def _area(value: Any) -> dict | None:
    if isinstance(value, str):
        out = _parse_area_text(value)
    elif isinstance(value, dict):
        out = {
            "quocGia": value.get("quocGia") or value.get("quoc_gia") or "Việt Nam",
            "tinh": value.get("tinh") or value.get("tinhThanh") or "",
            "xa": value.get("xa") or value.get("phuong") or value.get("phường") or "",
            "diaChi": (value.get("chiTietDuoiXa") or value.get("diaChi") or value.get("dia_chi")
                       or value.get("chiTiet") or ""),
        }
        out = out if any(v for k, v in out.items() if k != "quocGia") else None
    else:
        return None
    if not out:
        return None
    out = _fix_old_four_level(out)
    # remap_area tra khoá theo tỉnh KHÔNG tiền tố ("da nang"): bỏ "Thành phố" trước, _province_label gắn lại sau.
    if out.get("tinh"):
        out["tinh"] = _strip_admin_prefix(out["tinh"])
    return remap_area(out, allow_diachi_fallback=True)


def _catalog_ward(area: dict | None) -> tuple[str | None, str | None]:
    """(tên phường/xã theo danh mục hiện hành, tên gốc KHÔNG chọn được).

    Giấy tờ cũ ghi phường đã giải thể mà bảng remap chưa có (vd một phường cũ của quận Thanh Khê) thì ô chọn
    trên cổng không có option đó — điền vào chỉ để extension báo không tìm thấy. Trả tên gốc để cảnh báo.
    Tỉnh ngoài danh mục thì giữ nguyên tên giấy tờ ghi.
    """
    xa = _text((area or {}).get("xa"))
    if not xa:
        return None, None
    province, found = ward_name_matches(_text(area.get("tinh")), xa)
    if province is None:
        return xa, None
    if len(found) == 1:
        return found[0], None
    return None, xa


def _area_text(area: dict | None) -> str | None:
    if not area:
        return None
    parts = [_text(area.get("diaChi")), _text(area.get("xa")), _province_label(area.get("tinh"))]
    return ", ".join(p for p in parts if p) or None


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or None


def _gender_from_identity(identity: str | None) -> str | None:
    """Chữ số thứ 4 của số định danh 12 số mã hóa thế kỷ + giới tính: chẵn → Nam, lẻ → Nữ (TT 59/2021/TT-BCA).

    Hồ sơ đất đai hay không kèm ảnh CCCD, chỉ có số CCCD trên giấy ủy quyền → đây là nguồn giới tính còn lại.
    """
    if not identity or len(identity) != 12:
        return None
    return "Nam" if int(identity[3]) % 2 == 0 else "Nữ"


def _gender(value: Any) -> str | None:
    f = _fold(value)
    if f in {"nam", "ong", "male"}:
        return "Nam"
    if f in {"nu", "ba", "female"}:
        return "Nữ"
    return None


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


def _parcel_number(value: Any) -> str | None:
    """'tờ bản đồ số 275' / 'Thửa 173' → '275' / '173'; giữ số kèm chữ ('12a') nhưng bỏ nhãn đứng trước."""
    text = _text(value)
    if not text:
        return None
    m = re.search(r"\d+[A-Za-z]?(?:[/-]\d+[A-Za-z]?)?", text)
    return m.group(0) if m else None


_ORG_MARKERS = ("cong ty", "doanh nghiep", "hop tac xa", "htx", "cty", "co phan", "tnhh", "co quan",
                "xi nghiep", "tap doan", "chi nhanh", "ngan hang", "uy ban", "ubnd", "trung tam", "ban quan ly")


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
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    def add_area(area: dict | None) -> None:
        if not area:
            return
        ward, stale = _catalog_ward(area)
        add("data[nation]", "Việt Nam")
        add("data[province]", _province_label(area.get("tinh")))
        add("data[district]", ward)
        # Phường cũ không quy đổi được → ô Phường để trống nên giữ tên cũ trong địa chỉ chi tiết cho khỏi mất.
        add("data[address]", _text(area.get("diaChiGoc") if stale else area.get("diaChi")) or _text(area.get("diaChi")))
        if stale:
            warnings.append(f"Phường/xã nơi cư trú người nộp trên giấy tờ là '{stale}' — không có trong danh mục "
                            "phường/xã hiện hành (địa danh cũ), cần chọn tay theo CCCD.")

    # --- CHỦ HỒ SƠ ---
    owner_name = _text(values.get("ChuHoSo_HoTen"))
    owner_is_tc = _is_to_chuc(values.get("ChuHoSo_LoaiChuThe"), owner_name)
    owner_id = _identity(values.get("ChuHoSo_SoDinhDanh"))
    owner_area = _area(values.get("ChuHoSo_DiaChi"))
    noi_dung = _text(values.get("NoiDungBienDong"))

    # --- NGƯỜI NỘP ---
    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    nop_area = _area(values.get("NguoiNop_DiaChi"))

    is_uy_quyen = bool(nop_name and owner_name and _fold(nop_name) != _fold(owner_name))
    person_is_uy_quyen = is_uy_quyen and bool(nop_id)

    # --- Chủ hồ sơ + nội dung (luôn điền) ---
    if not owner_name:
        warnings.append("Thiếu tên chủ hồ sơ (mục 1 Đơn đăng ký biến động).")
    add("data[ownerFullname]", owner_name)
    if noi_dung:
        add("data[noidungyeucaugiaiquyet]", noi_dung)
    else:
        warnings.append("Thiếu mục '2. Nội dung biến động' trong Đơn — ô Nội dung yêu cầu giải quyết (*) để trống.")
    add("data[note]", _text(values.get("GhiChu")))
    if owner_name:
        add("data[chonDoiTuong]", "Tổ chức" if owner_is_tc else "Cá nhân")
    if owner_is_tc:
        add("data[taxCode]", owner_id)

    phone = _phone(values.get("DienThoaiLienHe"))
    add("data[phoneNumber]", phone)
    if not phone:
        warnings.append("Không thấy số điện thoại liên hệ trong hồ sơ — ô Số điện thoại (*) cần nhập tay.")

    def fill_nguoi_nop(area: dict | None) -> None:
        add("data[birthday]", _date(values.get("NguoiNop_NgaySinh")))
        add("data[gender]", _gender(values.get("NguoiNop_GioiTinh")) or _gender_from_identity(nop_id))
        add("data[identityNumber]", nop_id)
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
        add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCap")))
        add("data[email]", _text(values.get("NguoiNop_Email")))
        add_area(area)
        if "data[birthday]" not in seen:
            warnings.append("Hồ sơ không ghi ngày sinh người nộp — ô Ngày sinh (*) cổng điền sẵn theo tài khoản đăng "
                            "nhập, cần đối chiếu CCCD người nộp.")
        if not area or not _text(area.get("xa")):
            warnings.append("Hồ sơ không ghi Phường/Xã nơi cư trú của người nộp — chọn tay theo CCCD.")

    if person_is_uy_quyen:
        # ỦY QUYỀN: chủ hồ sơ ≠ người nộp → BỎ TÍCH, điền cả 2 vai; địa chỉ = nơi cư trú của người nộp.
        add("data[isOwnerDossier]", False)
        add("data[fullname]", nop_name)
        fill_nguoi_nop(nop_area)
    elif owner_is_tc:
        # CHỦ TỔ CHỨC không có người được ủy quyền kèm CCCD → để trống nhân thân người nộp.
        add("data[isOwnerDossier]", False)
        warnings.append("Chủ hồ sơ là tổ chức nhưng không có giấy ủy quyền kèm CCCD người đi nộp — để trống thông "
                        "tin người nộp, cán bộ nhập tay.")
    else:
        # TỰ NỘP: chủ hồ sơ cá nhân = người nộp.
        add("data[isOwnerDossier]", True)
        add("data[fullname]", nop_name or owner_name)
        fill_nguoi_nop(nop_area or owner_area)

    # --- Phần II: thửa đất ---
    parcel_area = _area(values.get("ThuaDat_DiaChi"))
    if parcel_area:
        parcel_ward, parcel_stale = _catalog_ward(parcel_area)
        if parcel_ward:
            parcel_area = {**parcel_area, "xa": parcel_ward}
        add("data[nation2]", "Việt Nam")
        add("data[province2]", _province_label(parcel_area.get("tinh")))
        add("data[district2]", parcel_ward)
        if parcel_stale:
            warnings.append(f"Phường/xã thửa đất trên giấy tờ là '{parcel_stale}' — không có trong danh mục hiện "
                            "hành, cần chọn tay theo trang biến động của Giấy chứng nhận.")
    add("data[diaChiThuaDat]", _area_text(parcel_area) or _text(values.get("ThuaDat_DiaChi")))
    add("data[SoToBanDo]", _parcel_number(values.get("ThuaDat_SoTo")))
    add("data[SoThuaDat]", _parcel_number(values.get("ThuaDat_SoThua")))

    return out, warnings
