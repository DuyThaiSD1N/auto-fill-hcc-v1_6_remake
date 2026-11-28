"""Dịch dữ kiện đã trích sang ô SurveyJS của biểu mẫu đăng ký thành lập hộ kinh doanh (1.001612, Cổng DVC quốc gia).

Radio "Loại người nộp" quyết định bộ ô (Mapping_Dang_ky_HKD_DVC_Quoc_gia, 2 sheet):
- 1 "Người có thẩm quyền ký giấy đề nghị" (tài khoản = chủ hộ): nhân thân, quốc tịch, dân tộc, thường trú cổng khoá theo
  CSDLQG → chỉ còn điện thoại, email, nơi ở hiện tại.
- 2 "Người được ủy quyền" (tài khoản = người nộp thay): khối người nộp cổng đổ họ tên / ngày sinh / số định danh, còn
  điện thoại, email, nơi ở hiện tại; khối chủ hộ nhập tay toàn bộ.
Chọn theo mốc tài khoản (formContext); thiếu mốc thì theo hồ sơ (có giấy ủy quyền → 2). Phần thông tin hộ kinh doanh
(tên, trụ sở, ngành nghề, vốn, thuế, chủ thể) chung hai trường hợp; luật làm sạch dùng lại của bản HkdOnline.
"""

import re
from typing import Any

from app.pipelines._shared.formatting import upper_person_name
from app.pipelines.cap_phieu_ly_lich_tu_phap_cong_an_cap_tinh.process.mapper import _area, _same_person
from app.pipelines.dang_ky_kinh_doanh.process import mapper as hkd
from app.pipelines.khai_sinh_dvc_moi.process.mapper import _digits, _fold, _full_date
from app.pipelines.khai_sinh_dvc_moi.process.reason import requester_context

from .schema import LOAI_NGUOI_NOP, UI_COMP_BY_NAME

PROCEDURE_KEY = "dang-ky-thanh-lap-ho-kinh-doanh"

CHU_HO = "Người có thẩm quyền ký giấy đề nghị"
UY_QUYEN = "Người được ủy quyền"
_LOAI_NGUOI_NOP_CODE = {CHU_HO: "1", UY_QUYEN: "2"}

CA_NHAN = "Cá nhân"
HO_GIA_DINH = "Các thành viên hộ gia đình"
_CHU_THE_CODE = {CA_NHAN: "CA_NHAN", HO_GIA_DINH: "HO_GIA_DINH"}

KE_KHAI = "Phương pháp kê khai"
_VIET_NAM = "Việt Nam"
# Hình thức nhận kết quả mặc định (người dùng chốt 27/11): option thứ 2 của cổng — nhận tại bộ phận một cửa.
RESULT_METHOD = "Trả kết quả tại bộ phận tiếp nhận và trả kết quả"

# Cấu hình theo tài khoản (server đặt, client không tự bật) — cùng địa bàn với bản HkdOnline nhưng KHOÁ RIÊNG để không
# đụng cờ của luồng đó.
SKIP_START_DATE_OPTION = "hkdDvcqgSkipStartDate"
LINE_DETAIL_OPTION = "hkdDvcqgLineDetail"

KHOAN_WARNING = ("Giấy đề nghị chọn 'Phương pháp khoán' nhưng biểu mẫu cổng chỉ có 'Phương pháp kê khai' — đối chiếu "
                 "với người nộp trước khi nộp.")
HO_GIA_DINH_WARNING = ("Chủ thể thành lập là 'Các thành viên hộ gia đình': nhập tay bảng thành viên hộ gia đình trên "
                       "cổng và đính văn bản ủy quyền của các thành viên vào dòng 2.")
ACCOUNT_WARNING = ("Tài khoản đang nộp không phải chủ hộ cũng không phải bên được ủy quyền trên giấy ủy quyền — tự nhập "
                   "điện thoại, email, nơi ở hiện tại của người nộp.")
PHONE_EMAIL_WARNING = "Giấy tờ không ghi {what} của người nộp — cổng bắt buộc, nhập tay."
CHU_HO_NOT_ACCOUNT_WARNING = ("Tờ khai chọn 'Người có thẩm quyền ký giấy đề nghị' nhưng tài khoản đang đăng nhập không "
                              "phải chủ hộ — cổng lấy nhân thân người nộp theo tài khoản: chủ hộ tự đăng nhập, hoặc sửa tờ "
                              "khai thành 'Người được ủy quyền'.")
