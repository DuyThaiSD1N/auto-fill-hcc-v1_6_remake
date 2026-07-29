"""Map compact source facts to standard DOM UI fields for land registration."""

import re

from app.pipelines.dang_ky_dat_dai.process.schema import UI_ALIASES, UI_COMP_BY_NAME

from app.pipelines._shared.compact_agent.issuer import default_issuer


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


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

    has_cccd = bool(values.get("Cccd_SoDinhDanh") or values.get("Cccd_HoTen"))
    has_gcn = bool(values.get("Gcn_SoPhatHanh") or values.get("Gcn_NgayCap") or values.get("Gcn_CoQuanCap"))

    if has_cccd:
        identity_no = values.get("Cccd_SoDinhDanh")
        issuer = values.get("Cccd_NoiCap") or default_issuer(values.get("Cccd_NgayCap"))
        add("CongDan_tenCongDan", values.get("Cccd_HoTen"))
        add("CongDan_tenCoQuanToChuc", values.get("Cccd_HoTen"))
        add("CongDan_maSoThueNguoiNop", identity_no)
        add("CongDan_ngaySinhCongDan", values.get("Cccd_NgaySinh"))
        add("CongDan_gioiTinhCongDan", values.get("Cccd_GioiTinh"))
        add("CongDan_danTocCongDan", values.get("Cccd_DanToc"))
        add("CongDan_soCmnd", identity_no)
        add("CongDan_ngayCapCmnd", values.get("Cccd_NgayCap"))
        add("CongDan_noiCapCmnd", issuer)
        add("CongDan_soCCCD", identity_no)

    add("CongDan_maDMQuocGia", "Việt Nam")
    add("CongDan_diaChiNuocNgoai", "Việt Nam")

    if has_gcn:
        add("CongDan_soGCNGP", _serial(values.get("Gcn_SoPhatHanh")))
        add("CongDan_ngayCapGCNGP", values.get("Gcn_NgayCap"))
        add("CongDan_noiCapGCNGP", _issuer(values.get("Gcn_CoQuanCap")))

    return out
