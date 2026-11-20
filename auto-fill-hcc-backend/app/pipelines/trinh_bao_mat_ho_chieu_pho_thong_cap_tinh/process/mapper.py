"""Dựng ô form ``CongDan__fs*`` / ``CongDan_*`` từ dữ kiện nguồn — thủ tục 1.001445 (Cổng DVC Bộ Công an, cấp tỉnh).

Thứ tự nguồn theo file mapping "Mapping_Trinh_bao_mat_ho_chieu_1.001445" (sheet "Ma trận đa nguồn"):
- Ngày cấp ĐDCN/CMND: CCCD (khi cùng người với đơn / tờ khai) → tờ khai TK01 mục 4. Đơn TK05 không có mục này; "ngày cấp"
  ở mục 7 đơn là của HỘ CHIẾU.
- Nơi cấp CMND/CCCD (ô chữ): CCCD mặt sau → suy theo ngày cấp (``default_issuer``). "Cơ quan cấp" ở mục 7 đơn là của hộ
  chiếu, không dùng.
- Số điện thoại: đơn mục 6 → tờ khai mục 7. Email: giấy tờ không có (tờ khai có ghi thì lấy).
- Địa chỉ nơi cư trú hiện nay: đơn mục 5 "Nơi cư trú hiện tại" (đã theo đơn vị hành chính mới) → tờ khai mục 8 → CCCD.
  Mapping xếp CCCD trước nhưng ghi rõ CCCD cấp trước 01/07/2025 có thể in địa giới cũ → ưu tiên đối chiếu đơn / tờ khai.
  Tờ khai mục 11 (địa chỉ cơ quan) và "Địa chỉ nhận hộ chiếu" KHÔNG dùng.
- Thông tin trình báo (số / ngày cấp / cơ quan cấp hộ chiếu, ngày mất, lý do): đơn mục 7–9 → tờ khai mục 13 / 14.
- Cơ quan tiếp nhận (ô 17): chỉ có Phòng Quản lý XNC Công an tỉnh đã chọn ở bước chọn trường hợp hồ sơ → ``agency_field``
  cờ ``firstOption`` như hộ chiếu 1.001456.

Ô khoá (họ tên, giới tính, ngày sinh, số ĐDCN) cổng lấy theo tài khoản VNeID → không phát. Có ``options.formContext``
(Auto Fill / trợ lý đọc hai ô readonly ``CongDan_tenCongDan`` / ``CongDan_soCmnd``) mà giấy tờ là của người khác (user
20/11/2026, như hộ chiếu 1.001456):
- người trên giấy từ đủ 14 tuổi (hoặc không rõ ngày sinh) → CHẶN, không điền ô nào (``account_block``; runner gắn
  ``result["blocked"]`` để Auto Fill / trợ lý hiện câu báo);
- người trên giấy dưới 14 tuổi → cha, mẹ, người đại diện trình báo thay (dòng 1 bảng Thành phần hồ sơ): điền khối địa
  chỉ + thông tin trình báo, bỏ các ô của người đề nghị (ngày cấp / nơi cấp CCCD, số điện thoại, email) và cảnh báo.
"""

import re
from datetime import date, datetime

from app.pipelines._shared import fold
from app.pipelines._shared.area_remap import canonical_province, province_label
from app.pipelines._shared.compact_agent.issuer import default_issuer
# Email: làm sạch chung các thủ tục Bộ Công an (dấu phẩy OCR, tên miền đọc lệch), user 19/11/2026.
from app.pipelines._shared.formatting import clean_email as _email
from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.mapper import _passport_number, agency_field
from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.process.mapper import (
    _area,
    _by_name,
    _date,
    _issuer,
    _phone,
    _plain,
    _same_person,
)
from app.pipelines.trinh_bao_mat_ho_chieu_pho_thong_cap_tinh.process.schema import UI_COMP_BY_NAME, WAIT_MS
from app.pipelines._shared.formatting import keep_portal_values

EMAIL_WARNING = "Giấy tờ không có email — ô Email (*) cần nhập tay."
AGENCY_WARNING = (
    "Mục Nơi tiếp nhận hồ sơ: ô Cơ quan tiếp nhận (*) chỉ có Phòng Quản lý xuất nhập cảnh của tỉnh đã chọn ở bước chọn "
    "trường hợp hồ sơ — hệ thống chọn mục đó; kiểm tra đúng tỉnh muốn nộp."
)
NOT_REMEMBER_WARNING = "Đơn trình báo ghi không nhớ số hộ chiếu bị mất — ô Số hộ chiếu bị mất để trống."
NO_ACCOUNT_WARNING = (
    "Chưa đối chiếu được giấy tờ với tài khoản VNeID đang đăng nhập (không đọc được ô Họ và tên / Số ĐDCN trên form) — "
    "kiểm tra giấy tờ đúng là của chủ tài khoản trước khi nộp."
)
ACCOUNT_MISMATCH_CODE = "account_mismatch"

