"""Dựng ô UI ``CongDan_*`` từ dữ kiện nguồn — thủ tục 1.115557 (Lai Châu).

Thứ tự nguồn theo file mapping: thẻ CCCD → Đơn đăng ký biến động Mẫu số 16 → giấy kèm theo (Bảng 16a, Mẫu số 09,
Mẫu số 03a) → Giấy chứng nhận / Sổ địa chính (họ tên, danh xưng). Riêng ĐỊA CHỈ (Tỉnh/Xã/Chi tiết, Nơi ở hiện tại, Địa
chỉ thường trú) ưu tiên Đơn trước thẻ: thẻ cấp trước sáp nhập in thị trấn/huyện cũ, còn Đơn kê khai theo đơn vị hành
chính mới (danh mục xã của cổng chỉ có tên mới).

Hồ sơ scan chung kèm thẻ của CẢ người đồng sử dụng: bộ ``Cccd_*`` / ``DonKhac_*`` chỉ dùng khi khớp người viết đơn (cùng
họ tên hoặc cùng số CCCD với mục I Đơn Mẫu 16). Cổng đổ sẵn bước 2 theo tài khoản đăng nhập → ô chữ không có nguồn phát
``clear`` (ô bắt buộc thêm ``markEmpty``), trừ khi extension báo tài khoản chính là người nộp.

Hàm chuẩn hoá (ngày, số giấy tờ, địa chỉ, nơi cấp) dùng chung với 1.115578 — cùng cổng, cùng bộ ô ``CongDan_*``.
"""

import re

from app.pipelines._shared import fold
from app.pipelines._shared.area_remap import province_label
from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_lai_chau.process.schema import (
    BLANK_TEXT_FIELDS,
    REQUIRED_BLANK,
    UI_ALIASES,
    UI_COMP_BY_NAME,
)
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.process.mapper import (
    _area,
    _by_name,
    _date,
    _email,
    _full_address,
    _gender,
    _id_number,
    _issuer,
    _issuer_province,
    _phone,
    _plain,
    _same_person,
    account_is_applicant,
)

_LABELS = {
    "CongDan_tenCongDan": "Họ và tên",
    "CongDan_ngaySinhCongDan": "Ngày sinh",
    "CongDan_soCmnd": "Số CMND/CCCD",
    "CongDan_diaChi": "Số nhà/Đường/Tổ/Ấp/Thôn/Xóm",
}


def _tax_code(value) -> str | None:
    """MST 10 số (+ "-xxx" chi nhánh) hoặc 12 số (số định danh dùng làm MST cá nhân)."""
    text = re.sub(r"\s", "", _plain(value) or "")
    if re.fullmatch(r"\d{10}(?:-\d{3})?|\d{12}", text):
        return text
    return None


def _is_owner(name, number, owner: str | None, owner_id: str | None) -> bool:
    """Giấy (thẻ, đơn kèm) thuộc người viết đơn: khớp họ tên HOẶC số CCCD. Không có gì để so → coi là đúng người."""
    compared = False
    if _plain(name) and owner:
        if _same_person(name, owner):
            return True
        compared = True
    digits = _id_number(number)
    if digits and owner_id:
        if digits == owner_id:
            return True
        compared = True
    return not compared


def _fuller_detail(declared: dict | None, other: dict | None) -> dict | None:
    """Đơn Mẫu 16 viết tay hay rơi chữ cuối tên bản (OCR đọc "Tình" thành "Tỉnh" rồi bị coi là cấp tỉnh). Giấy kèm
    (Mẫu 03a đánh máy) cùng xã mà phần chi tiết chỉ DÀI THÊM chữ ở cuối → lấy bản đầy đủ đó."""
    if not declared or not other:
        return declared
    if fold(_plain(declared.get("xa")) or "") != fold(_plain(other.get("xa")) or ""):
        return declared
    short, full = fold(_plain(declared.get("diaChi")) or ""), fold(_plain(other.get("diaChi")) or "")
    if full and (not short or full.startswith(short + " ")):
        return {**declared, "diaChi": other.get("diaChi")}
    return declared


