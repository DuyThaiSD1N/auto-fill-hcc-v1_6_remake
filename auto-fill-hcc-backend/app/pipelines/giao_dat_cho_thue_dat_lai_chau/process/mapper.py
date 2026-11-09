"""Dựng ô UI ``CongDan_*`` từ dữ kiện nguồn — thủ tục 1.115577 (Lai Châu).

Theo file mapping: ô TỔ CHỨC lấy từ Đơn đề nghị giao đất Mẫu số 01 (mục 1 người đề nghị + dòng "Thành lập theo Quyết
định ..." = Số/Ngày/Nơi cấp GCN/GP, mục 2 trụ sở, mục 3 điện thoại), tên dự phòng = "Chủ đầu tư" của quyết định phê duyệt
dự án; "Đối tượng nộp" = Tổ chức. Ô CÁ NHÂN chỉ lấy từ thẻ CCCD của người đi nộp. Nhóm địa chỉ (Tỉnh / Xã / Số nhà) theo
trụ sở trên Đơn khi người đề nghị là tổ chức, theo Đơn rồi thẻ khi là cá nhân.

Người đề nghị là tổ chức: người nộp = chủ tài khoản đăng nhập (đại diện tổ chức) → ô cá nhân không có thẻ thì GIỮ giá trị
cổng đổ theo tài khoản, chỉ nhắc kiểm tra Giới tính / Dân tộc. Người đề nghị là cá nhân: như các thủ tục Lai Châu khác, ô
chữ thiếu xoá về trống (trừ khi tài khoản chính là người nộp).

Hàm chuẩn hoá (ngày, số giấy tờ, địa chỉ, nơi cấp) dùng chung với 1.115578 — cùng cổng, cùng bộ ô ``CongDan_*``.
"""

from app.pipelines._shared import fold
from app.pipelines._shared.area_remap import province_label
from app.pipelines._shared.compact_agent.issuer import default_issuer
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
from app.pipelines.giao_dat_cho_thue_dat_lai_chau.process.schema import (
    PERSONAL_TEXT_FIELDS,
    REQUIRED_BLANK,
    UI_ALIASES,
    UI_COMP_BY_NAME,
)

ORGANIZATION, PERSON = "Tổ chức", "Cá nhân"
# Tên người đề nghị chứa các cụm này là tổ chức (LLM bỏ sót Don_LoaiNguoiDeNghi vẫn chọn đúng "Đối tượng nộp").
_ORG_MARKERS = (
    "ban quan ly", "ban qlda", "cong ty", "uy ban nhan dan", "ubnd", "trung tam", "hop tac xa", "doanh nghiep",
    "tap doan", "chi nhanh", "co quan", "don vi", "benh vien", "truong ", "so ", "phong ", "cuc ", "tong cuc",
    "van phong", "hoi ", "quy ",
)
_LABELS = {
    "CongDan_tenCongDan": "Họ và tên",
    "CongDan_ngaySinhCongDan": "Ngày sinh",
    "CongDan_soCmnd": "Số CMND/CCCD",
    "CongDan_diaChi": "Số nhà/Đường/Tổ/Ấp/Thôn/Xóm",
}


def _is_organization(kind, name) -> bool:
    folded = fold(_plain(kind) or "")
    if "to chuc" in folded:
        return True
    if "ca nhan" in folded or "ho gia dinh" in folded:
        return False
    named = f" {fold(_plain(name) or '')} "
    return any(f" {marker}" in named for marker in _ORG_MARKERS)


def _tax_code(value) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if len(digits) in (10, 12, 13) else None


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

    applicant = _plain(values.get("Don_NguoiDeNghi"))
    organization = _is_organization(values.get("Don_LoaiNguoiDeNghi"), applicant or values.get("Pd_ChuDauTu"))
    if organization:
        applicant = applicant or _plain(values.get("Pd_ChuDauTu"))

    # Thẻ đọc được: là thẻ người đi nộp. Người đề nghị là CÁ NHÂN mà thẻ mang tên khác (vd thẻ người thân nộp kèm) thì
    # không phải thẻ người nộp: bỏ cả bộ Cccd_*.
    card = values
    if not organization and applicant and values.get("Cccd_HoTen") and not _same_person(values.get("Cccd_HoTen"), applicant):
        card = {key: value for key, value in values.items() if not key.startswith("Cccd_")}
    has_card = any(key.startswith("Cccd_") for key in card)

    name = _plain(card.get("Cccd_HoTen")) or (None if organization else applicant)
    identity_no = _id_number(card.get("Cccd_SoDinhDanh")) or _id_number(values.get("Don_SoGiayTo"))
    issue_date = _date(card.get("Cccd_NgayCap"))
    issuer = _issuer(card.get("Cccd_NoiCap")) or (default_issuer(issue_date) if issue_date else None)

    add("CongDan_tenCongDan", name.upper() if name else None)
    if organization:
        add("CongDan_tenCoQuanToChuc", applicant)
        add("CongDan_maSoThueNguoiNop", _tax_code(values.get("Don_MaSoThue")))
        # Ban quản lý dự án là đơn vị sự nghiệp: "giấy chứng nhận / giấy phép" của tổ chức = quyết định thành lập.
        add("CongDan_soGCNGP", _plain(values.get("Don_QdThanhLapSo")))
        add("CongDan_ngayCapGCNGP", _date(values.get("Don_QdThanhLapNgay")))
        add("CongDan_noiCapGCNGP", _plain(values.get("Don_QdThanhLapCoQuan")))
    add("CongDan_ngaySinhCongDan", _date(card.get("Cccd_NgaySinh")))
    add("CongDan_gioiTinhCongDan", _gender(card.get("Cccd_GioiTinh")))
    add("CongDan_danTocCongDan", _plain(card.get("Cccd_DanToc")))
    add("CongDan_soCmnd", identity_no)
    add("CongDan_ngayCapCmnd", issue_date)
    add("CongDan_noiCapCmnd", issuer)
    add("CongDan_soCCCD", identity_no)
    add("CongDan_maTinhCapCMND", _issuer_province(issuer))

    card_residence = _area(card.get("Cccd_NoiCuTru"))
    office = _area(values.get("Don_DiaChi"))
    residence = office or card_residence
    if residence:
        add("CongDan_maTinhThanh", province_label(residence.get("tinh")))
        add("CongDan_maPhuongXa", _plain(residence.get("xa")))
        add("CongDan_diaChi", _plain(residence.get("diaChi")))
    if applicant:
        add("CongDan__select_1", ORGANIZATION if organization else PERSON)
    # Nơi ở / thường trú là của CÁ NHÂN người nộp: tổ chức chỉ lấy theo thẻ, không lấy trụ sở.
    personal_home = card_residence if organization else (card_residence or office)
    add("CongDan_noiOHienTai", _full_address(personal_home))
    add("CongDan_diaChiThuongTru", _full_address(personal_home))
    add("CongDan_diDong", _phone(values.get("Don_DienThoai")))
    add("CongDan_email", _email(values.get("Don_Email")))

    if organization:
        if not has_card:
            warnings.append(
                "Hồ sơ không có căn cước của người đi nộp — các ô cá nhân giữ theo tài khoản đăng nhập; kiểm tra Giới "
                "tính (cổng để sẵn \"Nữ\") và Dân tộc trước khi bấm Đồng ý và tiếp tục."
            )
        return out, warnings

    if not account_is_applicant(options, identity_no):
        missing_required = []
        for field_name in PERSONAL_TEXT_FIELDS:
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
        warnings.append("Dân tộc không có trên giấy tờ — kiểm tra ô Dân tộc trên trang.")
    return out, warnings
