"""Dựng ô UI ``CongDan_*`` từ dữ kiện nguồn — thủ tục 2.002862 (Lai Châu).

Thứ tự nguồn theo file mapping: CCCD → Tờ khai Mẫu 01 → Biên bản Mẫu 02 → Giấy hộ nghèo. Riêng ĐỊA CHỈ
ưu tiên Tờ khai/Biên bản trước thẻ (thẻ scan mất dấu, thẻ cũ ghi đơn vị hành chính trước sáp nhập) — cùng
cách ``dang_ky_dat_dai_tai_san`` (cùng cổng, cùng bộ ô).
"""

import re

from app.pipelines._shared import fold
from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines.ho_tro_mai_tang_dan_toc_thieu_so_lai_chau.process.schema import UI_ALIASES, UI_COMP_BY_NAME

# "Nơi cấp CMND (CA Tỉnh)" là SELECT danh mục tỉnh: chỉ điền khi nơi cấp đúng là công an một tỉnh/thành.
# Thẻ căn cước ghi "Bộ Công an"/"Cục Cảnh sát QLHC về TTXH" -> không có option, để trống.
_CA_PROVINCE_RE = re.compile(
    r"C[ÔO]NG\s*AN\s+(?:T[ỈI]NH|TH[ÀA]NH\s*PH[ỐO]|TP\.?)\s+(.+)$",
    re.IGNORECASE,
)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _plain(value) -> str | None:
    if not isinstance(value, str):
        return None
    return " ".join(value.replace("\n", " ").split()).strip(" :;,.-") or None


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
    if not any(area[key] for key in ("tinh", "xa", "diaChi")):
        return None
    # remap_area đổi tên đơn vị hành chính cũ sang tên sau sáp nhập — option của cổng chỉ có tên mới.
    return remap_area(area) or area


def _full_address(area: dict) -> str | None:
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


def _issuer(value) -> str | None:
    """Chuẩn hóa nơi cấp; Tờ khai/Biên bản hay ghi tắt "Bộ công an cấp."."""
    text = _plain(value)
    if not text:
        return None
    if "bo cong an" in fold(text):
        return "Bộ Công an"
    return text


def _issuer_province(value) -> str | None:
    text = _plain(value)
    if not text:
        return None
    match = _CA_PROVINCE_RE.search(text)
    if not match:
        return None
    bare = _plain(match.group(1))
    return province_label(bare) if bare else None


def _same_person(left, right) -> bool:
    left, right = fold(_plain(left) or ""), fold(_plain(right) or "")
    return bool(left) and left == right


def enrich(fields: list[dict]) -> list[dict]:
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

    # Thẻ đọc được mà mang tên NGƯỜI CHẾT (hồ sơ kèm cả CCCD người chết) thì không phải thẻ người nộp:
    # bỏ cả bộ Cccd_*, dùng Tờ khai.
    cccd = values
    if _same_person(values.get("Cccd_HoTen"), values.get("NguoiChet_HoTen")):
        cccd = {key: value for key, value in values.items() if not key.startswith("Cccd_")}

    name = _plain(cccd.get("Cccd_HoTen")) or _plain(values.get("ToKhai_HoTen"))
    identity_no = _plain(cccd.get("Cccd_SoDinhDanh")) or _plain(values.get("ToKhai_SoCccd"))
    issue_date = cccd.get("Cccd_NgayCap") or values.get("ToKhai_NgayCap")
    issuer = (
        _issuer(cccd.get("Cccd_NoiCap"))
        or _issuer(values.get("ToKhai_NoiCap"))
        or default_issuer(cccd.get("Cccd_NgayCap"))
    )

    add("CongDan_tenCongDan", name.upper() if name else None)
    # Chỉ khi CƠ QUAN, TỔ CHỨC đứng ra mai táng; hộ gia đình/cá nhân để trống.
    add("CongDan_tenCoQuanToChuc", _plain(values.get("ToChuc_Ten")))
    add("CongDan_ngaySinhCongDan", cccd.get("Cccd_NgaySinh") or values.get("ToKhai_NgaySinh"))
    add("CongDan_gioiTinhCongDan", _plain(cccd.get("Cccd_GioiTinh")))

    # Thẻ Căn cước mới không in dân tộc → lấy dòng "Hộ gia đình ông/bà" của Giấy hộ nghèo, nhưng CHỈ khi chủ
    # hộ chính là người nộp (người chết làm chủ hộ thì dân tộc dòng đó là của người chết).
    ethnicity = _plain(cccd.get("Cccd_DanToc"))
    if not ethnicity and _same_person(values.get("HoNgheo_ChuHo"), name):
        ethnicity = _plain(values.get("HoNgheo_DanToc"))
    add("CongDan_danTocCongDan", ethnicity)

    add("CongDan_soCmnd", identity_no)
    add("CongDan_ngayCapCmnd", issue_date)
    add("CongDan_noiCapCmnd", issuer)
    add("CongDan_soCCCD", identity_no)
    add("CongDan_maTinhCapCMND", _issuer_province(issuer))
    add("CongDan_maDMQuocGia", "Việt Nam")

    residence = _area(values.get("ToKhai_ThuongTru")) or _area(cccd.get("Cccd_NoiCuTru"))
    if residence:
        add("CongDan_maTinhThanh", province_label(residence.get("tinh")))
        add("CongDan_maPhuongXa", _plain(residence.get("xa")))
        add("CongDan_diaChi", _plain(residence.get("diaChi")))
        add("CongDan_diaChiThuongTru", _full_address(residence))
    current = _area(values.get("ToKhai_NoiO")) or residence
    if current:
        add("CongDan_noiOHienTai", _full_address(current))

    add("CongDan_diDong", _phone(values.get("NguoiNop_DienThoai")))
    return out