# Mục 9 đơn TK05: đoạn văn sau nhãn tới dòng "Làm tại …" / "Người trình báo" / phần ghi chú.
_REASON_RE = re.compile(
    r"9\.\s*Ho[àa]n\s+c[ảa]nh\s+v[àa]\s+l[ýy]\s+do\s+c[ụu]\s+th[ểe]\s+(?:b[ịi]\s+)?m[ấa]t\s+h[ộo]\s+chi[ếe]u\s*:?\s*"
    r"(.+?)(?=\n\s*(?:L[àa]m\s+t[ạa]i|Ng[ưu][ờo]i\s+tr[ìi]nh\s+b[áa]o|Ghi\s+ch[úu])|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_LOST_DATE_RE = re.compile(r"8\.\s*H[ộo]\s+chi[ếe]u\s+tr[êe]n\s+đ[ãa]\s+b[ịi]\s+m[ấa]t.{0,80}?ng[àa]y\s*:?\s*"
                           r"(\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{4})", re.IGNORECASE | re.DOTALL)
_LOST_NUMBER_RE = re.compile(r"S[ốo]\s+h[ộo]\s+chi[ếe]u\s*:?\s*([A-Z]\s?\d{7,8})\b")
_REPORT_TITLE_RE = re.compile(r"đ[ơo]n\s+tr[ìi]nh\s+b[áa]o\s+m[ấa]t\s+h[ộo]\s+chi[ếe]u", re.IGNORECASE)
# "Kính gửi: Công an xã …" — đơn gửi cấp xã trong khi thủ tục này nộp tại Phòng Quản lý XNC Công an tỉnh.
_COMMUNE_AGENCY_RE = re.compile(r"\bcong an (xa|phuong|thi tran|dac khu)\b")


def _text(value) -> str | None:
    """Chuỗi một dòng; ô chấm chấm / "trống" / "không" coi như không có."""
    text = _plain(value)
    if not text or not re.search(r"[0-9A-Za-zÀ-ỹ]", text):
        return None
    if fold(text) in ("trong", "khong", "khong co", "khong ap dung"):
        return None
    return text


def _not_remember(value) -> bool:
    return "khong nho" in fold(_plain(value) or "")


def _paragraph(value) -> str | None:
    """Đoạn văn nguyên văn: OCR / LLM xuống dòng theo khổ giấy → nối lại thành một đoạn, giữ nguyên chữ và dấu câu."""
    if not isinstance(value, str):
        return None
    text = " ".join(value.split()).strip()
    return text if re.search(r"[0-9A-Za-zÀ-ỹ]", text) else None


def _id_number(value) -> str | None:
    digits = re.sub(r"\D", "", _plain(value) or "")
    return digits if len(digits) in (12, 9) else None


def _shouting_fix(text: str | None) -> str | None:
    """"XÃ KHỔNG Lào" / "tỉnh LAI CHÂU" (đơn viết tay in hoa lẫn thường) → "Xã Khổng Lào" / "Tỉnh Lai Châu"."""
    text = _plain(text)
    if not text:
        return None
    if any(len(word) > 1 and word.isupper() for word in text.split()) or text[0].islower():
        return " ".join(word[:1].upper() + word[1:].lower() for word in text.split())
    return text


def _residence(*values) -> dict | None:
    for value in values:
        area = _area(value)
        if area and (area.get("tinh") or area.get("xa")):
            return area
    return None


def _applicant(values: dict) -> tuple[str | None, str | None]:
    """(họ tên, số định danh) của người trên giấy: đơn TK05 → tờ khai TK01 → CCCD."""
    name = None
    for prefix in ("DonTrinhBao_", "ToKhai_"):
        name = " ".join(filter(None, (_text(values.get(prefix + "Ho")), _text(values.get(prefix + "ChuDemTen")))))
        if name:
            break
    name = name or _text(values.get("Cccd_HoTen"))
    number = (_id_number(values.get("DonTrinhBao_SoDinhDanh")) or _id_number(values.get("ToKhai_SoDinhDanh"))
              or _id_number(values.get("Cccd_SoDinhDanh")))
    return name, number


