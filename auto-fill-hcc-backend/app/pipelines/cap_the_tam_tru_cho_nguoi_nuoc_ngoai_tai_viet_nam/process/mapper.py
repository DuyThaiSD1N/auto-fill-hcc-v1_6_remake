"""Dựng ô form ``CongDan__fs*`` / ``CongDan_*`` / ``HoSoOnline_*`` — thủ tục 1.003460 (Cổng DVC Bộ Công an).

Thứ tự nguồn theo file mapping (cột "Dữ liệu được lấy từ", [UT1] trước):
- Người nước ngoài: hộ chiếu (trang nhân thân + MRZ có chữ số kiểm tra, trang thị thực, dấu nhập cảnh) → Tờ khai NA8 →
  Văn bản NA6 → giấy phép lao động. Quốc tịch gốc ưu tiên NA8 (chỉ NA8 ghi đúng quốc tịch gốc); nghề nghiệp NA8 → chức
  danh GPLĐ → vị trí công việc NA6; địa chỉ / nơi làm việc ở nước ngoài, tạm trú tại VN, điện thoại, email: NA8.
- Mục đích nhập cảnh: theo ký hiệu thị thực / thẻ (LĐ2 → "lao động", mapping ghi CẦN XÁC NHẬN) → từ khoá trong câu NA8.
- Bên bảo lãnh: form khoá "Thân nhân" theo tài khoản đăng nhập (họ tên / ngày sinh / số giấy tờ readonly). Ngày cấp, cơ
  quan cấp: thẻ căn cước (nếu có). Quan hệ: NA7 → "Người sử dụng lao động – <cơ quan>" khi cơ quan NA6 bảo lãnh lao động
  (mapping: đề xuất, CẦN XÁC NHẬN). Địa chỉ: căn cước → trụ sở / địa chỉ trên văn bản đề nghị. Điện thoại, email: NA6/NA7.
- Cấp thẻ tạm trú đến ngày: NA8 mục 12 → thời hạn GPLĐ (thẻ không được vượt). Lý do: NA8. "Những điều cần trình bày
  thêm" (bắt buộc, NA8 không có mục): ghép ký hiệu thẻ + văn bản đề nghị (số, ngày, cơ quan, mã số DN) + GPLĐ.
- Ghi chú: trang nào của tệp hồ sơ gộp là giấy gì (process/runner.py dựng, ảnh ánh xạ mục 6).
"""

import re
from datetime import date

from app.pipelines._shared import fold
from app.pipelines._shared.area_remap import canonical_province, province_label
from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines.cap_the_tam_tru_cho_nguoi_nuoc_ngoai_tai_viet_nam.process.schema import (
    MUC_DICH_BY_KY_HIEU,
    UI_COMP_BY_NAME,
    WAIT_MS,
)
from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.process.mapper import (
    _border_gate,
    _country,
    _gender,
    _has_area,
    _id_digits,
    _passport_number,
    _passport_type,
    _purpose,
    _same_name,
    _text,
    ocr_fallback,
    parse_mrz,
)
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.process.mapper import (
    _area,
    _by_name,
    _date,
    _issuer,
    _phone,
    _plain,
)
# Email: làm sạch chung các thủ tục Bộ Công an (dấu phẩy OCR, tên miền đọc lệch), user 19/11/2026.
from app.pipelines._shared.formatting import clean_email as _email
from app.pipelines._shared.formatting import keep_portal_values

__all__ = ["enrich", "ocr_fallback"]

# Ký hiệu thẻ / thị thực: 2 chữ (Đ được viết D khi fold) + số tuỳ chọn — "LĐ2", "DN1", "TT".
_SYMBOL_RE = re.compile(r"^\s*([A-ZĐ]{2}\d?)\b")
_SYMBOL_IN_TEXT_RE = re.compile(r"(?:th[ịi]\s+th[ựu]c|k[ýy]\s+hi[ệe]u)\s*:?\s*([A-ZĐ]{2}\d?)\b", re.IGNORECASE)
_ORG_RE = re.compile(r"\b(cong ty|tong cong ty|doanh nghiep|ngan hang|truong|vien|benh vien|hop tac xa|van phong|"
                     r"chi nhanh|co quan|to chuc|so |uy ban|bo |dai su quan|lanh su quan)", re.IGNORECASE)

