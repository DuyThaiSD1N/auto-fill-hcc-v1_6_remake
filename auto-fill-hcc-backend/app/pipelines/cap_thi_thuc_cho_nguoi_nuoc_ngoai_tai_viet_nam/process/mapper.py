"""Dựng ô form ``CongDan__fs*`` / ``CongDan_*`` từ dữ kiện nguồn — thủ tục 1.001194 (Cổng DVC Bộ Công an).

Thứ tự nguồn theo file mapping (cột "Dữ liệu được lấy từ", sheet "Ma trận đa nguồn"):
- Người đề nghị (người nước ngoài): hộ chiếu (trang nhân thân + MRZ có chữ số kiểm tra) → tờ khai NA5 mục I. Quốc
  tịch gốc, nghề nghiệp, mục đích nhập cảnh, địa chỉ tạm trú, điện thoại, email chỉ có trên tờ khai. Ngày nhập cảnh,
  cửa khẩu, tạm trú đến: dấu kiểm chứng trên hộ chiếu → tờ khai.
- Người bảo lãnh: thẻ căn cước (ngày cấp, cơ quan cấp, nơi cư trú) → giấy chứng nhận kết hôn (nơi cư trú, quan hệ) →
  tờ khai mục II.2. Họ tên / ngày sinh / số CCCD là ô readonly cổng lấy từ tài khoản đăng nhập → không phát.
- Địa chỉ tạm trú của người bảo lãnh: tờ khai gộp "thường trú/tạm trú" một dòng mà form tách hai nhóm đều bắt buộc →
  điền trùng địa chỉ thường trú, cảnh báo (mapping ghi "CẦN XÁC NHẬN nghiệp vụ").
- Nội dung đề nghị: tờ khai mục III, IV.
"""

import re
from datetime import date

from app.pipelines._shared import fold
from app.pipelines._shared.area_remap import canonical_province, province_label
from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.process.schema import (
    CODE_BY_VI_NAME,
    COUNTRY_BY_CODE,
    CUA_KHAU_SAN_BAY_PREFIX,
    GIOI_TINH_NAM,
    GIOI_TINH_NU,
    LOAI_HC_CONG_VU,
    LOAI_HC_NGOAI_GIAO,
    LOAI_HC_PHO_THONG,
    MUC_DICH_BY_KEYWORD,
    THI_THUC_MOT_LAN,
    THI_THUC_NHIEU_LAN,
    UI_COMP_BY_NAME,
    WAIT_MS,
)
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.process.mapper import (
    _area,
    _by_name,
    _date,
    _email,
    _issuer,
    _phone,
    _plain,
)

# Dòng 2 MRZ hộ chiếu (ICAO 9303 TD3): số 9 ký tự + kiểm tra, quốc tịch, ngày sinh + kiểm tra, giới tính, hết hạn + kiểm tra.
_MRZ_LINE2_RE = re.compile(r"([A-Z0-9<]{9})(\d)([A-Z<]{3})(\d{6})(\d)([MFX<])(\d{6})(\d)")
# Dòng 1: "P<" + mã nước phát hành + HỌ<<TÊN<ĐỆM.
_MRZ_LINE1_RE = re.compile(r"P[A-Z<]([A-Z<]{3})([A-Z]+(?:<[A-Z]+)*)<<([A-Z]+(?:<[A-Z]+)*)")
_PASSPORT_RE = re.compile(r"^[A-Z0-9]{5,9}$")
_MARK = r"[☐☒☑✓✔xX□■]"
_VISA_LINE_RE = re.compile(r"c[ấa]p\s+th[ịi]\s+th[ựu]c\s*:?(.{0,160})", re.IGNORECASE | re.DOTALL)
_FOOTNOTE_RE = re.compile(r"\s*\(\s*\d\s*\)\s*$")