def _without(values: dict, prefix: str) -> dict:
    return {key: value for key, value in values.items() if not key.startswith(prefix)}


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

    # Người nộp = người viết Đơn Mẫu 16. Giấy kèm (Mẫu 09/03a/Bảng 16a) hay thẻ mang người KHÁC (vợ/chồng đồng sử dụng
    # scan chung một file) thì bỏ cả bộ đó.
    don_owner, don_id = _plain(values.get("Don_HoTen")), _id_number(values.get("Don_SoGiayTo"))
    if not _is_owner(values.get("DonKhac_HoTen"), values.get("DonKhac_SoCccd"), don_owner, don_id):
        values = _without(values, "DonKhac_")
    owner = don_owner or _plain(values.get("DonKhac_HoTen")) or _plain(values.get("Gcn_HoTen"))
    owner_id = don_id or _id_number(values.get("DonKhac_SoCccd"))
    cccd = values
    if not _is_owner(values.get("Cccd_HoTen"), values.get("Cccd_SoDinhDanh"), owner, owner_id):
        cccd = _without(values, "Cccd_")

    name = (
        _plain(cccd.get("Cccd_HoTen"))
        or don_owner
        or _plain(values.get("DonKhac_HoTen"))
        or _plain(values.get("Gcn_HoTen"))
    )
    # GCN / Sổ địa chính đứng tên cả vợ chồng: danh xưng chỉ dùng khi người đứng đầu là người nộp.
    gcn = values if not values.get("Gcn_HoTen") or _same_person(values.get("Gcn_HoTen"), name) else {}

    identity_no = (
        _id_number(cccd.get("Cccd_SoDinhDanh")) or don_id or _id_number(values.get("DonKhac_SoCccd"))
    )
    issue_date = (
        _date(cccd.get("Cccd_NgayCap")) or _date(values.get("Don_NgayCap")) or _date(values.get("DonKhac_NgayCap"))
    )
    issuer = (
        _issuer(cccd.get("Cccd_NoiCap"))
        or _issuer(values.get("Don_CoQuanCap"))
        or _issuer(values.get("DonKhac_NoiCap"))
        or (default_issuer(issue_date) if issue_date else None)
    )

    add("CongDan_tenCongDan", name.upper() if name else None)
    # Chỉ khi người sử dụng đất là CƠ QUAN, TỔ CHỨC; cá nhân/hộ gia đình để trống.
    add("CongDan_tenCoQuanToChuc", _plain(values.get("ToChuc_Ten")))
    add("CongDan_maSoThueNguoiNop", _tax_code(values.get("Don_MaSoThue")))
    add(
        "CongDan_ngaySinhCongDan",
        _date(cccd.get("Cccd_NgaySinh")) or _date(values.get("Don_NgaySinh")) or _date(values.get("DonKhac_NgaySinh")),
    )
    add("CongDan_gioiTinhCongDan", _gender(cccd.get("Cccd_GioiTinh")) or _gender(gcn.get("NguoiSdd_GioiTinh")))
    add("CongDan_danTocCongDan", _plain(cccd.get("Cccd_DanToc")))
    add("CongDan_soCmnd", identity_no)
    add("CongDan_ngayCapCmnd", issue_date)
    add("CongDan_noiCapCmnd", issuer)
    add("CongDan_soCCCD", identity_no)
    add("CongDan_maTinhCapCMND", _issuer_province(issuer))

    card_residence = _area(cccd.get("Cccd_NoiCuTru"))
    extra_address = _area(values.get("DonKhac_DiaChi"))
    declared = _fuller_detail(_area(values.get("Don_DiaChi")), extra_address) or extra_address
    residence = declared or card_residence
    if residence:
        add("CongDan_maTinhThanh", province_label(residence.get("tinh")))
        add("CongDan_maPhuongXa", _plain(residence.get("xa")))
        add("CongDan_diaChi", _plain(residence.get("diaChi")))
        add("CongDan_noiOHienTai", _full_address(residence))
    # Mapping: thẻ / Giấy chứng nhận in thường trú CŨ (trước sáp nhập) → lấy địa chỉ Đơn kê khai, rồi mới tới thẻ.
    add("CongDan_diaChiThuongTru", _full_address(declared) or _full_address(card_residence))

    add("CongDan_diDong", _phone(values.get("Don_DienThoai")) or _phone(values.get("DonKhac_DienThoai")))
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
                "Giấy tờ không có " + ", ".join(missing_required) + " của người viết đơn — đã xoá giá trị cổng đổ sẵn "
                "theo tài khoản, vui lòng nhập tay."
            )
        if "CongDan_danTocCongDan" not in seen:
            warnings.append(
                "Dân tộc không có trên giấy tờ (thẻ căn cước gắn chip không in) — kiểm tra ô Dân tộc, cổng tự gán "
                "theo tài khoản đăng nhập."
            )
    return out, warnings
