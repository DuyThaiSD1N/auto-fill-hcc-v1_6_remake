"""Dựng ô UI ``CongDan_*`` từ dữ kiện nguồn — thủ tục 1.115590 (Lai Châu).

Thứ tự nguồn theo file mapping: CCCD → Đơn đăng ký biến động Mẫu 16 → Giấy ủy quyền → Giấy chứng nhận. Riêng ĐỊA
CHỈ (3 ô bắt buộc Tỉnh/Xã/Chi tiết + Nơi ở hiện tại) ưu tiên Đơn trước thẻ (Đơn là kê khai mới nhất, thẻ cũ ghi
đơn vị hành chính trước sáp nhập) — cùng cách ``dang_ky_dat_dai_tai_san`` (cùng cổng, cùng bộ ô). Ô "Địa chỉ thường
trú" thì theo mapping: thẻ → Giấy ủy quyền → trang thay đổi của GCN → Đơn.

Giấy ủy quyền có cả NGƯỜI ĐƯỢC ỦY QUYỀN: mọi field ``UyQuyen_*`` chỉ dùng khi họ tên bên ủy quyền trùng người nộp,
tránh ghép ngày sinh/số căn cước của người khác vào hồ sơ.
"""

import re

from app.pipelines._shared import fold
from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines.dang_ky_cap_giay_chung_nhan_doi_voi_toan_bo_dien_tich_dat_lai_chau.process.schema import (
    UI_ALIASES,
    UI_COMP_BY_NAME,
)

