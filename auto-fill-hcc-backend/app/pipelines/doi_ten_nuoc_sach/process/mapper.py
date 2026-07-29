"""Map compact source facts to DOM UI fields for water-contract name transfer."""

import re
from typing import Any

from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines.doi_ten_nuoc_sach.process.schema import UI_ALIASES, UI_COMP_BY_NAME


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, str):
        text = " ".join(value.replace("\n", " ").split()).strip(" :;,-")
        return text or None
    if isinstance(value, dict):
        return _full_address(value)
    text = str(value).strip()
    return text or None


def _field(value: Any, *keys: str) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in keys:
        raw = value.get(key)
        if raw not in (None, "", {}, []):
            return _text(raw)
    return None


def _full_address(value: Any) -> str | None:
    if isinstance(value, str):
        return _text(value)
    if not isinstance(value, dict):
        return None
    direct = _field(value, "fullText", "full", "text", "diaChiDayDu")
    if direct:
        return direct
    parts = [
        _field(value, "diaChi", "chiTiet", "thonXom", "soNha"),
        _field(value, "xa", "phuongXa"),
        _field(value, "huyen", "quanHuyen"),
        _field(value, "tinh", "tinhThanh"),
    ]
    return ", ".join(p for p in parts if p) or None


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
    text = re.sub(r"\b(GIÁM\s*ĐỐC|CHỦ\s*TỊCH)\b.*$", "", text, flags=re.IGNORECASE).strip(" :;,-")
    text = re.sub(r"ỦY\s*BAN\s*NHÂN\s*DÂN", "UBND", text, flags=re.IGNORECASE)
    return text or None


def _phone(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    text = text.upper().replace("O", "0").replace("S", "5")
    digits = re.sub(r"\D", "", text)
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    if len(digits) == 10 and digits.startswith("0"):
        return digits
    return None


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    return digits or None


def _capitalize_security_issuer(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = (
        text.lower()
        .replace("ô", "o")
        .replace("ộ", "o")
        .replace("ỏ", "o")
        .replace("ồ", "o")
        .replace("ơ", "o")
        .replace("ờ", "o")
        .replace("ớ", "o")
        .replace("ở", "o")
        .replace("ợ", "o")
    )
    if "bo cong an" in folded or "ministry of public security" in folded:
        return "Bộ Công an"
    return text


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

    que_quan = values.get("Cccd_QueQuan")
    noi_cu_tru = values.get("Cccd_NoiCuTru")
    address_source = que_quan if isinstance(que_quan, dict) and que_quan else noi_cu_tru
    identity_no = _identity(values.get("Cccd_SoDinhDanh"))
    issuer = _capitalize_security_issuer(values.get("Cccd_NoiCap")) or default_issuer(values.get("Cccd_NgayCap"))

    add("CongDan_tenCongDan", values.get("Cccd_HoTen"))
    add("CongDan_tenCoQuanToChuc", values.get("DonDoiTen_TenCoQuanToChuc"))
    add("CongDan_maSoThueNguoiNop", _identity(values.get("DonDoiTen_MaSoThue")))
    add("CongDan_ngaySinhCongDan", values.get("Cccd_NgaySinh"))
    add("CongDan_gioiTinhCongDan", values.get("Cccd_GioiTinh"))
    add("CongDan_danTocCongDan", values.get("Cccd_DanToc") or "Kinh")
    add("CongDan_soCmnd", identity_no)
    add("CongDan_ngayCapCmnd", values.get("Cccd_NgayCap"))
    add("CongDan_noiCapCmnd", issuer)
    add("CongDan_maTinhThanh", _field(address_source, "tinh", "tinhThanh"))
    add("CongDan_maPhuongXa", _field(address_source, "xa", "phuongXa"))
    add("CongDan_diaChi", _field(address_source, "diaChi", "chiTiet", "thonXom", "soNha"))
    add("CongDan_diDong", _phone(values.get("DonDoiTen_SoDienThoai")))

    add("CongDan_maDMQuocGia", "Việt Nam")
    add("CongDan_diaChiNuocNgoai", "Việt Nam")

    add("CongDan_soGCNGP", _serial(values.get("Gcn_SoPhatHanh")))
    add("CongDan_ngayCapGCNGP", values.get("Gcn_NgayCap"))
    add("CongDan_noiCapGCNGP", _issuer(values.get("Gcn_CoQuanCap")))
    add("CongDan_soCCCD", identity_no)
    add(
        "CongDan_noiOHienTai",
        _text(values.get("DonDoiTen_DiaChiHopDong"))
        or _text(values.get("DonDoiTen_DiaChiThuongTru"))
        or _full_address(noi_cu_tru),
    )
    add(
        "CongDan_diaChiThuongTru",
        _text(values.get("DonDoiTen_DiaChiThuongTru")) or _full_address(noi_cu_tru),
    )

    return out