UY_QUYEN_IS_ACCOUNT_WARNING = ("Tờ khai chọn 'Người được ủy quyền' nhưng tài khoản đang đăng nhập là chính chủ hộ — kiểm "
                               "tra lại người nộp trên tờ khai.")

# Tờ khai cán bộ nhập trên tab của Auto Fill (khoá options như bản HkdOnline): runner map thẳng, KHÔNG OCR/LLM.
TO_KHAI_OPTION = hkd.TO_KHAI_OPTION
# Lựa chọn người nộp trên tờ khai (cán bộ chọn TRƯỚC khi kê khai) — dữ kiện chỉ có ở luồng tờ khai, LLM không trả.
NGUOI_NOP_FACT = "NguoiNop_Loai"
_TO_KHAI_NGUOI_NOP = {"chu_ho": CHU_HO, "uy_quyen": UY_QUYEN}
_TO_KHAI_CHU_THE = {"ca_nhan": CA_NHAN, "ho_gia_dinh": HO_GIA_DINH}
_LEADING_AMOUNT = re.compile(r"^\s*(\d[\d.,\s]*)")


def with_account_process_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Bản sao options với cờ theo tài khoản: phường Phương Liễu (Bắc Ninh) không điền ngày bắt đầu hoạt động; cách ghi
    cột "Chi tiết ngành nghề" theo địa bàn như bản HkdOnline."""
    result = dict(options or {})
    result.pop(SKIP_START_DATE_OPTION, None)
    result.pop(LINE_DETAIL_OPTION, None)
    if procedure != PROCEDURE_KEY:
        return result
    if hkd.is_bac_ninh_phuong_lieu(user):
        result[SKIP_START_DATE_OPTION] = True
    if mode := hkd.line_detail_mode(user):
        result[LINE_DETAIL_OPTION] = mode
    return result


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


# Cổng kiểm tên hộ kinh doanh: phải bắt đầu bằng "HỘ KINH DOANH", chỉ chữ IN HOA, số và các ký tự dưới đây.
NAME_PREFIX = "HỘ KINH DOANH"
_NAME_PUNCT = set("%&,().-+:\\/;\"“”'‘’*")
_OCR_NAME_LINE = re.compile(r"Tên hộ kinh doanh viết bằng tiếng Việt[^:\n]*:\s*(.+)", re.IGNORECASE)


def _ocr_business_name(name: str, ocr_text: str) -> str:
    """Dòng tên hộ trên OCR Giấy đề nghị cùng chữ với tên LLM trả (chỉ khác dấu) → lấy bản OCR: LLM / lượt sửa dấu hay
    làm mất dấu ("THÀNH" thành "THANH"), OCR chép đúng dấu in trên giấy."""
    for match in _OCR_NAME_LINE.finditer(ocr_text or ""):
        line = hkd._strip_household_prefix(_text(match.group(1)).strip(" .…"))
        if line and _fold(line) == _fold(name):
            return line
    return name


def business_name(value: Any, owner: Any, ocr_text: str = "") -> tuple[str, bool]:
    """(tên hộ kinh doanh theo luật cổng, suy đoán). Thiếu tên → tên chủ hộ (luật bản HkdOnline, ô vàng)."""
    name = hkd._strip_household_prefix(value)
    guessed = not name
    name = _ocr_business_name(name, ocr_text) if name else _text(owner)
    name = "".join(ch for ch in name.upper() if ch.isalnum() or ch.isspace() or ch in _NAME_PUNCT)
    name = _text(name)
    if not name:
        return "", guessed
    return f"{NAME_PREFIX} {name}", guessed


def _truthy(value: Any) -> bool:
    return value is True or _fold(value) in ("true", "co", "1", "x")


def _gender(value: Any) -> str:
    folded = _fold(value)
    if folded in ("nam", "male", "m"):
        return "Nam"
    if folded in ("nu", "female", "f"):
        return "Nữ"
    return ""


def _id12(value: Any) -> str:
    digits = _digits(value)
    return digits if len(digits) == 12 else ""


def _card_of(values: dict, name: Any, number: Any) -> dict:
    """Thẻ căn cước của đúng người (khớp số, thiếu số thì khớp họ tên) trong Cccd_DanhSach — nguồn bù thiếu."""
    cards = values.get("Cccd_DanhSach")
    for card in cards if isinstance(cards, list) else []:
        if isinstance(card, dict) and _same_person(_text(name), _digits(number), card.get("hoTen"),
                                                   card.get("soDinhDanh")):
            return card
    return {}


def facts_from_to_khai(form: dict[str, Any]) -> list[dict]:
    """Tờ khai đã nhập (ToKhaiDvcqg.model_dump()) → dữ kiện cùng tên với LLM trả, để ``enrich`` dùng chung.

    Phần Giấy đề nghị dùng lại hàm của bản HkdOnline (chỉ gọi, không sửa), rồi tách riêng thường trú / nơi ở hiện tại,
    dân tộc, quốc tịch, chủ thể thành lập như biểu mẫu cổng. Bỏ ``ChuHo_DiaChi`` và thẻ căn cước dựng từ tờ khai:
    nơi ở hiện tại để trống thì ``enrich`` lấy thường trú và tô vàng như khi đọc giấy. Người nộp lấy theo lựa chọn trên
    tờ khai, không đoán theo giấy ủy quyền.
    """
    values = {f["name"]: f["value"] for f in hkd.facts_from_to_khai(form)}
    for name in ("ChuHo_DiaChi", "Cccd_DanhSach", "HinhThucDangKy"):
        values.pop(name, None)
    amount = _LEADING_AMOUNT.match(_text(form.get("vonKinhDoanh")))
    values.update({
        "ChuHo_NoiThuongTru": hkd._to_khai_addr(form.get("thuongTru")),
        "ChuHo_NoiOHienTai": hkd._to_khai_addr(form.get("noiO")),
        "ChuHo_DanToc": _text(form.get("danToc")),
        "ChuHo_QuocTich": _text(form.get("quocTich")),
        "ChuTheThanhLap": _TO_KHAI_CHU_THE.get(_text(form.get("chuThe")), ""),
        "TruSo_KhongKinhDoanhTaiTruSo": True if form.get("khongKinhDoanhTaiTruSo") is True else None,
        # "150.000.000 đồng (Một trăm năm mươi triệu đồng)" → chỉ phần bằng số; không có số thì bỏ.
        "Von_SoTien": amount.group(1) if amount else "",
    })
    nguoi_nop = form.get("nguoiNop") if isinstance(form.get("nguoiNop"), dict) else {}
    variant = _TO_KHAI_NGUOI_NOP.get(_text(nguoi_nop.get("loai")), "")
    values[NGUOI_NOP_FACT] = variant
    if variant == UY_QUYEN:
        values.update({
            "UyQuyen_CoGiayUyQuyen": True,
            "UyQuyen_NguoiDuocUyQuyen_HoTen": _text(nguoi_nop.get("hoTen")),
            "UyQuyen_NguoiDuocUyQuyen_SoDinhDanh": _digits(nguoi_nop.get("soDinhDanh")),
            "UyQuyen_NguoiDuocUyQuyen_DienThoai": _text(nguoi_nop.get("dienThoai")),
            "UyQuyen_NguoiDuocUyQuyen_Email": _text(nguoi_nop.get("email")),
            "UyQuyen_NguoiDuocUyQuyen_NoiOHienTai": hkd._to_khai_addr(nguoi_nop.get("noiO")),
        })
    return [{"name": name, "value": value} for name, value in values.items() if value not in (None, "", {}, [])]


def loai_nguoi_nop(values: dict, options: dict | None) -> tuple[str, bool]:
    """(radio loại người nộp, suy đoán). Tờ khai đã chọn → theo lựa chọn đó. Còn lại: tài khoản trùng chủ hộ → 1; khác
    → 2; thiếu mốc tài khoản → có giấy ủy quyền (hoặc đọc được bên được ủy quyền) thì 2, không thì 1 (ô vàng)."""
    chosen = values.get(NGUOI_NOP_FACT)
    if chosen in _LOAI_NGUOI_NOP_CODE:
        return chosen, False
    account_name, account_id = requester_context(options)
    same = _same_person(account_name, account_id, values.get("ChuHo_HoTen"), values.get("ChuHo_SoDinhDanh"))
    if same is not None:
        return (CHU_HO if same else UY_QUYEN), False
    delegated = _truthy(values.get("UyQuyen_CoGiayUyQuyen")) or bool(
        _text(values.get("UyQuyen_NguoiDuocUyQuyen_HoTen")) or _digits(values.get("UyQuyen_NguoiDuocUyQuyen_SoDinhDanh")))
    return (UY_QUYEN if delegated else CHU_HO), True


def business_lines(values: dict, line_mode: str = "") -> tuple[list[dict], list[str]]:
    """Dòng bảng ngành nghề {ma, ten, chiTiet, chinh}: mã 4 số; ``ten`` là tên chuẩn theo mã (danh mục cổng chọn theo tên
    chuẩn), thiếu mã thì tên trên giấy; ``chiTiet`` là tên trên giấy khi khác tên chuẩn (luật cột mô tả của bản
    HkdOnline, kể cả cách ghi theo địa bàn). Đúng MỘT ngành chính."""
    rows: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()
    raw = values.get("NganhNghe_DanhSach")
    for row in raw if isinstance(raw, list) else []:
        if not isinstance(row, dict):
            continue
        code = hkd._clean_business_code(row.get("ma"))
        name = hkd._capitalize_first(row.get("ten"))
        if not (code or name) or (code and code in seen):
            continue
        if code:
            seen.add(code)
        rows.append({"ma": code, "ten": name, "chinh": bool(row.get("chinh"))})
    direct = hkd._clean_business_code(values.get("NganhNghe_MaChinh"))
    if direct and direct not in seen:
        rows.insert(0, {"ma": direct, "ten": hkd._capitalize_first(values.get("NganhNghe_TenChinh")), "chinh": True})
    main = hkd._main_business_code(values)
    if main:
        for row in rows:
            row["chinh"] = row["ma"] == main
    elif rows and not any(row["chinh"] for row in rows):
        rows[0]["chinh"] = True
    else:
        first = next(i for i, row in enumerate(rows) if row["chinh"]) if rows else -1
        for i, row in enumerate(rows):
            row["chinh"] = i == first
    official = hkd._official_line_names()
    out = []
    for row in rows:
        if row["ma"]:
            detail, _replace = hkd.line_detail(row["ma"], row["ten"], line_mode)
            out.append({"ma": row["ma"], "ten": official.get(row["ma"]) or row["ten"], "chiTiet": detail,
                        "chinh": row["chinh"]})
        else:
            out.append({"ma": "", "ten": row["ten"], "chiTiet": row["ten"], "chinh": row["chinh"]})
            warnings.append(f"Ngành '{row['ten']}' chưa có mã ngành cấp 4 — cổng bắt buộc mã cho mọi dòng, chọn tay.")
    return out, warnings


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = {f.get("name"): f.get("value") for f in fields or [] if isinstance(f, dict)}
    options = options or {}
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value, default: bool = False, **extra) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        field = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": value, **extra}
        if default:
            field["default"] = True  # extension tô viền vàng: giá trị không đọc thẳng từ giấy tờ
        out.append(field)
        seen.add(name)

    def add_area(names: tuple[str, str, str], area: dict | None, default: bool = False) -> None:
        if not area:
            return
        add(names[0], area.get("tinh"), default)
        if area.get("tinh"):  # xã nạp theo tỉnh: thiếu tỉnh thì danh mục xã rỗng
            add(names[1], area.get("xa"), default)
        add(names[2], area.get("diaChi"), default)

    phones = hkd._contact_phones(values)
    owner_card = _card_of(values, values.get("ChuHo_HoTen"), values.get("ChuHo_SoDinhDanh"))
    residence = _area(values.get("ChuHo_NoiThuongTru")) or _area(owner_card.get("diaChi") or owner_card.get("chiTietDuoiXa"))
    current = _area(values.get("ChuHo_NoiOHienTai")) or _area(values.get("ChuHo_DiaChi"))
    current_guessed = not current and bool(residence)
    current = current or residence

    variant, guessed = loai_nguoi_nop(values, options)
    # Radio chốt TRƯỚC: cổng ẩn / hiện cả khối ô theo lựa chọn này.
    add(LOAI_NGUOI_NOP, variant, default=guessed, code=_LOAI_NGUOI_NOP_CODE[variant])
    if values.get(NGUOI_NOP_FACT) in _LOAI_NGUOI_NOP_CODE:
        # Lựa chọn trên tờ khai thắng mốc tài khoản, nhưng lệch thì báo: cổng đổ nhân thân người nộp theo tài khoản.
        account_name, account_id = requester_context(options)
        owner = _same_person(account_name, account_id, values.get("ChuHo_HoTen"), values.get("ChuHo_SoDinhDanh"))
        if variant == CHU_HO and owner is False:
            warnings.append(CHU_HO_NOT_ACCOUNT_WARNING)
        elif variant == UY_QUYEN and owner is True:
            warnings.append(UY_QUYEN_IS_ACCOUNT_WARNING)

    if variant == CHU_HO:
        add("citizenPhone1", phones["ChuHo_DienThoai"])
        add("citizenEmail1", hkd._clean_email(values.get("ChuHo_Email")))
        add_area(("tinhThanhhientai", "phuongXahientai", "câu hỏi1__1782221422172"), current, current_guessed)
        missing = [what for name, what in (("citizenPhone1", "điện thoại"), ("citizenEmail1", "thư điện tử"))
                   if name not in seen]
        if missing:
            warnings.append(PHONE_EMAIL_WARNING.format(what=" và ".join(missing)))
    else:
        account_name, account_id = requester_context(options)
        delegate_name = values.get("UyQuyen_NguoiDuocUyQuyen_HoTen")
        delegate_id = values.get("UyQuyen_NguoiDuocUyQuyen_SoDinhDanh")
        # Khối người nộp là của TÀI KHOẢN: chỉ lấy liên hệ / nơi ở của bên được ủy quyền khi đó đúng là tài khoản (hoặc
        # không có mốc tài khoản để so).
        if _same_person(account_name, account_id, delegate_name, delegate_id) is not False:
            delegate_card = _card_of(values, delegate_name, delegate_id)
            add("citizensdt", hkd._clean_phone(values.get("UyQuyen_NguoiDuocUyQuyen_DienThoai")))
            add("citizenEmail", hkd._clean_email(values.get("UyQuyen_NguoiDuocUyQuyen_Email")))
            delegate_current = _area(values.get("UyQuyen_NguoiDuocUyQuyen_NoiOHienTai"))
            delegate_home = _area(values.get("UyQuyen_NguoiDuocUyQuyen_DiaChi")) or _area(
                delegate_card.get("diaChi") or delegate_card.get("chiTietDuoiXa"))
            add_area(("câu hỏi4__1761724625529", "câu hỏi5__1761724625529", "câu hỏi3__1761724625529"),
                     delegate_current or delegate_home, not delegate_current)
            missing = [what for name, what in (("citizensdt", "điện thoại"), ("citizenEmail", "thư điện tử"))
                       if name not in seen]
            if missing:
                warnings.append(PHONE_EMAIL_WARNING.format(what=" và ".join(missing)))
        else:
            warnings.append(ACCOUNT_WARNING)

        # Khối chủ hộ: Giấy đề nghị trước, thẻ căn cước của chủ hộ bù chỗ thiếu.
        owner_id = _id12(values.get("ChuHo_SoDinhDanh")) or _id12(owner_card.get("soDinhDanh"))
        add("citizennguoidangkyhkd", upper_person_name(values.get("ChuHo_HoTen") or owner_card.get("hoTen")))
        add("citizenngaythang", _full_date(values.get("ChuHo_NgaySinh")) or _full_date(owner_card.get("ngaySinh")))
        add("citizengioitinhnguoidangky", _gender(values.get("ChuHo_GioiTinh")) or _gender(owner_card.get("gioiTinh")))
        add("SoDinhdanhcanhanNDK", owner_id)
        add("câu hỏi5__1779097616381", phones["ChuHo_DienThoai"])
        add("câu hỏi1__1782891904359", _text(values.get("ChuHo_Fax")))
        nationality = _text(values.get("ChuHo_QuocTich"))
        add("citizenQuocTich_NDK", nationality or (_VIET_NAM if owner_id else ""), default=not nationality)
        add("citizenDantoc_NDK", _text(values.get("ChuHo_DanToc")))
        add_area(("bảng3__1782890713158", "citizenxanguoidangky", "Diachichitietnoithuongtrunguoidangky"), residence)
        add_area(("Noiohientaitinh", "Noiohientaiphuong", "Noiohientaichitiet"), current, current_guessed)

    # ── Mục 1, 2: tên + trụ sở ──
    name, name_guessed = business_name(values.get("HoKinhDoanh_Ten"), values.get("ChuHo_HoTen"),
                                       str(options.get("_ocr_text") or ""))
    add("tenHoKinhDoanh", name, default=name_guessed)
    add("tenNuocNgoai", _text(values.get("HoKinhDoanh_TenNuocNgoai")))
    add("tenVietTat", _text(values.get("HoKinhDoanh_TenVietTat")))
    office = _area(values.get("TruSo_DiaChi"))
    add("diaChiChiTiet", (office or {}).get("diaChi"))
    if office and (office.get("tinh") or office.get("xa")):
        # Tỉnh / phường trụ sở cổng khoá theo cơ quan đã chọn ở bước "Chọn cơ quan thực hiện".
        place = ", ".join(part for part in (office.get("xa"), office.get("tinh")) if part)
        warnings.append(f"Tỉnh/Phường trụ sở trên cổng khoá theo cơ quan đã chọn — đối chiếu với trụ sở trên Giấy đề "
                        f"nghị ({place}); lệch thì chọn lại cơ quan thực hiện.")
    add("dienThoai", phones["TruSo_DienThoai"])
    add("fax", _text(values.get("TruSo_Fax")))
    add("Thudientu", hkd._clean_email(values.get("TruSo_Email")))
    add("website", _text(values.get("TruSo_Website")))
    if _truthy(values.get("TruSo_KhongKinhDoanhTaiTruSo")):
        add("khongHoatDongTaiTruSo", True)

    # ── Mục 3, 4: ngành nghề + vốn ──
    lines, line_warnings = business_lines(values, str(options.get(LINE_DETAIL_OPTION) or ""))
    add("nganhNgheKinhDoanh", lines)
    warnings.extend(line_warnings)
    add("vonKinhDoanh", str(int(_digits(values.get("Von_SoTien")))) if _digits(values.get("Von_SoTien")) else "")

    # ── Mục 5: thuế ──
    tax = _area(values.get("Thue_DiaChiNhanThongBao"))
    # Chỉ kê khai địa chỉ nhận thông báo thuế khi KHÁC trụ sở (đúng ghi chú trên mẫu và biểu mẫu); lệch một phần coi là
    # khác (thà điền còn hơn bỏ sót) như bản HkdOnline.
    if tax and not (office and all(_fold(tax.get(k)) == _fold(office.get(k)) for k in ("tinh", "xa", "diaChi"))):
        add_area(("câu hỏi8__1782890713158", "câu hỏi9__1782890713158", "câu hỏi7__1782890713158"), tax)
    add("dienThoaiThue", phones["Thue_DienThoai"])
    add("emailThue", hkd._clean_email(values.get("Thue_Email")))
    if not options.get(SKIP_START_DATE_OPTION):
        add("ngayBatDauHoatDong", _full_date(values.get("Thue_NgayBatDau")))
    workers = _digits(values.get("Thue_SoLaoDong"))
    add("soLuongLaoDong", str(int(workers)) if workers else "")
    # Cổng chỉ có một lựa chọn (kê khai) và chọn sẵn: chỉ ghi khi ô còn trống.
    add("phuongPhapTinhThue", KE_KHAI, code="KE_KHAI", onlyIfEmpty=True)
    if "khoan" in _fold(values.get("Thue_PhuongPhapTinh")):
        warnings.append(KHOAN_WARNING)

    # ── Mục 6: chủ thể thành lập ──
    subject = HO_GIA_DINH if "ho gia dinh" in _fold(values.get("ChuTheThanhLap")) else (
        CA_NHAN if "ca nhan" in _fold(values.get("ChuTheThanhLap")) else "")
    add("doiTuongThanhLap", subject or CA_NHAN, default=not subject, code=_CHU_THE_CODE[subject or CA_NHAN])
    if subject == HO_GIA_DINH:
        warnings.append(HO_GIA_DINH_WARNING)

    add("hinhThucNhanKetQua", RESULT_METHOD, default=True)

    raw_id = values.get("ChuHo_SoDinhDanh")
    if raw_id and not _id12(raw_id):
        warnings.append(f"Số định danh chủ hộ đọc được '{raw_id}' không đủ 12 số — đối chiếu Giấy đề nghị.")
    return out, warnings
