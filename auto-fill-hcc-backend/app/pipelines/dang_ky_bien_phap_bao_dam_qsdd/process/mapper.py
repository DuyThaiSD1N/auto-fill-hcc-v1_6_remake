"""Map compact source facts → Form.io data[...] (cổng Đà Nẵng) cho thủ tục "Đăng ký biện pháp bảo đảm
bằng QSDĐ, tài sản gắn liền với đất".

Một chủ thể = NGƯỜI YÊU CẦU ĐĂNG KÝ (= chủ hồ sơ = người nộp). Cá nhân → nhân thân; Tổ chức → tên +
mã số thuế. TICH data[isOwnerDossier] (chủ hồ sơ = người nộp; ô mặc định chưa tick).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.dang_ky_bien_phap_bao_dam_qsdd.process.schema import UI_COMP_BY_NAME


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
    if len(parts) >= 3:
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

    residence = _area(values.get("ChuThe_DiaChi"))
    phone = _phone(values.get("ChuThe_DienThoai"))
    email = _text(values.get("ChuThe_Email"))
    id_date = _date(values.get("ChuThe_NgayCap"))
    issuer = _issuer(values.get("ChuThe_NoiCap"))

    def add_address(area) -> None:
        if not area:
            return
        add("data[province]", _province_label(area.get("tinh")))
        add("data[district]", _commune_label(area.get("xa")))
        add("data[address]", _text(area.get("diaChi")))

    # Xác định cá nhân / tổ chức.
    loai = _fold(values.get("ChuThe_LoaiChuThe"))
    ten_tc = _text(values.get("ChuThe_TenToChuc"))
    mst = _identity(values.get("ChuThe_MaSoThue"))
    ho_ten = _text(values.get("ChuThe_HoTen"))
    identity = _identity(values.get("ChuThe_SoDinhDanh"))
    is_to_chuc = ("chuc" in loai) or (bool(ten_tc or mst) and not (ho_ten or identity))

    if is_to_chuc:
        # === TỔ CHỨC (vd ngân hàng) === chủ hồ sơ tổ chức → data[organization] (KHÔNG dùng ownerFullname
        # là ô của cá nhân). Người nộp (fullname) do cổng tự đổ từ tài khoản; tích isOwnerDossier để copy.
        add("data[chonDoiTuong]", "Tổ chức")
        add("data[organization]", ten_tc)
        add("data[taxCode]", mst)
        add("data[identityNumber]", mst)
        add("data[nation]", "Việt Nam")
        add_address(residence)
        add("data[phoneNumber]", phone)
        add("data[email]", email)
        if not ten_tc:
            warnings.append("Thiếu tên tổ chức người yêu cầu đăng ký.")
    else:
        # === CÁ NHÂN ===
        add("data[chonDoiTuong]", "Cá nhân")
        add("data[fullname]", ho_ten)
        add("data[ownerFullname]", ho_ten)
        add("data[birthday]", _date(values.get("ChuThe_NgaySinh")))
        add("data[gender]", _text(values.get("ChuThe_GioiTinh")))
        add("data[identityNumber]", identity)
        add("data[identityDate]", id_date)
        add("data[identityAgency]", issuer)
        add("data[nation]", "Việt Nam")
        add_address(residence)
        add("data[phoneNumber]", phone)
        add("data[email]", email)
        if not ho_ten:
            warnings.append("Thiếu họ tên người yêu cầu đăng ký (cá nhân) từ CCCD/Phiếu Mẫu 01a.")

    # Chủ hồ sơ = người nộp → TICH (ô mặc định CHƯA tick).
    add("data[isOwnerDossier]", True)

    return out, warnings