def has_account_anchor(options: dict | None) -> bool:
    """Auto Fill / trợ lý đọc được ô khoá Họ và tên / Số ĐDCN của khối Người đề nghị (``options.formContext``)."""
    context = (options or {}).get("formContext") or {}
    return any(context.get(key) for key in ("applicantIdentityNumber", "identityNumber", "applicantFullname"))


def _other_person(values: dict, options: dict | None) -> tuple[str, str] | None:
    """(chủ tài khoản, người trên giấy) khi giấy tờ là của người KHÁC chủ tài khoản VNeID đang đăng nhập (so số định
    danh trước; số lệch mà tên trùng thì coi là OCR đọc lệch số). Không có mốc tài khoản / không đủ dữ kiện → None."""
    context = (options or {}).get("formContext") or {}
    account_id = _id_number(context.get("applicantIdentityNumber") or context.get("identityNumber"))
    account_name = _text(context.get("applicantFullname"))
    doc_name, doc_id = _applicant(values)
    if account_id and doc_id and len(account_id) == len(doc_id):
        mismatch = account_id != doc_id and not (account_name and doc_name and _same_person(account_name, doc_name))
    elif account_name and doc_name:
        mismatch = not _same_person(account_name, doc_name)
    else:
        return None
    if not mismatch:
        return None
    account = account_name.upper() if account_name else f"người có số định danh {account_id}"
    document = doc_name.upper() if doc_name else f"người có số định danh {doc_id}"
    return account, document


def _under_14(values: dict, today: date | None = None) -> bool:
    """Người bị mất hộ chiếu (theo ngày sinh mục 3 đơn → tờ khai → CCCD) chưa đủ 14 tuổi. Không đọc được ngày sinh →
    False (coi như người thành niên tự trình báo)."""
    for key in ("DonTrinhBao_NgaySinh", "ToKhai_NgaySinh", "Cccd_NgaySinh"):
        text = _date(values.get(key))
        if not text:
            continue
        born = datetime.strptime(text, "%d/%m/%Y").date()
        today = today or date.today()
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return 0 <= age < 14
    return False


def account_block(values: dict, options: dict | None, today: date | None = None) -> dict | None:
    """``{code, message, accountName, documentName}`` khi giấy tờ là của người KHÁC chủ tài khoản VNeID, ngược lại None.

    Khối Người đề nghị (họ tên, giới tính, ngày sinh, số ĐDCN) cổng khoá theo CSDL dân cư của tài khoản đăng nhập; số
    điện thoại, email, ngày cấp / nơi cấp CCCD, nơi cư trú cùng khối là của CHÍNH người đó → điền giấy của người khác chỉ
    ra form trộn hai người (ảnh chạy thật 20/11: SĐT của người trên giấy vào hồ sơ của chủ tài khoản). Như hộ chiếu
    1.001456: chặn, không điền gì. Ngoại lệ: người trên giấy dưới 14 tuổi → cha, mẹ, người đại diện trình báo thay (dòng 1
    bảng Thành phần hồ sơ), không chặn (``enrich`` chỉ bỏ các ô của người đề nghị).
    """
    other = _other_person(values, options)
    if not other or _under_14(values, today):
        return None
    account, document = other
    return {
        "code": ACCOUNT_MISMATCH_CODE,
        "accountName": account,
        "documentName": document,
        "message": (
            f"Chưa điền: giấy tờ tải lên là của {document}, còn tài khoản VNeID đang đăng nhập là của {account} (khối "
            f"Người đề nghị cổng khoá theo tài khoản). Vui lòng đăng nhập VNeID của {document} rồi làm lại, hoặc tải giấy "
            f"tờ đúng của {account}."
        ),
    }