PHOTO_WARNING = (
    "Đầu biểu mẫu có 2 ô tải ảnh .jpg dưới 2 MB: Ảnh chân dung 4x6 nền trắng của người đề nghị (hồ sơ thường chưa có) và "
    "ảnh Trang nhân thân hộ chiếu — tải tay, không thuộc bảng Thành phần hồ sơ."
)
AGENCY_WARNING = (
    "Mục Nơi tiếp nhận hồ sơ: ô Cơ quan tiếp nhận theo cơ quan đã chọn ở bước chọn trường hợp hồ sơ; tự chọn Nơi nhận "
    "thị thực (Nhận trực tiếp / Nhận qua bưu chính) — giấy tờ không ghi."
)


def _text(value) -> str | None:
    """Chuỗi một dòng; ô chấm chấm / "trống" / "không" coi như không có."""
    text = _plain(value)
    if not text or not re.search(r"[0-9A-Za-zÀ-ỹ]", text):
        return None
    if fold(text) in ("trong", "khong", "khong co", "khong ap dung"):
        return None
    return text


def _words(value) -> frozenset[str]:
    return frozenset(re.sub(r"[^a-z0-9 ]", " ", fold(_plain(value) or "")).split())


def _same_name(left, right) -> bool:
    """Tên người nước ngoài hay đảo thứ tự (Surname trước / sau) → so tập chữ."""
    a, b = _words(left), _words(right)
    return bool(a) and a == b


def _check_digit(text: str) -> int:
    total = 0
    for i, char in enumerate(text):
        value = int(char) if char.isdigit() else (ord(char) - 55 if char.isalpha() else 0)
        total += value * (7, 3, 1)[i % 3]
    return total % 10


def _mrz_date(yymmdd: str, *, future: bool) -> str | None:
    yy, mm, dd = int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:])
    year = 2000 + yy if future or 2000 + yy <= date.today().year else 1900 + yy
    try:
        return date(year, mm, dd).strftime("%d/%m/%Y")
    except ValueError:
        return None


def parse_mrz(value) -> dict:
    """Dòng MRZ → {so, maQuocGia, ngaySinh, gioiTinh, ngayHetHan, ho, ten}; mỗi phần chỉ nhận khi đúng chữ số kiểm tra."""
    out: dict = {}
    raw = str(value or "").upper()
    compact = re.sub(r"\s", "", raw)
    line2 = _MRZ_LINE2_RE.search(compact)
    if line2:
        number, n_check, nation, dob, dob_check, sex, expiry, exp_check = line2.groups()
        if _check_digit(number) == int(n_check) and _PASSPORT_RE.match(number.rstrip("<")):
            out["so"] = number.rstrip("<")
            out["maQuocGia"] = nation.strip("<")
        if _check_digit(dob) == int(dob_check):
            out["ngaySinh"] = _mrz_date(dob, future=False)
        if _check_digit(expiry) == int(exp_check):
            out["ngayHetHan"] = _mrz_date(expiry, future=True)
        if sex in "MF":
            out["gioiTinh"] = sex
    for token in raw.split():
        line1 = _MRZ_LINE1_RE.match(token)
        if line1:
            out["ho"] = line1.group(2).replace("<", " ").strip()
            out["ten"] = line1.group(3).replace("<", " ").strip()
            break
    return {key: val for key, val in out.items() if val}


def _passport_number(value) -> str | None:
    compact = re.sub(r"[\s.\-]", "", _plain(value) or "").upper()
    return compact if _PASSPORT_RE.match(compact) and re.search(r"\d", compact) else None


def _country(value) -> str | None:
    """Tên nước / mã ICAO trên giấy → tên tiếng Anh của danh mục cổng ("Ca-na-đa" / "CANADA" / "CAN" → "Canada")."""
    text = _text(value)
    if not text:
        return None
    upper = text.strip().upper()
    if upper in COUNTRY_BY_CODE:
        return COUNTRY_BY_CODE[upper]
    key = " ".join(re.sub(r"[^a-z ]", " ", fold(text).replace("-", " ")).split())
    if key in CODE_BY_VI_NAME:
        return COUNTRY_BY_CODE[CODE_BY_VI_NAME[key]]
    for name in COUNTRY_BY_CODE.values():
        if fold(name) == key:
            return name
    return text.title() if re.fullmatch(r"[A-Za-z .'\-]+", text) else None