PHOTO_WARNING = (
    "Đầu biểu mẫu có 2 ô tải ảnh .jpg dưới 2 MB: Ảnh chân dung (cổng đòi ảnh 4x6 nền trắng — hồ sơ giấy thường chỉ có ảnh "
    "2x3) và ảnh Trang nhân thân hộ chiếu — tải tay, không thuộc bảng Thành phần hồ sơ."
)
# Runner gắn được ảnh chân dung (ô filename46, comp bca-photo) mà không thấy trang hộ chiếu có MRZ → chỉ còn nhắc ô
# Trang nhân thân hộ chiếu (filenamehc). Gắn được cả hai thì bỏ hẳn câu nhắc.
PASSPORT_PAGE_WARNING = (
    "Ô ảnh Trang nhân thân hộ chiếu ở đầu biểu mẫu (tệp .jpg dưới 2 MB) — tải tay, không thuộc bảng Thành phần hồ sơ."
)
AGENCY_WARNING = (
    "Mục Nơi tiếp nhận hồ sơ: ô Cơ quan tiếp nhận tự chọn cơ quan đã chọn ở bước chọn trường hợp hồ sơ; công dân tự "
    "chọn Nơi nhận kết quả (Nhận trực tiếp / Nhận qua bưu chính) — giấy tờ không ghi."
)


def _visa_symbol(codes: tuple, sentences: tuple = ()) -> str | None:
    """Ký hiệu thẻ / thị thực: ô ký hiệu (trang thị thực, bìa "LĐ2 – lao động …") lấy ở ĐẦU chuỗi; câu tự do (mục đích
    nhập cảnh NA8 "… (thị thực LĐ2)") chỉ nhận ký hiệu đứng sau chữ "thị thực" / "ký hiệu" — đầu câu "DU LỊCH" không phải
    ký hiệu."""
    for value in codes:
        match = _SYMBOL_RE.match((_plain(value) or "").upper())
        if match:
            return match.group(1).upper()
    for value in sentences:
        match = _SYMBOL_IN_TEXT_RE.search(_plain(value) or "")
        if match:
            return match.group(1).upper()
    return None


def _purpose_by_symbol(symbol: str | None) -> str | None:
    key = fold(symbol or "").upper()
    for prefix, option in MUC_DICH_BY_KY_HIEU:
        if key.startswith(prefix):
            return option
    return None


def _to_date(value: str | None) -> date | None:
    try:
        day, month, year = (int(part) for part in (value or "").split("/"))
        return date(year, month, day)
    except (TypeError, ValueError):
        return None


def _is_org(name: str | None, kind: str | None) -> bool:
    if fold(kind or "").replace(" ", "").endswith("na7"):
        return False
    return bool(fold(kind or "").replace(" ", "").endswith("na6") or (name and _ORG_RE.search(fold(name))))


def _org_name(value) -> str | None:
    """Tên cơ quan in hoa có số chú thích "(1)" ở cuối → bỏ chú thích."""
    text = _text(value)
    return re.sub(r"\s*\(\s*\d\s*\)\s*$", "", text).strip() if text else None


def trinh_bay_them(values: dict, symbol: str | None, org: str | None) -> str | None:
    """"Những điều cần trình bày thêm" (bắt buộc, NA8 không có mục) — mapping đề xuất ghi thông tin cơ quan bảo lãnh
    (khối cơ quan đang ẩn) + căn cứ GPLĐ: "Đề nghị cấp thẻ tạm trú ký hiệu LĐ2 theo Văn bản đề nghị số … ngày … của …
    (mã số doanh nghiệp …); Giấy phép lao động số … do … cấp ngày …, thời hạn từ … đến …"."""
    so, ngay = _text(values.get("VanBan_So")), _date(values.get("VanBan_Ngay"))
    mst = re.sub(r"\D", "", _plain(values.get("Bia_MaSoDoanhNghiep")) or "")
    gpld_so = _text(values.get("GPLD_So"))
    if not (so or org or gpld_so):
        return None
    head = f"Đề nghị cấp thẻ tạm trú ký hiệu {symbol}" if symbol else "Đề nghị cấp thẻ tạm trú"
    if so:
        head += f" theo Văn bản đề nghị số {so}" + (f" ngày {ngay}" if ngay else "") + (f" của {org}" if org else "")
    elif org:
        head += f" do {org} bảo lãnh"
    if org and mst:
        head += f" (mã số doanh nghiệp {mst})"
    parts = [head]
    if gpld_so:
        cq, cap = _text(values.get("GPLD_CoQuanCap")), _date(values.get("GPLD_NgayCap"))
        tu, den = _date(values.get("GPLD_TuNgay")), _date(values.get("GPLD_DenNgay"))
        line = f"Giấy phép lao động số {gpld_so}" + (f" do {cq} cấp" if cq else "") + (f" ngày {cap}" if cap else "")
        if tu and den:
            line += f", thời hạn từ {tu} đến {den}"
        parts.append(line)
    return "; ".join(parts) + "."


