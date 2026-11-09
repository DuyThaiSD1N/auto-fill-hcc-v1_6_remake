"""Dựng ô UI ``CongDan_*`` từ dữ kiện nguồn — thủ tục 1.115578 (Lai Châu).

Thứ tự nguồn theo file mapping: thẻ CCCD → Đơn đề nghị Mẫu số 02 → Giấy chứng nhận (mục I + trang thay đổi) → Trích
lục bản đồ địa chính. Riêng ĐỊA CHỈ (Tỉnh/Xã/Chi tiết, Nơi ở hiện tại, Địa chỉ thường trú) ưu tiên Đơn trước thẻ: thẻ
cấp trước sáp nhập in địa chỉ cũ, còn Đơn kê khai theo đơn vị hành chính mới (danh mục xã của cổng chỉ có tên mới);
thường trú rơi tiếp về trang thay đổi của Giấy chứng nhận rồi mới tới thẻ.

Giấy chứng nhận/Trích lục đứng tên CẢ hai vợ chồng: field ``Gcn_*`` chỉ dùng khi tên người đứng đầu trùng người nộp.
Cổng đổ sẵn bước 2 theo tài khoản đăng nhập → ô chữ không có nguồn phát ``clear`` (ô bắt buộc thêm ``markEmpty``),
trừ khi extension báo tài khoản chính là người nộp (formContext cùng số định danh).
"""

import re

from app.pipelines._shared import fold
from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import default_issuer, normalize_issuer
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.process.schema import (
    BLANK_TEXT_FIELDS,
    REQUIRED_BLANK,
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
_WARD_PREFIX_RE = re.compile(r"^(?:xã|phường|thị trấn|đặc khu)\s", re.IGNORECASE)
_LABELS = {
    "CongDan_tenCongDan": "Họ và tên",
    "CongDan_ngaySinhCongDan": "Ngày sinh",
    "CongDan_soCmnd": "Số CMND/CCCD",
    "CongDan_diaChi": "Số nhà/Đường/Tổ/Ấp/Thôn/Xóm",
}


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _plain(value) -> str | None:
    if not isinstance(value, str):
        return None
    return " ".join(value.replace("\n", " ").split()).strip(" :;,.-") or None


def _person_name(value) -> str | None:
    """Trích lục ghi "Lê Văn A (Trần Thị B)" → chỉ người đầu."""
    text = _plain(value)
    if not text:
        return None
    return _plain(re.sub(r"\(.*?\)|\(.*$", " ", text))


def _area(value) -> dict | None:
    """Nhận object {quocGia,tinh,xa,diaChi|chiTietDuoiXa}; chuỗi trần chỉ đủ để điền ô chi tiết."""
    if isinstance(value, str):
        text = _plain(value)
        return {"tinh": "", "xa": "", "diaChi": text} if text else None
    if not isinstance(value, dict):
        return None
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("chiTietDuoiXa") or value.get("chiTiet") or "",
    }
    if not any(area[key] for key in ("tinh", "xa", "diaChi")):
        return None
    # remap_area đổi tên đơn vị hành chính cũ sang tên sau sáp nhập — option của cổng chỉ có tên mới.
    area = remap_area(area) or area
    # Xã không có trong danh mục thì remap giữ nguyên chữ Đơn viết ("xã X") → viết hoa tiền tố như danh mục.
    xa = _plain(area.get("xa")) or ""
    if _WARD_PREFIX_RE.match(xa):
        area = {**area, "xa": xa[0].upper() + xa[1:]}
    return area


def _full_address(area: dict | None) -> str | None:
    if not area:
        return None
    parts = [_plain(area.get("diaChi")), _plain(area.get("xa")), province_label(area.get("tinh"))]
    return ", ".join(part for part in parts if part) or None


def _id_number(value) -> str | None:
    # 12 số = CCCD/số định danh, 9 số = CMND cũ. Thẻ/GCN hay chen dấu chấm hoặc tiền tố "CCCD số".
    if value in (None, ""):
        return None
    digits = re.sub(r"\D", "", str(value))
    return digits if len(digits) in (12, 9) else None


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
    """Ô ngày của cổng (Nth.Validator.DateTime) chỉ nhận dd/mm/yyyy — GCN chỉ ghi NĂM sinh thì bỏ."""
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
    """GCN ghi tắt "Cục Cảnh Sát QLHC về TTXH", thẻ in "Cục trưởng Cục Cảnh sát..." → tên cơ quan đầy đủ."""
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


