"""Map compact source facts to standard DOM UI fields for procedure 1.013978."""

import re

from app.pipelines.dang_ky_dat_dai_tai_san.process.schema import UI_ALIASES, UI_COMP_BY_NAME

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer

# "Nơi cấp CMND (CA Tỉnh)" là SELECT danh mục tỉnh: chỉ điền được khi nơi cấp đúng là công an một
# tỉnh/thành. Thẻ căn cước đời mới ghi "Bộ Công an"/"Cục Cảnh sát QLHC về TTXH" -> không có option
# tương ứng, để trống còn hơn chọn bừa một tỉnh.
_CA_PROVINCE_RE = re.compile(
    r"C[ÔO]NG\s*AN\s+(?:T[ỈI]NH|TH[ÀA]NH\s*PH[ỐO]|TP\.?)\s+(.+)$",
    re.IGNORECASE,
)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _plain(value) -> str | None:
    """Chuẩn hóa 1 chuỗi (bỏ xuống dòng/khoảng trắng thừa)."""
    if not isinstance(value, str):
        return None
    return " ".join(value.replace("\n", " ").split()).strip(" :;,-") or None


def _area(value) -> dict | None:
    """Nhận object {quocGia,tinh,xa,diaChi}; chuỗi trần chỉ đủ để điền ô chi tiết."""
    if isinstance(value, str):
        text = _plain(value)
        return {"tinh": "", "xa": "", "diaChi": text} if text else None
    if not isinstance(value, dict):
        return None
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("dia_chi") or value.get("chiTiet") or "",
    }
    if not any(area.values()):
        return None
    # remap_area đổi tên đơn vị hành chính cũ sang tên sau sáp nhập — option của cổng chỉ có tên mới.
    return remap_area(area) or area


def _full_address(area: dict) -> str | None:
    """Chuỗi địa chỉ đầy đủ cho 2 ô text "Nơi ở hiện tại"/"Địa chỉ thường trú"."""
    parts = [_plain(area.get("diaChi")), _plain(area.get("xa")), province_label(area.get("tinh"))]
    return ", ".join(part for part in parts if part) or None


def _phone(value) -> str | None:
    text = _plain(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if text.lstrip().startswith("+84") and digits.startswith("84"):
        digits = "0" + digits[2:]
    return digits if 9 <= len(digits) <= 11 else None


def _email(value) -> str | None:
    text = _plain(value)
    if not text:
        return None
    text = text.replace(" ", "")
    return text if re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", text) else None


def _issuer_province(value) -> str | None:
    """Suy tỉnh cấp CMND từ nơi cấp; không khớp "Công an tỉnh/TP X" thì trả None."""
    text = _plain(value)
    if not text:
        return None
    match = _CA_PROVINCE_RE.search(text)
    if not match:
        return None
    bare = _plain(match.group(1))
    return province_label(bare) if bare else None


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
        # "Tên cơ quan/tổ chức" và "MSDN/MST" CHỈ dành cho hồ sơ PHÁP NHÂN. Hồ sơ cá nhân/hộ gia
        # đình phải để TRỐNG: trước đây lấy họ tên người dân làm tên tổ chức và lấy số CCCD làm mã số
        # thuế -> ghi sai bản chất pháp lý của hồ sơ.
        add("CongDan_tenCoQuanToChuc", values.get("ToChuc_Ten"))
        add("CongDan_maSoThueNguoiNop", values.get("ToChuc_MaSoThue"))
        add("CongDan_ngaySinhCongDan", values.get("Cccd_NgaySinh"))
        add("CongDan_gioiTinhCongDan", values.get("Cccd_GioiTinh"))
        add("CongDan_danTocCongDan", values.get("Cccd_DanToc"))
        add("CongDan_soCmnd", identity_no)
        add("CongDan_ngayCapCmnd", values.get("Cccd_NgayCap"))
        add("CongDan_noiCapCmnd", issuer)
        add("CongDan_soCCCD", identity_no)
        add("CongDan_maTinhCapCMND", _issuer_province(issuer))

    add("CongDan_maDMQuocGia", "Việt Nam")
    add("CongDan_diaChiNuocNgoai", "Việt Nam")

    # Địa chỉ (3 ô BẮT BUỘC của bước 2). Ưu tiên ĐƠN/TỜ KHAI người dân lập rồi mới đến CCCD: thẻ cấp
    # trước sắp xếp đơn vị hành chính còn ghi tỉnh/huyện CŨ đã sáp nhập, chọn theo thẻ sẽ trượt option.
    residence = _area(values.get("Don_DiaChi")) or _area(values.get("Cccd_NoiCuTru"))
    if residence:
        add("CongDan_maTinhThanh", province_label(residence.get("tinh")))
        add("CongDan_maPhuongXa", _plain(residence.get("xa")))
        add("CongDan_diaChi", _plain(residence.get("diaChi")))
        full = _full_address(residence)
        add("CongDan_noiOHienTai", full)
        add("CongDan_diaChiThuongTru", full)

    add("CongDan_diDong", _phone(values.get("Don_DienThoai")))
    add("CongDan_email", _email(values.get("Don_Email")))

    if has_gcn:
        add("CongDan_soGCNGP", _serial(values.get("Gcn_SoPhatHanh")))
        add("CongDan_ngayCapGCNGP", values.get("Gcn_NgayCap"))
        add("CongDan_noiCapGCNGP", _issuer(values.get("Gcn_CoQuanCap")))

    return out
