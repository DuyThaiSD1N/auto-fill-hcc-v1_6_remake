"""Dựng ô UI ``CongDan_*`` từ dữ kiện nguồn — thủ tục 1.115591 (Lai Châu).

Theo file mapping "Mapping_TTHC_1.115591_ToChucKinhTe_NhanCNQSDD_DuAn_DVC_LaiChau":
  - "Đối tượng nộp" luôn = Tổ chức (thủ tục dành cho tổ chức kinh tế);
  - ô TỔ CHỨC từ mục 1 văn bản Mẫu số 30: tên, MSDN = MST = Số GCN/GP, ngày cấp lần đầu, cơ quan cấp;
  - nhóm địa chỉ (Tỉnh / Xã / Số nhà) theo trụ sở mục 3 → địa chỉ liên hệ mục 4 → địa bàn mảnh trích đo (chỉ tỉnh/xã);
  - ô CÁ NHÂN là của người đại diện (người nộp): CCCD → mục 2 văn bản cho họ tên, ngày sinh, giới tính, số định danh;
    ngày cấp, nơi cấp, dân tộc, thường trú CHỈ từ thẻ. Thẻ mang tên KHÁC người đại diện → người đi nộp là người khác
    (được giới thiệu/ủy quyền): ô cá nhân theo cả bộ thẻ, không trộn ngày sinh/số định danh của người đại diện.

Cổng đổ sẵn ô cá nhân theo tài khoản đăng nhập (mapping: "phải sửa") → ô chữ không có nguồn phát ``clear`` (ô bắt buộc
thêm ``markEmpty``) như [[o-thieu-tra-ve-trong]], trừ khi extension báo tài khoản chính là người nộp.

Hàm chuẩn hoá dùng chung với 1.115578 / 1.115577 — cùng cổng, cùng bộ ô ``CongDan_*``.
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
from app.pipelines.giao_dat_cho_thue_dat_lai_chau.process.mapper import ORGANIZATION, _tax_code
from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhuong_qsdd_du_an_lai_chau.process.schema import (
    PERSONAL_TEXT_FIELDS,
    REQUIRED_BLANK,
    UI_ALIASES,
    UI_COMP_BY_NAME,
)

_LABELS = {
    "CongDan_tenCongDan": "Họ và tên",
    "CongDan_ngaySinhCongDan": "Ngày sinh",
    "CongDan_soCmnd": "Số CMND/CCCD",
}


def _organization_name(item1, header) -> str | None:
    """Tên mục 1, cắt theo tên cơ quan ban hành góc trái trên khi tên đó là phần đầu của mục 1.

    Chữ ký Giám đốc đè lên dòng "Giấy chứng nhận đăng ký doanh nghiệp Công ty trách nhiệm hữu hạn một thành viên" ngay
    sau tên → OCR nuốt mất nửa dòng, chữ còn sót ("thành viên") dính vào tên ở mục 1.
    """
    name, top = _plain(item1), _plain(header)
    if not name or not top:
        return name or top
    words, target = name.split(), fold(top)
    for count in range(1, len(words) + 1):
        if fold(" ".join(words[:count])) == target:
            return _plain(" ".join(words[:count]))
    return name


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

    representative = _plain(values.get("Vb_NguoiDaiDien"))
    card_name = _plain(values.get("Cccd_HoTen"))
    has_card = any(key.startswith("Cccd_") for key in values)
    # Thẻ của người khác (người đi nộp thay) → không lấy mục 2 văn bản bù ô thẻ thiếu.
    other_bearer = bool(card_name and representative and not _same_person(card_name, representative))
    letter = {} if other_bearer else values

    name = card_name or representative
    identity_no = _id_number(values.get("Cccd_SoDinhDanh")) or _id_number(letter.get("Vb_SoDinhDanh"))
    issue_date = _date(values.get("Cccd_NgayCap"))
    issuer = _issuer(values.get("Cccd_NoiCap")) or (default_issuer(issue_date) if issue_date else None)

    add("CongDan_tenCongDan", name.upper() if name else None)
    add("CongDan_tenCoQuanToChuc", _organization_name(values.get("Vb_ToChuc"), values.get("Vb_TenCoQuanBanHanh")))
    tax_code = _tax_code(values.get("Vb_MaSoDoanhNghiep"))
    add("CongDan_maSoThueNguoiNop", tax_code)
    add("CongDan_ngaySinhCongDan", _date(values.get("Cccd_NgaySinh")) or _date(letter.get("Vb_NgaySinh")))
    add("CongDan_gioiTinhCongDan", _gender(values.get("Cccd_GioiTinh")) or _gender(letter.get("Vb_GioiTinh")))
    add("CongDan_danTocCongDan", _plain(values.get("Cccd_DanToc")))
    add("CongDan_soCmnd", identity_no)
    add("CongDan_ngayCapCmnd", issue_date)
    add("CongDan_noiCapCmnd", issuer)
    add("CongDan_soCCCD", identity_no)
    add("CongDan_maTinhCapCMND", _issuer_province(issuer))

    office = _area(values.get("Vb_DiaChiTruSo")) or _area(values.get("Vb_DiaChiLienHe"))
    parcel = _area(values.get("TrichDo_DiaBan"))
    province = (office or {}).get("tinh") or (parcel or {}).get("tinh")
    ward = (office or {}).get("xa") or (parcel or {}).get("xa")
    add("CongDan_maTinhThanh", province_label(province) if province else None)
    add("CongDan_maPhuongXa", _plain(ward))
    # Chi tiết dưới xã chỉ theo trụ sở: "Bản ..." trên mảnh trích đo là vị trí khu đất, không phải trụ sở.
    add("CongDan_diaChi", _plain((office or {}).get("diaChi")))
    add("CongDan__select_1", ORGANIZATION)
    # Nơi ở / thường trú là của CÁ NHÂN người nộp: chỉ theo thẻ, không lấy trụ sở tổ chức.
    home = _full_address(_area(values.get("Cccd_NoiCuTru")))
    add("CongDan_noiOHienTai", home)
    add("CongDan_diaChiThuongTru", home)
    add("CongDan_diDong", _phone(values.get("Vb_DienThoai")))
    add("CongDan_email", _email(values.get("Vb_Email")))
    # Giấy chứng nhận đăng ký doanh nghiệp lấy mã số doanh nghiệp làm số giấy (mapping STT 23).
    add("CongDan_soGCNGP", tax_code)
    add("CongDan_ngayCapGCNGP", _date(values.get("Vb_GcnNgayCap")))
    add("CongDan_noiCapGCNGP", _plain(values.get("Vb_GcnNoiCap")))

    if other_bearer:
        warnings.append(
            f"Căn cước trong hồ sơ mang tên {card_name.upper()}, khác người đại diện ở mục 2 văn bản đề nghị "
            f"({representative.upper()}) — đã điền người nộp theo căn cước; nếu người này nộp thay thì đính kèm giấy "
            "giới thiệu/ủy quyền."
        )
    if "CongDan_diaChi" not in seen:
        warnings.append("Không đọc được địa chỉ trụ sở (mục 3 văn bản đề nghị) — nhập ô Số nhà/Đường/Tổ/Ấp/Thôn/Xóm.")

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
                "Giấy tờ không có " + ", ".join(missing_required) + " của người đại diện — đã xoá giá trị cổng đổ sẵn "
                "theo tài khoản, vui lòng nhập tay."
            )
    if "CongDan_danTocCongDan" not in seen:
        warnings.append(
            "Dân tộc không có trên giấy tờ" + ("" if has_card else " (hồ sơ không có căn cước)")
            + " — kiểm tra ô Dân tộc của người đại diện trên trang."
        )
    return out, warnings