def account_is_applicant(options: dict | None, identity: str | None) -> bool:
    """Tài khoản đăng nhập CHÍNH LÀ người nộp (extension gửi formContext, số định danh trùng) → bước 2 cổng đổ sẵn đúng
    người, ô giấy tờ thiếu giữ giá trị cổng thay vì xoá."""
    context = (options or {}).get("formContext") or {}
    account = _id_number(context.get("applicantIdentityNumber") or context.get("identityNumber"))
    return bool(account and identity and account == identity)


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
        field = {"name": name, "comp": comp, "value": value}
        if name in UI_ALIASES:
            field["aliases"] = UI_ALIASES[name]
        out.append(field)
        seen.add(name)

    # Người nộp = người đề nghị trên Đơn. Thẻ đọc được mà mang tên KHÁC (vd căn cước của vợ/chồng nộp kèm) thì không
    # phải thẻ người nộp: bỏ cả bộ Cccd_*.
    owner = _plain(values.get("Don_HoTen")) or _plain(values.get("Gcn_HoTen"))
    cccd = values
    if values.get("Cccd_HoTen") and owner and not _same_person(values.get("Cccd_HoTen"), owner):
        cccd = {key: value for key, value in values.items() if not key.startswith("Cccd_")}

    name = (
        _plain(cccd.get("Cccd_HoTen"))
        or _plain(values.get("Don_HoTen"))
        or _plain(values.get("Gcn_HoTen"))
        or _person_name(values.get("TrichLuc_HoTen"))
    )
    # GCN đứng tên cả vợ chồng: chỉ dùng khi đọc được tên người đứng đầu và trùng người nộp (không đọc được tên thì tin
    # LLM đã lấy đúng người đề nghị như prompt dặn).
    gcn = values if not values.get("Gcn_HoTen") or _same_person(values.get("Gcn_HoTen"), name) else {}

    identity_no = _id_number(cccd.get("Cccd_SoDinhDanh")) or _id_number(gcn.get("Gcn_SoCccdMoi"))
    # Thẻ in 01/12, GCN trang thay đổi có thể ghi lệch → ưu tiên thẻ (mapping).
    issue_date = _date(cccd.get("Cccd_NgayCap")) or _date(gcn.get("Gcn_NgayCapCccd"))
    issuer = (
        _issuer(cccd.get("Cccd_NoiCap"))
        or _issuer(gcn.get("Gcn_NoiCapCccd"))
        or (default_issuer(issue_date) if issue_date else None)
    )

    add("CongDan_tenCongDan", name.upper() if name else None)
    # Chỉ khi người đề nghị là CƠ QUAN, TỔ CHỨC; cá nhân/hộ gia đình để trống.
    add("CongDan_tenCoQuanToChuc", _plain(values.get("ToChuc_Ten")))
    add("CongDan_ngaySinhCongDan", _date(cccd.get("Cccd_NgaySinh")))
    add("CongDan_gioiTinhCongDan", _gender(cccd.get("Cccd_GioiTinh")) or _gender(gcn.get("NguoiSdd_GioiTinh")))
    add("CongDan_danTocCongDan", _plain(cccd.get("Cccd_DanToc")))
    add("CongDan_soCmnd", identity_no)
    add("CongDan_ngayCapCmnd", issue_date)
    add("CongDan_noiCapCmnd", issuer)
    add("CongDan_soCCCD", identity_no)
    add("CongDan_maTinhCapCMND", _issuer_province(issuer))

    card_residence = _area(cccd.get("Cccd_NoiCuTru"))
    residence = _area(values.get("Don_DiaChi")) or card_residence
    if residence:
        add("CongDan_maTinhThanh", province_label(residence.get("tinh")))
        add("CongDan_maPhuongXa", _plain(residence.get("xa")))
        add("CongDan_diaChi", _plain(residence.get("diaChi")))
        add("CongDan_noiOHienTai", _full_address(residence))
    # Mapping: thẻ in thường trú CŨ (cấp trước biến động/sáp nhập) → Đơn → trang thay đổi GCN → thẻ.
    add(
        "CongDan_diaChiThuongTru",
        _full_address(_area(values.get("Don_DiaChi")))
        or _plain(gcn.get("Gcn_ThuongTruMoi"))
        or _full_address(card_residence),
    )

    add("CongDan_diDong", _phone(values.get("Don_DienThoai")))
    add("CongDan_email", _email(values.get("Don_Email")))

    if not account_is_applicant(options, identity_no):
        missing_required = []
        for field_name in BLANK_TEXT_FIELDS:
            if field_name in seen:
                continue
            item = {"name": field_name, "comp": UI_COMP_BY_NAME[field_name], "value": "", "clear": True}
            if field_name in REQUIRED_BLANK:
                item["markEmpty"] = True
                missing_required.append(_LABELS[field_name])
            out.append(item)
            seen.add(field_name)
        if missing_required:
            warnings.append(
                "Giấy tờ không có " + ", ".join(missing_required) + " của người đề nghị — đã xoá giá trị cổng đổ sẵn "
                "theo tài khoản, vui lòng nhập tay."
            )
        if "CongDan_danTocCongDan" not in seen:
            warnings.append(
                "Dân tộc không có trên giấy tờ (thẻ căn cước gắn chip không in) — kiểm tra ô Dân tộc, cổng tự gán "
                "theo tài khoản đăng nhập."
            )
    return out, warnings