# "Nơi cấp CMND (CA Tỉnh)" là SELECT danh mục tỉnh: chỉ điền khi nơi cấp đúng là công an một tỉnh/thành.
# Thẻ căn cước ghi "Bộ Công an"/"Cục Cảnh sát QLHC về TTXH" -> không có option, để trống.
_CA_PROVINCE_RE = re.compile(
    r"C[ÔO]NG\s*AN\s+(?:T[ỈI]NH|TH[ÀA]NH\s*PH[ỐO]|TP\.?)\s+(.+)$",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$")


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


def _full_address(area: dict | None) -> str | None:
    if not area:
        return None
    parts = [_plain(area.get("diaChi")), _plain(area.get("xa")), province_label(area.get("tinh"))]
    return ", ".join(part for part in parts if part) or None


def _digits(value, lengths: tuple[int, ...]) -> str | None:
    """Số giấy tờ/mã số thuế: Đơn viết tay hay chen dấu chấm ("012.345...") hoặc tiền tố "CCCD:"."""
    if value in (None, ""):
        return None
    digits = re.sub(r"\D", "", str(value))
    return digits if len(digits) in lengths else None


def _id_number(value) -> str | None:
    # 12 số = CCCD/số định danh, 9 số = CMND cũ.
    return _digits(value, (12, 9))


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


def _date(value) -> str | None:
    """Ô ngày của cổng (Nth.Validator.DateTime) chỉ nhận dd/mm/yyyy — Đơn/GCN chỉ ghi NĂM sinh thì bỏ."""
    match = _DATE_RE.match(_plain(value) or "")
    if not match:
        return None
    day, month, year = match.groups()
    return f"{int(day):02d}/{int(month):02d}/{year}"


def _gender(value) -> str | None:
    folded = fold(_plain(value) or "")
    if folded in ("nam", "ong", "male"):
        return "Nam"
    if folded in ("nu", "ba", "female"):
        return "Nữ"
    return None


def _issuer(value) -> str | None:
    """Giấy ủy quyền ghi tắt "Cục cảnh sát QLHC về TTXH" → cổng muốn tên đầy đủ (theo mapping)."""
    text = _plain(value)
    if not text:
        return None
    return normalize_issuer(text) or None


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

    # Người nộp = người sử dụng đất đứng tên trên Đơn. Thẻ đọc được mà mang tên KHÁC (vd căn cước của người được ủy
    # quyền nộp kèm) thì không phải thẻ người nộp: bỏ cả bộ Cccd_*.
    cccd = values
    if values.get("Cccd_HoTen") and values.get("Don_HoTen") and not _same_person(
        values.get("Cccd_HoTen"), values.get("Don_HoTen")
    ):
        cccd = {key: value for key, value in values.items() if not key.startswith("Cccd_")}

    name = _plain(cccd.get("Cccd_HoTen")) or _plain(values.get("Don_HoTen")) or _plain(values.get("Gcn_HoTen"))
    # Giấy ủy quyền chỉ được dùng khi chắc bên ủy quyền là người nộp; GCN có thể đứng tên nhiều người nên chỉ loại
    # khi đọc được tên và tên đó khác.
    uq = values if _same_person(values.get("UyQuyen_HoTen"), name) else {}
    gcn = values if not values.get("Gcn_HoTen") or _same_person(values.get("Gcn_HoTen"), name) else {}

    identity_no = (
        _id_number(cccd.get("Cccd_SoDinhDanh"))
        or _id_number(values.get("Don_SoGiayTo"))
        or _id_number(uq.get("UyQuyen_SoCccd"))
        or _id_number(gcn.get("Gcn_SoCccdMoi"))
    )
    issue_date = (
        _date(cccd.get("Cccd_NgayCap")) or _date(uq.get("UyQuyen_NgayCap")) or _date(gcn.get("Gcn_NgayCapCccd"))
    )
    issuer = (
        _issuer(cccd.get("Cccd_NoiCap"))
        or _issuer(uq.get("UyQuyen_NoiCap"))
        or _issuer(gcn.get("Gcn_NoiCapCccd"))
        or (default_issuer(issue_date) if issue_date else None)
    )

    add("CongDan_tenCongDan", name.upper() if name else None)
    # Chỉ khi người sử dụng đất là CƠ QUAN, TỔ CHỨC; cá nhân/hộ gia đình để trống.
    add("CongDan_tenCoQuanToChuc", _plain(values.get("ToChuc_Ten")))
    # Mục "Mã số thuế" của Đơn: từ 01/7/2025 số định danh dùng làm MST cá nhân nên trùng số CCCD là bình thường.
    add("CongDan_maSoThueNguoiNop", _digits(values.get("Don_MaSoThue"), (10, 12, 13)))
    add("CongDan_ngaySinhCongDan", _date(cccd.get("Cccd_NgaySinh")) or _date(uq.get("UyQuyen_NgaySinh")))
    add("CongDan_gioiTinhCongDan", _gender(cccd.get("Cccd_GioiTinh")) or _gender(values.get("NguoiSdd_GioiTinh")))
    add("CongDan_danTocCongDan", _plain(cccd.get("Cccd_DanToc")))
    add("CongDan_soCmnd", identity_no)
    add("CongDan_ngayCapCmnd", issue_date)
    add("CongDan_noiCapCmnd", issuer)
    add("CongDan_soCCCD", identity_no)
    add("CongDan_maTinhCapCMND", _issuer_province(issuer))
    add("CongDan_maDMQuocGia", "Việt Nam")

    card_residence = _area(cccd.get("Cccd_NoiCuTru"))
    residence = _area(values.get("Don_DiaChi")) or card_residence
    if residence:
        add("CongDan_maTinhThanh", province_label(residence.get("tinh")))
        add("CongDan_maPhuongXa", _plain(residence.get("xa")))
        add("CongDan_diaChi", _plain(residence.get("diaChi")))
        add("CongDan_noiOHienTai", _full_address(residence))
    add(
        "CongDan_diaChiThuongTru",
        _full_address(card_residence)
        or _plain(uq.get("UyQuyen_ThuongTru"))
        or _plain(gcn.get("Gcn_ThuongTruMoi"))
        or _full_address(residence),
    )

    add("CongDan_diDong", _phone(values.get("Don_DienThoai")))
    add("CongDan_email", _email(values.get("Don_Email")))
    return out
