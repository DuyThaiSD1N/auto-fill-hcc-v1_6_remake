"""Map compact source facts → Form.io data[...] fields cho "Xóa đăng ký phương tiện thủy nội địa".

CHỦ PHƯƠNG TIỆN là subject CHÍNH → điền vào **Block 1** (panel thongTinChung #1). Toggle cá nhân/tổ chức
CHỈ ở **SELECT #1** (`data[chonDoiTuong]` occ=0). **KHÔNG BAO GIỜ đụng SELECT #2 (occ=1) và Block 2**
(fullName/canCuocCongDan/chuPhuongTien2/soDangKy3...) — cổng dùng Block 1 làm khối khai chính:
- Select #1 = Tổ chức → hiện khối "Thông tin doanh nghiệp" #1 → điền organization/maDinhDanh/dongSoHuu/
  province1/district1/address1/phoneNumber1/email1.
- Select #1 = Cá nhân → hiện khối cá nhân Block 1 → điền fullname/birthday/gender/identityNumber/
  identityDate/province/district/address/phoneNumber/email.
Route TẤT ĐỊNH loại đối tượng theo LoaiDoiTuong (có mã định danh tổ chức / tên tổ chức → Tổ chức).
- Phần III (panel1): data[tenPhuongTien]/soDangKy1/SoGiayChungNhan/lyDoCapLai — nơi khai tên PT/số ĐK.
- Phần IV: data[TinTTTe] (địa danh) / data[TDTTK] (ngày) / data[nguoiLamDon].
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.formatting import normalize_date
from app.pipelines.xoa_dang_ky_phuong_tien_thuy.process.schema import UI_COMP_BY_NAME


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
            value.get("diaChi") or value.get("dia_chi") or value.get("chiTiet"),
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
    """Chuẩn hóa 'Tỉnh …' / 'Thành phố …' — bỏ tiền tố cũ rồi phân loại lại."""
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


_ORG_MARKERS = ("cong ty", "doanh nghiep", "hop tac xa", "htx", "cong ty", "cty", "co phan",
                "trach nhiem huu han", "tnhh", "co quan", "xi nghiep", "tap doan", "chi nhanh")


def _is_to_chuc(loai: Any, name: Any, ma_tochuc: Any) -> bool:
    """Route TẤT ĐỊNH: tổ chức nếu LLM báo 'Tổ chức', có mã định danh tổ chức, hoặc tên có từ khóa DN."""
    if _identity(ma_tochuc):
        return True
    if "to chuc" in _fold(loai):
        return True
    if "ca nhan" in _fold(loai):
        return False
    return any(m in _fold(name) for m in _ORG_MARKERS)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int | None]] = set()

    def add(name: str, value, *, occurrence=None) -> None:
        seen_key = (name, occurrence)
        if seen_key in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if occurrence is not None:
            field["occurrence"] = occurrence
        out.append(field)
        seen.add(seen_key)

    def add_area(province_name, district_name, address_name, area, *, occurrence=None) -> None:
        if not area:
            return
        add(province_name, _province_label(area.get("tinh")), occurrence=occurrence)
        add(district_name, _commune_label(area.get("xa")), occurrence=occurrence)
        add(address_name, _text(area.get("diaChi")), occurrence=occurrence)

    # ===== CHỦ PHƯƠNG TIỆN = subject CHÍNH → điền vào Block 1 (panel thongTinChung #1). =====
    # QUAN TRỌNG: toggle cá nhân/tổ chức CHỈ ở SELECT #1 (data[chonDoiTuong] occ=0). Select #2 (occ=1) và
    # toàn bộ Block 2 (fullName/canCuoc/chuPhuongTien2/soDangKy3...) KHÔNG BAO GIỜ điền (cổng dùng Block 1
    # làm khối khai chính; Select #1=Tổ chức hiện khối doanh nghiệp #1, =Cá nhân hiện khối cá nhân Block 1).
    cpt_name = _text(values.get("ChuPhuongTien_HoTen"))
    cpt_ma_tc = _identity(values.get("ChuPhuongTien_MaDinhDanhToChuc"))
    cpt_cccd = _identity(values.get("ChuPhuongTien_SoDinhDanh"))
    cpt_area = _area(values.get("ChuPhuongTien_TruSo"))
    cpt_phone = _phone(values.get("ChuPhuongTien_DienThoai"))
    cpt_email = _text(values.get("ChuPhuongTien_Email"))
    cpt_daidien = _text(values.get("ChuPhuongTien_NguoiDaiDien"))
    cpt_birthday = _date(values.get("ChuPhuongTien_NgaySinh"))
    cpt_gender = _text(values.get("ChuPhuongTien_GioiTinh"))
    cpt_id_date = _date(values.get("ChuPhuongTien_NgayCap"))
    pt_ten = _text(values.get("PhuongTien_Ten"))
    pt_sodk = _text(values.get("PhuongTien_SoDangKy"))

    if not cpt_name:
        warnings.append("Thiếu tên chủ phương tiện từ Đơn/CCCD.")

    is_to_chuc = _is_to_chuc(values.get("ChuPhuongTien_LoaiDoiTuong"), cpt_name, cpt_ma_tc)

    # SELECT #1 (occ=0) — toggle loại đối tượng. Set TRƯỚC để cổng hiện đúng khối.
    add("data[chonDoiTuong]", "Tổ chức" if is_to_chuc else "Cá nhân")

    if is_to_chuc:
        # Khối "Thông tin doanh nghiệp" #1 (hiện khi Select #1 = Tổ chức).
        add("data[organization]", cpt_name)
        add("data[maDinhDanh]", cpt_ma_tc)
        add("data[dongSoHuu]", cpt_daidien)
        add_area("data[province1]", "data[district1]", "data[address1]", cpt_area)
        add("data[phoneNumber1]", cpt_phone)
        add("data[email1]", cpt_email)
    else:
        # Khối cá nhân Block 1 (hiện khi Select #1 = Cá nhân).
        add("data[fullname]", cpt_name)
        add("data[birthday]", cpt_birthday)
        add("data[gender]", cpt_gender)
        add("data[identityNumber]", cpt_cccd)
        add("data[identityDate]", cpt_id_date)
        add_area("data[province]", "data[district]", "data[address]", cpt_area)
        add("data[phoneNumber]", cpt_phone)
        add("data[email]", cpt_email)

    # ===== Phần III: ĐẶC ĐIỂM PHƯƠNG TIỆN (panel1) — nơi khai tên PT/số ĐK chính thức. =====
    add("data[tenPhuongTien]", pt_ten)
    add("data[soDangKy1]", pt_sodk)
    add("data[SoGiayChungNhan]", _text(values.get("PhuongTien_SoGiayChungNhan")))
    add("data[lyDoCapLai]", _text(values.get("PhuongTien_LyDoXoa")))

    # ===== Phần IV: NƠI LẬP ĐƠN =====
    dia_danh = _text(values.get("ToKhai_DiaDanh")) or (cpt_area.get("tinh") if cpt_area else None)
    add("data[TinTTTe]", _province_label(dia_danh) if dia_danh else None)
    add("data[TDTTK]", _date(values.get("ToKhai_NgayLap")))
    add("data[nguoiLamDon]", _text(values.get("ToKhai_NguoiLamDon")) or cpt_name)

    return out, warnings
