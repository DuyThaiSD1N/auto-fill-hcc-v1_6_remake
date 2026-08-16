"""Map compact source facts to standard DOM UI fields for land correction."""

import re
import unicodedata

from app.pipelines.dinh_chinh_sai_sot.process.schema import UI_ALIASES, UI_COMP_BY_NAME

from app.pipelines._shared.compact_agent.issuer import default_issuer


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _plain(value) -> str | None:
    """Chuẩn hóa 1 chuỗi (bỏ xuống dòng/khoảng trắng thừa)."""
    if not isinstance(value, str):
        return None
    return " ".join(value.replace("\n", " ").split()).strip(" :;,-") or None


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _strip_admin_prefix(value) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(tỉnh|thành phố|tp\.?|xã|phường|thị trấn|tt\.?|huyện|quận|thị xã)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _province_label(value) -> str | None:
    text = _plain(value)
    if not text:
        return None
    folded = _fold(text)
    if folded.startswith(("tinh ", "thanh pho ", "tp ")):
        return text
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "tp ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {_strip_admin_prefix(text)}"


def _area(value) -> dict | None:
    """NguoiNop_NoiCuTru thường là object {quocGia,tinh,xa,diaChi}; hỗ trợ cả chuỗi rơi vào diaChi."""
    if isinstance(value, str):
        text = _plain(value)
        return {"tinh": "", "xa": "", "diaChi": text} if text else None
    if not isinstance(value, dict):
        return None
    out = {
        "tinh": value.get("tinh") or value.get("tỉnh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("xã") or value.get("phuong") or value.get("phường") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    return out if any(out.values()) else None


def _full_address(area: dict) -> str | None:
    parts = [_plain(area.get("diaChi")), _plain(area.get("xa")), _province_label(area.get("tinh"))]
    return ", ".join(p for p in parts if p) or None


def _phone(value) -> str | None:
    text = _plain(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if text.lstrip().startswith("+84") and digits.startswith("84"):
        digits = "0" + digits[2:]
    return digits if 9 <= len(digits) <= 11 else None


def _normalize_serial(prefix: str, number: str) -> str | None:
    prefix = re.sub(r"[^A-Z]", "", (prefix or "").upper())
    number = re.sub(r"\D", "", number or "")
    if not prefix or not number:
        return None
    if prefix.startswith("SO") and len(prefix) > 2:
        prefix = prefix[2:]
    elif prefix.startswith("S") and len(prefix) > 1:
        prefix = prefix[1:]
    if not 1 <= len(prefix) <= 3 or not 5 <= len(number) <= 8:
        return None
    return f"{prefix} {number}"


def _serial(value):
    if not isinstance(value, str):
        return None
    text = re.split(r"\(|số\s+vào\s+sổ|so\s+vao\s+so", value, maxsplit=1, flags=re.IGNORECASE)[0]
    text = " ".join(text.replace("\n", " ").split()).strip(" :;,-")
    match = re.search(r"\b([A-Z]{1,5})\s*[-.]?\s*(\d{5,8})\b", text.upper())
    if match:
        serial = _normalize_serial(match.group(1), match.group(2))
        if serial:
            return serial
    return text or None


def _issuer(value):
    if not isinstance(value, str):
        return None
    text = " ".join(value.replace("\n", " ").split()).strip(" :;,-")
    text = re.sub(r"^TM\.?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bCHỦ\s*TỊCH\b.*$", "", text, flags=re.IGNORECASE).strip(" :;,-")
    text = re.sub(r"ỦY\s*BAN\s*NHÂN\s*DÂN", "UBND", text, flags=re.IGNORECASE)
    return text or None


def enrich(fields: list[dict]) -> list[dict]:
    """Derive deterministic UI fields from compact source facts."""
    values = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if name in UI_ALIASES:
            field["aliases"] = UI_ALIASES[name]
        out.append(field)
        seen.add(name)

    has_applicant = bool(values.get("NguoiNop_SoDinhDanh") or values.get("NguoiNop_HoTen"))
    has_gcn = bool(values.get("Gcn_SoPhatHanh") or values.get("Gcn_NgayCap") or values.get("Gcn_CoQuanCap"))

    if has_applicant:
        identity_no = values.get("NguoiNop_SoDinhDanh")
        issue_date = values.get("NguoiNop_NgayCapGiayTo")
        issuer = values.get("NguoiNop_NoiCapGiayTo") or default_issuer(issue_date)
        add("CongDan_tenCongDan", values.get("NguoiNop_HoTen"))
        add("CongDan_ngaySinhCongDan", values.get("NguoiNop_NgaySinh"))
        add("CongDan_gioiTinhCongDan", values.get("NguoiNop_GioiTinh"))
        add("CongDan_danTocCongDan", values.get("NguoiNop_DanToc"))
        add("CongDan_soCmnd", identity_no)
        add("CongDan_ngayCapCmnd", issue_date)
        add("CongDan_noiCapCmnd", issuer)
        add("CongDan_soCCCD", identity_no)

    add("CongDan_maDMQuocGia", "Việt Nam")
    add("CongDan_diaChiNuocNgoai", "Việt Nam")
    add("CongDan_diDong", _phone(values.get("NguoiNop_DienThoai")))

    # Địa chỉ nơi cư trú đã xác định theo vai trò người nộp. eForm Lai Châu 2 cấp: tỉnh → xã + chi tiết.
    residence = _area(values.get("NguoiNop_NoiCuTru"))
    if residence:
        add("CongDan_maTinhThanh", _province_label(residence.get("tinh")))
        add("CongDan_maPhuongXa", _plain(residence.get("xa")))
        add("CongDan_diaChi", _plain(residence.get("diaChi")))
        full = _full_address(residence)
        add("CongDan_diaChiThuongTru", full)
        add("CongDan_noiOHienTai", full)

    if has_gcn:
        add("CongDan_soGCNGP", _serial(values.get("Gcn_SoPhatHanh")))
        add("CongDan_ngayCapGCNGP", values.get("Gcn_NgayCap"))
        add("CongDan_noiCapGCNGP", _issuer(values.get("Gcn_CoQuanCap")))

    return out
