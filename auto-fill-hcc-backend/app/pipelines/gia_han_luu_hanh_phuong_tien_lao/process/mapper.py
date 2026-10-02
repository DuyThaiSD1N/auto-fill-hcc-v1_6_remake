"""Map compact source facts → Form.io data[...] fields cho "Gia hạn thời gian lưu hành tại Việt Nam cho phương
tiện của Lào" (Bộ Xây dựng). Helper chuẩn hoá copy cap_giay_phep_lien_van_viet_lao; mọi key PHẲNG.

Người nộp = người xin gia hạn (cá nhân). Ô người nộp cổng đổ sẵn theo tài khoản đăng nhập (thường là cán bộ)
→ giấy tờ không có dữ liệu thì xoá trắng ô input/date thay vì để nguyên giá trị tài khoản.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.gia_han_luu_hanh_phuong_tien_lao.process.schema import UI_COMP_BY_NAME


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
            value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường"),
            value.get("huyen") or value.get("quanHuyen"),
            value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh"),
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
        return text
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "tp ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {_strip_admin_prefix(text)}"


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
        "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    return out if any(out.values()) else None


def _identity(value: Any) -> str | None:
    """Số CCCD (12) / CMND (9) / MST (10, có mã chi nhánh thì 13). Độ dài khác → không phải số định danh
    (vd 'Số (Number)' của Giấy chứng nhận đăng ký xe bị LLM đọc nhầm) → bỏ."""
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits if len(digits) in (9, 10, 12, 13) else None


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


def _tp(value: Any) -> str | None:
    """Đổi 'Thành phố' → 'TP' cho khớp option web (Kính gửi: 'Sở Xây dựng TP Đà Nẵng'; 'Tại': 'TP Đà Nẵng').
    Tỉnh giữ nguyên 'tỉnh …'. choiceMatches so substring 2 chiều nên phần còn lại tự khớp."""
    text = _text(value)
    if not text:
        return None
    return re.sub(r"\bthành\s*phố\b", "TP", text, flags=re.IGNORECASE)



def _plate(value: Any) -> str | None:
    """Biển số có ký hiệu chữ + dãy số ngắn; dãy CHỈ gồm chữ số dài hơn 8 là mã tem/mã vạch in cạnh nhãn
    'Registration Number' (OCR không đọc được chữ Lào của biển) → bỏ, không điền sai."""
    text = _text(value)
    if not text:
        return None
    compact = re.sub(r"[\s.\-]", "", text)
    return None if compact.isdigit() and len(compact) > 8 else text


def _days(value: Any) -> str | None:
    """Ô "Thời gian gia hạn" nhận SỐ ngày: '10 ngày' → '10'; không có số thì bỏ."""
    m = re.search(r"\d+", _text(value) or "")
    return m.group(0) if m else None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    _ = options
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

    def put(name: str, value) -> None:
        """Ô người nộp: cổng đổ sẵn thông tin tài khoản VNeID (thường là cán bộ) → giấy tờ không có dữ liệu
        thì yêu cầu extension XOÁ TRẮNG ô input/date; ô select giữ nguyên."""
        if value not in (None, "", {}, []):
            add(name, value)
            return
        comp = UI_COMP_BY_NAME.get(name)
        if name in seen or comp not in ("dom-input", "dom-date"):
            return
        out.append({"name": name, "comp": comp, "value": "", "clear": True})
        seen.add(name)

    # --- Người nộp = người xin gia hạn ---
    name = _text(values.get("NguoiNop_HoTen"))
    raw_identity = _text(values.get("NguoiNop_SoDinhDanh"))
    identity = _identity(raw_identity)
    residence = _area(values.get("NguoiNop_ThuongTru")) or {}

    if not name:
        warnings.append("Thiếu họ tên người xin gia hạn từ Giấy đề nghị Mẫu 07.")
    if raw_identity and not identity:
        warnings.append(f"Số định danh đọc được '{raw_identity}' không phải số CCCD/CMND hợp lệ — đã để trống.")
    elif not identity:
        warnings.append("Hồ sơ không có CCCD người xin gia hạn — đã để trống số CCCD, ngày sinh, ngày cấp; vui "
                        "lòng nhập tay.")

    add("data[chonDoiTuong]", "Cá nhân")
    put("data[fullname]", name)
    put("data[birthday]", _date(values.get("NguoiNop_NgaySinh")))
    add("data[gender]", _text(values.get("NguoiNop_GioiTinh")))
    put("data[identityNumber]", identity)
    put("data[identityDate]", _date(values.get("NguoiNop_NgayCapCccd")))
    add("data[identityAgency]", _issuer(values.get("NguoiNop_NoiCapCccd")))
    add("data[nation]", "Việt Nam" if name else None)
    add("data[province]", _province_label(residence.get("tinh")))
    add("data[district]", _text(residence.get("xa")))
    put("data[address]", _text(residence.get("diaChi")))
    put("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")))
    put("data[email]", _text(values.get("NguoiNop_Email")))

    # --- Đề nghị gia hạn ---
    add("data[T_CoQuan]", _tp(values.get("DeNghi_KinhGui")))              # option: "Sở Xây dựng TP Đà Nẵng"
    add("data[LyDoGiaHan]", _text(values.get("DeNghi_LyDo")))
    add("data[ThoiGianNhapCanh]", _date(values.get("DeNghi_ThoiGianNhapCanh")))
    add("data[ThoiGianGiaHan]", _days(values.get("DeNghi_SoNgayGiaHan")))
    plate = _plate(values.get("DeNghi_BienSo"))
    if values.get("DeNghi_BienSo") and not plate:
        warnings.append(f"Biển số đọc được '{_text(values.get('DeNghi_BienSo'))}' là dãy số dài (mã tem), không "
                        "phải biển số — vui lòng nhập tay.")
    add("data[BienSoXeGiaHan]", plate)
    add("data[ThoiGianGiaHanTuNgay]", _date(values.get("DeNghi_TuNgay")))
    add("data[ThoiGianGiaHanDenNgay]", _date(values.get("DeNghi_DenNgay")))
    add("data[tenDiaPhuong]", _province_label(values.get("DeNghi_Tai")))   # option: "Thành phố Đà Nẵng" (đầy đủ)
    add("data[kyTenDongDau]", name)

    if not values.get("DeNghi_ThoiGianNhapCanh"):
        warnings.append("Chưa xác định được thời gian nhập cảnh (trang Record của giấy phép liên vận) — vui "
                        "lòng nhập tay.")
    else:
        # Dấu xuất/nhập cảnh chồng lên nhau, OCR đọc lẫn Arrival/Departure → ngày có thể lệch giữa các lần.
        warnings.append("Thời gian nhập cảnh lấy từ dấu trên trang Record của giấy phép liên vận — cán bộ đối "
                        "chiếu lại dấu nhập cảnh mới nhất.")
    return out, warnings