def enrich(fields: list[dict], options: dict | None = None, *, ghi_chu: str | None = None) -> tuple[list[dict], list[str]]:
    del options
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
        if name in WAIT_MS:
            field["waitMs"] = WAIT_MS[name]
        out.append(field)
        seen.add(name)

    def add_area(area: dict, province: str, ward: str, detail: str) -> None:
        add(province, province_label(canonical_province(area.get("tinh")) or area.get("tinh")) if area.get("tinh") else None)
        add(ward, _plain(area.get("xa")))
        add(detail, _plain(area.get("diaChi")))

    has_form = any(key.startswith("ToKhai_") for key in values)
    mrz = parse_mrz(values.get("HoChieu_MRZ"))
    passport_name = " ".join(filter(None, (_text(values.get("HoChieu_Ho")), _text(values.get("HoChieu_Ten"))))) or \
        " ".join(filter(None, (mrz.get("ho"), mrz.get("ten"))))
    passport_no = mrz.get("so") or _passport_number(values.get("HoChieu_So"))
    form_no = _passport_number(values.get("ToKhai_SoHoChieu"))
    form_name = _text(values.get("ToKhai_HoTen"))
    # Hộ chiếu của người KHÁC → bỏ cả bộ hộ chiếu, lấy theo tờ khai.
    if (passport_name or passport_no) and form_name and not _same_name(passport_name, form_name) and \
            not (passport_no and passport_no == form_no):
        values = {key: value for key, value in values.items() if not key.startswith("HoChieu_")}
        mrz, passport_name, passport_no = {}, "", None
        warnings.append("Hộ chiếu tải lên không phải của người đề nghị ghi trong tờ khai — đã bỏ qua, điền theo tờ khai.")
    applicant = passport_name or form_name
    applicant_no = passport_no or form_no
    # Giấy phép lao động của người khác (cùng cơ quan bảo lãnh nhiều người) → không dùng.
    gpld_name, gpld_no = _text(values.get("GPLD_HoTen")), _passport_number(values.get("GPLD_SoHoChieu"))
    if (gpld_name or gpld_no) and (applicant or applicant_no) and not (
            (gpld_no and gpld_no == applicant_no) or (gpld_name and applicant and _same_name(gpld_name, applicant))):
        values = {key: value for key, value in values.items() if not key.startswith("GPLD_")}
        warnings.append("Giấy phép lao động tải lên không phải của người đề nghị — đã bỏ qua.")

    # ── Phần III: người đề nghị (người nước ngoài) ──
    name = applicant or _text(values.get("GPLD_HoTen"))
    add("CongDan_tenCongDan", " ".join(name.upper().split()) if name else None)
    add("CongDan__fs_BCAGioiTinhCd", _gender(mrz.get("gioiTinh")) or _gender(values.get("HoChieu_GioiTinh"))
        or _gender(values.get("ToKhai_GioiTinh")))
    add("CongDan_ngaySinhCongDan", mrz.get("ngaySinh") or _date(values.get("HoChieu_NgaySinh"))
        or _date(values.get("ToKhai_NgaySinh")))
    nationality = (_country(mrz.get("maQuocGia")) or _country(values.get("HoChieu_MaQuocGia"))
                   or _country(values.get("HoChieu_QuocTich")) or _country(values.get("ToKhai_QuocTichHienNay")))
    origin = _country(values.get("ToKhai_QuocTichGoc"))
    add("CongDan__fs_BCAQuocTichGoc", origin or nationality)
    if not origin and nationality:
        warnings.append("Tờ khai không ghi Quốc tịch gốc — đã điền theo quốc tịch trên hộ chiếu, kiểm tra lại.")
    add("CongDan__fs_BCAQuocTichHienNay", nationality)
    add("CongDan__fs_BCANgheNghiep", _text(values.get("ToKhai_NgheNghiep")) or _text(values.get("GPLD_ChucDanh"))
        or _text(values.get("VanBan_ViTriCongViec")))
    add("CongDan__fs_BCASoHoChieu", passport_no or form_no)
    if passport_no and form_no and passport_no != form_no:
        warnings.append(f"Số hộ chiếu trên tờ khai ({form_no}) khác hộ chiếu tải lên ({passport_no}) — đã điền theo hộ "
                        "chiếu, kiểm tra lại mục 7.")
    add("CongDan__fs_BCALoaiHoChieu", _passport_type(values.get("HoChieu_Loai"))
        or _passport_type(values.get("ToKhai_LoaiHoChieu")))
    add("CongDan__fs_BCACoQuanCap", _text(values.get("HoChieu_CoQuanCap")) or _text(values.get("ToKhai_HoChieu_CoQuanCap")))
    add("CongDan__fs_BCAHoChieuDenNgay", mrz.get("ngayHetHan") or _date(values.get("HoChieu_NgayHetHan"))
        or _date(values.get("ToKhai_HoChieu_DenNgay")))
    add("CongDan__fsDCCUTRU_NUOCNGOAI", _text(values.get("ToKhai_DiaChiCuTruNuocNgoai")))
    add("CongDan__fsDCLAMVIEC_NUOCNGOAI", _text(values.get("ToKhai_NoiLamViecNuocNgoai")))
    add("CongDan__fs_BCANgayNhapCanh", _date(values.get("HoChieu_NhapCanh_Ngay")) or _date(values.get("ToKhai_NgayNhapCanh")))
    add("CongDan__fs_BCAQuaCuaKhau", _border_gate(values.get("HoChieu_NhapCanh_CuaKhau"))
        or _border_gate(values.get("ToKhai_CuaKhau")))
    symbol = _visa_symbol((values.get("HoChieu_ThiThuc_KyHieu"), values.get("Bia_KyHieuThe")),
                          (values.get("ToKhai_MucDichNhapCanh"), values.get("ToKhai_LyDo")))
    add("CongDan__fs_BCAMucDichNhapCanh", _purpose_by_symbol(symbol) or _purpose(values.get("ToKhai_MucDichNhapCanh")))
    add("CongDan__fs_BCATamTruDen", _date(values.get("HoChieu_TamTruDen")) or _date(values.get("ToKhai_TamTruDen")))
    stay = _area(values.get("ToKhai_DiaChiTamTru"))
    if _has_area(stay):
        add_area(stay, "CongDan__fs_BCATinhTamTru", "CongDan__fs_BCAXaTamTru", "CongDan__fs_BCADiaChiTamTru")
    elif has_form:
        warnings.append("Không tách được tỉnh, xã của Địa chỉ tạm trú tại Việt Nam (mục 10) — chọn tay Tỉnh/Thành phố, "
                        "Phường/xã và nhập địa chỉ chi tiết.")
    add("CongDan_diDong", _phone(values.get("ToKhai_DienThoai")))
    add("CongDan_email", _email(values.get("ToKhai_Email")))

    # ── Phần IV: bên bảo lãnh (họ tên / ngày sinh / số giấy tờ readonly theo tài khoản đăng nhập) ──
    has_card = bool(_id_digits(values.get("Cccd_SoDinhDanh")) or _text(values.get("Cccd_HoTen")))
    issued = _date(values.get("Cccd_NgayCap")) if has_card else None
    add("CongDan__fs_BCANgayCapCMNDBaoLanh", issued)
    issuer = _issuer(values.get("Cccd_NoiCap")) if has_card else None
    add("CongDan__fs_BCACoQuanCapCMNDBaoLanh", issuer or (default_issuer(issued) if issued else None))
    org_kind = _text(values.get("VanBan_Loai"))
    sponsor = _org_name(values.get("VanBan_BenBaoLanh"))
    org = sponsor if _is_org(sponsor, org_kind) else None
    relation = _text(values.get("VanBan_QuanHe"))
    if not relation and org:
        labor = bool(_text(values.get("GPLD_So"))) or fold(symbol or "").startswith("ld")
        relation = f"Người sử dụng lao động – {org}" if labor else f"Cơ quan, tổ chức bảo lãnh – {org}"
    add("CongDan__fs_BCAQuanHeNguoiDeNghi", relation)
    home = (_area(values.get("Cccd_NoiCuTru")) if has_card else None)
    home_from_letter = False
    if not _has_area(home):
        home, home_from_letter = _area(values.get("VanBan_DiaChi")), True
    if _has_area(home):
        add_area(home, "CongDan__fs_BCATinhThuongTru", "CongDan__fs_BCAXaThuongTru",
                 "CongDan__fs_BCADiaChiThuongTruVNBaoLanh")
    add("CongDan__fs_BCADiDongBaoLanh", _phone(values.get("VanBan_DienThoai")))
    add("CongDan__fs_BCAEmailBaoLanh", _email(values.get("VanBan_Email")))
    if org:
        warnings.append(
            f"Bên bảo lãnh là cơ quan, tổ chức ({org}) nhưng form khoá \"Thân nhân\" theo tài khoản đăng nhập — đã điền "
            f"Quan hệ \"{relation}\""
            + (" và địa chỉ, điện thoại theo trụ sở trên văn bản đề nghị" if home_from_letter and _has_area(home) else "")
            + "; kiểm tra lại cách khai mục bảo lãnh."
        )
    if not has_card:
        warnings.append("Hồ sơ không có thẻ căn cước của người đăng nhập (bên bảo lãnh) — nhập tay ô Cấp ngày, Cơ quan "
                        "cấp giấy tờ ở mục bảo lãnh.")

    # ── Phần V: nội dung đề nghị ──
    card_until = _date(values.get("ToKhai_The_DenNgay"))
    permit_until = _date(values.get("GPLD_DenNgay"))
    add("CongDan__fs_BCAGiaHanTamTruDenNgay", card_until or permit_until)
    if not card_until and permit_until:
        warnings.append(f"Tờ khai không ghi ngày đề nghị cấp thẻ đến — đã điền theo thời hạn giấy phép lao động "
                        f"({permit_until}), kiểm tra lại.")
    elif card_until and permit_until and (_to_date(card_until) or date.min) > (_to_date(permit_until) or date.max):
        warnings.append(f"Ngày đề nghị cấp thẻ ({card_until}) vượt thời hạn giấy phép lao động ({permit_until}) — thẻ "
                        "tạm trú không được dài hơn giấy phép lao động.")
    add("CongDan__fs_BCALyDoDeNghiCapThiThuc", _text(values.get("ToKhai_LyDo")))
    add("CongDan__fs_BCADieuCanTrinhBayThem", trinh_bay_them(values, symbol, org or sponsor))
    add("HoSoOnline_ghiChu", ghi_chu)

    # ── Cảnh báo ô bắt buộc giấy tờ không có ──
    if has_form or passport_no:
        missing = [
            label for name, label in (
                ("CongDan__fs_BCAQuocTichHienNay", "Quốc tịch hiện nay"),
                ("CongDan__fs_BCANgheNghiep", "Nghề nghiệp/ chức vụ"),
                ("CongDan__fs_BCALoaiHoChieu", "Loại hộ chiếu"),
                ("CongDan__fsDCCUTRU_NUOCNGOAI", "Địa chỉ cư trú ở nước ngoài"),
                ("CongDan__fsDCLAMVIEC_NUOCNGOAI", "Địa chỉ nơi làm việc ở nước ngoài"),
                ("CongDan__fs_BCAMucDichNhapCanh", "Mục đích nhập cảnh"),
                ("CongDan__fs_BCATamTruDen", "Được phép tạm trú đến ngày"),
                ("CongDan_diDong", "Điện thoại liên hệ"),
                ("CongDan_email", "Email liên hệ"),
                ("CongDan__fs_BCAQuanHeNguoiDeNghi", "Quan hệ với người đề nghị"),
                ("CongDan__fs_BCADiDongBaoLanh", "Điện thoại (bên bảo lãnh)"),
                ("CongDan__fs_BCAEmailBaoLanh", "Email liên hệ (bên bảo lãnh)"),
                ("CongDan__fs_BCAGiaHanTamTruDenNgay", "Cấp thẻ tạm trú đến ngày"),
                ("CongDan__fs_BCALyDoDeNghiCapThiThuc", "Lý do"),
                ("CongDan__fs_BCADieuCanTrinhBayThem", "Những điều cần trình bày thêm"),
            ) if name not in seen
        ]
        if missing:
            warnings.append("Giấy tờ không có / không đọc được — nhập tay các ô bắt buộc: " + ", ".join(missing) + ".")
    warnings.append(PHOTO_WARNING)
    warnings.append(AGENCY_WARNING)
    if out:
        # Cơ quan tiếp nhận: chọn mục thật đầu tiên (cùng ô, cùng luật hộ chiếu 1.001456 — user 19/11/2026).
        from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.mapper import agency_field

        out.append(agency_field())
    # Ô liên hệ khối Thân nhân (khoá theo tài khoản) = chủ tài khoản VNeID: cổng đổ sẵn thì giữ (user 20/11/2026).
    keep_portal_values(out, ('CongDan__fs_BCADiDongBaoLanh', 'CongDan__fs_BCAEmailBaoLanh'))
    return out, warnings