def _gender(value) -> str | None:
    folded = fold(_plain(value) or "")
    if folded in ("m", "nam", "male"):
        return GIOI_TINH_NAM
    if folded in ("f", "nu", "female"):
        return GIOI_TINH_NU
    return None


def _passport_type(value) -> str | None:
    folded = fold(_plain(value) or "")
    if not folded:
        return None
    if folded in ("p", "pp") or "pho thong" in folded or "ordinary" in folded:
        return LOAI_HC_PHO_THONG
    if folded in ("d", "pd") or "ngoai giao" in folded or "diplomatic" in folded:
        return LOAI_HC_NGOAI_GIAO
    if folded in ("s", "o", "ps", "po") or "cong vu" in folded or "official" in folded or "service" in folded:
        return LOAI_HC_CONG_VU
    return None


def _border_gate(value) -> str | None:
    """"Cửa khẩu Sân bay quốc tế Nội Bài" → "SBQT Nội Bài" (option cổng); cửa khẩu khác bỏ tiền tố, khớp chứa chữ."""
    text = _text(value)
    if not text:
        return None
    airport = re.sub(r"^(c[ửu]a\s+kh[ẩa]u\s+)?(c[ảa]ng\s+h[àa]ng\s+kh[ôo]ng\s+qu[ốo]c\s+t[ếe]|s[âa]n\s+bay\s+qu[ốo]c\s+t[ếe]"
                     r"|sbqt)\s+", "", text, flags=re.IGNORECASE)
    if airport != text:
        return f"{CUA_KHAU_SAN_BAY_PREFIX} {airport.strip()}"
    return re.sub(r"^c[ửu]a\s+kh[ẩa]u\s+(qu[ốo]c\s+t[ếe]\s+|ch[íi]nh\s+|ph[ụu]\s+)?", "", text, flags=re.IGNORECASE).strip()


def _purpose(value) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = fold(text)
    for keyword, option in MUC_DICH_BY_KEYWORD:
        if keyword in folded:
            return option
    return text


def _visa_entries(value) -> str | None:
    folded = fold(_plain(value) or "").replace("_", " ")
    if "nhieu" in folded or "multiple" in folded:
        return THI_THUC_NHIEU_LAN
    if "mot" in folded or "single" in folded:
        return THI_THUC_MOT_LAN
    return None


def _relation(value) -> str | None:
    text = _text(value)
    return _FOOTNOTE_RE.sub("", text).strip() if text else None


def _id_digits(value) -> str | None:
    digits = re.sub(r"\D", "", _plain(value) or "")
    return digits if len(digits) in (9, 12) else None


def _has_area(area: dict | None) -> bool:
    return bool(area and (area.get("tinh") or area.get("xa")))


def ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    """compact_field_fallback: dòng MRZ luôn dò lại từ chữ OCR (chữ số kiểm tra chắc hơn LLM chép); ô "một lần / nhiều
    lần" mục III.1 LLM bỏ sót thì đọc thứ tự dấu đánh dấu sau nhãn "Cấp thị thực"."""
    if isinstance(raw_fields, dict):
        fields = dict(raw_fields)
    else:
        fields = {item.get("name"): item.get("value") for item in raw_fields or []
                  if isinstance(item, dict) and item.get("name")}
    for doc in documents or []:
        text = str(doc.get("text") or "")
        if not parse_mrz(fields.get("HoChieu_MRZ")).get("so"):
            lines = [line.strip().replace(" ", "") for line in text.upper().splitlines()]
            mrz = [line for line in lines if _MRZ_LINE1_RE.match(line) or _MRZ_LINE2_RE.search(line)]
            if parse_mrz("\n".join(mrz)).get("so"):
                fields["HoChieu_MRZ"] = "\n".join(mrz)
        if not _text(fields.get("ToKhai_LoaiThiThuc")) and re.search(r"t[ờo]\s+khai", text, re.IGNORECASE):
            match = _VISA_LINE_RE.search(text)
            marks = re.findall(_MARK, match.group(1)) if match else []
            if len(marks) >= 2:
                checked = [m not in "☐□" for m in marks[:2]]
                if checked == [False, True]:
                    fields["ToKhai_LoaiThiThuc"] = "nhieu_lan"
                elif checked == [True, False]:
                    fields["ToKhai_LoaiThiThuc"] = "mot_lan"
    return fields


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
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
    # Hộ chiếu của người KHÁC (nộp nhầm của người đi cùng) → bỏ cả bộ hộ chiếu, lấy theo tờ khai.
    if (passport_name or passport_no) and form_name and not _same_name(passport_name, form_name) and \
            not (passport_no and passport_no == form_no):
        values = {key: value for key, value in values.items() if not key.startswith("HoChieu_")}
        mrz, passport_name, passport_no = {}, "", None
        warnings.append("Hộ chiếu tải lên không phải của người đề nghị ghi trong tờ khai — đã bỏ qua, điền theo tờ khai.")
    has_passport = bool(passport_no or passport_name)

    # ── Phần II: người đề nghị ──
    name = passport_name or form_name
    add("CongDan_tenCongDan", " ".join(name.upper().split()) if name else None)
    add("CongDan_ngaySinhCongDan", mrz.get("ngaySinh") or _date(values.get("HoChieu_NgaySinh"))
        or _date(values.get("ToKhai_NgaySinh")))
    add("CongDan__fs_BCAGioiTinhCd", _gender(mrz.get("gioiTinh")) or _gender(values.get("HoChieu_GioiTinh"))
        or _gender(values.get("ToKhai_GioiTinh")))
    nationality = (_country(mrz.get("maQuocGia")) or _country(values.get("HoChieu_MaQuocGia"))
                   or _country(values.get("HoChieu_QuocTich")) or _country(values.get("ToKhai_QuocTichHienNay")))
    add("CongDan__fs_BCAQuocTichHienNay", nationality)
    add("CongDan__fs_BCAQuocTichGoc", _country(values.get("ToKhai_QuocTichGoc")))
    add("CongDan__fs_BCANgheNghiep", _text(values.get("ToKhai_NgheNghiep")))
    add("CongDan__fs_BCASoHoChieu", passport_no or form_no)
    if passport_no and form_no and passport_no != form_no:
        warnings.append(f"Số hộ chiếu trên tờ khai ({form_no}) khác hộ chiếu tải lên ({passport_no}) — đã điền theo hộ "
                        "chiếu, kiểm tra lại mục I.7.")
    passport_type = _passport_type(values.get("HoChieu_Loai")) or _passport_type(values.get("ToKhai_LoaiHoChieu"))
    add("CongDan__fs_BCALoaiHoChieu", passport_type)
    add("CongDan__fs_BCACoQuanCap", _text(values.get("HoChieu_CoQuanCap")) or _text(values.get("ToKhai_HoChieu_CoQuanCap")))
    add("CongDan__fs_BCAHoChieuDenNgay", mrz.get("ngayHetHan") or _date(values.get("HoChieu_NgayHetHan"))
        or _date(values.get("ToKhai_HoChieu_DenNgay")))
    add("CongDan__fs_BCANgayNhapCanh", _date(values.get("HoChieu_NhapCanh_Ngay")) or _date(values.get("ToKhai_NgayNhapCanh")))
    add("CongDan__fs_BCAQuaCuaKhau", _border_gate(values.get("HoChieu_NhapCanh_CuaKhau"))
        or _border_gate(values.get("ToKhai_CuaKhau")))
    add("CongDan__fs_BCATamTruDen", _date(values.get("HoChieu_TamTruDen")) or _date(values.get("ToKhai_TamTruDen")))
    add("CongDan__fs_BCAMucDichNhapCanh", _purpose(values.get("ToKhai_MucDichNhapCanh")))

    stay = _area(values.get("ToKhai_DiaChiTamTru"))
    if _has_area(stay):
        add_area(stay, "CongDan__fs_BCATinhTamTru", "CongDan__fs_BCAXaTamTru", "CongDan__fs_BCADiaChiTamTru")
    elif has_form:
        warnings.append("Không tách được tỉnh, xã của Địa chỉ tạm trú tại Việt Nam (mục I.9) — chọn tay Tỉnh/Thành phố, "
                        "Phường/xã và nhập địa chỉ chi tiết.")
    add("CongDan_diDong", _phone(values.get("ToKhai_DienThoai")))
    add("CongDan_email", _email(values.get("ToKhai_Email")))

    # ── Phần III: thân nhân bảo lãnh ──
    sponsor_name = _text(values.get("ToKhai_BaoLanh_HoTen"))
    sponsor_id = _id_digits(values.get("ToKhai_BaoLanh_SoGiayTo"))
    card_id = _id_digits(values.get("Cccd_SoDinhDanh"))
    card_name = _text(values.get("Cccd_HoTen"))
    if (card_id or card_name) and (sponsor_id or sponsor_name) and not (
            (card_id and card_id == sponsor_id) or (card_name and sponsor_name and _same_name(card_name, sponsor_name))):
        values = {key: value for key, value in values.items() if not key.startswith("Cccd_")}
        card_id = card_name = None
        warnings.append("Thẻ căn cước tải lên không phải của người bảo lãnh ghi trong tờ khai — đã bỏ qua.")
    has_card = bool(card_id or card_name)
    if _text(values.get("ToKhai_CoQuanBaoLanh")):
        warnings.append(f"Tờ khai ghi cơ quan, tổ chức bảo lãnh \"{_text(values.get('ToKhai_CoQuanBaoLanh'))}\" — form "
                        "đang khoá \"Thân nhân\" theo tài khoản đăng nhập; kiểm tra lại người nộp hồ sơ.")

    issued = (_date(values.get("Cccd_NgayCap")) if has_card else None) or _date(values.get("ToKhai_BaoLanh_NgayCap"))
    add("CongDan__fs_BCANgayCapCMNDBaoLanh", issued)
    issuer = _issuer(values.get("Cccd_NoiCap")) if has_card else None
    if not issuer and has_card and issued:
        issuer = default_issuer(issued)
    add("CongDan__fs_BCACoQuanCapCMNDBaoLanh", issuer or _issuer(values.get("ToKhai_BaoLanh_CoQuanCap")))
    card_no = _text(values.get("ToKhai_BaoLanh_TheTamTruSo"))
    add("CongDan__fs_BCATheTamTruSo", card_no)
    if card_no:
        add("CongDan__fs_BCANgayCapTheTamTruSo", _date(values.get("ToKhai_BaoLanh_TheTamTru_NgayCap")))
        add("CongDan__fs_BCACoQuanCapTheTamTruSo", _text(values.get("ToKhai_BaoLanh_TheTamTru_CoQuanCap")))

    relation = _relation(values.get("ToKhai_BaoLanh_QuanHe"))
    wife, husband = _text(values.get("KetHon_Vo_HoTen")), _text(values.get("KetHon_Chong_HoTen"))
    sponsor_ref = sponsor_name or card_name
    if not relation and sponsor_ref:
        relation = "Vợ" if wife and _same_name(wife, sponsor_ref) else ("Chồng" if husband and _same_name(husband, sponsor_ref)
                                                                           else None)
    add("CongDan__fs_BCAQuanHeNguoiDeNghi", relation)

    # Nơi cư trú người bảo lãnh: CCCD (địa giới mới) → cột của người bảo lãnh trên giấy kết hôn → tờ khai mục II.2.
    kh_home = None
    if sponsor_ref and wife and _same_name(wife, sponsor_ref):
        kh_home = _area(values.get("KetHon_Vo_NoiCuTru"))
    elif sponsor_ref and husband and _same_name(husband, sponsor_ref):
        kh_home = _area(values.get("KetHon_Chong_NoiCuTru"))
    home = next((area for area in (_area(values.get("Cccd_NoiCuTru")) if has_card else None, kh_home,
                                   _area(values.get("ToKhai_BaoLanh_DiaChi"))) if _has_area(area)), None)
    if home:
        add_area(home, "CongDan__fs_BCATinhThuongTru", "CongDan__fs_BCAXaThuongTru",
                 "CongDan__fs_BCADiaChiThuongTruVNBaoLanh")
        add_area(home, "CongDan__fs_BCATinhTamTruBaoLanh", "CongDan__fs_BCAXaTamTruBaoLanh",
                 "CongDan__fs_BCADiaChiTamTruBaoLanh")
        warnings.append("Địa chỉ tạm trú tại Việt Nam của người bảo lãnh: giấy tờ chỉ ghi một địa chỉ (thường trú/tạm "
                        "trú) — đã điền trùng địa chỉ thường trú, sửa lại nếu người bảo lãnh tạm trú nơi khác.")
    elif has_form:
        warnings.append("Không tách được tỉnh, xã của địa chỉ người bảo lãnh — chọn tay hai nhóm Địa chỉ thường trú / "
                        "tạm trú tại Việt Nam (mục III).")
    add("CongDan__fs_BCADiDongBaoLanh", _phone(values.get("ToKhai_BaoLanh_DienThoai")))
    add("CongDan__fs_BCAEmailBaoLanh", _email(values.get("ToKhai_BaoLanh_Email")))

    # ── Phần IV: nội dung đề nghị ──
    entries = _visa_entries(values.get("ToKhai_LoaiThiThuc"))
    add("CongDan__fs_BCACapThiThucLan", entries)
    add("CongDan__fs_BCAThiThucDenNgay", _date(values.get("ToKhai_ThiThuc_DenNgay")))
    add("CongDan__fs_BCALyDoDeNghiCapThiThuc", _text(values.get("ToKhai_LyDo")))
    add("CongDan__fs_BCADieuCanTrinhBayThem", _text(values.get("ToKhai_TrinhBayThem")))
    if _date(values.get("ToKhai_GiaHan_DenNgay")):
        warnings.append("Tờ khai có ghi \"Gia hạn tạm trú đến ngày\" (mục III.2) — thủ tục này chỉ cấp thị thực; gia hạn "
                        "tạm trú làm ở thủ tục riêng.")

    # ── Cảnh báo ô bắt buộc giấy tờ không có ──
    if has_form or has_passport:
        missing = [
            (name, label) for name, label in (
                ("CongDan__fs_BCAQuocTichGoc", "Quốc tịch gốc"),
                ("CongDan__fs_BCAQuocTichHienNay", "Quốc tịch hiện nay"),
                ("CongDan__fs_BCANgheNghiep", "Nghề nghiệp/ chức vụ"),
                ("CongDan__fs_BCALoaiHoChieu", "Loại hộ chiếu (cổng để sẵn \"Khác\")"),
                ("CongDan__fs_BCAMucDichNhapCanh", "Mục đích nhập cảnh"),
                ("CongDan__fs_BCATamTruDen", "Được phép tạm trú đến ngày"),
                ("CongDan_diDong", "Điện thoại"),
                ("CongDan_email", "Email liên hệ"),
                ("CongDan__fs_BCAQuanHeNguoiDeNghi", "Quan hệ với người đề nghị"),
                ("CongDan__fs_BCANgayCapCMNDBaoLanh", "Cấp ngày (CCCD người bảo lãnh)"),
                ("CongDan__fs_BCADiDongBaoLanh", "Điện thoại (người bảo lãnh)"),
                ("CongDan__fs_BCAEmailBaoLanh", "Email liên hệ (người bảo lãnh)"),
                ("CongDan__fs_BCAThiThucDenNgay", "Có giá trị đến ngày (thị thực)"),
                ("CongDan__fs_BCALyDoDeNghiCapThiThuc", "Lý do"),
            ) if name not in seen
        ]
        if missing:
            warnings.append("Giấy tờ không có / không đọc được — nhập tay các ô bắt buộc: "
                            + ", ".join(label for _, label in missing) + ".")
        if not entries:
            warnings.append("Tờ khai không thấy rõ ô \"một lần / nhiều lần\" (mục III.1) — cổng để sẵn \"Nhiều lần\", "
                            "kiểm tra lại.")
    warnings.append(PHOTO_WARNING)
    warnings.append(AGENCY_WARNING)
    return out, warnings