def ocr_fallback(raw_fields, documents: list[dict]) -> dict:
    """compact_field_fallback: LLM có lượt bỏ sót mục 9 (đoạn dài) / ngày mất / số hộ chiếu dù OCR đọc đủ → field còn
    trống thì đọc thẳng từ chữ OCR của đơn trình báo."""
    if isinstance(raw_fields, dict):
        fields = dict(raw_fields)
    else:
        fields = {item.get("name"): item.get("value") for item in raw_fields or []
                  if isinstance(item, dict) and item.get("name")}
    for doc in documents or []:
        text = str(doc.get("text") or "")
        if not _REPORT_TITLE_RE.search(text):
            continue
        if not _paragraph(fields.get("DonTrinhBao_LyDo")):
            match = _REASON_RE.search(text)
            if match and _paragraph(match.group(1)):
                fields["DonTrinhBao_LyDo"] = _paragraph(match.group(1))
        if not _date(fields.get("DonTrinhBao_NgayMat")):
            match = _LOST_DATE_RE.search(text)
            if match:
                fields["DonTrinhBao_NgayMat"] = re.sub(r"\s", "", match.group(1))
        if not _text(fields.get("DonTrinhBao_SoHoChieu")):
            match = _LOST_NUMBER_RE.search(text)
            if match:
                fields["DonTrinhBao_SoHoChieu"] = match.group(1).replace(" ", "")
    return fields


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    if has_account_anchor(options):
        blocked = account_block(values, options)
        if blocked:
            return [], [blocked["message"]]
        warnings: list[str] = []
    else:
        warnings = [NO_ACCOUNT_WARNING]
    out: list[dict] = []
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

    has_report = any(key.startswith("DonTrinhBao_") for key in values)
    has_form = any(key.startswith("ToKhai_") for key in values)
    applicant, doc_id = _applicant(values)
    # Thẻ CCCD của người KHÁC (nộp nhầm thẻ người thân) → bỏ cả bộ Cccd_*.
    card_name, card_id = _text(values.get("Cccd_HoTen")), _id_number(values.get("Cccd_SoDinhDanh"))
    if (card_name or card_id) and (applicant or doc_id) and not (
            (card_id and card_id == doc_id) or (card_name and applicant and _same_person(card_name, applicant))):
        values = {key: value for key, value in values.items() if not key.startswith("Cccd_")}
        card_name = card_id = None
        warnings.append("Thẻ căn cước tải lên không phải của người trình báo ghi trong đơn — đã bỏ qua.")
    # Không bị chặn mà vẫn khác người → trẻ dưới 14 tuổi, cha / mẹ / người đại diện đăng nhập trình báo thay.
    other_person = _other_person(values, options)

    # ── Người đề nghị: ô mở (ngày cấp, nơi cấp CCCD, SĐT, email) — của CHỦ TÀI KHOẢN ──
    if other_person:
        account, document = other_person
        warnings.append(
            f"Giấy tờ là của {document} (dưới 14 tuổi), tài khoản VNeID đang đăng nhập là của {account} (người trình báo "
            f"thay) — chưa điền Ngày cấp, Nơi cấp CMND/CCCD, Số điện thoại, Email của người đề nghị: nhập tay theo "
            f"{account}; đính kèm giấy khai sinh / giấy tờ giám hộ vào dòng người đại diện hợp pháp."
        )
    else:
        form_id = _id_number(values.get("ToKhai_SoDinhDanh"))
        # Ngày cấp ở tờ khai chỉ dùng khi tờ khai cùng số định danh với đơn (hoặc không ghi số).
        issue_date = (_date(values.get("Cccd_NgayCap")) if card_id else None) or \
            (_date(values.get("ToKhai_NgayCap")) if not form_id or form_id == doc_id else None)
        add("CongDan__fsNgayCapCMND", issue_date)
        issuer = _issuer(values.get("Cccd_NoiCap")) if card_id or card_name else None
        if not issuer and issue_date and len(card_id or doc_id or "") == 12:
            issuer = default_issuer(issue_date)  # CMND 9 số do Công an tỉnh cũ cấp → không đoán
        add("CongDan__fsNoiCapCMND", issuer)
        if "CongDan__fsNgayCapCMND" not in seen:
            warnings.append("Giấy tờ không có ngày cấp CCCD (đơn trình báo không có mục này) — nhập tay ô Ngày cấp "
                            "ĐDCN/CMND (*), hoặc tải thêm ảnh thẻ căn cước hai mặt.")
        if "CongDan__fsNoiCapCMND" not in seen:
            warnings.append("Không xác định được nơi cấp CCCD — nhập tay ô Nơi cấp CMND/CCCD (*).")
        add("CongDan_diDong", _phone(values.get("DonTrinhBao_DienThoai")) or _phone(values.get("ToKhai_DienThoai")))
        add("CongDan_email", _email(values.get("ToKhai_Email")))
        if "CongDan_diDong" not in seen:
            warnings.append("Giấy tờ không có số điện thoại — ô Số điện thoại (*) cần nhập tay.")
        if "CongDan_email" not in seen:
            warnings.append(EMAIL_WARNING)

    # ── Địa chỉ nơi cư trú hiện nay ──
    area = _residence(values.get("DonTrinhBao_NoiCuTru"), values.get("ToKhai_ThuongTru"),
                      values.get("Cccd_NoiThuongTru"))
    if area:
        province = canonical_province(area.get("tinh")) or _shouting_fix(area.get("tinh"))
        add("CongDan__fs_BCATinhTamTru", province_label(province) or province if province else None)
        add("CongDan__fs_BCAXaTamTru", _shouting_fix(area.get("xa")))
        add("CongDan__fs_BCADiaChiTamTru", _plain(area.get("diaChi")))
    if has_report or has_form:
        if "CongDan__fs_BCAXaTamTru" not in seen:
            warnings.append("Không tách được tỉnh, xã của nơi cư trú hiện tại — chọn tay Tỉnh/Thành phố, Phường/Xã (*).")
        if "CongDan__fs_BCADiaChiTamTru" not in seen:
            warnings.append("Giấy tờ không ghi số nhà / thôn / tổ dân phố của nơi cư trú — nhập tay ô Địa chỉ chi tiết (*).")

    # ── Thông tin trình báo (đơn mục 7–9, dự phòng tờ khai mục 13 – 14) ──
    report_no = values.get("DonTrinhBao_SoHoChieu")
    passport = _passport_number(report_no)
    form_passport = _passport_number(values.get("ToKhai_HoChieuCu_So"))
    number = passport or (None if _not_remember(report_no) else form_passport)
    add("CongDan__fs_BCASoHoChieu", number)
    if _not_remember(report_no) and not number:
        warnings.append(NOT_REMEMBER_WARNING)
    if passport and form_passport and passport != form_passport:
        warnings.append(f"Số hộ chiếu ở đơn trình báo ({passport}) khác số hộ chiếu gần nhất ở tờ khai ({form_passport}) "
                        "— đã điền theo đơn, kiểm tra lại.")
    issued = _date(values.get("DonTrinhBao_NgayCapHoChieu"))
    if not issued and number and form_passport == number:  # ngày cấp mục 13 tờ khai chỉ khi cùng cuốn hộ chiếu
        issued = _date(values.get("ToKhai_HoChieuCu_NgayCap"))
    add("CongDan__fs_BCANgayCapHoChieu", issued)
    add("CongDan__fs_BCACoQuanCap", _text(values.get("DonTrinhBao_CoQuanCapHoChieu")))
    add("CongDan__fs_BCAThoiGianMatHC", _date(values.get("DonTrinhBao_NgayMat")))

    reason = _paragraph(values.get("DonTrinhBao_LyDo"))
    add("CongDan__fs_BCALyDoMatHC", reason)
    if not reason:
        request = _paragraph(values.get("ToKhai_NoiDungDeNghi"))
        if request and re.search(r"\bmat\b", fold(request)):
            add("CongDan__fs_BCALyDoMatHC", request)
            warnings.append(f"Không đọc được mục 9 đơn trình báo — ô Hoàn cảnh và lý do mất hộ chiếu (*) tạm lấy nội dung "
                            f"đề nghị của tờ khai (\"{request}\"); ghi rõ hoàn cảnh bị mất trước khi nộp.")
        else:
            warnings.append("Không đọc được hoàn cảnh, lý do mất hộ chiếu (mục 9 đơn trình báo) — nhập tay ô Hoàn cảnh và "
                            "lý do cụ thể mất hộ chiếu (*).")

    # ── Cảnh báo ──
    if has_report and not number and not _not_remember(report_no):
        warnings.append("Đơn trình báo không ghi số hộ chiếu bị mất — ô Số hộ chiếu bị mất (không bắt buộc) để trống; nhập "
                        "nếu người trình báo nhớ số.")
    kinh_gui = _plain(values.get("DonTrinhBao_KinhGui"))
    if kinh_gui and _COMMUNE_AGENCY_RE.search(fold(kinh_gui)):
        warnings.append(f"Đơn trình báo kính gửi \"{kinh_gui}\" (Công an cấp xã) trong khi thủ tục này nộp tại Phòng Quản "
                        "lý xuất nhập cảnh Công an tỉnh — kiểm tra lại nơi nộp hoặc chọn thủ tục cấp xã (1.010386).")
    warnings.append(AGENCY_WARNING)
    # ── Nơi tiếp nhận hồ sơ: ô 17 Cơ quan tiếp nhận (cuối form). Không đọc được gì → không phát riêng ô này. ──
    if out:
        out.append(agency_field())
    # Ô người đề nghị = chủ tài khoản VNeID: cổng đổ sẵn thì giữ nguyên, trống mới điền theo giấy (user 20/11/2026).
    keep_portal_values(out, ('CongDan_diDong', 'CongDan_email'))
    return out, warnings
